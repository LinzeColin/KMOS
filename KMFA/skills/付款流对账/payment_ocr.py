#!/usr/bin/env python3
"""macOS Vision 本机 OCR。

刻意不用视觉模型：读错一个金额会把真问题静默抵扣掉，比读不出来严重得多。
本机、确定性、不联网。

`setRecognitionLevel_` 的取值是 **0=accurate、1=fast**，别搞反 ——
2026-09-09 传成 1，把 41,516.05 读成了 41.51&05。
依赖 pyobjc，装的时候必须 `pip install --only-binary=:all:`（源码编译会失败）。
"""
import os, sys

VENV_PY = os.path.expanduser("~/.local/share/kmfa-payment-alert/venv/bin/python")


def ocr_file(path):
    import Vision, Quartz
    from Foundation import NSURL
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    if src is None:
        return ""
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if img is None:
        return ""
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0)                 # 0 = accurate
    req.setUsesLanguageCorrection_(False)
    req.setRecognitionLanguages_(["zh-Hans", "en-US"])
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None)
    ok, _ = handler.performRequests_error_([req], None)
    if not ok:
        return ""
    lines = []
    for obs in (req.results() or []):
        c = obs.topCandidates_(1)
        if c and len(c):
            lines.append(str(c[0].string()))
    return "\n".join(lines)


def main():
    for p in sys.argv[1:]:
        print("<<<FILE>>>" + p)
        try:
            print(ocr_file(p))
        except Exception as exc:
            print(f"<<<ERROR>>>{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
