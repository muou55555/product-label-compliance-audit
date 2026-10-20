#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在华注册编号自动核查（Playwright 浏览器自动化兜底）
当平台没有 browser-task 等浏览器 skill 时，用本脚本独立完成：
  打开海关总署“进口食品境外生产企业注册信息”系统 → 自动填编号 → 查询
  → 抓取结果（国家/类别/企业/注册日期/有效期/状态）→ 截图 → 输出结构化 JSON。

官方查询页（编号直查免登录）：https://ciferquery.singlewindow.cn/
注意：官方数据接口直连会返回加密/重定向，故必须走浏览器，本脚本即用浏览器自动化替代手工 GUI。

依赖：
  pip install playwright
  playwright install chromium
用法：
  python query_customs.py CGEO23012201060023 [--out result.json] [--shot evidence.png] [--headed]
"""
import argparse, json, re, shutil, sys, datetime
from pathlib import Path

URL = "https://ciferquery.singlewindow.cn/"
TABLE = "#ciferMessStatVoList"
COLUMNS = ["no", "country", "category", "china_reg_no", "overseas_reg_no",
           "enterprise", "address", "reg_date", "exp_date", "state"]
INVALID_STATES = ("注销", "撤销", "暂停", "过期", "失效")
VALID_STATES = ("有效", "正常")


def decode_reg_no(reg_no):
    """解码在华注册编号：C + 国家码 + 类别码 + 注册日期(YYMMDD) + 顺序号。"""
    m = re.match(r"^C(?P<country>[A-Z]{2,3})(?P<cat>\d{4})"
                 r"(?P<date>\d{6})(?P<seq>\d{3,4})$", reg_no)
    if not m:
        return {"valid_format": False, "raw": reg_no}
    d = m.group("date")
    reg_date = f"20{d[0:2]}-{d[2:4]}-{d[4:6]}"
    return {
        "valid_format": True,
        "prefix": "C（在华注册标识）",
        "country_code": m.group("country"),
        "category_code": m.group("cat"),
        "reg_date": reg_date,
        "sequence": m.group("seq"),
    }


def find_executable():
    for name in ("chromium", "chromium-browser", "google-chrome",
                 "google-chrome-stable", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def classify(records):
    """依据结果状态给出判定。"""
    if not records:
        return "待核实", "官方系统未查到该编号，须核对编号真伪、企业与类别是否一致"
    r = records[0]
    st = r.get("state", "")
    if any(k in st for k in INVALID_STATES):
        return "不符合", f"状态为“{st}”，注册资格已失效，其产品不得进口/销售"
    if any(k in st for k in VALID_STATES):
        exp = r.get("exp_date", "")
        today = datetime.date.today().isoformat()
        if exp and exp < today:
            return "不符合", f"状态虽为“{st}”，但有效期至 {exp}，已届满"
        return "符合", f"状态为“{st}”且在有效期内（至 {exp}）"
    return "待核实", f"状态字段为“{st}”，须人工确认"


def query(reg_no, shot_path=None, headed=False, timeout=60):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "error": "缺少 playwright",
                "fix": "pip install playwright && playwright install chromium"}

    exe = find_executable()
    launch_kw = {"headless": not headed,
                 "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if exe:
        launch_kw["executable_path"] = exe

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kw)
            page = browser.new_page(viewport={"width": 1360, "height": 900})
            page.goto(URL, wait_until="networkidle", timeout=timeout * 1000)
            page.fill("#regCo", reg_no)
            page.click("button:has-text('查询')")
            try:
                page.wait_for_selector(f"{TABLE} tbody tr", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(1500)

            rows = page.locator(f"{TABLE} tbody tr")
            records = []
            n = rows.count()
            for i in range(n):
                cells = rows.nth(i).locator("td")
                vals = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
                rec = {}
                for k, v in zip(COLUMNS, vals[:len(COLUMNS)]):
                    rec[k] = v
                if rec.get("china_reg_no"):
                    records.append(rec)

            if shot_path:
                shot_path = Path(shot_path)
                if records:
                    try:
                        page.locator(TABLE).screenshot(path=str(shot_path))
                    except Exception:
                        page.screenshot(path=str(shot_path), full_page=True)
                else:
                    page.screenshot(path=str(shot_path), full_page=True)
            browser.close()
    except Exception as e:
        return {"ok": False, "error": f"浏览器执行失败：{e}",
                "fix": "确认网络可访问；或执行 playwright install chromium"}

    verdict, reason = classify(records)
    return {
        "ok": True,
        "reg_no": reg_no,
        "source": URL,
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "record_count": len(records),
        "records": records,
        "verdict": verdict,
        "verdict_reason": reason,
        "decoded": decode_reg_no(reg_no),
        "screenshot": str(shot_path) if shot_path else None,
        "open_items": [
            "核查该批次实际报关/启运日期是否早于有效期届满日",
            "有效期内已合法进口的库存能否销售，须属地海关/市场监管认定",
            "确认企业是否已重新注册取得新编号",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="在华注册编号自动核查（Playwright）")
    ap.add_argument("reg_no", help="在华注册编号，如 CGEO23012201060023")
    ap.add_argument("--out", help="结果 JSON 输出路径")
    ap.add_argument("--shot", help="证据截图输出路径(.png)")
    ap.add_argument("--headed", action="store_true", help="显示浏览器窗口")
    a = ap.parse_args()

    result = query(a.reg_no, a.shot, a.headed)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("已写出结果：", a.out)
    else:
        print(text)
    if not result.get("ok"):
        sys.exit(2)
    print(f"判定：{result.get('verdict')} —— {result.get('verdict_reason')}")


if __name__ == "__main__":
    main()
