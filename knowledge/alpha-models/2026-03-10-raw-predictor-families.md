# Raw Predictor 家族：有哪些、怎么做、哪些适合当前项目

Date: 2026-03-10
Category: alpha-models

## 研究问题

alpha 层最前面的 `raw predictors` 到底有哪些典型家族。

要回答的不只是“列几个因子名”，而是：

- 按机构/文献，predictor 通常分哪些类
- 每类 predictor 的原始输入是什么
- 通常怎么构造
- 对我们当前 4h crypto 项目，哪些类现在可做，哪些暂时做不了

## 核心结论

`raw predictors` 可以稳定地归到下面 6 类：

1. `price / trend`
2. `reversal / mean reversion`
3. `volatility / liquidity / implementation`
4. `derivatives / carry / crowding`
5. `on-chain value / usage / tokenomics`
6. `attention / sentiment / macro / cross-asset state`

对我们当前项目最现实的排序是：

- 现在立刻可做：
  - `price / trend`
  - `reversal`
  - `volatility / liquidity`
- 数据补齐后再做：
  - `derivatives / carry / crowding`
  - `on-chain value / usage`
- 更后面再做：
  - `attention / sentiment`

## 1. Price / trend predictors

### 研究依据

Liu 和 Tsyvinski 的研究明确指出：

- crypto returns 可被 `time-series momentum` 预测
- attention proxy 也显著预测 returns

Source:

- Risks and Returns of Cryptocurrency
  - https://www.nber.org/papers/w24877

crypto 的 intraday / interday 研究也继续支持：

- 存在 momentum 效应
- 且在某些状态下更明显

Sources:

- Dynamic time series momentum of cryptocurrencies
  - https://www.sciencedirect.com/science/article/pii/S1062940821000590
- State transitions and momentum effect in cryptocurrency market
  - https://www.sciencedirect.com/science/article/pii/S1544612325016101

### 原始输入

- close
- high / low
- volume

### 常见构造方式

- lookback return
  - `ret_30bar`
  - `ret_120bar`
  - `ret_360bar`
- moving average gap
  - `ema_fast / ema_slow - 1`
- breakout
  - `close / rolling_max`
  - `close / rolling_min`
- trend persistence
  - 连涨/连跌计数

### 对我们项目的意义

这类 predictor 是当前最容易先做对的，因为：

- 数据最完整
- 工程最简单
- 与我们已有 4h 数据天然对齐

当前代表：

- `ema_gap_120_360`
- `breakout_360bar`

## 2. Reversal / mean reversion predictors

### 研究依据

crypto 文献里，反转不是边缘现象，而是主线之一。

ScienceDirect 这篇关于 crypto 的研究指出：

- 很强的预测信号来自前一天收益
- 低上一日收益的币后续表现更好
- 但结果依赖 liquidity
- 最大、最可交易的币更接近日动量，而不是普遍反转

Source:

- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://www.sciencedirect.com/science/article/pii/S1057521921002349

另一篇关于 intraday predictability 的研究也表明：

- crypto 同时存在 intraday momentum 和 reversal
- 并且会随 liquidity、jumps、事件而变化

Source:

- Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both
  - https://www.sciencedirect.com/science/article/pii/S1062940822000833

### 原始输入

- short-horizon returns
- jump proxies
- intrabar range

### 常见构造方式

- `-ret_1bar`
- `-ret_6bar`
- `-ret_18bar`
- volatility-adjusted reversal
  - `-ret_h / realized_vol`
- streak reversal
  - 先累计连涨/连跌，再做反向 predictor

### 对我们项目的意义

这类 predictor 对 4h 特别重要，因为：

- 4h 已经足够短，容易出现过度反应和回吐
- 但同时也更怕交易成本和延迟

当前代表：

- `rev_18bar_voladj`

## 3. Volatility / liquidity / implementation predictors

### 研究依据

Gu, Kelly, Xiu 的机器学习资产定价研究表明：

- 主导 predictor 家族里包括 momentum、liquidity、volatility

Source:

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398

crypto 相关研究也强调：

- reversal 和 momentum 的表现依赖 liquidity
- intraday predictability 会受 liquidity 影响

Sources:

- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://www.sciencedirect.com/science/article/pii/S1057521921002349
- Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both
  - https://www.sciencedirect.com/science/article/pii/S1062940822000833

### 原始输入

- volume
- dollar volume
- high / low / close
- possibly order-book depth

### 常见构造方式

- realized volatility
- Amihud illiquidity
- volume shock
- turnover shock
- liquidity-adjusted trend / reversal

### 对我们项目的意义

这类 predictor 有两种角色：

1. 本身可作为 alpha predictor
2. 更常见的是作为 condition / implementation filter

对当前项目，第一版最实用的定位是：

