# Rule Form Whitelist

Date: 2026-03-10
Category: alpha-models

## 研究问题

在 `rule / grammar generator` 中，`moving_average_rule`、`trading_range_breakout`、`filter_rule` 到底应该生成哪些具体 rule forms。

## 核心结论

1. 公开资料足够支持一版 **rule form whitelist v1**。
2. `moving_average_rule` 不应只做一种形式，至少应区分：
   - price-vs-MA rule
   - short-vs-long MA crossover
3. `trading_range_breakout` 的核心形式是：
   - price breaks above rolling max
   - price breaks below rolling min
   - ternary coding
4. `filter_rule` 的核心形式是：
   - price relative to past reference exceeds threshold
   - 超阈值才触发 bullish / bearish signal
5. v1 不应同时引入过多复杂 forms；先把这三类核心 forms 跑通。

## Source-Backed

### 1. Moving average rules 至少有两种 canonical forms

公开技术规则文献里，最常见的 MA rule 不是单一一种，而至少包括：

- `price vs moving average`
- `short moving average vs long moving average`

前者例如：

- close above SMA(n)
- close below SMA(n)

后者例如：

- SMA(short) above SMA(long)
- EMA(short) above EMA(long)

来源：

- Technical Analysis on the Bitcoin Market: Trading Opportunities or Investors’ Pitfall?
  - https://www.mdpi.com/2227-9091/8/2/44
- The profitability of simple moving averages and trading range breakout in the Asian stock markets
  - https://doi.org/10.1016/j.asieco.2005.12.001

### 2. Trading range breakout 的 canonical form 就是上破 / 下破区间

TRB 文献和 support-resistance 规则的核心都是：

- 若价格高于过去窗口高点，触发 bullish breakout
- 若价格低于过去窗口低点，触发 bearish breakout
- 否则中性

这天然对应：

- `+1 / 0 / -1`

来源：

- The profitability of simple moving averages and trading range breakout in the Asian stock markets
- Simple technical trading rules of stock returns: evidence from 1987 to 1998 in Chile

### 3. Filter rule 的 canonical form 是阈值过滤的 directional rule

技术规则文献中，filter rules 的典型形式是：

- 若价格相对过去参考价上涨超过 `x%`
  - 做多
- 若价格相对过去参考价下跌超过 `x%`
  - 做空
- 否则保持中性

来源：

- The predictive ability of technical trading rules: an empirical analysis of developed and emerging equity markets
- Further evidence on the returns to technical trading rules: Insights from fourteen currencies

## Rule Form Whitelist V1

### A. Moving Average Rule

#### Source-backed forms

1. `price_above_sma(n)`
   - `close > sma(close, n)` -> `+1`
   - else `-1`

2. `price_above_ema(n)`
   - `close > ema(close, n)` -> `+1`
   - else `-1`

3. `sma_crossover(short, long)`
   - `sma(short) > sma(long)` -> `+1`
   - else `-1`

4. `ema_crossover(short, long)`
   - `ema(short) > ema(long)` -> `+1`
   - else `-1`

#### Not in v1

- triple moving average rules
- adaptive / variable MA rules with free parameters

这些有研究，但不应在 v1 一起铺开。

### B. Trading Range Breakout

#### Source-backed forms

1. `breakout_high_low(n)`
   - `close > rolling_max(close, n)` -> `+1`
   - `close < rolling_min(close, n)` -> `-1`
   - else `0`

2. `support_resistance_break(n)`
   - 与上面本质等价
   - v1 可以不单独实现，合并到 `breakout_high_low`

#### Not in v1

- volatility-adjusted breakout
- channel breakout with extra band logic

### C. Filter Rule

#### Source-backed forms

1. `price_filter_from_ref(n, threshold)`
   - 若 `close / ref_price(n) - 1 > threshold` -> `+1`
   - 若 `< -threshold` -> `-1`
   - else `0`

其中 `ref_price(n)` 可以是：

- lagged close
- rolling mean close

为了 v1 收敛，建议只保留：

2. `price_filter_from_lag(n, threshold)`
   - `close / lag(close, n) - 1`

#### Not in v1

- 复杂多阈值 filter
- filter + MA hybrid rule

## Family-to-Form Mapping

### Moving average family

推荐 v1 形式：

- `price_above_sma(n)`
- `price_above_ema(n)`
- `sma_crossover(short, long)`
- `ema_crossover(short, long)`

### Breakout family

推荐 v1 形式：

- `breakout_high_low(n)`

### Filter family

推荐 v1 形式：

- `price_filter_from_lag(n, threshold)`

## What Is Still Not Fully Fixed

下面这些还不是知识库直接定稿：

1. crossover 的 `short/long` 具体配对
2. filter rule 的 threshold 集合
3. 是否在 v1 就加入 `price_above_sma` 与 `sma_crossover` 两种 MA forms，还是先只上其中一种

## Project-Specific Inference

如果要尽快形成一个可实施的 `rule / grammar generator v1`，最稳的 form whitelist 是：

- `price_above_sma(n)`
- `price_above_ema(n)`
- `breakout_high_low(n)`
- `price_filter_from_lag(n, threshold)`

而把：

- `sma_crossover(short, long)`
- `ema_crossover(short, long)`

放到 v1.1，而不是 v1 同时铺开。

原因：

- 这样 rule family 仍然覆盖完整
- operator 最少
- 候选数量不会膨胀太快
- 更容易先判断 rule generator 这条线本身有没有增益

## 结论

`rule / grammar generator` 现在已经接近可实施：

- family 已基本清楚
- operator 已基本清楚
- horizon 已基本清楚
- 具体 form 也已经收敛到少数 canonical rules

剩下没完全定死的，只剩：

- v1 是不是把 crossover 一起上
- filter 的 threshold 用几档
