#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用配料完整性检查（自包含，Skill 可直接运行，不依赖外部项目）。

核心公式：缺失 = 应标集合 − 已标集合。
“应标集合”由 5 个确定性证据源推断，而非写死“水”，故可泛化：
  1) 物理形态：液态/半固态/浆状 -> 须有液相（水或油）
  2) 生产工艺：盐水->水+盐；油炸->油；烘焙->水已挥发（豁免）
  3) 自身声明：正文“内含/添加 X” -> X 必须进配料表
  4) 品类标准：酸奶->生乳；巧克力->可可
  5) 定量闭合：固形物占比反推液相（固形物13% -> 约87%水）

用法：
  python3 ingredient_completeness.py facts.json
  python3 ingredient_completeness.py --category soy_sauce \
      --ingredients "黄豆、小麦、食用盐、白砂糖" \
      --form liquid --process brine,fermentation_in_liquid --solid 13
  加 --json 输出机器结果
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_KNOWLEDGE = os.path.join(_HERE, "..", "knowledge")


@dataclass
class RequiredItem:
    canonical: str
    source: str
    evidence: str


@dataclass
class SimpleFacts:
    category: str = ""
    ingredients: str = ""
    physical_form: Optional[str] = None
    processes: List[str] = field(default_factory=list)
    solid_content_pct: Optional[float] = None
    all_text: List[str] = field(default_factory=list)

    @classmethod
    def from_label_facts(cls, d: dict) -> "SimpleFacts":
        attrs = d.get("category_attributes", {}) or {}
        proc = attrs.get("process", [])
        if isinstance(proc, str):
            proc = [proc]
        fields = d.get("fields", {}) or {}
        texts = [str(v.get("value", "")) for v in fields.values()]
        return cls(
            category=d.get("category", ""),
            ingredients=str(fields.get("ingredients", {}).get("value", "")),
            physical_form=attrs.get("physical_form"),
            processes=proc,
            solid_content_pct=attrs.get("solid_content_pct"),
            all_text=texts)


def split_ingredients(text: str) -> List[str]:
    raw = str(text or "")
    for sep in ["、", "，", ",", "；", ";", "/"]:
        raw = raw.replace(sep, "|")
    out = []
    for t in raw.split("|"):
        for a, b in [("（", "）"), ("(", ")")]:
            while a in t and b in t:
                i, j = t.find(a), t.find(b)
                if j > i:
                    t = (t[:i] + " " + t[i + 1:j] + " " + t[j + 1:]).strip()
                else:
                    break
        out.append(t)
    return out


