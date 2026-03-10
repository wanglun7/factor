# Raw Predictor：已调研到的具体因子设计

Date: 2026-03-10
Category: alpha-models

## 先纠正一个问题

现有文件 [2026-03-10-raw-predictor-families.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-raw-predictor-families.md) 主要回答的是：

- predictor 有哪些家族
- 每类常见输入是什么
- 常见模板是什么

它**没有**把 `raw predictor` 整理成“来源明确、可以直接引用的具体设计清单”。

所以，如果标准是：

- 只能基于知识库已经调研到的内容做
- 没调研到的要继续调研

那么截至这份文件之前，知识库对 `raw predictor` 的具体设计是**不够的**。

本文件只保留已经调研到、且有来源支持的具体 predictor 设计，不再混入项目层面的自行发挥。

## 1. 自身滞后收益：time-series momentum / short-term return

### 设计

- 用资产自身的过去收益作为 predictor
- 文献已明确支持：
  - `past own return -> future return`
  - 包括 time-series momentum 和 very short-horizon lagged return

### 来源

#### Risks and Returns of Cryptocurrency

Liu 和 Tsyvinski 明确指出：

- crypto returns 存在强 time-series momentum

Source:

- https://www.nber.org/papers/w24877

#### Forecasting cryptocurrency returns with machine learning

这篇文章的 highlights 明确写到：

- `1-day lagged returns have great predictive power for crypto returns`

Source:

- https://www.sciencedirect.com/science/article/pii/S0275531923000314

### 当前能确认到的具体形式

- `lagged return` 本身是已调研到的具体 predictor
- `time-series momentum` 本身是已调研到的具体 predictor

### 目前还不能声称已经调研清楚的部分

- 哪个固定 lookback 窗口应当成为我们的 canonical v1 设计
- 例如 `6bar / 18bar / 120bar` 这种窗口，目前还不是知识库里被论文直接给出的标准结论

## 2. 前一日收益反转：short-term reversal

### 设计

- 用非常短期过去收益作为反向 predictor
- 文献直接支持：
  - 前一日低收益币后续表现更好

### 来源

#### Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets

摘要直接说明：

- 强预测信号来自前一天收益
- 前一日收益较低的币，后续表现更好

Source:

- https://www.sciencedirect.com/science/article/pii/S1057521921002349

### 当前能确认到的具体形式

- `previous-day return`
- `negative lagged return as reversal predictor`

### 目前还不能声称已经调研清楚的部分

- 在 4h 场景下，是否应直接迁移成 `-ret_6bar`
- 这属于频率映射，不是当前知识库已经证实的结论

## 3. Amihud illiquidity：流动性 predictor

### 设计

- 用 Amihud measure 作为 liquidity proxy
- 然后检验其与 future returns 的关系

### 来源

#### Liquidity risk and expected cryptocurrency returns

摘要明确说明：

- 论文使用 `Amihud measure` 作为 liquidity proxy
- 发现 liquidity 与 future returns 存在显著关系

Source:

- https://doi.org/10.1002/ijfe.2431
- https://econpapers.repec.org/article/wlyijfiec/v_3a28_3ay_3a2023_3ai_3a1_3ap_3a472-492.htm

### 当前能确认到的具体形式

- `Amihud illiquidity` 是已调研到的具体 predictor

### 目前还不能声称已经调研清楚的部分

- 该 predictor 在 time-series 单资产框架下的最优用法
- 论文更偏 cross-section 定价，不是 4h perp 单资产 timing 设计

## 4. Google Search / abnormal attention

### 设计

- 用 Google search volume，尤其是 abnormal Google search volume，作为 predictor

### 来源

#### Risks and Returns of Cryptocurrency

Liu 和 Tsyvinski 明确指出：

- investor attention proxies strongly forecast cryptocurrency returns

Source:

- https://www.nber.org/papers/w24877

#### Google search and cross-section of cryptocurrency returns and trading activities

摘要明确说明：

- abnormal Google search volume 较高的加密货币，后续 returns 更高

Source:

- https://www.sciencedirect.com/science/article/pii/S2214635024001060

### 当前能确认到的具体形式

- `attention proxy`
- `abnormal Google search volume`

### 目前还不能声称已经调研清楚的部分

- abnormal 的精确定义
- 搜索关键词选择
- 时间聚合方式

这些在当前公开摘要层面还不够细。

## 5. Fear & Greed Index

### 设计

- 用 Crypto Fear and Greed Index 作为 predictor

### 来源

#### Predicting cryptocurrency returns for real-world investments: A daily updated and accessible predictor

highlights 和摘要都明确说明：

- 使用 `Crypto Fear and Greed Index`
- 在 `1 day to 1 week` 的预测 horizon 上有显著预测力

Source:

- https://www.sciencedirect.com/science/article/abs/pii/S154461232300778X

### 当前能确认到的具体形式

- `Fear and Greed Index level` 本身是已调研到的具体 predictor

