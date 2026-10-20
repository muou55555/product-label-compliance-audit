#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置标准 PDF 读取/检索工具。用户无需上传标准。

子命令：
  list                         列出内置标准与页数/文字层
  search <关键词> [--std ID]   全文检索（仅文字层PDF），返回页码与片段
  page   <ID> <页码>           输出某页文本（扫描件提示用 render）
  render <ID> <页码> [-o out.png]  渲染页面为图片（扫描件视觉读取）

依赖：PyMuPDF(pip install pymupdf)
"""
import argparse
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD_DIR = os.path.join(ROOT, "standards")
MANIFEST = os.path.join(STD_DIR, "standards_manifest.yaml")


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return yaml.safe_load(f)["standards"]


def _open(spec):
    import fitz
    return fitz.open(os.path.join(STD_DIR, spec["file"]))


def cmd_list(args):
    for sid, s in load_manifest().items():
        layer = "文字层" if s["text_layer"] else "扫描件(需视觉)"
        print(f"{sid:10} {s['title']}  {s['version']}  "
              f"{s['pages']}页  {layer}  -> {s['file']}")


def cmd_search(args):
    import fitz
    found = 0
    for sid, spec in load_manifest().items():
        if args.std and sid != args.std:
            continue
        if not spec["text_layer"]:
            continue
        doc = _open(spec)
        for i, page in enumerate(doc):
            text = page.get_text()
            if args.keyword in text:
                snippet = text.replace("\n", " ")
                pos = snippet.find(args.keyword)
                print(f"[{sid} 第{i+1}页] …{snippet[max(0,pos-30):pos+60]}…")
                found += 1
    if not found:
        print("未命中（扫描件 GB-T15037 请用 render 视觉读取）。")


def cmd_page(args):
    spec = load_manifest()[args.std]
    doc = _open(spec)
    text = doc[args.page - 1].get_text()
    if not text.strip():
        print("该页无文字层，请使用 render 渲染后视觉读取。")
        return
    print(text)


def cmd_render(args):
    import fitz
    spec = load_manifest()[args.std]
    doc = _open(spec)
    page = doc[args.page - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    out = args.output or f"{args.std}_p{args.page}.png"
    pix.save(out)
    print("已渲染：", out)


def main():
    ap = argparse.ArgumentParser(description="内置标准读取")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.add_argument("--std", default="")
    s.set_defaults(func=cmd_search)

    p = sub.add_parser("page")
    p.add_argument("std")
    p.add_argument("page", type=int)
    p.set_defaults(func=cmd_page)

    r = sub.add_parser("render")
    r.add_argument("std")
    r.add_argument("page", type=int)
    r.add_argument("-o", "--output", default="")
    r.set_defaults(func=cmd_render)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
