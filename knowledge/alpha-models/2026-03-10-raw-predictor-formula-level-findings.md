# Raw Predictor：公式级与定义级调研结果

Date: 2026-03-10
Category: alpha-models

## 目的

把 `raw predictor` 从“方向/设计名”继续推进到“公式级、定义级”。

本文件只记录目前已经有来源支持的定义，不写项目自定义窗口，不补自行推导公式。

## 1. Trend：目前已经到定义级的设计

### 1.1 Variable Moving Average Rule

来源：

- [Technical trading rules in the cryptocurrency market](https://www.researchgate.net/publication/337814783_Technical_trading_rules_in_the_cryptocurrency_market)

目前能确认到的定义：

- 这篇文章明确使用 `Variable Moving Average (VMA)` 规则。
- 规则本质是比较“短期均线”和“长期均线”。
- 文中短端直接取当前价格的对数，长端是过去 `n` 天价格对数的移动平均。
- 文中测试的 `n` 是：
  - `20`
  - `50`
  - `100`
  - `150`
  - `200`
- 交易信号定义为：
  - 短端高于长端时发出买入信号
  - 否则不持有

当前可严格写入知识库的 concrete design：

- `current log price vs n-day moving average of log price`
- `n ∈ {20, 50, 100, 150, 200}`

当前还不能直接推出的内容：

- 4h 场景下应如何映射这些 `n`
- 是否要用 `EMA gap` 形式替代该 VMA 定义

### 1.2 SMA / EMA Rule

来源：

- [Technical Analysis on the Bitcoin Market: Trading Opportunities or Investors’ Pitfall?](https://www.mdpi.com/2227-9091/8/2/44)

目前能确认到的定义：

- `SMA` 定义为固定窗口价格的简单平均
- `EMA` 定义为带平滑系数的指数加权平均
- 文中明确把 MA/EMA 与价格交叉作为信号规则：
  - MA/EMA 从下向上穿越价格时，形成买入信号
  - 从上向下穿越时，形成卖出信号
- 文中使用的窗口示例：
  - `12`
  - `24`
  - `72`
- EMA 的平滑参数示例：
  - `λ = 0.94`

当前可严格写入知识库的 concrete design：

- `SMA(k)`
- `EMA(k, λ)`
- `price-vs-MA crossover`
- `price-vs-EMA crossover`

当前还不能直接推出的内容：

- 哪组窗口应该成为 canonical crypto raw predictor
- `EMA fast / EMA slow - 1` 是否能直接当作 source-backed canonical 定义

### 1.3 Trading Range Breakout

来源：

- [The profitability of technical trading rules in the Bitcoin market](https://www.sciencedirect.com/science/article/pii/S1544612319303770)
- 搜索结果中给出的论文片段已明确列出该规则的定义与参数

目前能确认到的定义：

- `support_t` 定义为过去 `n` 个观测的最低价
- `resistance_t` 定义为过去 `n` 个观测的最高价
- 信号定义为：
  - 若当前价格高于 `resistance_t`，则买入
  - 若当前价格低于 `support_t`，则卖出
- 文中使用的 `n` 是：
  - `50`
  - `150`
  - `200`

当前可严格写入知识库的 concrete design：

- `support = rolling min of prior n prices`
- `resistance = rolling max of prior n prices`
- `breakout buy/sell on support-resistance breach`
- `n ∈ {50, 150, 200}`

当前还不能直接推出的内容：

- 用 close、high/low 还是别的价格输入更合适
- 4h 场景是否应保持同一窗口长度还是做频率映射

## 2. Funding / Perp：目前已经到定义级的设计

### 2.1 Funding Rate Level

来源：

- [Predicting Ethereum price with perpetual futures contract funding rates](https://aaltodoc.aalto.fi/items/7a663327-a08a-4f52-b274-33e881be7c7f)
- [Funding Rates | Coin Metrics Docs](https://docs.coinmetrics.io/market-data/market-data-overview/funding-rates/funding-rates)

目前能确认到的定义：

- `funding rate level` 本身就是可研究对象
- 该研究直接围绕 ETH perpetual funding rates 与后续价格关系展开
- Coin Metrics 明确区分：
  - `realized funding rate`
  - `predicted funding rate`

当前可严格写入知识库的 concrete design：

- `realized funding rate`
- `predicted funding rate`
- `lagged funding rate`

当前还不能直接推出的内容：

- 该 predictor 最佳是用 level、moving average 还是 shock
- 哪个 lookback 应成为 canonical 规范

### 2.2 Funding Formula Components

来源：

- [Coinbase International Exchange Trading Rules](https://www.coinbase.com/en-mx/international-exchange/legal/trading-rules)
- [Funding Rates | Coinbase Help](https://help.coinbase.com/derivatives/perpetual-style-futures/funding-rate)
- [Funding Rate | Futures Help Center](https://futuresdoc.gitbook.io/help-center/perpetual/overview/funding-rate)

目前能确认到的定义：

- funding rate 是由 perpetual 与 spot 的偏离驱动的
- Coinbase 给出明确公式：
  - `Funding Rate = α * Premium + (1 - α) * Previous Funding Rate`
  - `Premium = (Mark Price - Index Price) / Index Price / 24`
- Binance-like 文档明确 funding 的核心构件包括：
  - `premium index`
  - `interest/base component`
- 同类文档还给出：
  - `Funding Rate Basis Rate = Latest Funding Rate × (Time Remaining / Settlement Interval)`

当前可严格写入知识库的 concrete design：

- `premium`
- `funding rate level`
- `previous funding rate`
- `predicted funding rate`
- `funding-basis-rate`

当前还不能直接推出的内容：

- `funding shock`
- `funding term structure`
- `funding-price divergence`

这些方向现在只到“合理候选”，还没到知识库里有统一公式级支持。

### 2.3 Basis

来源：

- [Anatomy of cryptocurrency perpetual futures returns](https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/)
- [Coin Metrics API docs](https://docs.coinmetrics.io/api/v4)

目前能确认到的定义：

- perpetual futures returns 的研究明确把 `basis` 作为 predictor 家族
- 文中还提到：
  - `spot premium`
  - `log basis`
  - futures 与 spot spread
- Coin Metrics 对 basis 的定义已经清楚到指标层：
  - `basis` 是 futures price 与 underlying spot price 的相对差
  - 其 API 指标里有 annualized basis，如 `30d/120d expiration`

当前可严格写入知识库的 concrete design：

- `relative futures-spot basis`
- `log basis`
- `annualized basis`

当前还不能直接推出的内容：

- perpetual 合约在无固定到期日下，我们应采用哪一种统一 basis 定义
- `basis` 和 `funding` 如何组合成单一 raw predictor

## 3. 到目前为止可以严格确认的 raw predictor 定义

当前知识库已经可以严格确认的、到“定义级”的 raw predictor 包括：

- `current price vs moving average`
- `current log price vs n-day moving average of log prices`
- `SMA(k)`
- `EMA(k, λ)`
- `support / resistance breakout`
- `realized funding rate`
- `predicted funding rate`
- `premium`
- `funding-basis-rate`
- `relative futures-spot basis`
- `log basis`
- `annualized basis`

## 4. 当前仍未调研到足够细的部分

截至现在，下面这些仍然不能说知识库已经完全调研清楚：

- `EMA gap = EMA_fast / EMA_slow - 1`
- `funding shock`
- `funding term structure`
- `funding-price divergence`
- perpetual `basis` 的统一 canonical 公式
- 把日频窗口严谨迁移到 4h 的规则

所以当前仍不能直接拍板一个“完全 source-backed 的 canonical v1 raw predictor 清单”。

## Sources

- Technical trading rules in the cryptocurrency market
  - https://www.researchgate.net/publication/337814783_Technical_trading_rules_in_the_cryptocurrency_market
- Technical Analysis on the Bitcoin Market: Trading Opportunities or Investors’ Pitfall?
  - https://www.mdpi.com/2227-9091/8/2/44
- The profitability of technical trading rules in the Bitcoin market
  - https://www.sciencedirect.com/science/article/pii/S1544612319303770
- Predicting Ethereum price with perpetual futures contract funding rates
  - https://aaltodoc.aalto.fi/items/7a663327-a08a-4f52-b274-33e881be7c7f
- Funding Rates | Coin Metrics Docs
  - https://docs.coinmetrics.io/market-data/market-data-overview/funding-rates/funding-rates
- Coinbase International Exchange Trading Rules
  - https://www.coinbase.com/en-mx/international-exchange/legal/trading-rules
- Funding Rates | Coinbase Help
  - https://help.coinbase.com/derivatives/perpetual-style-futures/funding-rate
- Funding Rate | Futures Help Center
  - https://futuresdoc.gitbook.io/help-center/perpetual/overview/funding-rate
- Anatomy of cryptocurrency perpetual futures returns
  - https://www.research.ed.ac.uk/en/publications/anatomy-of-cryptocurrency-perpetual-futures-returns/
- Coin Metrics API docs
  - https://docs.coinmetrics.io/api/v4
