#!/usr/bin/env python3
"""与 ocr_with_vision.swift 同契约的 Python OCR 助手（TSK.KMFA.SKL.0005，云端替换）。

用法（由 generate_screenshot_ocr_sidecars.py 经 KMFA_FUND_VISION_OCR_COMMAND 调用）：
  python3 ocr_with_python.py <图片路径>...
stdout 契约（与 swift 版一致）：每图一行 JSON
  {"path": "<绝对路径>", "status": "ocr_text_available|no_text_from_engine|ocr_engine_error", "text": "...", "reason": "..."}

引擎链（有一个可用即可）：
  KMFA_FUND_PYOCR_ENGINES   默认 "rapidocr,tesseract"
    - rapidocr  : rapidocr_onnxruntime（PP-OCRv4 模型，onnxruntime 推理，linux-arm64 有轮子）
    - tesseract : pytesseract + 系统 tesseract-ocr（语言 KMFA_FUND_TESSERACT_LANG，默认 chi_sim+eng）
  KMFA_FUND_PYOCR_MIN_SCORE 默认 0.5（rapidocr 置信度过滤）

自检：python3 ocr_with_python.py --selftest
  用 PIL 合成含金额的中文图片走一遍引擎链；无可用引擎时 exit 3（SKIPPED）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _emit(path: str, status: str, text: str = "", reason: str = "") -> None:
    print(json.dumps({"path": path, "status": status, "text": text, "reason": reason}, ensure_ascii=False), flush=True)


class EngineUnavailable(Exception):
    pass


def _engine_rapidocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise EngineUnavailable(f"rapidocr_onnxruntime 不可用: {exc.__class__.__name__}") from exc
    ocr = RapidOCR()
    min_score = float(os.environ.get("KMFA_FUND_PYOCR_MIN_SCORE", "0.5"))

    def run(image_path: Path) -> str:
        result, _elapse = ocr(str(image_path))
        if not result:
            return ""
        lines = [str(text) for _box, text, score in result if float(score) >= min_score and str(text).strip()]
        return "\n".join(lines).strip()

    return run, "rapidocr_onnxruntime(PP-OCRv4)"


def _engine_tesseract():
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise EngineUnavailable(f"pytesseract/PIL 不可用: {exc.__class__.__name__}") from exc
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:  # noqa: BLE001 - 任何原因不可用都降级
        raise EngineUnavailable(f"tesseract 二进制不可用: {exc.__class__.__name__}") from exc
    lang = os.environ.get("KMFA_FUND_TESSERACT_LANG", "chi_sim+eng")

    def run(image_path: Path) -> str:
        with Image.open(image_path) as image:
            return (pytesseract.image_to_string(image, lang=lang) or "").strip()

    return run, f"tesseract({lang})"


_ENGINE_FACTORIES = {"rapidocr": _engine_rapidocr, "tesseract": _engine_tesseract}


def load_engine_chain() -> list[tuple]:
    order = [name.strip() for name in os.environ.get("KMFA_FUND_PYOCR_ENGINES", "rapidocr,tesseract").split(",") if name.strip()]
    chain, errors = [], []
    for name in order:
        factory = _ENGINE_FACTORIES.get(name)
        if factory is None:
            errors.append(f"未知引擎 {name}")
            continue
        try:
            chain.append(factory())
        except EngineUnavailable as exc:
            errors.append(str(exc))
    if not chain:
        raise EngineUnavailable("; ".join(errors) or "引擎链为空")
    return chain


def ocr_paths(paths: list[str]) -> int:
    try:
        chain = load_engine_chain()
    except EngineUnavailable as exc:
        for raw in paths:
            _emit(str(Path(raw).expanduser()), "ocr_engine_error", reason=f"python OCR 引擎链不可用: {exc}")
        return 0
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.is_file():
            _emit(str(path), "ocr_engine_error", reason="source image not found")
            continue
        text, last_reason = "", ""
        for run, label in chain:
            try:
                text = run(path)
            except Exception as exc:  # noqa: BLE001 - 单图失败换下一引擎
                last_reason = f"{label} 失败: {exc.__class__.__name__}"
                continue
            if text:
                _emit(str(path), "ocr_text_available", text=text, reason=label)
                break
            last_reason = f"{label} 未识别出文本"
        if not text:
            _emit(str(path), "no_text_from_engine", reason=last_reason)
    return 0


def selftest() -> int:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("SELFTEST SKIPPED: 本机无 PIL（容器内执行验收）", file=sys.stderr)
        return 3
    try:
        chain = load_engine_chain()
    except EngineUnavailable as exc:
        print(f"SELFTEST SKIPPED: 无可用 OCR 引擎（{exc}）——容器内执行验收", file=sys.stderr)
        return 3
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "sample.png"
        image = Image.new("RGB", (640, 160), "white")
        draw = ImageDraw.Draw(image)
        draw.text((20, 40), "Payment 1234.56 CNY 2026-07-17", fill="black")
        image.save(image_path)
        for run, label in chain:
            text = run(image_path)
            assert "1234" in text.replace(",", "").replace(" ", ""), f"{label} 未识别出金额数字: {text!r}"
            print(f"SELFTEST PASS [{label}]: {text!r}")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    if args[0] == "--selftest":
        return selftest()
    return ocr_paths(args)


if __name__ == "__main__":
    raise SystemExit(main())
