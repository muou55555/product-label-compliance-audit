#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告证据完整性校验（交付前确定性闸门）。

用途：用户上传多张产品标签图时，确保生成的 HTML 把**每一张**都嵌入并显示，
而不是只显示其中一张。报告生成后、交付前运行本脚本。

检查：
  1) 统计 HTML 中 <img> 数量（含 data URI 内嵌图）；
  2) 与期望数量比对（--expect N，或 --manifest 列出源图，取其条目数）；
  3) 每张 data URI 可解码且非空（防止损坏/空图）；
  4) 输出缺失数量，退出码 0/1。

用法：
  python3 check_report_evidence.py 报告.html --expect 3
  python3 check_report_evidence.py 报告.html --manifest sources.json
  # sources.json 可为 {"images": ["a.png","b.png", ...]} 或 LabelFacts 附件清单
"""
from __future__ import annotations
import argparse, base64, json, re, sys
from pathlib import Path

IMG_RE = re.compile(r"<img\b[^>]*?\bsrc=\"([^\"]+)\"", re.IGNORECASE)


def count_images(html: str):
    imgs = []
    for m in IMG_RE.finditer(html):
        src = m.group(1)
        ok, size = True, None
        if src.startswith("data:image/"):
            b64 = src.split(",", 1)[1] if "," in src else ""
            try:
                raw = base64.b64decode(b64)
                size = len(raw)
                ok = size > 0
            except Exception:
                ok, size = False, 0
        imgs.append({"src_head": src[:24], "embedded": ok, "bytes": size})
    return imgs


def expected_count(manifest: str):
    if not manifest:
        return None
    d = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if isinstance(d, dict):
        for key in ("images", "attachments", "source_images", "files"):
            if isinstance(d.get(key), list):
                return len(d[key])
    if isinstance(d, list):
        return len(d)
    return None


def main():
    ap = argparse.ArgumentParser(description="报告证据完整性校验")
    ap.add_argument("html")
    ap.add_argument("--expect", type=int, default=None,
                    help="期望嵌入的图片数量（至少）")
    ap.add_argument("--manifest", default=None,
                    help="源图清单 JSON（取其 images 条目数）")
    a = ap.parse_args()

    text = Path(a.html).read_text(encoding="utf-8")
    imgs = count_images(text)
    exp = a.expect if a.expect is not None else expected_count(a.manifest)

    bad = [i for i in imgs if not i["embedded"]]
    print(f"报告内嵌图片数：{len(imgs)}（损坏/空图 {len(bad)}）")
    if exp is not None:
        print(f"源图/期望图片数：{exp}")
        if len(imgs) < exp:
            print(f"缺失：{exp - len(imgs)} 张未嵌入报告")
    if bad:
        for b in bad:
            print("  损坏/空图：", b["src_head"])
    passed = (not bad) and (exp is None or len(imgs) >= exp)
    print("校验：通过" if passed else "校验：不通过（须补全证据图）")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
