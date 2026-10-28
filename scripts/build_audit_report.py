#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
产品标签合规审核 —— 甲方正式报告生成器（公文模板版）
输出自包含 HTML（证据图以 base64 内嵌），再用 html_to_pdf.py 转 PDF。

数据结构见 audit_input.example.json。渲染口径：
- 封面 + 元信息表；
- 一 审核结论（判定框 + 分类统计表）；
- 二 审核范围/方法/依据；三 标签标示信息；
- 四 审核发现（卡片：严重不符合/不规范/待检测核验/风险提示）；
- 五 符合项汇总；六 整改建议；证据图；签字与声明。
"""
import argparse, base64, html, json, os, re
from pathlib import Path

CSS = """
  :root{
    --navy:#1F3864; --navy-d:#16294D; --paper:#FFFFFF; --bg:#EEF0F4;
    --line:#D9DDE5; --line-d:#B9C1CF;
    --red:#A52823; --red-bg:#F8ECEB;
    --amber:#8A5A00; --amber-bg:#F7F0DE;
    --blue:#1F4E79; --blue-bg:#EAF0F7;
    --green:#2E6B35; --green-bg:#EAF3EB;
    --ink:#1C1F26; --sub:#5B6370;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:'Noto Serif CJK SC','Songti SC','SimSun',serif;
    font-size:14.5px;line-height:1.75;}
  .wrap{max-width:960px;margin:0 auto;padding:0 0 56px;background:var(--paper);
    box-shadow:0 0 0 1px var(--line);}
  .sans{font-family:'Noto Sans CJK SC','Microsoft YaHei','PingFang SC',sans-serif;}
  .cover{background:var(--navy);color:#fff;padding:34px 44px 26px;}
  .cover .kicker{font-size:12.5px;letter-spacing:4px;opacity:.82;}
  .cover h1{font-size:27px;margin:10px 0 4px;letter-spacing:2px;font-weight:700;}
  .cover .sub{font-size:13px;opacity:.85;}
  .meta{margin:0;padding:0;list-style:none;}
  .meta-row{display:flex;flex-wrap:wrap;border-bottom:1px solid var(--line);}
  .meta-row:last-child{border-bottom:none;}
  .meta-cell{flex:1 1 46%;padding:10px 14px;font-size:13.5px;}
  .meta-cell:nth-child(odd){border-right:1px solid var(--line);}
  .meta-cell .k{color:var(--sub);display:inline-block;min-width:96px;}
  .body{padding:8px 44px 0;}
  h2{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif;
    font-size:17.5px;color:var(--navy);margin:34px 0 12px;padding-bottom:7px;
    border-bottom:2px solid var(--navy);letter-spacing:1px;}
  h3{font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif;
    font-size:14.5px;margin:20px 0 8px;color:var(--ink);}
  p{margin:8px 0;}
  .small{font-size:12.5px;color:var(--sub);}
  table{width:100%;border-collapse:collapse;font-size:13.5px;margin:8px 0;}
  th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top;}
  th{background:#F3F5F9;font-family:'Noto Sans CJK SC',sans-serif;font-weight:600;color:var(--navy-d);}
  .badge{display:inline-block;padding:1px 10px;border-radius:3px;font-size:12px;
    font-family:'Noto Sans CJK SC',sans-serif;font-weight:600;white-space:nowrap;}
  .b-red{background:var(--red-bg);color:var(--red);border:1px solid #E2B8B5;}
  .b-amber{background:var(--amber-bg);color:var(--amber);border:1px solid #E3D3A8;}
  .b-blue{background:var(--blue-bg);color:var(--blue);border:1px solid #B9CCE0;}
  .b-green{background:var(--green-bg);color:var(--green);border:1px solid #B8D3BC;}
  .stat td:first-child{text-align:center;}
  .stat td:nth-child(2){text-align:center;font-family:'Noto Sans CJK SC',sans-serif;font-weight:700;}
  .nc{border:1px solid var(--line-d);border-radius:6px;margin:14px 0;overflow:hidden;}
  .nc.sev-red{border-left:5px solid var(--red);}
  .nc.sev-amber{border-left:5px solid var(--amber);}
  .nc.sev-blue{border-left:5px solid var(--blue);}
  .nc.sev-green{border-left:5px solid var(--green);}
  .nc-head{padding:11px 16px;background:#F7F8FA;border-bottom:1px solid var(--line);}
  .nc-head .no{font-family:'Noto Sans CJK SC',sans-serif;font-weight:700;color:var(--navy);margin-right:10px;}
  .nc-head .t{font-family:'Noto Sans CJK SC',sans-serif;font-weight:600;font-size:14.5px;}
  .kv{margin:0;}
  .kv th{width:96px;background:#FAFBFC;text-align:center;font-weight:600;}
  .kv tr:last-child th,.kv tr:last-child td{border-bottom:none;}
  .law{background:#F3F5F9;border-left:3px solid var(--navy);padding:6px 12px;margin:5px 0;
    font-size:13px;border-radius:0 4px 4px 0;}
  .law .src{font-family:'Noto Sans CJK SC',sans-serif;color:var(--navy);font-weight:600;}
  ul{margin:6px 0;padding-left:22px;} li{margin:4px 0;}
  .mono{font-family:Consolas,Menlo,monospace;}
  img.shot{width:100%;border:1px solid var(--line);border-radius:4px;display:block;}
  .figcap{font-size:12.5px;color:var(--sub);margin:6px 0 18px;text-align:center;}
  .sign{margin-top:40px;display:flex;flex-wrap:wrap;gap:18px;}
  .sign .cell{flex:1 1 220px;font-size:14px;}
  .sign .line{display:inline-block;min-width:150px;border-bottom:1px solid var(--ink);height:1.4em;}
  .decl{margin-top:30px;border-top:1px solid var(--line);padding-top:14px;}
  .decl li{font-size:12.5px;color:var(--sub);}
  .verdict{border-radius:6px;padding:12px 18px;margin:10px 0;}
  .verdict .vtext{margin-left:8px;font-family:'Noto Sans CJK SC',sans-serif;font-weight:600;}
  @media print{
    body{background:#fff;} .wrap{box-shadow:none;max-width:100%;padding-bottom:0;}
    .nc,.sign,.verdict,.law,.stat,.figcap,img.shot{page-break-inside:avoid;}
    h2,h3{page-break-after:avoid;}
  }
"""


def inline(t):
    """安全行内：转义后支持 **粗体**、`代码`。"""
    if t is None:
        return ""
    s = html.escape(str(t))
    s = re.sub(r'`([^`]+)`', r'<span class="mono">\1</span>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def img_data(path, base):
    p = Path(path)
    if not p.is_absolute():
        p = Path(base) / p
    b = p.read_bytes()
    ext = p.suffix.lower().lstrip('.') or 'jpeg'
    if ext == 'jpg':
        ext = 'jpeg'
    return f"data:image/{ext};base64," + base64.b64encode(b).decode()


def render_meta(meta):
    rows = []
    for r in meta:
        cells = "".join(
            f'<div class="meta-cell"><span class="k">{inline(x.get("k"))}</span>{inline(x.get("v"))}</div>'
            for x in r.get("cells", []))
        rows.append(f'<li class="meta-row">{cells}</li>')
    return '<ul class="meta">' + "".join(rows) + '</ul>'


def render_verdict(v):
    color = v.get("color", "red")
    border = {"red": "#E2B8B5", "amber": "#E3D3A8", "blue": "#B9CCE0",
              "green": "#B8D3BC"}.get(color, "#E2B8B5")
    return (f'<div class="verdict" style="border:1px solid {border};background:var(--{color}-bg);">'
            f'<span class="badge b-{color}">{inline(v.get("badge"))}</span>'
            f'<span class="vtext" style="color:var(--{color});">{inline(v.get("text"))}</span></div>')


def render_stats(stats):
    rows = ['<tr><th style="width:26%;">审核分类</th><th style="width:12%;">数量</th><th>主要内容</th></tr>']
    for s in stats:
        rows.append(
            f'<tr><td><span class="badge b-{s.get("color","blue")}">{inline(s.get("cat"))}</span></td>'
            f'<td>{inline(s.get("count"))}</td><td>{inline(s.get("content"))}</td></tr>')
    return '<table class="stat">' + "".join(rows) + '</table>'


def render_law_rows(rows):
    parts = []
    for r in rows:
        kind = r.get("kind", "html")
        if kind == "laws":
            body = "".join(
                f'<div class="law"><span class="src">{inline(l.get("src"))}</span>{inline(l.get("text"))}</div>'
                for l in r.get("laws", []))
        elif kind == "list":
            body = '<ul>' + "".join(f'<li>{inline(x)}</li>' for x in r.get("items", [])) + '</ul>'
        else:
            body = inline(r.get("html"))
        parts.append(f'<tr><th>{inline(r.get("th"))}</th><td>{body}</td></tr>')
    return '<table class="kv">' + "".join(parts) + '</table>'


def render_findings(groups):
    out = []
    for g in groups:
        out.append(f'<h3>{inline(g.get("heading"))}</h3>')
        if g.get("note"):
            out.append(f'<p class="small">{inline(g.get("note"))}</p>')
        for it in g.get("items", []):
            color = it.get("color", "amber")
            head = (f'<div class="nc-head"><span class="no">{inline(it.get("no"))}</span>'
                    f'<span class="badge b-{color}">{inline(it.get("badge"))}</span>'
                    f'<span class="t">{inline(it.get("title"))}</span></div>')
            out.append(f'<div class="nc sev-{color}">{head}{render_law_rows(it.get("rows", []))}</div>')
    return "".join(out)


def render_facts(facts):
    head = ('<tr><th style="width:18%;">标示项目</th><th style="width:32%;">标示内容</th>'
            '<th style="width:18%;">标示项目</th><th>标示内容</th></tr>')
    rows = []
    for r in facts:
        rows.append('<tr>' + "".join(f'<td>{inline(r.get(k))}</td>' for k in ("a", "b", "c", "d")) + '</tr>')
    return '<table>' + head + "".join(rows) + '</table>'


def render_table2(rows, heads):
    th = "".join(f'<th style="{h.get("style","")}">{inline(h.get("t"))}</th>' for h in heads)
    trs = []
    for r in rows:
        cells = "".join(f'<td>{inline(x)}</td>' for x in r.get("cells", []))
        trs.append(f'<tr>{cells}</tr>')
    return '<table><tr>' + th + '</tr>' + "".join(trs) + '</table>'


def build(data, base):
    cover = data.get("cover", {})
    cc = data.get("conclusion", {})
    parts = [f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{inline(cover.get("title"))}</title><style>{CSS}</style></head>
<body><div class="wrap">
  <div class="cover">
    <div class="kicker sans">{inline(cover.get("kicker"))}</div>
    <h1 class="sans">{inline(cover.get("title"))}</h1>
    <div class="sub sans">{inline(cover.get("subtitle"))}</div>
  </div>
  {render_meta(data.get("meta", []))}
  <div class="body">
''']
    parts.append(f'<h2>一、审核结论</h2><p>{inline(cc.get("intro"))}</p>')
    parts.append(render_verdict(cc.get("verdict", {})))
    parts.append(render_stats(cc.get("stats", [])))

    s = data.get("scope", {})
    parts.append('<h2>二、审核范围、方法与依据</h2>')
    parts.append(f'<h3>（一）审核范围</h3><p>{inline(s.get("scope"))}</p>')
    parts.append('<h3>（二）审核方法</h3><ul>' +
                 "".join(f'<li>{inline(m)}</li>' for m in s.get("methods", [])) + '</ul>')
    parts.append('<h3>（三）审核依据</h3>')
    std_rows = [{'cells': [x.get("name"), x.get("code")]} for x in s.get("standards", [])]
    parts.append(render_table2(std_rows, [
        {'t': '文件名称', 'style': 'width:34%;'}, {'t': '文号／编号'}]))

    f = data.get("facts", {})
    parts.append('<h2>三、标签标示信息</h2>')
    parts.append(f'<p class="small">{inline(f.get("note"))}</p>')
    parts.append(render_facts(f.get("rows", [])))
    if f.get("extra"):
        parts.append(f'<p class="small">{inline(f.get("extra"))}</p>')

    parts.append('<h2>四、审核发现</h2>')
    parts.append(render_findings(data.get("findings", {}).get("groups", [])))

    comp = data.get("compliant", {})
    parts.append('<h2>五、符合项汇总</h2>')
    parts.append(f'<p>{inline(comp.get("intro"))}</p>')
    comp_rows = [{'cells': [x.get("no"), x.get("item"), x.get("detail"), x.get("basis")]}
                 for x in comp.get("items", [])]
    parts.append(render_table2(comp_rows, [
        {'t': '序号', 'style': 'width:8%;'}, {'t': '核查项目', 'style': 'width:26%;'},
        {'t': '核查情况'}, {'t': '依据', 'style': 'width:18%;'}]))

    parts.append('<h2>六、整改与处置建议</h2><ul>' +
                 "".join(f'<li>{inline(x)}</li>' for x in data.get("recommendations", [])) + '</ul>')

    parts.append('<h2>证据</h2>')
    for ev in data.get("evidence", []):
        parts.append(f'<img class="shot" src="{img_data(ev.get("path"), base)}">')
        parts.append(f'<div class="figcap">{inline(ev.get("caption"))}</div>')

    sign = data.get("sign", {})
    parts.append(f'''<div class="sign">
    <div class="cell">审核人（签字）：<span class="line"></span></div>
    <div class="cell">审核单位（盖章）：<span class="line"></span></div>
    <div class="cell">出具日期：<span class="line" style="min-width:110px;">{inline(sign.get("date"))}</span></div>
  </div>
  <div class="decl"><p class="small sans" style="font-weight:600;">声明：</p><ul>
    <li>本报告依据委托方提供的标签图像及现行有效标准、法规文本作出，仅对送审标签图像所示内容负责；</li>
    <li>标签实物及产品实物的符合性，以实物核验、具备资质的实验室检测结果及监管部门意见为准；</li>
    <li>本报告仅供委托方内部合规管理及整改使用，未经书面同意不得用于其他用途。</li>
  </ul></div>
  </div></div></body></html>''')
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="审核数据 JSON")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    data = json.loads(Path(a.input).read_text(encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.input))
    Path(a.out).write_text(build(data, base), encoding="utf-8")
    print("已生成：", a.out)


if __name__ == "__main__":
    main()
