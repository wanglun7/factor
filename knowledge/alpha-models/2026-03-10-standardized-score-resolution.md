# Standardized Score：收敛结论

Date: 2026-03-10
Category: alpha-models

## 研究问题

把 `standardized score` 这一层继续补到可以进入实现前评审的程度。

这次重点解决 4 个问题：

1. `time-series` 还是 `cross-sectional`
2. `binary / ternary rule` predictor 怎么进入 score 空间
3. predictor 方向怎么统一
4. 普通 `z-score` 还是 `robust z-score`

## Source-Backed

### 1. 公开方法论最明确支持的是 `winsorization + z-score`

MSCI 公开 methodology 和 factsheet 都很明确：

- 先对 descriptor 做 winsorization
- 再用 mean / std 计算 `z-score`
- 再把多个 standardized descriptors 合成 factor score

这部分证据是清楚的，且不是推论。

对应来源：

- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf
- MSCI Quality Indexes Methodology
  - https://www.msci.com/documents/10199/a13e0b86-7cb6-fc79-f278-60904dfab0ef

### 2. 方向统一的公开做法是“对不利变量取负”

MSCI 公开方法明确写到：

- 对于 Debt-to-Equity、Earnings Variability 这种“值越大越差”的变量
- 直接计算 negative z-score
- 目的是保证高分统一代表更好的暴露

这说明：

- `direction alignment` 是标准步骤
- 不需要等到 composite 再处理

对应来源：

- MSCI Quality Indexes Methodology
  - https://www.msci.com/documents/10199/a13e0b86-7cb6-fc79-f278-60904dfab0ef
- MSCI USA Minimum Volatility, Momentum and Sector Neutral Quality Index disclosure excerpt
  - https://www.sec.gov/Archives/edgar/data/1114446/000119312521029259/d106146d424b2.htm

### 3. `cross-sectional z-score` 是典型股票因子框架的标准做法

MSCI 公开方法里大量使用：

- region-relative z-score
- sector-relative z-score

这明确说明：

- `cross-sectional standardization` 是成熟方法
- 但它对应的是同一时点多证券比较的框架

对应来源：

- Franklin Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_Franklin_Global_Equity_Index.pdf
- LibertyQ Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_LibertyQ_Global_Equity_Index_May_2019.pdf

### 4. `time-series momentum` 的原始预测关系是“证券自己的过去 -> 自己的未来”

Moskowitz, Ooi, Pedersen 的时间序列动量研究明确是：

- 用一个证券自己的过去收益
- 去预测这个证券自己的未来收益

这说明：

- `time-series` 框架的基本对象是单资产自身历史
- 不是同一时点横截面的相对排序

对应来源：

- Time Series Momentum
  - https://www.aqr.com/insights/research/journal-article/time-series-momentum
  - https://research.cbs.dk/en/publications/time-series-momentum/

### 5. 时间序列趋势策略里，“趋势估计”和“仓位/缩放”是分开的

Deep Momentum Networks 的公开摘要明确写到：

- 常见时间序列动量策略需要显式定义
  - trend estimator
  - position sizing rule

这说明：

- raw / standardized signal 与最终仓位不是同一个对象
- rule-based signal 没必要强行伪装成连续 z-score 才能存在

对应来源：

- Enhancing Time Series Momentum Strategies Using Deep Neural Networks
  - http://arxiv.org/pdf/1904.04912
  - https://econpapers.repec.org/RePEc:arx:papers:1904.04912

### 6. 技术规则里，价格相对均线的最基础输出本来就是有界离散信号

关于 moving average rule，本次调研到的公开公式包括：

- 若价格高于移动平均，则取 `+1`
- 若价格低于移动平均，则取 `-1`
- 相等则维持或取 `0`

这说明：

- 一类技术规则型 predictor 天然就是 bounded signed rule
- 不存在“必须先 z-score 才能成为 score”的公开必要性

对应来源：

- The Technical Analysis Method of Moving Average Trading
  - https://core.ac.uk/download/pdf/153776849.pdf
- Which Trend Is Your Friend? 摘要
  - https://www.researchgate.net/publication/299434102_Which_Trend_Is_Your_Friend

## Industry-Standard

### 1. 连续 predictor 通常先做极值处理，再标准化

虽然不同机构细节不同，但公开框架高度一致：

- winsorize / cap outliers
- ordinary z-score
- 然后再合成

所以如果后续只选一个最稳妥的通用起点，行业标准就是：

- `winsorization + z-score`

### 2. 时间序列趋势/动量策略通常还会做波动率缩放

公开研究里，时间序列动量经常和 volatility scaling 一起出现。

这至少说明：

- 单资产时间序列 predictor 进入下一层时
- 用单资产自身历史波动或历史分布做缩放是常见做法

对应来源：

- Time Series Momentum and Volatility Scaling
  - https://www.sec.gov/about/divisions-offices/division-economic-risk-analysis/academic-publications/2016_kim_time-series-momentum_ap
  - https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Enhancing Time Series Momentum Strategies Using Deep Neural Networks
  - http://arxiv.org/pdf/1904.04912

