# Position Mapping 正式输出怎么选

Date: 2026-03-11
Category: alpha-models

## 研究问题

当前 `position mapping` 层同时产生了三种仓位映射变体：

- `linear_target_only`
- `linear_band`
- `linear_band_vol_target`

现有实现把 `linear_band_vol_target` 直接设为正式输出。这需要回答两个问题：

1. 机构是否会直接把“限制最多、最保守”的变体设为正式输出
2. position mapping 层应该按什么标准选择正式变体

## 核心结论

调研后，比较稳的结论是：

1. **不应硬编码某个更保守的变体为正式输出**
2. position mapping 的正式输出，应该通过一套**实现后净绩效 + 风险 + 交易 frictions** 的联合准则来选
3. 更保守的 mapping 不是天然更优；它只是一个候选变体
4. 对当前单资产 `BTC 4h` 设定，最合理的正式选择逻辑是：
   - 先保留 `linear_target_only` 作为 `anchor`
   - 再比较 `linear_band`
   - 再比较 `linear_band_vol_target`
   - 如果更保守的变体在实现后结果没有带来足够的风险/成本改善，则不应替代 anchor

## 研究依据

### 1. BlackRock：position sizing 之后还要看风险、成本和约束

BlackRock 的公开系统化投资流程明确强调：

- 先从 alpha score 出发构建仓位
- 但最终组合要同时考虑：
  - expected return
  - risk
  - transaction costs
  - constraints

这意味着：

- `scaled_alpha -> position` 之后，并不是“越保守越好”
- 正式输出应该在净收益、风险和 frictions 的联合目标下被选出

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### 2. MSCI：weighting / mapping 要看 transfer efficiency，而不是只看保守性

MSCI 关于 weighting scheme 和 transfer coefficient 的研究强调：

- 一个 mapping/weighting 方案的价值在于：
  - 它把 signal 有多有效地传到仓位
  - 同时有没有引入过高 turnover、意外暴露和 implementability 问题

这意味着：

- position mapping 层的正式输出不应只由“限制更多”决定
- 应看：
  - signal-to-position transfer
  - 风险控制
  - investability / turnover / capacity

Source:

- How Portfolio-Weighting Schemes Affected Factor Exposures
  - https://www.msci.com/research-and-insights/blog-post/how-portfolio-weighting-schemes-affected-factor-exposures

### 3. 交易成本文献：band / no-trade region 是为了应对成本，不是默认优于原始仓位

关于交易成本和 no-trade region / hysteresis 的研究结论是：

- 交易成本存在时，hysteresis / no-trade band 往往是合理的
- 但 band 的作用是减少无效交易和 implementation drag
- 不是说一旦加入 band，策略就自动更优

这意味着：

- `linear_band` 和 `linear_band_vol_target` 都应被视为 cost-aware 候选
- 需要和 `linear_target_only` 做净绩效和风险后的比较

Sources:

- Re-Interpreting the Failure of Foreign Exchange Market Efficiency Tests: Small Transaction Costs, Big Hysteresis Bands
  - https://www.nber.org/papers/w3319
- A Taxonomy of Anomalies and their Trading Costs
  - https://www.nber.org/papers/w20721

### 4. Volatility targeting 文献：vol targeting 是风控工具，不是默认 alpha 增强器

vol targeting 的公开研究支持它作为：

- 风险平滑工具
- 降低尾部波动的工具

但不支持简单地说：

- 加了 vol targeting，就应该替代原始 mapping 成为正式输出

更稳的理解是：

- vol targeting 是一个 risk-aware mapping 候选
- 它是否应成为正式输出，必须比较其对：
  - net return
  - Sharpe
  - drawdown
  - turnover
  - implementation shortfall
  的影响

Source:

- The Impact of Volatility Targeting
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538

### 5. 动态交易文献：面对成本，策略应在目标仓位和当前仓位之间权衡

Garleanu and Pedersen 的动态交易研究表明：

- 在 returns 可预测且交易有成本时
- 最优策略不是每次直接跳到目标仓位
- 而是在：
  - 当前仓位
  - 目标仓位
  - 未来预期目标
 之间做带成本的折中

这进一步支持：

- `linear_target_only`
- `linear_band`
- `linear_band_vol_target`

都只是近似不同程度的 cost-aware transfer rule

因此：

- 正式输出应该通过比较来选
- 不该预设“带更多约束的版本就是正式版”

Source:

- Dynamic Trading with Predictable Returns and Transaction Costs
  - https://www.nber.org/papers/w15205

## 对当前项目的直接结论

### 1. 现有实现的问题

当前仓库把：

- `linear_band_vol_target`

直接设为 `official_variant`

这个选择逻辑更像：

- 工程上的保守默认

而不是：

- 研究上比较后选出的 winner

### 2. 更合理的正式选择逻辑

对当前 `BTC 4h` 单资产设定，position mapping 层更合理的选择方式是：

1. 把 `linear_target_only` 当作 position-layer `anchor`
2. 统一评估：
   - `linear_target_only`
   - `linear_band`
   - `linear_band_vol_target`
3. 用联合准则选正式输出

## 建议的正式评估指标

### A. Transfer quality

- `scaled_alpha_to_realized_corr`
- `target_to_realized_corr`

### B. Net performance

- `net_total_return`
- `annual_return`
- `Sharpe`
- `max_drawdown`

### C. Trading frictions

- `mean_turnover`
- `cost_drag`
- `implementation_shortfall`
- `execution realism adjusted net return`

### D. Risk control

- `realized_annual_vol`
- `vol_target effectiveness`

## 建议的正式选择原则

### Strong win

候选 mapping 只有在同时满足：

- `execution-adjusted Sharpe >= anchor`
- `execution-adjusted net_total_return >= 0.90 * anchor`
- `mean_turnover < anchor`
- `cost_drag < anchor`

时，才替代 `linear_target_only`

### Robust win

若候选 mapping：

- `execution-adjusted Sharpe > anchor`
- `execution-adjusted net_total_return >= 0.80 * anchor`
- 且风险与成本明显改善

则可以作为“更稳正式输出”

### 否则

保留：

- `linear_target_only` 作为正式输出

## 结论

position mapping 层的正式输出选择，不应由“限制更多”来决定，而应由：

- signal transfer
- net performance
- turnover / cost
- execution-adjusted robustness

的联合比较来决定。

对当前项目，这意味着：

- 现有 `linear_band_vol_target` 作为正式输出的逻辑还不够硬
- 下一步应把 position mapping 层改成：
  - `anchor = linear_target_only`
  - 统一 horse race
  - 若更保守变体没有实证胜出，则不应覆盖 anchor
