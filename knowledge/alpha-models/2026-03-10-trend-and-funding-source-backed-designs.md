# Trend 与 Funding：已调研到的具体 Predictor 设计

Date: 2026-03-10
Category: alpha-models

## 研究目标

补齐 `raw predictor` 里之前没有调研充分的两块：

1. `trend` 具体设计
2. `funding / perp` 具体设计

本文件只记录已经有来源支撑的具体 predictor 设计，不做项目层补充。

## A. Trend：已调研到的具体设计

### 1. Moving Average Rules

#### 直接证据

关于 Bitcoin 技术交易规则的研究明确写到：

- 研究应用了七种 `trend-following indicators`
- 其中包括 `moving averages`
- 这些规则在 Bitcoin 市场上具有显著预测力

Source:

- The profitability of technical trading rules in the Bitcoin market
  - https://www.sciencedirect.com/science/article/pii/S1544612319303770

另一篇研究考察了隐私币上的简单移动平均规则：

- 使用 `simple moving average trading strategies`
- 在部分加密资产上有效，但并非对整个样本普遍有效

Source:

- Profitability of technical trading rules among cryptocurrencies with privacy function
  - https://www.sciencedirect.com/science/article/pii/S1544612320300829

#### 目前能确认的具体设计

- `moving average rule`
- `simple moving average strategy`
- `variable moving average strategy`

#### 目前还不能确认到的细节

- 哪一组均线窗口应作为 canonical crypto v1
- 例如 `20/60`、`10/50`、`120/360` 等，目前知识库还没有充足证据定死

### 2. Trading Range Breakout

#### 直接证据

Bitcoin 技术交易规则研究明确写到：

- `trading range breakout` 具有显著 forecasting power
- 基于 Sharpe ratio 能跑赢 buy-and-hold

Source:

- The profitability of technical trading rules in the Bitcoin market
  - https://www.sciencedirect.com/science/article/pii/S1544612319303770

#### 目前能确认的具体设计

- `trading range breakout`
- `breakout above/below prior range`

#### 目前还不能确认到的细节

- 用多少个 bar/day 作为 breakout 窗口
- 是否需要 band/filter
- 是否应使用 high/low range 还是 close-only range

### 3. Trend-based technical indicators

#### 直接证据

《Trend-based forecast of cryptocurrency returns》明确写到：

- `trend-based indicators predict crypto market returns at various horizons`
- `price-based signals outperform volume-based signals in the short term`
- `volume-based signals are more effective in the long run`

Source:

- Trend-based forecast of cryptocurrency returns
  - https://www.sciencedirect.com/science/article/pii/S0264999323001359

#### 目前能确认的具体设计层级

这篇文章在摘要层面只足够支持：

- `trend-based price indicators` 是具体 predictor 类
- `trend-based volume indicators` 是具体 predictor 类

但它没有在当前公开摘要里把每个 indicator 的公式展开到可以直接做 canonical 设计。

### A 结论

`trend` 这一块，现在知识库已经足够明确支持：

- `moving average rules`
- `trading range breakout`
- 更广义的 `trend-based price indicators`

但仍然**不够**支持我们直接写出某个固定窗口、某个固定公式就是 v1 canonical 设计。

也就是说：

- `EMA gap` 这个方向现在已有“趋势类均线规则”层面的来源支持
- 但 `ema_fast / ema_slow - 1` 的具体形式和窗口，仍未被知识库调研到足够细

## B. Funding / Perp：已调研到的具体设计

### 1. Funding rate level

#### 直接证据

关于 ETH perpetual funding rate 的研究明确写到：

- funding rates 与市场价格存在 Granger causality
- funding rates 对价格变化有 predictive power
- 以 forecasted funding rates 为基础的策略回测表现有边际优势

Source:

- Predicting Ethereum price with perpetual futures contract funding rates
  - https://aaltodoc.aalto.fi/items/7a663327-a08a-4f52-b274-33e881be7c7f

#### 目前能确认的具体设计

- `funding rate level`
- `forecasted funding rate`

#### 目前仍不够明确的部分

- 预测窗口
- 是否应使用平滑 funding、lagged funding、还是变化率

### 2. Trading behavior / speculative net-short behavior

