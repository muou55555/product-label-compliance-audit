# 02 · 规则优先引擎与知识库

## 目录
- 一、为什么规则优先
- 二、四层知识库
- 三、品类路由清单
- 四、覆盖率与兜底
- 五、规则生命周期闸门
- 六、规则数据模型

## 一、为什么规则优先

模型语义判断虽灵活，但**不确定、难复现、难审计**。合规判定必须可追溯，因此：
- 能用规则确定判定的，绝不交给模型；
- 模型只负责两类：**识别**（读图/OCR）与**语义兜底**（夸大/背书/版式）；
- 模型产物不直接作为最终结论依据。

## 二、四层知识库

```
common/       通用标签规则：一次建成，全部品类适用（GB 7718 等）
data_tables/  限量数据表：结构化 CSV/DB，按食品分类号检索
categories/   品类专属规则：按需增量，只建高频品类
registry/     资质/注册规则：进口编号、生产许可等
```

关键：**限量是"数据"不是"规则"**。新品类限量无需写规则，只需在数据表中按
`food_code` 组织，运行时检索。规则只引用"查哪张表、哪个字段"。

## 三、品类路由清单（manifest）

```yaml
categories:
  wine:
    package: categories/wine.yaml
    standard: GB/T 15037-2006
    food_code: "15.03.01"
    data_tables: [gb2760, gb2762, gb2761]
    attributes:
      color: [white, rose, red]
      sweetness: [dry, semi_dry, semi_sweet, sweet]
  dairy:
    package: null           # 未建 -> 自动兜底
    standard: GB 19302
    food_code: "01.0"
    data_tables: [gb2760, gb2762, gb2761, gb14880, gb28050]
```

## 四、覆盖率与兜底

任意品类的审核项大致分为：

| 类别 | 占比 | 无品类包时 |
|---|---|---|
| 通用标签 + 限量数据 | 70%–80% | 始终可判 |
| 品类专属项 | 20%–30% | 动态读标准 + 待人工 |

未覆盖的处置：
1. 通用规则与限量数据照常判定；
2. 读取标签所标执行标准，由模型抽取专属要求作为**建议**；
3. 无法确定项标"待人工"，并生成"待补充品类规则"；
4. **不把未覆盖项判为合规，也不硬编结果。**

## 五、规则生命周期闸门

```
proposed（模型/人工提议）
  → 隔离 staging（不进入实时判定）
  → 自动校验（必填字段、引用原文、正反样例）
  → 人工对照标准原文审核
  → published（版本号、依据、样例）
  → 对后续审核生效
  → deprecated（标准换版停用/替换）
```

自动校验要点：
- 有 ID/名称/合法路由/合法检查类型；
- 检查类型所需字段齐全；
- 引用必须含原句；
- 具备 positive/negative 样例。

**禁止"生成即用"**：未发布规则永远无法被实时审核引用。

## 六、规则数据模型（YAML）

```yaml
- id: GB7718-4.1.5.1
  name: 净含量应由净含量、数字和法定计量单位组成
  check: {type: regex, field: net_content,
          pattern: '\\d+(\\.\\d+)?\\s*(ml|mL|g|kg|l|L)'}
  route: engine
  applies: {}
  citation: {clause: "4.1.5.1", quote: "净含量的标示应由净含量、数字和法定计量单位组成。", page: 5}
  status: published
  test_cases: {positive: ["187 ml"], negative: ["187"]}
```

判定路由对应：`engine` 直接判定；`lab` 查 `lab.*`；`browser` 查 `registry`；
`model` 走语义兜底。
