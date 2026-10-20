# 版本更新记录（CHANGELOG）

本 Skill 采用语义化版本号（SemVer：主版本.次版本.修订号）。
当前版本见 `VERSION` 文件；SKILL.md 标题下同步标注。

## [1.3.0] - 2026-10-20

### 新增
- **通用配料完整性引擎（自包含、可泛化）**，不再是"发现水就补水规则"的打补丁：
  - 知识数据：`knowledge/ingredient_ontology.yaml`（同义词/物理形态/工艺）、
    `knowledge/required_ingredients.yaml`（品类必需原料）、
    `knowledge/common_ingredient_completeness.yaml`（规则视角+正反样例）；
  - 可执行脚本：`scripts/ingredient_completeness.py`，由 5 个证据源
    （物理形态/工艺/自身声明/品类标准/定量闭合）推断"应标集合"，
    与已标集合做差，自动发现水/油/盐/奶/可可/添加剂等任一漏标；
  - 支持 LabelFacts JSON 或命令行参数，`--json` 输出机器结果，仅依赖 PyYAML。
- 已处理泛化边界：发酵菌种（曲/酵母，加工微生物）不强制标；"防腐剂"等类别词
  不误判；烘焙/蒸馏/干燥中已挥发的水豁免。
- references/07 新增"配料完整性核对方法论"。

## [1.1.0] - 2026-10-19

### 新增
- `scripts/query_customs.py`：在华注册编号自动核查（Playwright 浏览器自动化兜底）。
- 四份标准 PDF 内置在 `standards/`。
