# 通用型食品标签合规审核 Skill

> 版本：v1.3.0　|　适用：任意预包装食品（含进口），不局限于葡萄酒

一个可移植的标签合规审核 Skill，把一次标签审核做成**确定性、可审计、可复现**的过程，
并产出可交付的甲方正式报告（HTML / PDF）。

## 核心架构：规则优先（rule-first）

**规则引擎做主干，模型只负责识别与语义兜底。**

- 缺项、漏标、字体字号、单位、小数点、标示形式、繁体字、限量查表 → 规则引擎确定性判定；
- 读图 / OCR、夸大 / 背书 / 版式等语义判断 → 模型处理，且模型不直接给出最终合规结论；
- 无法由图像得出的残留量、理化、微生物 → 送检；进口编号状态 → 联网核验。

## 标准流程

1. 采集与识别：标签原图逐字识别，产出结构化事实 `LabelFacts`；
2. 第一步·标签形式审核：对照 GB 7718 逐条检查；
3. 第二步·内容合规审核：限量查表 + 品类专属指标 + 贮存条件；
4. 资质核查：进口核查在华注册编号，国内核查生产许可；
5. 逐条判定：每条规则输出结论 + 原因 + 依据原文；
6. 生成报告并导出：甲方正式报告（HTML / PDF）。

## 目录结构

```
SKILL.md                 入口与流程
VERSION / CHANGELOG.md   版本号与更新记录
knowledge/               配料本体 / 品类必需原料 / 完整性规则
references/              七份参考文档（流程、引擎、标准、编号、报告、完整性）
scripts/                 可复用脚本
standards/               内置四份标准 PDF（无需用户上传）
```

## 通用配料完整性引擎

不只针对“水”，而是泛化到任意配料：

```
缺失 = 应标集合 − 已标集合
```

应标集合由 5 个证据源推断：物理形态、生产工艺、自身声明、品类标准、定量闭合。
可自动发现水 / 油 / 盐 / 奶 / 可可 / 添加剂等任一漏标；已挥发水、发酵菌种、类别词等
边界已正确处理。

## 可复用脚本

```bash
# 读取/检索内置标准
python3 scripts/query_standard.py list
python3 scripts/query_standard.py search "二氧化硫" --std GB2760

# 配料完整性检查
python3 scripts/ingredient_completeness.py facts.json --json

# 在华注册编号核查（Playwright 兜底）
python3 scripts/query_customs.py CGEO23012201060023 --out result.json --shot shot.png

# 生成甲方报告并转 PDF
python3 scripts/build_audit_report.py audit_data.json -o report.html
python3 scripts/html_to_pdf.py report.html report.pdf
```

## 内置标准

| 标准 | 用途 |
|---|---|
| GB 7718-2011 预包装食品标签通则 | 通用标签形式 |
| GB 2758-2012 发酵酒及其配制酒 | 发酵酒品类 |
| GB/T 15037-2006 葡萄酒 | 葡萄酒品类（扫描件） |
| GB 2760-2014 食品添加剂使用标准 | 添加剂限量 |

审核以最新现行版本为准；新增标准放入 `standards/` 并在 manifest 登记即可。

## 许可证

仅用于合规审核与内部管理。