class CompletenessChecker:
    def __init__(self, knowledge: str = _KNOWLEDGE):
        with open(os.path.join(knowledge, "ingredient_ontology.yaml"),
                  encoding="utf-8") as f:
            self.ont = yaml.safe_load(f)
        with open(os.path.join(knowledge, "required_ingredients.yaml"),
                  encoding="utf-8") as f:
            self.req = yaml.safe_load(f)
        self.alias_map: Dict[str, str] = {}
        for canon, spec in self.ont["canonical"].items():
            self.alias_map[canon] = canon
            for a in spec.get("aliases", []):
                self.alias_map[a] = canon

    def canonical_of(self, text: str) -> Optional[str]:
        t = str(text or "").strip()
        if t in self.alias_map:
            return self.alias_map[t]
        for alias in sorted(self.alias_map, key=len, reverse=True):
            if alias and alias in t:
                return self.alias_map[alias]
        return None

    def declared(self, ingredients: str) -> Set[str]:
        out: Set[str] = set()
        for tok in split_ingredients(ingredients):
            c = self.canonical_of(tok)
            if c:
                out.add(c)
        return out

    def label(self, canon: str) -> str:
        if canon == "__phase__":
            return "液相来源(水/油)"
        spec = self.ont["canonical"].get(canon, {})
        aliases = spec.get("aliases", [])
        return aliases[0] if aliases else canon

    def analyze(self, facts: SimpleFacts):
        declared = self.declared(facts.ingredients)
        evaporated = self._evaporated(facts)

        items: List[RequiredItem] = []
        items += self._from_process(facts)
        items += self._from_form(facts, items)
        items += self._from_declaration(facts)
        items += self._from_category(facts)
        items += self._from_closure(facts)

        seen: Dict[str, RequiredItem] = {}
        for it in items:
            if it.canonical in evaporated or it.canonical in seen:
                continue
            seen[it.canonical] = it
        required = list(seen.values())

        missing = [it for it in required if it.canonical not in declared]
        phase = next((it for it in missing if it.canonical == "__phase__"), None)
        if phase is not None and ({"water", "oil"} & declared):
            missing.remove(phase)
        return declared, required, missing

    def _evaporated(self, facts):
        ev: Set[str] = set()
        for p in facts.processes:
            rule = self.ont["process"].get(p)
            if rule:
                ev.update(rule.get("evaporated", []))
        if facts.physical_form == "solid":
            ev.add("water")
        return ev

    def _from_process(self, facts):
        out = []
        for p in facts.processes:
            rule = self.ont["process"].get(p)
            if not rule:
                continue
            for canon in rule.get("adds", []):
                out.append(RequiredItem(
                    canon, "工艺",
                    f"工艺“{p}”（{rule.get('note','')}）必需投入"))
        return out

    def _from_form(self, facts, process_items):
        if not facts.physical_form:
            return []
        rule = self.ont["physical_form"].get(facts.physical_form)
        if not rule or not rule.get("requires_phase"):
            return []
        if any(it.canonical in rule["requires_phase"] for it in process_items):
            return []
        return [RequiredItem(
            "__phase__", "形态",
            f"物理形态“{facts.physical_form}”，须标示液相（水或油）")]

    def _from_declaration(self, facts):
        out, found = [], set()
        signals = ["内含", "添加", "含有", "加入", "使用了"]
        for text in facts.all_text:
            if not any(s in text for s in signals):
                continue
            for alias in sorted(self.alias_map, key=len, reverse=True):
                if alias in text and self.alias_map[alias] not in found:
                    canon = self.alias_map[alias]
                    found.add(canon)
                    short = text if len(text) < 26 else text[:26] + "…"
                    out.append(RequiredItem(
                        canon, "自身声明",
                        f"正文声称“{short}”，该物质须入配料表"))
        return out

    def _from_category(self, facts):
        rule = self.req.get("categories", {}).get(facts.category)
        if not rule:
            return []
        return [RequiredItem(
            r["canonical"], "品类标准",
            f"{rule['standard']}：{r['quote']}")
            for r in rule.get("requires", [])]

    def _from_closure(self, facts):
        if facts.solid_content_pct is None or \
                facts.physical_form not in ("liquid", "semi_liquid",
                                           "semi_solid", "paste"):
            return []
        liquid = 100 - float(facts.solid_content_pct)
        if liquid > 50:
            return [RequiredItem(
                "water", "定量闭合",
                f"固形物约{facts.solid_content_pct}%，非固体(含水)约"
                f"{liquid:.0f}%，须标示液相")]
        return []


def main(argv=None):
    ap = argparse.ArgumentParser(description="通用配料完整性检查")
    ap.add_argument("facts_json", nargs="?", help="LabelFacts 事实 JSON")
    ap.add_argument("--category", default="")
    ap.add_argument("--ingredients", default="")
    ap.add_argument("--form", default=None)
    ap.add_argument("--process", default="", help="逗号分隔多个工艺")
    ap.add_argument("--solid", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.facts_json:
        with open(args.facts_json, encoding="utf-8") as f:
            facts = SimpleFacts.from_label_facts(json.load(f))
    else:
        facts = SimpleFacts(
            category=args.category, ingredients=args.ingredients,
            physical_form=args.form,
            processes=[p for p in args.process.split(",") if p],
            solid_content_pct=args.solid,
            all_text=[args.ingredients])

    chk = CompletenessChecker()
    declared, required, missing = chk.analyze(facts)

    if args.json:
        print(json.dumps({
            "complete": not missing,
            "declared": sorted(declared),
            "missing": [{"canonical": it.canonical,
                         "label": chk.label(it.canonical),
                         "source": it.source, "evidence": it.evidence}
                        for it in missing]
        }, ensure_ascii=False, indent=2))
        return 0 if not missing else 1

    print("配料完整性检查：")
    print("已标：", "、".join(chk.label(c) for c in sorted(declared)) or "无")
    if missing:
        print("结论：不符合（应标未标）")
        for it in missing:
            print(f"  - 漏标「{chk.label(it.canonical)}」[{it.source}]："
                  f"{it.evidence}")
        return 1
    print("结论：符合，配料完整")
    return 0


if __name__ == "__main__":
    sys.exit(main())
