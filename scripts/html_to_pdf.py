#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 转 PDF：优先用本机 headless Chromium / Chrome（打印样式已在报告内）。
用法：python3 html_to_pdf.py report.html report.pdf
也可改用 Playwright：page.pdf(path=..., format='A4', print_background=True)
"""
import os
import shutil
import subprocess
import sys


def find_browser():
    for name in ("chromium", "chromium-browser", "google-chrome",
                 "google-chrome-stable"):
        p = shutil.which(name)
        if p:
            return p
    return None


def main():
    if len(sys.argv) != 3:
        print("用法: python3 html_to_pdf.py <input.html> <output.pdf>")
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    browser = find_browser()
    if not browser:
        print("未找到 Chromium/Chrome，请安装或改用 Playwright。")
        sys.exit(2)

    subprocess.run([
        browser, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", f"--print-to-pdf={dst}",
        "file://" + src,
    ], check=True)
    print("已生成：", dst)


if __name__ == "__main__":
    main()
