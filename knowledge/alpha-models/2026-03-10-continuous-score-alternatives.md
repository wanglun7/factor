# Continuous Predictor Score：备选方法调研

Date: 2026-03-10
Category: alpha-models

## 研究问题

当前 `continuous predictor` 在 standardized score 层被明显压缩后，下一步可研究的替代方法有哪些，以及这些方法里哪些有公开证据支持。

## 核心结论

目前能明确说的有 3 点：

1. `rolling winsorization + moving z-score` 只是一个通用起点，不是已证实最优
2. `rank / percentile transform` 是资产定价和机器学习里真实存在的替代标准化方案
3. `EW-moment z-score` 至少有证据表明，时间变化 z-score 的构造不应默认只用简单 moving moments

但当前仍然**没有**足够 source-backed 证据，直接证明：

- funding / basis / premium 在 crypto 4h 上最优就应使用某一种单独替代法

所以这一步的状态是：

- 已经可以提出一组有来源支持的候选方法
- 但还不能直接说哪一种就是最终方案

## Source-Backed

### 1. rank transform / percentile mapping 是明确存在的标准化路线

Gu, Kelly, Xiu 的资产定价机器学习论文明确写到：

- 他们按期对 characteristic 做横截面排序
- 再把 rank 映射到 `[-1, 1]`

这说明：

- `rank-based normalization` 是正式存在的方法
- 它不是工程拍脑袋

来源：

- Empirical Asset Pricing via Machine Learning
  - https://academic.oup.com/rfs/article/33/5/2223/5758276
  - 关键描述见脚注与正文：按期 cross-sectionally rank characteristics，并映射到 `[-1,1]`

### 2. z-score 的时间权重构造本身可变，EW moments 是真实替代方案

关于 time-varying z-score 的研究表明：

- exponentially weighted moments 可能优于简单 moving moments

这说明：

- 如果继续用 z-score 思路
- 也不应直接把当前 rolling moving mean/std 当成唯一形式

来源：

- Time-varying Z-score measures for bank insolvency risk: Best practice
  - https://www.sciencedirect.com/science/article/pii/S0927539823000610
  - https://econpapers.repec.org/RePEc:eee:empfin:v:73:y:2023:i:c:p:170-179

### 3. carry / basis / funding 的经济含义往往落在 level / spread 本身

我们已有的 perp / basis 研究支持的是：

- funding level
- premium
- basis
- log basis

这些 predictor 在文献中是以 level / spread 形式出现的，而不是先定义为“相对自己历史均值几个标准差”。

这意味着：

- raw level preserve 是有研究语义支撑的候选方向

来源：

- Perpetual Futures Pricing
  - https://www.nber.org/papers/w32936
- Anatomy of Perpetual Futures Returns
- ETH / funding 相关研究

## Industry-Standard

基于公开研究，可以把下面这些视为合理候选路线：

### 1. raw-level-preserving transform

对 carry / basis / spread 这类 signal：

- 保留 level
- 只做轻度 clipping / cap
- 不做深度 recentring

### 2. rank / percentile transform

把连续 predictor：

- 映射为 percentile
- 或 rank 到固定区间，如 `[-1,1]`

优点是：

- 对厚尾更稳
- 减弱极端值主导
- 不依赖 mean/std 稳定性

### 3. EW-moment z-score

仍保留 z-score 框架，但：

- 不用简单 moving window
- 改用 exponentially weighted mean/std

它更适合处理：

- 慢变量
- 分布漂移
- regime 变化

## Project-Specific Inference

对我们当前这批 continuous predictors，最值得研究的 3 条替代路线应该是：

### 1. raw-level-preserving score

适用对象：

- `funding_rate_level`
- `lagged_funding_rate_1`
- `premium`
- `relative_basis`
- `log_basis`
- `funding_basis_rate`

做法方向：

- 仅轻度 clip
- 方向统一
- 不做 rolling recentering

### 2. rank / percentile score

适用对象：

- 几乎所有 continuous predictors

做法方向：

- 每个资产自己做 time-series rank / percentile
- 再映射到有界区间

### 3. EW z-score

适用对象：

- `prev_day_return`
- `amihud_20w`
- funding / basis 也可作为对照组

做法方向：

- 继续做 z-score
- 但用 EW mean/std 替代当前 moving moments

## Insufficient Evidence

当前还没有足够 source-backed 证据直接定死：

- carry / basis / funding 在我们这个 crypto 4h 环境里，最终必须选哪条替代路线
- time-series rank 是否优于 time-series z-score
- raw-level-preserving score 的具体 clip 规则
- 哪类 continuous predictor 适合 shared method，哪类必须 family-specific method

## 当前收敛结论

如果继续推进，最合理的研究顺序不是直接改最终代码，而是：

1. 保留当前 `moving z-score` 作为 baseline
2. 增加 2 到 3 条 continuous-specific alternatives
3. 在同一真实样本上比较：
   - spread preservation
   - monotonicity
   - delay stability
4. 再决定 funding / basis / liquidity / reversal 各自应采用哪种 standardized score

## Sources

- Empirical Asset Pricing via Machine Learning
  - https://academic.oup.com/rfs/article/33/5/2223/5758276
- Time-varying Z-score measures for bank insolvency risk: Best practice
  - https://www.sciencedirect.com/science/article/pii/S0927539823000610
  - https://econpapers.repec.org/RePEc:eee:empfin:v:73:y:2023:i:c:p:170-179
- Perpetual Futures Pricing
  - https://www.nber.org/papers/w32936
