#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配料名称合规性检查（自包含，与"完整性检查"并列）。

解决的问题：配料表"存在"且"完整"，不代表每个配料的"名称"标准。
本脚本对每个配料名做两件确定性的事：
  1) 修饰词/声称词扫描：天然、纯、特级、有机、零添加、手工、野生……
  2) 标准名称归一化：去掉修饰词后，须能映射到配料本体的标准名称；
     映射不上 -> 待核实（不硬判、不漏判）。

检测顺序：先白名单整体豁免（天然水、天然矿泉水、无核…），再扫描修饰词。

用法：
  python3 ingredient_name_check.py --ingredients "番茄、水、天然香辛料（辣椒粉）"
  python3 ingredient_name_check.py facts.json --json
  # facts.json 为 LabelFacts（取 fields.ingredients.value）
"""
from __future__ import annotations
import argparse, json, os, sys
from typing import Dict, List, Optional

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_KNOWLEDGE = os.path.join(_HERE, "..", "knowledge")


def split_ingredients(text: str) -> List[str]:
    raw = str(text or "")
    # 保留括号内容但去掉括号，便于逐个成分扫描
    for a, b in [("（", "）"), "(", ")"]:
        while a in raw and b in raw:
            i, j = raw.find(a), raw.find(b)
            if j > i:
                raw = raw[:i] + "、" + raw[i + 1:j] + raw[j + 1:]
            else:
                break
    for sep in ["、", "，", ",", "；", ";", "/"]:
        raw = raw.replace(sep, "|")
    return [t.strip() for t in raw.split("|") if t.strip()]


class NameChecker:
    def __init__(self, knowledge: str = _KNOWLEDGE):
        with open(os.path.join(knowledge, "ingredient_name_modifiers.yaml"),
                  encoding="utf-8") as f:
            mod = yaml.safe_load(f)
        self.groups = mod["modifiers"]
        wl = mod.get("whitelist", {}) or {}
        self.wl_exact = set(wl.get("exact", []) or [])
        self.wl_attr = list(wl.get("attribute_prefix", []) or [])
        # 归一化用配料本体
        self.alias_map: Dict[str, str] = {}
        with open(os.path.join(knowledge, "ingredient_ontology.yaml"),
                  encoding="utf-8") as f:
            ont = yaml.safe_load(f)
        for canon, spec in ont["canonical"].items():
            self.alias_map[canon] = canon
            for a in spec.get("aliases", []):
                self.alias_map[a] = canon
        # 修饰词按长度降序，避免“纯天然”被“天然”先截断
        self.lex = []
        for risk, g in self.groups.items():
            for w in g.get("words", []):
                self.lex.append((w, risk, g))
        self.lex.sort(key=lambda x: len(x[0]), reverse=True)

    def normalize(self, text: str) -> Optional[str]:
        t = str(text or "").strip()
        if t in self.alias_map:
            return self.alias_map[t]
        for alias in sorted(self.alias_map, key=len, reverse=True):
            if alias and alias in t:
                return self.alias_map[alias]
        return None

    def check_token(self, token: str):
        """返回 (命中修饰列表, 去修饰后核心, 归一化结果)。"""
        t = token.strip()
        # 白名单整体豁免
        if t in self.wl_exact:
            return [], t, self.normalize(t)
        for p in self.wl_attr:
            if t.startswith(p):
                return [], t, self.normalize(t)

        hits, rest = [], t
        # 反复扫描，允许一个词含多个修饰（如“纯天然手工”）
        changed = True
        while changed:
            changed = False
            for w, risk, g in self.lex:
                if w in rest:
                    hits.append({"word": w, "risk": risk,
                                 "color": g.get("color", "amber"),
                                 "label": g.get("label", ""),
                                 "note": g.get("note", "")})
                    rest = rest.replace(w, "", 1)
                    changed = True
                    break
        rest = rest.strip()
        canon = self.normalize(rest) if rest else None
        return hits, rest, canon

    def analyze(self, ingredients: str, strict: bool = False):
        findings = []
        for tok in split_ingredients(ingredients):
            hits, core, canon = self.check_token(tok)
            if hits:
                # 有修饰：报告修饰；若去掉修饰后为空（整个名称只是声称），
                # 明确指出“无实际配料名称”
                only_claim = bool(not core)
                findings.append({
                    "token": tok,
                    "modifiers": hits,
                    "core": core,
                    "canonical": canon,
                    "only_claim": only_claim,
                })
            elif strict and core and not canon:
                # 严格模式：本体未覆盖的名称，仅作“待补充/待核实”，不硬判
                findings.append({"token": tok, "modifiers": [],
                                 "core": core, "canonical": None,
                                 "unknown": True})
        return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="配料名称合规性检查")
    ap.add_argument("facts_json", nargs="?", help="LabelFacts 事实 JSON")
    ap.add_argument("--ingredients", default="")
    ap.add_argument("--strict", action="store_true",
                    help="本体未覆盖名称也列为待核实（默认关闭，避免误报）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ingredients = args.ingredients
    if args.facts_json:
        d = json.load(open(args.facts_json, encoding="utf-8"))
        ingredients = str(d.get("fields", {}).get("ingredients", {})
                          .get("value", ""))

    chk = NameChecker()
    findings = chk.analyze(ingredients, strict=args.strict)

    if args.json:
        print(json.dumps({"name_compliant": not findings,
                          "findings": findings}, ensure_ascii=False, indent=2))
        return 0 if not findings else 1

    print("配料名称合规性检查：")
    if not findings:
        print("结论：符合，配料名称未发现非标准修饰/声称")
        return 0
    print("结论：不符合／待核实")
    for f in findings:
        if f.get("unknown"):
            print(f"  - 「{f['token']}」未在本体中匹配标准名称，"
                  f"须人工核实（严格模式）")
            continue
        for h in f["modifiers"]:
            print(f"  - 「{f['token']}」含修饰“{h['word']}”"
                  f"[{h['label']}]：{h['note']}")
        if f.get("only_claim"):
            print(f"  - 「{f['token']}」仅为声称，缺少实际配料名称")
    return 1


if __name__ == "__main__":
    sys.exit(main())
