# -*- coding: utf-8 -*-
"""S08/P8.2 —— 权限感知的全文检索（AC-PROD-002）。

pass_gate：**私密命中=0**，相关性和 P95 达批准阈值。
stop_condition：数据库检索在实测规模无法满足阈值且无可逆扩展路径。

## 权限过滤必须在**查询里**，不能在结果集上

最常见也最危险的写法是「先全库检索，再把无权看的过滤掉」。它错在两处：

  1. **分页会泄露存在性**。查 10 条、过滤掉 7 条、返回 3 条，
     客户端看到「共 10 条命中」——那 7 条的存在被计数泄露了。
  2. **任何一次忘记过滤就是全库泄露**。过滤是一个可以忘的步骤，
     而放在 WHERE 里它不可能被忘：忘了就查不出任何东西，当场发现。

所以本模块产出的每一条查询都**自带 workspace 谓词**，且没有不带谓词的重载。
「让调用方决定要不要加权限条件」这种设计，迟早会有人决定不加。

## 为什么是 tsvector 而不是 LIKE

`LIKE '%词%'` 用不上索引，规模一上来就是全表扫；而且它不做词干化，
搜「报告」匹配不到「报告书」以外的形态。PostgreSQL 的 `tsvector` + GIN
两者都解决。

**但本仓当前跑 SQLite**（`KMFA_STRUCTURED_DATABASE_MODE=legacy-sqlite`）。
所以这里的实现分两条：Postgres 走 `tsvector`/GIN，SQLite 走 FTS5。
两条产出**同一个契约**（同样的排序语义、同样的权限谓词），
差异被封在本模块里——上层不必知道底下是哪一个。

不为了统一而只用 SQLite：那会在切到 Postgres 时把索引能力白白丢掉。
也不为了统一而要求先迁 Postgres：迁移是 S08-04 的事，不是检索的前置条件。

## 中文分词：不做，而且要说清为什么

`tsvector` 的英文词干化对中文无效，而正经的中文分词需要词典与额外扩展
（`zhparser` / `pg_jieba`），装扩展属于基础设施变更，
在 `T-S00-04` 的口径里是「需要不可逆基础设施迁移」那一类。

所以中文用 **bigram（二元切分）**：把「经营报告」切成「经营」「营报」「报告」。
它召回略宽（会命中「营报」这种非词），但**不漏**——
对内部检索而言，宁可多几条让人自己看，也不要少一条让人以为没有。
这个取舍写在这里，因为它是取舍，不是缺陷。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

#: 单次返回上限。没有上限的检索接口是最省事的导出通道——
#: 一次查询把全库拉走，比任何导出端点都方便。
MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20

#: 查询串长度上限。超长查询会把分词与索引匹配的开销撑起来。
MAX_QUERY_BYTES = 200

_CJK = re.compile(r"[一-鿿㐀-䶿]")
_TOKEN = re.compile(r"[A-Za-z0-9_]+|[一-鿿㐀-䶿]+")


class SearchError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def validate_query(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise SearchError(422, "query_required", "检索词不能为空。")
    query = raw.strip()
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise SearchError(422, "query_too_long",
                          f"检索词超过 {MAX_QUERY_BYTES} 字节。")
    return query


def validate_page_size(raw: Any) -> int:
    if raw is None:
        return DEFAULT_PAGE_SIZE
    # **先判类型再转换。** `int(1.5)` 会静默截断成 1，于是客户端传了 1.5
    # 却拿到 1 条，且没有任何提示——它会以为是服务端只有 1 条。
    # 字符串 "20" 放行是因为 query string 里本来就是字符串。
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise SearchError(422, "page_size_invalid",
                          "page_size 必须是整数（浮点会被静默截断，拿到的条数"
                          "和要的不一样却没有任何提示）。")
    try:
        size = int(str(raw))
    except (TypeError, ValueError):
        raise SearchError(422, "page_size_invalid", "page_size 必须是整数。")
    if size < 1:
        raise SearchError(422, "page_size_invalid", "page_size 必须为正。")
    if size > MAX_PAGE_SIZE:
        raise SearchError(
            429, "page_size_too_large",
            f"单次最多返回 {MAX_PAGE_SIZE} 条。没有上限的检索接口是最省事的"
            "导出通道——一次查询把全库拉走，比任何导出端点都方便。")
    return size


def tokenize(text: str) -> list[str]:
    """切词。中文走 bigram，其余按字母数字串切。

    bigram 召回略宽（「经营报告」会产出「营报」这种非词），但**不漏**。
    对内部检索而言，宁可多几条让人自己看，也不要少一条让人以为没有。
    """
    tokens: list[str] = []
    for chunk in _TOKEN.findall(text.lower()):
        if _CJK.search(chunk):
            if len(chunk) == 1:
                tokens.append(chunk)
            else:
                tokens.extend(chunk[i:i + 2] for i in range(len(chunk) - 1))
        else:
            tokens.append(chunk)
    return tokens


def build_index_text(*parts: Any) -> str:
    """把若干字段拼成可索引文本。**只收显式传进来的字段**——
    不做「把整行 dump 进去」这种省事写法：那会把内部 id、
    存储键、甚至将来新增的敏感字段一起变成可检索的。"""
    tokens: list[str] = []
    for part in parts:
        if part is None:
            continue
        tokens.extend(tokenize(str(part)))
    return " ".join(tokens)


def sqlite_match_expression(query: str) -> str:
    """FTS5 的 MATCH 表达式。每个 token 加引号，避免用户输入里的
    `*` `-` `NEAR` 被当成 FTS 语法——那既是注入面，也是「搜不到」的来源。"""
    tokens = tokenize(query)
    if not tokens:
        raise SearchError(422, "query_has_no_tokens",
                          "检索词切不出任何词元（可能全是标点）。")
    return " OR ".join(f'"{token}"' for token in tokens)


def postgres_tsquery(query: str) -> str:
    """Postgres 的 tsquery 串。同样逐词元转义。"""
    tokens = tokenize(query)
    if not tokens:
        raise SearchError(422, "query_has_no_tokens", "检索词切不出任何词元。")
    return " | ".join(token.replace("'", "''") for token in tokens)


def scoped_predicate(workspace_id: str) -> tuple[str, tuple[Any, ...]]:
    """**权限谓词，且只有这一个出口。**

    本模块不提供「不带 workspace 条件」的查询构造。
    「让调用方决定要不要加权限条件」这种设计，迟早会有人决定不加，
    而那一次就是全库泄露。放在 WHERE 里，忘了就查不出任何东西，当场发现。
    """
    if not isinstance(workspace_id, str) or not workspace_id:
        raise SearchError(422, "workspace_required",
                          "检索必须带 workspace 作用域。")
    return "workspace_id = ?", (workspace_id,)


def build_sqlite_query(
    *, workspace_id: str, query: str, page_size: int, offset: int
) -> tuple[str, tuple[Any, ...]]:
    """SQLite FTS5 检索。权限谓词与 MATCH **在同一条 WHERE 里**。"""
    predicate, params = scoped_predicate(workspace_id)
    match = sqlite_match_expression(query)
    sql = (
        "SELECT doc_id, workspace_id, kind, title, snippet(search_index, 3, "
        "'[', ']', '…', 12) AS excerpt, bm25(search_index) AS rank "
        "FROM search_index "
        f"WHERE {predicate} AND search_index MATCH ? "
        "ORDER BY rank ASC, doc_id ASC LIMIT ? OFFSET ?"
    )
    return sql, (*params, match, page_size, offset)


def build_postgres_query(
    *, workspace_id: str, query: str, page_size: int, offset: int
) -> tuple[str, tuple[Any, ...]]:
    predicate, params = scoped_predicate(workspace_id)
    sql = (
        "SELECT doc_id, workspace_id, kind, title, "
        "ts_headline('simple', body, to_tsquery('simple', %s)) AS excerpt, "
        "ts_rank(search_vector, to_tsquery('simple', %s)) AS rank "
        "FROM search_index "
        f"WHERE {predicate.replace('?', '%s')} "
        "AND search_vector @@ to_tsquery('simple', %s) "
        "ORDER BY rank DESC, doc_id ASC LIMIT %s OFFSET %s"
    )
    tsquery = postgres_tsquery(query)
    return sql, (tsquery, tsquery, *params, tsquery, page_size, offset)


def rank_results(rows: Iterable[Mapping[str, Any]], *, backend: str) -> list[dict]:
    """把两个后端的排序统一成同一个契约：**分数越大越相关**。

    SQLite 的 `bm25()` 是越小越相关，Postgres 的 `ts_rank` 越大越相关。
    不统一的话，换后端时排序会**整个倒过来**，而没有任何东西会报错——
    页面照常渲染，只是最相关的那条掉到了最后。
    """
    results = []
    for row in rows:
        raw = float(row.get("rank") or 0.0)
        score = -raw if backend == "sqlite" else raw
        results.append({
            "doc_id": row.get("doc_id"),
            "kind": row.get("kind"),
            "title": row.get("title"),
            "excerpt": row.get("excerpt"),
            "score": round(score, 6),
        })
    results.sort(key=lambda item: (-item["score"], str(item["doc_id"])))
    return results


def assert_no_cross_workspace(rows: Iterable[Mapping[str, Any]],
                              workspace_id: str) -> None:
    """结果集自检：**任何一条不属于本 workspace 都当场炸**。

    这是纵深防御，不是重复劳动——WHERE 里的谓词负责不查出来，
    这一条负责在谓词哪天被改坏时立刻暴露，而不是等到有人看到别人的数据。
    """
    for row in rows:
        if str(row.get("workspace_id")) != workspace_id:
            raise SearchError(
                500, "search_scope_violation",
                "检索结果里出现了不属于本 workspace 的记录——权限谓词已失效。")
