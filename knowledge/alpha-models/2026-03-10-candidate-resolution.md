# Raw Predictor Candidate Resolution

Date: 2026-03-10
Category: alpha-models

## 目的

把当前 raw predictor code catalog 里剩余未定项彻底分清：

- 哪些可以升级成 implementable
- 哪些应从代码 catalog 移除

本文件只保留基于外部搜索和已存知识库的结论，不做项目层臆测。

## 结论总表

### 可升级为 implementable

- `sma_price_crossover_12`
- `sma_price_crossover_24`
- `sma_price_crossover_72`
- `ema_price_crossover_12`
- `ema_price_crossover_24`
- `ema_price_crossover_72`

原因：

- 知识库已经有公式级/定义级依据：
  - `SMA(k)`
  - `EMA(k, λ)`
  - `price-vs-MA crossover`
  - `price-vs-EMA crossover`
- 公开资料已经给出窗口示例：
  - `12`
  - `24`
  - `72`

来源：

- Technical Analysis on the Bitcoin Market: Trading Opportunities or Investors’ Pitfall?
  - https://www.mdpi.com/2227-9091/8/2/44
- [已有知识库] [2026-03-10-raw-predictor-formula-level-findings.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-raw-predictor-formula-level-findings.md)

## 应从代码 catalog 移除

### 1. `forecasted_funding_rate`

结论：

- 从代码 catalog 移除

原因：

- 不是公式问题，而是现实数据问题
- Coin Metrics 对 `predicted funding rate` 的定义已经很清楚
- 但它是独立数据流，不是我们当前公开数据链稳定可得的数据
- Coin Metrics 文档还显示覆盖开始时间有限，例如 Binance 从 2024-11-06 才开始
- 所以它不适合作为当前完整历史流程里的 implementable raw predictor

来源：

- Predicted Funding Rates | Coin Metrics Docs
  - https://gitbook-docs.coinmetrics.io/market-data/market-data-overview/funding-rates/predicted-funding-rates

### 2. `annualized_basis`

结论：

- 从代码 catalog 移除

原因：

- `annualized basis` 的公式对于有固定到期日 futures 是明确的
- 但知识库和文档都把它定义成：
  - futures vs spot
  - 按到期剩余天数做 annualization
- perpetual 没有固定 expiry
- 所以 `annualized_basis` 不能直接作为当前 perp raw predictor 的 canonical 对象

来源：

- Basis | Coin Metrics Docs
  - https://gitbook-docs.coinmetrics.io/market-data/market-data-overview/basis
- What is Basis? | Cube Exchange
  - https://www.cube.exchange/what-is/basis

### 3. `funding_carry`

结论：

- 从代码 catalog 移除

原因：

- 当前证据支持的是 `funding carry trade` 作为策略方向
- 它更像：
  - long spot / short perp
  - 收 funding + basis 的 delta-neutral 结构
- 不是一个独立、单一、已经在知识库里收敛出公式的 raw predictor
- 如果继续放在 raw predictor catalog，会混淆“单变量 predictor”和“策略构造”

来源：

- Exploring Risk and Return Profiles of Funding Rate Arbitrage on CEX and DEX
  - https://www.sciencedirect.com/science/article/pii/S2096720925000818
- What is Basis? | Cube Exchange
  - https://www.cube.exchange/what-is/basis

### 4. `generic_time_series_momentum`

结论：

- 从代码 catalog 移除

原因：

- `time-series momentum` 作为方向是成立的
- 但当前知识库已实现层已经有更具体的趋势 predictor：
  - `vma_*`
  - `trb_*`
  - 以及即将升级的 `sma/ema crossover`
- `generic_time_series_momentum` 只是一个泛化占位名，不是单一 canonical 公式
- 如果保留，只会和现有具体 trend predictor 重叠

来源：

- Time series momentum
  - https://econpapers.repec.org/RePEc:eee:jfinec:v:104:y:2012:i:2:p:228-250
- Time Series Momentum Implemented
  - https://research.cbs.dk/en/studentProjects/time-series-momentum-implemented-testing-the-performance-of-long-/
- [已有知识库] [2026-03-10-raw-predictor-source-backed-designs.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-raw-predictor-source-backed-designs.md)

### 5. `generic_short_term_reversal_intraday`

结论：

- 从代码 catalog 移除

原因：

- 当前外部证据只能支持：
  - crypto 存在 intraday momentum 与 reversal
  - 以及 daily `last-day return` 的反转信号
- 但没有足够的公开定义把它收敛成单一、可直接编码的 intraday reversal 公式
- 继续把它留在代码 catalog，只会保留一个模糊占位项

来源：

- Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both
  - https://www.sciencedirect.com/science/article/pii/S1062940822000833
- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://www.sciencedirect.com/science/article/pii/S1057521921002349

## 阶段性结论

对当前 code catalog，最干净的处理是：

- 升级 6 个 `SMA/EMA crossover`
- 移除 5 个未闭环项

这样 raw predictor 代码层只保留：

- 已研究透
- 可真实计算
- 可完整评估

知识库仍保留所有被移除项的研究记录，但不再让它们占用代码 catalog 的位置。
