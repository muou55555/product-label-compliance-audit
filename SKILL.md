---
name: product-label-compliance-audit
description: >-
  通用型预包装食品（含进口）标签合规审核并产出可交付报告（HTML / PDF）。
  当用户需要对食品外包装标签做合规性检查、识别缺项漏标 / 字体字号 / 单位 / 小数点位数 /
  标示形式 / 配料表与添加剂超标 / 限量 / 贮存条件 / 繁体字 / 进口在华注册编号核查，
  并要求逐条给出依据（精确到文件、章节、原句、页码）、无论是否合规都输出逐条比对过程、
  生成甲方正式报告或 PDF 时使用。适用于葡萄酒、乳制品、饮料、糕点、肉制品等任意品类
  （品类规则与限量数据按品类加载，不局限于某一产品）。
---

# 产品标签合规审核

> **Skill 版本：v1.3.0**（版本号见 `VERSION`，更新记录见 `CHANGELOG.md`）

把一次标签审核做成**确定性、可审计、可复现**的过程，最终交付甲方正式报告。
核心原则：**规则优先（rule-first）——引擎做主干，模型只负责识别与语义兜底。**

## 一、标准流程（按序执行）

1. **采集与识别**：对标签原图逐字识别；必要时放大分区核对。产出结构化事实
   `LabelFacts`（字段值/引导词/像素字高/版面 + 品类属性）。识别口径见 [references/01-workflow.md](references/01-workflow.md)。
2. **第一步·标签形式审核**：对照内置通用标签标准（GB 7718，见 `standards/`），逐条检查
   缺项、漏标、字体字号、单位、小数点位数、标示形式、引导词、同版面、繁体字。
3. **第二步·内容合规审核**：按内置品类标准与限量数据（GB 2760/2758/15037 等）
   做限量查表（添加剂/污染物/真菌毒素/营养）与品类专属指标比对；核对贮存条件、配料/添加剂是否违规或超标。
4. **资质核查**：进口商品核查"在华注册编号"状态、原产国/境内代理商信息；
   国内商品核查生产许可证/标准代号。详见 [references/04-registry-check.md](references/04-registry-check.md)。
5. **逐条判定**：每条规则输出 `结论 + 原因 + 依据原文`；无论合规与否都给完整比对过程。
6. **生成报告并导出**：甲方正式报告（公文风格、不合规与合规分区、隐藏技术实现），
   需要时转 PDF。详见 [references/05-report-and-pdf.md](references/05-report-and-pdf.md)。

## 二、四类判定路由（确定性的来源）

| route | 判定者 | 场景 | 无数据时 |
|---|---|---|---|
| `engine` | 规则引擎 | 缺项/格式/单位/枚举/繁体字/同版面 | 确定判定 |
| `lab` | 实验室回填 | 残留量、理化、微生物、净含量短缺量 | 待检测 |
| `browser` | 联网核验 | 在华注册编号等资质状态 | 待联网 |
| `model` | 模型语义兜底 | 夸大、背书、保健、版式结构 | 待人工 |

**铁律**：模型不得给出最终合规结论；模型未启用或调用失败时，相关项一律落"待人工/待检测"，
不得编造数值或把未覆盖项判为合规。

## 三、知识库四层（支持任意品类，不穷举）

```
common/       通用标签规则（一次建成，全部品类适用）
data_tables/  限量数据表（CSV/DB，按食品分类号检索，不写规则）
categories/   品类专属规则（按需增量，只建高频品类）
registry/     资质/注册规则
```

- 已落地的通用规则与**配料完整性引擎**见本 Skill 的 `knowledge/` 目录（含配料本体、品类必需原料，带正反样例）；
- 配料完整性**可由 `scripts/ingredient_completeness.py` 直接运行判定**（自包含，仅依赖 PyYAML）；
- 新品类 = 限量数据入表 + 品类专属规则（在本体补同义词/工艺、在必需原料表登记）+ 品类清单登记；
- 未建模品类走"通用 + 查表 + 动态读标准 + 待人工"兜底，**不硬编、不漏判**；
- 规则迭代须过闸门：`proposed → 隔离校验+人工 → published`，禁止"生成即用"。

机制细节见 [references/02-rule-first-engine.md](references/02-rule-first-engine.md)。

## 四、标准库与引用规范

**四份标准 PDF 已内置在 `standards/`（GB7718、GB2758、GB-T15037、GB2760），
用户无需再上传标准。** 内置清单、关键页码与读取方法见
[references/06-bundled-standards.md](references/06-bundled-standards.md)。

- 用 `scripts/query_standard.py` 检索文字层标准、按页取文本、渲染扫描件；
- 更多标准清单、食品分类号与换版注意事项见 [references/03-standards-catalog.md](references/03-standards-catalog.md)；
- 引用必须精确到 **文件 / 章节或表号 / 原句 / 页码**；原句加引号；
- 区分"已查证（标准/官方系统）"与"一方称"；不确定标"待核实"；内置版本若较旧需提示以最新现行版为准。

## 五、可复用脚本

- `scripts/query_standard.py`：读取/检索内置标准 PDF（list/search/page/render）；
- `scripts/build_audit_report.py`：由审核结果 JSON 生成自包含甲方报告（**公文模板版**：深蓝封面 + 元信息表 + 六大章节 + 卡片式发现 + 证据图 base64 内嵌 + 签字与声明）。数据结构见 `scripts/audit_input.example.json`；行内支持 `**粗体**`、`` `代码` ``；
- `scripts/html_to_pdf.py`：打印样式 + headless 浏览器导出 PDF（已做卡片/签字块跨页保护）。
- `scripts/query_customs.py`：在华注册编号自动核查（**Playwright 浏览器自动化兜底**）。平台没有 browser-task 等浏览器 skill 时，自动打开官方系统、填编号、查询、抓取企业/类别/有效期/状态并截图、输出 JSON（含编号解码与自动判定）。用法见 [references/04-registry-check.md](references/04-registry-check.md)。
- `scripts/ingredient_completeness.py`：**通用配料完整性检查（自包含、可泛化）**。由 5 个证据源（物理形态/工艺/自身声明/品类标准/定量闭合）推断"应标集合"，与已标集合做差，输出缺失项（水、油、盐、奶、可可、添加剂等），支持传 LabelFacts JSON 或命令行参数，`--json` 输出机器结果。方法见 [references/07-ingredient-completeness.md](references/07-ingredient-completeness.md)。

## 六、交付前自检

- 逐条重算关键数字（合计/偏差/校验位）；缺项/字高/单位等逐项核对；
- 真实渲染报告检查（截断、方块字、空白页、证据图是否显示）；
- 说明检测/核验/联网/人工等未闭环项及边界；不把未覆盖项说成合规。