## Project-Specific Inference

下面这些不是公开资料逐字给出的结论，而是基于上面证据做的项目层收敛。

### 1. v1 应优先采用 `time-series per asset`，不采用 `cross-sectional per bar`

理由：

- 我们当前主线是时间序列 alpha，不是截面排序
- `time-series momentum` 的原始预测关系是单资产自己的过去预测自己的未来
- 股票因子里的 `region/sector-relative z-score` 主要服务于横截面比较

所以当前最贴合研究对象的 v1 选择是：

- 每个 predictor
- 对每个资产
- 用 rolling window 在该资产自身历史上标准化

### 2. 连续 predictor 的 v1 标准化应是：

- 先做 winsorization
- 再做 rolling ordinary z-score

而不是默认上 `robust z-score`

原因不是 robust 不好，而是：

- 当前知识库里，公开机构方法论最清楚支持的是 ordinary z-score
- 对 `robust z-score` 没有同等强度的机构公开证据

### 3. 规则型 predictor 不应强行再做 z-score

对于：

- `trb_*`
- `sma_price_crossover_*`
- `ema_price_crossover_*`

更稳妥的 v1 做法是：

- 保持它们作为 bounded signed score
- 直接进入下一层

也就是：

- 若原始规则本身有 `-1/0/+1`，就保留该有界形式
- 若原始规则目前是 `0/1`，应先在 score 层改成有方向、中心化后的有界规则，而不是再去滚动 z-score

这里最重要的依据是：

- 公开规则型技术分析公式本来就输出离散仓位/信号
- 公开证据没有要求必须把这类离散规则再转换成 rolling z-score

### 4. `direction alignment` 应在 standardized score 层完成

v1 的统一规则应该是：

- score 越大，代表越偏多 / 预期 alpha 越强

所以：

- 反转类、illiquidity 类、funding/basis 类
- 哪些需要翻符号
- 应该在 standardized score 层一次性定死

## Insufficient Evidence

### 1. `robust z-score` 还没有足够公开证据支持其成为默认方案

目前知识库没有找到与 MSCI 这类公开方法论同等级的证据，证明：

- 在机构 alpha/factor 标准化里
- `median / MAD` 应该默认取代 ordinary mean/std

因此：

- `robust z-score` 目前不能直接被写成 source-backed 默认实现

### 2. `binary / ternary predictor` 的最优统一编码仍未完全被公开资料定死

本次调研可以确定的是：

- 这类规则可以天然是有界离散信号

但公开资料没有统一告诉我们：

- `0/1` 应该映射到 `-1/+1`
- 还是 `0/+1`
- 还是 `-1/0/+1`

所以这一步如果要实现，仍然属于项目设计决策，不是公开方法直接给出的唯一答案。

## 当前收敛结论

如果现在只基于已经调研到的内容，`standardized score` 层最稳妥的 v1 结论是：

1. 连续 predictor：
   - `winsorization + rolling ordinary z-score`
   - 范围是 `time-series per asset`

2. 规则型 predictor：
   - 不强行 rolling z-score
   - 保持为 bounded signed score

3. 方向统一：
   - 在 standardized score 层完成
   - 保证高分统一表示更强 alpha

4. `cross-sectional z-score`：
   - 是成熟方法
   - 但不作为当前时间序列 alpha v1 的默认方案

5. `robust z-score`：
   - 可以作为后续 robustness check
   - 但当前不能直接作为 source-backed 默认实现

## 对下一步实现的影响

这意味着下一步如果进入实现，不应该直接写一个“所有 predictor 都 rolling robust z-score”的通用器。

更合理的 v1 结构应该是：

- `continuous predictor scorer`
  - winsorize
  - rolling z-score

- `rule predictor scorer`
  - bounded signed mapping

- `direction alignment layer`
  - 统一符号

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf
- MSCI Quality Indexes Methodology
  - https://www.msci.com/documents/10199/a13e0b86-7cb6-fc79-f278-60904dfab0ef
- Franklin Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_Franklin_Global_Equity_Index.pdf
- LibertyQ Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_LibertyQ_Global_Equity_Index_May_2019.pdf
- Time Series Momentum
  - https://www.aqr.com/insights/research/journal-article/time-series-momentum
  - https://research.cbs.dk/en/publications/time-series-momentum/
- Time Series Momentum and Volatility Scaling
  - https://www.sec.gov/about/divisions-offices/division-economic-risk-analysis/academic-publications/2016_kim_time-series-momentum_ap
  - https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Enhancing Time Series Momentum Strategies Using Deep Neural Networks
  - http://arxiv.org/pdf/1904.04912
  - https://econpapers.repec.org/RePEc:arx:papers:1904.04912
- The Technical Analysis Method of Moving Average Trading
  - https://core.ac.uk/download/pdf/153776849.pdf
- Which Trend Is Your Friend?
  - https://www.researchgate.net/publication/299434102_Which_Trend_Is_Your_Friend
