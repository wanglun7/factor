# Position / Portfolio Mapping：Scaled Alpha 之后怎么接

Date: 2026-03-11
Category: alpha-models

## 研究问题

在当前链路里，alpha 层已经能产出：

- `official composite alpha`
- `forecast_return_30bar`
- `scaled_alpha in [-1, 1]`

下一层需要回答：

1. `scaled alpha` 后面首先接什么
2. 第一版 position / portfolio mapping 应该怎么做
3. 对当前 `BTC 4h single-asset`，v1 应优先哪种映射方式

## 核心结论

调研后，更稳的结论是：

1. `scaled alpha` 后面先接 `position sizing / portfolio mapping`，不是先接 regime
2. 对当前单资产 `BTC 4h`，v1 不应直接上完整优化器
3. 最合理的第一版是：
   - `scaled_alpha -> target_position`
   - target_position 再配：
     - hysteresis / hold band
     - volatility targeting
     - turnover penalty / rebalance smoothing
4. 也就是说，下一层的核心不是“再找更复杂模型”，而是做一层：
   - **signal-to-position transfer layer**

## 为什么先接 position / portfolio

### 1. 公开机构链路

BlackRock 的公开系统化投资链路是：

- signals / alpha score
- portfolio construction
- portfolio construction 同时考虑 expected return、risk、cost、constraints

这意味着：

- alpha 层之后，先进入的是 portfolio construction
- regime/risk/optimizer 属于 portfolio construction 的条件或模块，不是先于 position mapping 的独立前置

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### 2. Markowitz / Boyd 的框架

Boyd 对现代 Markowitz 的综述强调：

- expected return forecast 需要转成持仓权重
- 再与风险、成本、约束联合优化

这说明：

- `scaled alpha` 不是终点
- 后面自然接的是 position / weight mapping

Source:

- Markowitz Portfolio Construction at Seventy
  - https://stanford.edu/~boyd/papers/markowitz.html

### 3. MSCI 的 transfer coefficient 思路

MSCI 关于 weighting scheme 的研究明确强调：

- 关键不是只有 signal 本身
- 还要看 signal 能多有效地传到组合权重
- 这类“skill transfer”可以用 transfer coefficient 思路衡量

这直接支持：

- `scaled alpha -> position` 应该被当作正式一层研究

Source:

- How Portfolio-Weighting Schemes Affected Factor Exposures
  - https://www.msci.com/research-and-insights/blog-post/how-portfolio-weighting-schemes-affected-factor-exposures

## 可选方法

## A. Hard threshold / ternary position

做法：

- `scaled_alpha > entry` -> `+1`
- `scaled_alpha < -entry` -> `-1`
- 中间为 `0`

优点：

- 简单
- 稳定
- 易解释

问题：

- 丢失强弱信息
- 容易在阈值附近抖动

结论：

- 适合作为 baseline
- 不适合作为当前 v1 的唯一正式实现

## B. Linear score-to-position

做法：

- `target_position = k * scaled_alpha`
- 再 clip 到 `[-1, 1]`

优点：

- 最简单的连续仓位映射
- 完整保留强弱信息

问题：

- 对噪音敏感
- 在 `scaled_alpha` 小幅波动时会频繁调仓

结论：

- 必须配合 smoothing / hysteresis

## C. Piecewise linear with hold band

做法：

1. 把 `scaled_alpha` 映射到连续 target position
2. 但只有当目标仓位变化超过某个 band 时才真正调仓

例如：

- 目标仓位按 `scaled_alpha` 连续变化
- 若与当前仓位差值 `< band`，则维持不动
- 超过 band 才更新

优点：

- 保留连续强度
- 显著降低噪音交易
- 很适合单资产中频时间序列系统

结论：

- 当前最适合的 v1

## D. Mean-variance / optimizer-first

做法：

- 直接拿 `forecast_return_30bar` 进完整优化器

问题：

- 当前是 `BTC` 单资产
- 还没有正式风险模型和成本模型
- 此时直接上优化器，结构上过早

结论：

- 不适合作为当前下一层的 v1

## 当前项目最合理的 v1

对 `BTC 4h single-asset`，下一层应定义为：

`scaled_alpha -> target_position -> realized_position`

其中：

### 1. Target position

- 采用连续映射：
  - `target_position = clip(position_scale * scaled_alpha, -max_abs_position, max_abs_position)`

### 2. Hold band / hysteresis

- 若 `|target_position - current_position| < rebalance_band`
  - 则保持原仓位
- 否则才更新到新仓位

### 3. Volatility targeting

- 再按 realized volatility 做简单缩放
- 避免同样 alpha 强度在高波动环境下带来过大风险

### 4. Cost-aware evaluation

- 这一层的评估必须同时看：
  - signal-to-position transfer
  - turnover
  - cost-adjusted return
  - delay robustness

## 为什么不是先做 regime

因为知识库前面已经反复指向：

- regime 应该服务 alpha 和 portfolio
- 不是替代 alpha 或 position 层
- 当前最缺的是把 `scaled alpha` 干净地传到仓位

在这个前提下，先上 regime 只会把系统复杂化。

## 对实施顺序的判断

最合理的顺序：

1. 先实现 `scaled_alpha -> position mapping v1`
2. 做这一层独立评估：
   - transfer quality
   - turnover
   - cost-adjusted performance
3. 再考虑：
   - risk model
   - optimizer
   - regime-conditioned position sizing

## 结论

`scaled alpha` 后面，知识库目前最支持的是：

- **先做 position / portfolio mapping**
- 第一版用：
  - 连续仓位映射
  - hold band / hysteresis
  - 简单 volatility targeting

也就是：

`scaled_alpha -> target_position -> constrained position`

而不是直接跳到 regime 或完整优化器。
