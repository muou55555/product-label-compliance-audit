# 06 · 内置标准与读取方法

标准 PDF 已随 Skill 打包，**用户无需每次上传**。审核时直接读取本 Skill 内的标准。

## 目录
- 一、内置标准清单
- 二、标准索引文件
- 三、读取命令
- 四、扫描件处理
- 五、审核时的引用流程

## 一、内置标准清单

| ID | 标准 | 页数 | 文字层 | 用途 |
|---|---|---|---|---|
| GB7718 | 预包装食品标签通则 (2011) | 20 | 有 | 通用标签形式 |
| GB2758 | 发酵酒及其配制酒 (2012) | 4 | 有 | 发酵酒品类 |
| GB-T15037 | 葡萄酒 (2006) | 11 | **无（扫描件）** | 葡萄酒品类 |
| GB2760 | 食品添加剂使用标准 (2014) | 473 | 有 | 添加剂限量 |

文件位于：`standards/`。

## 二、标准索引文件

`standards/standards_manifest.yaml` 记录每个标准的文件、页数、是否有文字层、
关键页码（如 GB2760 葡萄酒 SO₂ 在第 21 页；GB-T15037 理化表2 在第 8 页）。
需要时直接按关键页码定位，避免通读大文件。

## 三、读取命令（scripts/query_standard.py）

需要先安装 `pip install pymupdf`。

```bash
# 列出内置标准
python3 scripts/query_standard.py list

# 全文检索关键词（文字层 PDF）
python3 scripts/query_standard.py search "%vol" --std GB2758
python3 scripts/query_standard.py search "二氧化硫" --std GB2760

# 输出某页文本
python3 scripts/query_standard.py page GB2758 4

# 渲染某页为图片（扫描件/需要精确核对表格时）
python3 scripts/query_standard.py render GB-T15037 8 -o /tmp/p8.png
```

## 四、扫描件处理（GB-T15037）

- GB-T15037 为扫描件，**无法用文本检索**；
- 用 `render` 把对应页渲染为图片，再用视觉读取，或对照已渲染页面核对；
- 常用页：分类含糖量 p2、感官表1 p7、理化表2 p8、标签 p9、贮存 p10。

## 五、审核时的引用流程

1. 确定品类后，从 `standards/` 读取对应标准（不再要求用户上传）；
2. 形式审核 → 用 GB7718；
3. 品类内容 → 用品类标准 + GB2760 等限量；
4. 引用时给出：**文件 / 章节或表号 / 原句 / 页码**；
5. 若标准在外部已换版而内置版本较旧，需在报告中标注版本，并提示以最新现行版为准。

## 六、扩展更多内置标准

把新的标准 PDF 放入 `standards/`，并在 `standards_manifest.yaml` 登记
（ID、文件、页数、文字层、关键页码），读取脚本即可自动检索。
