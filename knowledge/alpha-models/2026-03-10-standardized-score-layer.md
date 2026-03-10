# Standardized Score 层：作用与是否需要单独研究

Date: 2026-03-10
Category: alpha-models

## 研究问题

`standardized score` 这一层到底是做什么的，是否需要单独研究。

## 核心结论

需要，而且必须单独研究。

原因很简单：

- raw predictor 只是原始预测变量
- 不同 predictor 的量纲、分布、稀疏度、极值性质都不同
- 不先做标准化，就不能严肃地做：
  - predictor 之间比较
  - composite alpha
  - calibration
  - optimizer input

所以 `standardized score` 不是可选的数据清洗，而是 alpha 层的正式一层。

## 它到底做什么

`standardized score` 的目标是把 raw predictor 变成“同一比较空间里的可用对象”。

它至少承担 4 个职责：

1. 去量纲
   - 让 `Amihud`、`lagged return`、`funding rate`、`basis` 这类不同单位的 predictor 可以比较

2. 控制极值
   - predictor 往往厚尾、偏态、跳点明显
   - 不控制极值，后面的组合和校准很容易被少数点劫持

3. 统一方向
   - 要保证 predictor 值越高，含义越一致，例如都表示“更偏多”或“更强 alpha”

4. 为合成层提供输入
   - composite alpha 通常吃 standardized scores，而不是原始 predictor

## 调研到的直接证据

### BlackRock

BlackRock 公开材料表明：

- 多类 signals 会被加权组合成 `final alpha score`

这意味着：

- 原始 signals 进入组合前，必须已经被映射到可比较的 score 空间

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### MSCI FactorLab

MSCI FactorLab 的说明非常直接：

- 一些 descriptors 同时提供 `derived values` 和 `standardized values`
- standardized values 是 derived value 的 `z-score` 版本

Source:

- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf

这直接说明：

- 在机构因子体系里，`derived/raw descriptor -> standardized score` 是标准流程

### MSCI Multi-Factor Methodology

MSCI 多因子指数方法论也明确写到：

- security-level descriptor 会先标准化成 `z-score`
- 再作为更高层 factor score 的组成部分

例如：

- Momentum factor score 是多个 security-level z-score 的加权和

Source:

- MSCI Diversified Multi-Factor Indexes Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/MSCI_Diversified_Multi_Factor_Indexes_Methodology_April_2015.pdf

这说明：

- 标准化层不是附属步骤
- 而是 composite factor / alpha 的前置层

## 对我们项目的直接含义

如果按知识库现在的结论，alpha 流程是：

`raw predictor -> standardized score -> composite alpha -> scaled alpha -> position/portfolio`

那么 `standardized score` 这一层现在还没有被完全做清楚。

raw predictor 这一层虽然已经有了，但后面如果不把 standardized score 研究清楚，就会卡在：

- 不知道连续值 predictor 和规则型 predictor 怎么放到同一空间
- 不知道 funding/basis 和价格类 predictor 怎么比较
- 不知道 composite alpha 应该吃什么输入

## 这一层当前应该研究什么

按知识库现状，这一层最该补的不是“是否需要”，而是“怎么做”。

至少要补 4 个问题：

1. `standardization method`
   - z-score
   - robust z-score
   - rank normalization
   - winsorization + z-score

2. `scope`
   - time-series per asset
   - cross-sectional per bar
   - hybrid

3. `binary / ternary rule handling`
   - 技术规则型 predictor 如何进入统一 score 空间

4. `direction alignment`
   - predictor 符号如何统一成“高值 = 更强 alpha”

## 阶段性结论

所以答案是：

- `standardized score` 这一层必须单独研究
- 它不是等 alpha 全部做完再顺手处理的步骤
- 它是 raw predictor 和 composite alpha 之间的正式桥层

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multi-Factor Indexes Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/MSCI_Diversified_Multi_Factor_Indexes_Methodology_April_2015.pdf