#### 直接证据

关于 crypto returns 与交易行为的研究明确写到：

- speculative retail traders 的 `net-short trading behavior`
- 以及其变化
- 对 cryptocurrency returns 有显著、经济上强的预测力

Source:

- Predictability of crypto returns: The impact of trading behavior
  - https://www.sciencedirect.com/science/article/pii/S2214635023000266

#### 目前能确认的具体设计

- `net-short trading behavior`
- `change in net-short trading behavior`

#### 现实限制

这类 predictor 依赖持仓分类数据，不是 Binance 公共 funding 文件能直接提供的。

### 3. Basis

#### 直接证据

关于 perpetual futures return anatomy 的研究明确写到：

- 他们评估了 `134 return predictors`
- predictor 家族包括：
  - `basis`
  - `momentum`
  - `volume`
  - `size`
  - `volatility`
- 结果里存在 `48 statistically significant futures returns`
- 两因子模型里包含 `basis` 与 `price-volume factors`

Source:

- Anatomy of cryptocurrency perpetual futures returns
  - https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/

#### 目前能确认的具体设计

- `basis` 是 perp/期货 returns 的具体 predictor 家族

#### 当前限制

- 我们现阶段知识库还没把这篇文章里 basis 的具体计算式挖到足够细
- 所以还不能直接写成 canonical 公式

### 4. Funding arbitrage / carry

#### 直接证据

关于 funding rate arbitrage 的研究明确围绕 funding rate 设计策略，并证明其风险收益特征可观。

Source:

- Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX
  - https://www.sciencedirect.com/science/article/pii/S2096720925000818

NBER 的 staking 研究也明确写到：

- 存在 `crypto carry premia`

Source:

- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640

#### 目前能确认的具体设计

- `funding carry`
- 更广义的 `crypto carry`

#### 当前限制

- 这里更强的是“策略/风险收益”层面的证据
- 还没有足够细的 predictor 公式，能直接变成 canonical raw predictor 规范

## 当前能严格声称已调研到的 source-backed concrete designs

到现在为止，`trend + funding` 里能严格写进知识库的具体设计有：

### Trend

- `moving average rule`
- `simple moving average strategy`
- `variable moving average strategy`
- `trading range breakout`

### Funding / Perp

- `funding rate level`
- `forecasted funding rate`
- `net-short trading behavior`
- `change in net-short trading behavior`
- `basis`
- `funding carry`

## 当前仍未调研到足够细，不能直接写进 canonical v1 的

- `ema_gap = ema_fast / ema_slow - 1`
- `funding_term_structure`
- `funding shock`
- `funding-price divergence`
- `basis exact formula`

这些方向现在只能说“有研究方向支撑”，还不能说“知识库已经有足够细的具体 canonical 设计”。

## 阶段性结论

`raw predictor` 方案现在仍然**没有完全调研清楚**。

但相比上一轮，已经补上了两点：

1. `trend` 里至少有了可引用的具体设计：
   - `moving average rules`
   - `trading range breakout`
2. `perp/funding` 里至少有了可引用的具体设计：
   - `funding rate level`
   - `forecasted funding rate`
   - `basis`
   - `net-short trading behavior`

下一步真正该补的是：

- 把这些设计继续往“公式级别、窗口级别、可直接纳入 canonical v1”的层次挖深

## Sources

- The profitability of technical trading rules in the Bitcoin market
  - https://www.sciencedirect.com/science/article/pii/S1544612319303770
- Profitability of technical trading rules among cryptocurrencies with privacy function
  - https://www.sciencedirect.com/science/article/pii/S1544612320300829
- Trend-based forecast of cryptocurrency returns
  - https://www.sciencedirect.com/science/article/pii/S0264999323001359
- Predicting Ethereum price with perpetual futures contract funding rates
  - https://aaltodoc.aalto.fi/items/7a663327-a08a-4f52-b274-33e881be7c7f
- Predictability of crypto returns: The impact of trading behavior
  - https://www.sciencedirect.com/science/article/pii/S2214635023000266
- Anatomy of cryptocurrency perpetual futures returns
  - https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/
- Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX
  - https://www.sciencedirect.com/science/article/pii/S2096720925000818
- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640
