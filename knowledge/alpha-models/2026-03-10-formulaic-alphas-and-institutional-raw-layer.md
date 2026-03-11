# Formulaic Alphas 与机构第一层 Raw Layer

Date: 2026-03-10
Category: alpha-models

## 研究问题

什么是 `101 Formulaic Alphas`，它是不是第一层因子生成方案。机构第一层 raw layer 到底怎么做，是否是研究员每天手工找很多 raw 因子。`descriptor x transform x horizon` 是否可以作为正式生成方案。

## 核心结论

1. `101 Formulaic Alphas` 是一类 **公式化 alpha 库**，不是完整机构流程
2. 它更像：
   - 一个信号 DSL / grammar
   - 一个公式模板库
   - 一个研究起点和种子集
3. 机构第一层通常不是“每天手工乱想因子”，而是：
   - 维护一套 descriptor 库
   - 定义可允许的变换族
   - 用标准研究流程持续筛选、淘汰、替换
4. `descriptor x transform x horizon` 本质上就是一种受约束的第一层生成方案
5. 如果要更自动化，正确方向也不是无约束乱搜，而是：
   - 先有 descriptor/grammar
   - 再做程序化生成或进化式搜索

## Source-Backed

### 1. 101 Formulaic Alphas 是显式公式库

Kakushadze 的论文明确给出 101 个可执行公式 alpha，这些 alpha 主要基于：

- open / high / low / close
- volume
- VWAP
- 少数行业/市值中性化处理

平均持有期约 0.6 到 6.4 天，alpha 两两平均相关性较低。

来源：

- 101 Formulaic Alphas
  - https://arxiv.org/abs/1601.00991
  - https://ideas.repec.org/p/arx/papers/1601.00991.html

### 2. 公式化 alpha 后来确实发展成自动生成方向

AutoAlpha 这类研究说明：

- 学界和部分工程团队会把 formulaic alphas 看成可搜索的结构空间
- 然后用 evolutionary / quality-diversity / RL 等方法自动挖掘

来源：

- AutoAlpha: an Efficient Hierarchical Evolutionary Algorithm for Mining Alpha Factors in Quantitative Investment
  - https://arxiv.org/abs/2002.08245
  - https://ideas.repec.org/p/arx/papers/2002.08245.html

### 3. 机构现实里维护的是大规模 descriptor / signal library

MSCI 的 FactorLab 公开说明里，明确提供：

- 197 个 factor descriptors
- 12 个 factor groups

这说明成熟机构工作流更像是维护和扩充 descriptor 库，而不是每天从零发明因子。

来源：

- MSCI FactorLab
  - https://www.msci.com/our-solutions/analytics/factor-lab

### 4. 大型系统化机构第一层是多类 signals 的标准化生产线

BlackRock 公开的 Systematic Investing 描述表明：

- 会长期维护大量 signals
- 信号来自传统和另类数据
- 最终做成统一 alpha score

截至 2025 年 BlackRock 公开材料里提到：

- 1000+ alpha signals
- 300+ unstructured data sources

这更像是“平台化信号工厂”，不是单人每天手工试几个 raw 因子。

来源：

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- BlackRock Alpha Reimagined / Data-driven investing
  - https://www.blackrock.com/us/individual/investment-ideas/systematic-investing
  - https://www.blackrock.com/us/financial-professionals/insights/data-driven-investing

## Industry-Standard

基于上面的证据，可以把第一层 raw layer 的主流做法概括成：

### 1. 不是手工逐个发明，而是“研究约束 + 系统生成”

常见做法是：

- 先定义 descriptor 家族
- 再定义可允许变换
- 再定义可允许窗口 / horizon
- 再程序化生成候选

### 2. Formulaic alpha 是一种 grammar

`101 Alphas` 这类东西最有价值的部分不是“101 个具体公式”，而是它隐含了一套可复用 grammar：

- rolling mean / std / rank / ts_rank
- correlation / covariance
- delta / lag
- sign / abs / scale
- min / max

也就是说，它代表的是“如何组合基础算子生成候选”。

### 3. 更成熟的团队会把第一层做成 descriptor library + generator

从工程角度看，机构更像是在维护：

- descriptor library
- transform library
- horizon library
- evaluation pipeline

而不是维护一个手写 Excel 因子列表。

## Project-Specific Inference

### 1. `descriptor x transform x horizon` 就是一种正式生成方案

它不是一句抽象口号，而是可以直接落地成生成器：

- `descriptor`
  - 原始经济量或状态量
  - 例如 return, basis, funding, volume, vol, amihud

- `transform`
  - 对 descriptor 做的有限操作
  - 例如 level, change, ratio, deviation, rank, vol-adjusted, interaction

- `horizon`
  - 观察尺度
  - 例如 short / medium / long

把三者组合起来，就会产生一小批结构化候选 raw predictors。

### 2. 这和 101 因子并不冲突

`101 Formulaic Alphas` 更像是：

- 手写的 formulaic grammar examples

`descriptor x transform x horizon` 更像是：

- 结构化的生成框架

前者给“公式模板”，后者给“生成机制”。

### 3. 对我们项目，第一层正确姿势不是继续手加 trend

当前最合理的是：

- 保留现有 trend 作为强基准
- 新一轮 raw 生成器专门打：
  - reversal
  - volatility_liquidity
  - derivatives_carry_funding

## 机构到底是不是每天大量找 raw 因子

更准确的答案是：

- **不是每天从零乱找**
- 也**不是完全不找**

现实里更像三类分工：

1. 平台/研究基础设施
   - 维护 descriptor 库、数据管线、评估框架
2. 研究员
   - 提出新 descriptor / 新变换 / 新数据源假设
   - 做小规模、机制驱动扩库
3. 自动化系统
   - 在受约束空间里做批量生成、筛选、淘汰

所以真正的机构第一层是：

**人定义研究边界，系统生成候选，流程自动淘汰。**

## 结论

如果你问“有没有什么生成因子的方案”，答案是有，而且至少有三类：

1. `formula library` 路线
   - 代表：101 Formulaic Alphas
2. `descriptor x transform x horizon` 路线
   - 更适合做可控的研究生成器
3. `grammar / evolutionary / RL mining` 路线
   - 代表：AutoAlpha 及其后续工作

对当前项目，最合适的不是直接上第三类，而是先把第二类做扎实，再视情况把第一类当模板库、把第三类当后续升级路线。