### 需要保留的谨慎点

2026 年一篇更新论文显示：

- `ΔFGI` 对 Bitcoin 日收益未表现出稳定预测力

Source:

- https://www.sciencedirect.com/science/article/pii/S305070062600006X

这说明：

- sentiment predictor 不能无条件纳入 canonical v1
- 同一类 predictor 也需要看更近期证据与目标资产范围

## 6. Staking ratio / crypto carry

### 设计

- 用 `staking ratio` 作为 predictor
- staking 还与 carry premia 相关

### 来源

#### The Tokenomics of Staking

NBER 页面明确写到：

- `staking ratios positively predict excess returns`
- 存在显著 `crypto carry premia`

Source:

- https://www.nber.org/papers/w33640

### 当前能确认到的具体形式

- `staking ratio`
- `crypto carry premia`

### 当前不能直接落地为 v1 的原因

- 我们还没有稳定、长期、可核验的 staking 数据链

## 7. On-chain activity：MVRV / active addresses / new addresses

### 设计

- 用链上特征预测 returns
- 当前公开证据里，最明确的是：
  - `market-to-realized-value ratio`
  - `new addresses`
  - `active addresses`

### 来源

#### Predicting cryptocurrency returns with machine learning: Evidence from high-dimensional factor modeling

highlights 明确写到：

- `market-to-realized-value ratio`
- `new addresses`
- `active addresses`

是最有影响力的 predictor

Source:

- https://www.sciencedirect.com/science/article/abs/pii/S0927538X25003701

### 当前能确认到的具体形式

- `MVRV`
- `new addresses`
- `active addresses`

### 当前不能直接落地为 v1 的原因

- 我们没有完整、可信、长期的链上数据管线

## 8. Cross-cryptocurrency lagged returns

### 设计

- 不是只看自身过去收益
- 也看其他加密货币的滞后收益对当前币的预测力

### 来源

#### Cross-cryptocurrency return predictability

摘要明确说明：

- other cryptocurrencies 的 lagged returns 可以显著预测 focal cryptocurrency 的 returns

Source:

- https://www.sciencedirect.com/science/article/abs/pii/S0165188924000551

### 当前能确认到的具体形式

- `lagged returns of other cryptocurrencies`

### 当前不能直接纳入 raw v1 的原因

- 它已经更接近 cross-asset predictor design
- 会显著抬高 predictor 层复杂度

## 9. 当前仍然没有被知识库充分调研清楚的方向

下面这些方向，知识库现在还不能说已经有“来源明确的具体 canonical 设计”：

- `EMA gap`
- `breakout`
- `funding level / funding shock / funding term structure`
- `OI change`
- `funding-price divergence`
- `volume shock`

原因不是这些方向一定没用，而是：

- 当前知识库里还没有把它们调研到“足以直接当 canonical v1 设计”的程度

所以如果严格按“只基于已调研知识库来做”，这些目前都不该直接进 v1 规范。

## 10. 到目前为止，知识库真正支持的 raw predictor 具体设计

基于当前已调研结果，知识库明确支持的具体 raw predictor 有：

- `own lagged return`
- `time-series momentum`
- `previous-day reversal`
- `Amihud illiquidity`
- `abnormal Google search volume`
- `Fear and Greed Index`
- `staking ratio`
- `MVRV`
- `new addresses`
- `active addresses`
- `cross-crypto lagged returns`

其中能直接进入近期 v1 候选池的，更稳妥的是：

- `own lagged return / time-series momentum`
- `previous-day reversal`
- `Amihud illiquidity`

因为这几个方向的来源更扎实，且数据口径更容易被做实。

## Sources

- Risks and Returns of Cryptocurrency
  - https://www.nber.org/papers/w24877
- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://www.sciencedirect.com/science/article/pii/S1057521921002349
- Liquidity risk and expected cryptocurrency returns
  - https://doi.org/10.1002/ijfe.2431
- Forecasting cryptocurrency returns with machine learning
  - https://www.sciencedirect.com/science/article/pii/S0275531923000314
- Google search and cross-section of cryptocurrency returns and trading activities
  - https://www.sciencedirect.com/science/article/pii/S2214635024001060
- Predicting cryptocurrency returns for real-world investments: A daily updated and accessible predictor
  - https://www.sciencedirect.com/science/article/abs/pii/S154461232300778X
- Do bitcoin returns move sentiment? Evidence from the crypto fear & greed index
  - https://www.sciencedirect.com/science/article/pii/S305070062600006X
- The Tokenomics of Staking
  - https://www.nber.org/papers/w33640
- Predicting cryptocurrency returns with machine learning: Evidence from high-dimensional factor modeling
  - https://www.sciencedirect.com/science/article/abs/pii/S0927538X25003701
- Cross-cryptocurrency return predictability
  - https://www.sciencedirect.com/science/article/abs/pii/S0165188924000551
