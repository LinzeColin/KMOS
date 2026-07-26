# external_api_policy 操作流程说明（普通人版）

你的问题不是“哪些对象允许”，而是“我应该怎么操作”。IDS 的设计应该让你不需要逐个标记 chunk，只需要在数据源或文档层做选择。

## 1. 默认状态

所有新导入资料默认：

```text
external_api_policy = denied
```

意思是：

```text
不把原文、不把 chunk、不把客户资料发给外部 API。
```

## 2. 你在界面上会看到的位置

未来 IDS 的 人类产品入口 里应有：

```text
资料台账 → 选择某个数据源或某份文档 → 外部 API 策略
```

## 3. 你可以选三种策略

### denied：禁止外发

适合：

```text
客户资料
合同
报价
生产异常
未确认授权资料
你不确定能不能外发的资料
```

这是默认值。

### summary_only：只允许摘要外发

意思是：系统先在本地生成或保存简短摘要，然后只把摘要给外部模型，不发原文。

适合：

```text
你想省钱、想降低风险，但又希望借助外部模型做 embedding 或增强意见的资料。
```

### full_text_allowed：允许文本块外发

意思是：允许把文档的 chunk 发给外部 API 做 embedding 或处理。

只适合：

```text
公开资料
你自己写的资料
已确认不敏感的样例资料
明确允许外部处理的资料
```

## 4. 你实际怎么操作

未来界面应是这个流程：

```text
1. 打开资料台账。
2. 选择一个数据源或一份文档。
3. 点击“外部 API 策略”。
4. 系统显示当前状态：默认 denied。
5. 你选择 denied / summary_only / full_text_allowed。
6. 系统显示风险说明和预计成本。
7. 你填写原因，例如“公开资料，可用于 embedding”。
8. 点击确认。
9. 系统记录审计日志。
10. 该数据源或文档下面的 chunk 自动继承策略。
```

你不需要逐条标记 chunk。

## 5. 最安全的日常规则

如果你不确定，选：

```text
denied
```

如果你希望借助外部能力但不想发原文，选：

```text
summary_only
```

只有确定没有敏感内容时，才选：

```text
full_text_allowed
```

## 6. Codex 应实现的后台规则

```text
data_source.external_api_policy → document 自动继承 → chunk 自动继承
```

每次外发必须记录：

```text
谁授权
什么时候授权
授权原因
发给哪个 provider
使用哪个 model
发了多少 token
对应哪个 source/document/chunk
```

## 7. 你现在需要做什么

v0.1 开发阶段你只需要记住：

```text
默认都 denied。
等系统做好资料台账和外部 API 策略 UI 后，再逐个数据源或文档改策略。
```