- 先作为 predictor 的调节项和评估维度
- 不急着全部独立做成 alpha 主因子

## 4. Derivatives / carry / crowding predictors

### 研究依据

crypto 市场一个明显区别于股票的地方，是衍生品结构变量可能直接带预测力。

staking 研究表明：

- staking ratios 正向预测 excess returns
- crypto carry premia 显著

Source:

- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640

对 perp 市场，funding rate 本身是非常自然的 crowding / carry proxy。
虽然我这次没找到足够强、且长期公开可用的数据文献来支撑 Binance OI 历史，但方向本身是对的。

### 原始输入

- funding rate
- open interest
- basis
- perp premium
- staking ratio / staking yield

### 常见构造方式

- average funding level
- funding change / funding term structure
- OI change
- funding-price divergence
- carry spread

### 对我们项目的意义

这是我们中期必须补的一类。

原因：

- 这类 predictor 是 crypto 特有信息
- 可能比纯价格类更接近“结构性 alpha”

但现实约束也明确：

- Binance 官方公开 OI 历史不足以支持多年回测
- 所以这类 predictor 目前只能部分做，不能作为 v1 主路径

## 5. On-chain value / usage / tokenomics predictors

### 研究依据

staking 论文已经说明：

- tokenomics 变量能预测回报

Source:

- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640

BlackRock 的系统化流程也说明：

- raw signals 可以来自传统和另类数据

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### 原始输入

- TVL
- fees
- active users
- circulating supply
- staking ratio
- token emissions / unlocks

### 常见构造方式

- market cap / TVL
- price / fees
- active users growth
- staking ratio level / change
- emission pressure

### 对我们项目的意义

这是我们后面最值得补的第二大块。

因为：

- 它提供 price 以外的信息
- 更可能形成 crypto-specific alpha

但当前限制是：

- 我们的数据链还不完整
- 目前只有 `tvl.csv`，缺更完整的 fees/users/staking 数据

## 6. Attention / sentiment / macro / cross-asset state predictors

### 研究依据

Liu 和 Tsyvinski 指出：

- investor attention proxy 显著预测 crypto returns

Source:

- Risks and Returns of Cryptocurrency
  - https://www.nber.org/papers/w24877

Google search 相关研究也显示：

- abnormal search volume 与后续 returns、volatility、trading volume 有显著关系

Source:

- Google search and cross-section of cryptocurrency returns and trading activities
  - https://www.sciencedirect.com/science/article/pii/S2214635024001060

Fear & Greed 这类可获得指标也被研究成可用 predictor。

Source:

- Predicting cryptocurrency returns for real-world investments: A daily updated and accessible predictor
  - https://www.sciencedirect.com/science/article/abs/pii/S154461232300778X

### 原始输入

- search volume
- social sentiment
- fear & greed
- macro series
- BTC dominance
- cross-asset returns

### 常见构造方式

- abnormal attention
- sentiment surprise
- macro shock sensitivity
- BTC-led state variables

### 对我们项目的意义

这类 predictor 很有潜力，但第一版不该优先。

原因：

- 数据治理复杂
- 解释性和口径稳定性问题更大
- 更适合在 alpha 层基础结构完成后补进来

## 对当前项目的最终建议

### v1 只做三类

1. `price / trend`
2. `reversal`
3. `volatility / liquidity`

### v2 再补两类

4. `derivatives / carry / crowding`
5. `on-chain value / usage`

### v3 再考虑

6. `attention / sentiment / macro`

## 对当前 4h crypto 的具体 raw predictor 候选

### 现在就能做

- `ema_gap_120_360`
- `breakout_360bar`
- `rev_6bar_voladj`
- `rev_18bar_voladj`
- `trend_strength / realized_vol`
- `amihud_120bar`
- `dollar_volume_shock_120bar`

### 数据补齐后可做

- `funding_level`
- `funding_change`
- `funding_price_divergence`
- `mcap_tvl_value`
- `staking_ratio`
- `fees_to_mcap`

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- Risks and Returns of Cryptocurrency
  - https://www.nber.org/papers/w24877
- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640
- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://www.sciencedirect.com/science/article/pii/S1057521921002349
- Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both
  - https://www.sciencedirect.com/science/article/pii/S1062940822000833
- Dynamic time series momentum of cryptocurrencies
  - https://www.sciencedirect.com/science/article/pii/S1062940821000590
- State transitions and momentum effect in cryptocurrency market
  - https://www.sciencedirect.com/science/article/pii/S1544612325016101
- Google search and cross-section of cryptocurrency returns and trading activities
  - https://www.sciencedirect.com/science/article/pii/S2214635024001060
- Predicting cryptocurrency returns for real-world investments: A daily updated and accessible predictor
  - https://www.sciencedirect.com/science/article/abs/pii/S154461232300778X
