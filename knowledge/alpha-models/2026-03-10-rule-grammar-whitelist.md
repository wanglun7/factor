# Rule / Grammar Generator Whitelist

Date: 2026-03-10
Category: alpha-models

## 研究问题

如果第一层要加一条 `rule / grammar generator`，那 v1 到底哪些 rule family、哪些 operator、哪些 horizon 能进入 whitelist。

## 核心结论

1. 公开研究和开源资料足够支持一版 **rule / grammar whitelist v1**。
2. 对当前项目，v1 最合理的 rule family 不是无限扩，而是先收在：
   - moving average rules
   - trading range breakout / support-resistance
   - filter rules
3. `channel breakout` 和更复杂规则有研究支持，但不应在 v1 一起放进来。
4. operator whitelist 应控制在少数基础时间序列算子，不做全量 Alpha101 grammar。
5. horizon 应先用少数经典尺度，不做密集网格。

## Source-Backed

### 1. Moving Average Rule 是明确的 rule family

技术交易规则文献长期反复研究：

- simple moving average rule
- variable moving average rule
- price / moving average crossover

来源：

- The profitability of the simple moving averages and trading range breakout in the Asian stock markets
  - https://doi.org/10.1016/j.asieco.2005.12.001
- Further evidence on the returns to technical trading rules: Insights from fourteen currencies
  - https://doi.org/10.1016/j.mulfin.2023.100808

### 2. Trading Range Breakout / Support-Resistance 也是明确的 rule family

文献明确把这些作为独立 rule family 研究：

- trading range breakout
- support / resistance rules

来源：

- Simple technical trading rules of stock returns: evidence from 1987 to 1998 in Chile
  - https://doi.org/10.1016/S1566-0141(00)00006-6
- The predictive ability of technical trading rules: an empirical analysis of developed and emerging equity markets
  - https://link.springer.com/article/10.1007/s11408-023-00433-2

### 3. Filter Rule 也是经典 technical rule family

技术交易规则综述和后续实证里，filter rule 一直是核心家族之一。

来源：

- The predictive ability of technical trading rules: an empirical analysis of developed and emerging equity markets
  - https://link.springer.com/article/10.1007/s11408-023-00433-2
- Further evidence on the returns to technical trading rules: Insights from fourteen currencies
  - https://doi.org/10.1016/j.mulfin.2023.100808

### 4. Operator 方面，公开资料支持少数基础时序算子

从 Qlib 和 Alpha101/operator 资料里，最清楚、最通用的一批 operator 是：

- `Ref / lag`
- `Mean / EMA`
- `Max / Min`
- `Delta`
- `Sign`
- `If`

这些足够支撑：

- MA rules
- crossover
- breakout
- filter rules

来源：

- Qlib feature engineering / operators
  - https://deepwiki.com/microsoft/qlib/4.6-datasets-and-feature-engineering
- 101 Formulaic Alphas
  - https://arxiv.org/abs/1601.00991

### 5. Horizon 方面，公开研究支持少数经典窗口，而不是密集网格

文献中常见且反复出现的技术规则窗口包括：

- 20
- 50
- 60
- 150
- 200

也有更短的：

- 12 / 24 / 72

但文献整体更支持“少数经典窗口组合”，不支持一开始做高密度网格乱扫。

来源：

- Asian stock markets MA/TRB paper
  - 20, 60
- 技术规则比较研究
  - 150-day MA
- 我们之前已有的 formula-level 调研
  - 12 / 24 / 72 作为具体示例

## Rule Family Whitelist V1

### Source-backed whitelist

- `moving_average_rule`
- `trading_range_breakout`
- `support_resistance_rule`
- `filter_rule`

### Not in v1

- `bollinger_band_rule`
- `oscillator_rule`
- `channel_breakout_rule`

这些不是没研究支持，而是 v1 不该同时把 rule family 开太多。

## Operator Whitelist V1

### Source-backed and sufficient

- `lag(x, n)`
- `sma(x, n)`
- `ema(x, n)`
- `rolling_max(x, n)`
- `rolling_min(x, n)`
- `delta(x, n)`
- `sign(x)`
- `if(condition, a, b)`

### Deliberately excluded in v1

- `corr`
- `cov`
- `ts_rank`
- `rank`
- `quantile`
- `slope`
- `r_square`

原因：

- 这些更适合后续扩展或更复杂的 grammar search
- v1 先把最基本、最可解释的 technical rule family 跑清楚

## Horizon Whitelist V1

### Source-backed family

- `short`
- `medium`
- `long`

### Project-specific mapping candidates

知识库不直接给出 crypto 4h 的唯一映射，但从文献和现有资料出发，v1 最合理的候选映射是：

- `short`
  - 12 / 24 / 72 bars 这类短规则尺度
- `medium`
  - 20 / 50 / 60 日等价尺度
- `long`
  - 150 / 200 日等价尺度

注意：

- 这里“具体映射到 4h”还不是 source-backed 定稿
- 只能说 classic horizons 的 family 是清楚的

## Project-Specific Inference

如果按当前项目落地 rule generator v1，最合理的限制应是：

### Rule family

- `moving_average_rule`
- `trading_range_breakout`
- `filter_rule`

把 `support_resistance_rule` 并入 breakout 路线，不单独做一套实现。

### Operator

只用：

- `lag`
- `sma`
- `ema`
- `rolling_max`
- `rolling_min`
- `delta`
- `sign`
- `if`

### Horizon

先不要用密集扫描。

更合理是少数经典组合，例如：

- short: `12 / 24 / 72`
- medium: `20 / 50 / 60`
- long: `150 / 200`

但这一步仍然属于工程定稿，不是知识库已经完全定死。

## 结论

`rule / grammar generator` 的 v1 whitelist 已经可以收敛到一个合理边界：

- family 先收在 MA / breakout / filter
- operator 先收在基础时序算子
- horizon 先用少数经典尺度

当前还没有被知识库完全定死的，只剩：

- classic windows 如何映射到 crypto 4h
- v1 是先做 MA + breakout，还是把 filter rule 也一起做进去
