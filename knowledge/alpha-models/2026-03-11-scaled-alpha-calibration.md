# Scaled Alpha：Composite Alpha 之后怎么校准

Date: 2026-03-11
Category: alpha-models

## 研究问题

在当前链路里，第三层已经能产出：

- `best single anchor`
- `anchor + satellite`
- `family subcomposite`

但这些对象本质上仍然只是 `alpha score`，还不是最终能直接喂给仓位层和优化层的 `scaled alpha`。

这一层需要回答：

1. `scaled alpha` 到底输出什么
2. `composite alpha score` 应该怎么映射成可执行强度
3. 对当前 `BTC 4h single-asset` 设定，v1 应该用什么校准方法

## 核心结论

调研后，更准确的结论是：

1. `scaled alpha` 的职责不是重新发现信号，而是把第三层 score 校准成可下游消费的强度对象
2. 机构公开流程里，研究层常先形成 `alpha score`，进入组合层前再做 `forecast mapping / scaling / rescaling`
3. 对我们当前 `BTC 4h single-asset`，v1 最合理的不是直接做高自由度 expected-return 回归，而是做：
   - `composite score`
   - `monotonic calibration`
   - `bounded scaled alpha`
4. 更具体地说，v1 更适合：
   - 用 train-only expanding/rolling 样本
   - 把 composite score 分桶
   - 估计每个桶对应的未来 `30 bar` 平均收益
   - 再把这个映射压到有界 alpha 强度

一句话：

- `composite alpha` 解决“如何合成”
- `scaled alpha` 解决“合成后的 score 到底该有多大”

## 直接证据

### 1. BlackRock 的公开口径

BlackRock 的公开系统化投资页面明确表述：

- 多个 signal 先形成 `final alpha score`
- 之后再进入 portfolio construction
- 组合构建同时考虑 expected return、风险和交易成本

这意味着：

- 研究层先产出 `alpha score`
- 进入组合层时，这个 score 会被当作 return potential 的输入，而不是直接裸用

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### 2. MSCI / Barra 的公开口径

MSCI 关于 alpha 与 risk alignment 的公开研究说明：

- 机构会把 alpha forecast 输入优化器
- 若 alpha 与 risk model 不对齐，会做 rescale / penalize residual alpha

这说明：

- 进入下游的对象通常不是原始 score
- 而是经过 rescale / alignment 的 `scaled alpha`

Source:

- MSCI: Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned

### 3. 组合优化层天然更适合吃 expected-return-like 输入

Boyd 等关于现代 Markowitz 的综述强调：

- 实务优化问题本质仍然是 expected return 与 risk 的权衡
- 现实中再加 transaction cost、杠杆和约束

这意味着：

- 组合层最自然吃的是 `mu`
- 即便研究层先产出的是 score，进入组合层前也常常要映射到更像 `mu` 的对象

Source:

- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html

### 4. 学术资产定价机器学习的共同点

Gu, Kelly, Xiu 的工作把问题定义得很清楚：

- return prediction / risk premia measurement 的核心，是把 predictor 更好地映射到 expected returns

这支持：

- `score -> forecast` 的校准层是正式一层
- 复杂模型未必必要，但 mapping 本身必要

Source:

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398

## 实现方法候选

### A. 直接 expected-return regression

做法：

- 用 composite score 直接回归未来 `30 bar return`
- 输出 `E[r_{t+30} | score_t]`

优点：

- 最接近优化器输入

问题：

- 对单资产高噪音时间序列很脆
- 当前样本量不算小，但自由度一高，很容易过拟合

结论：

- 不适合作为当前 v1

### B. Monotonic bucket calibration

做法：

1. 用 train-only 样本对 `composite alpha score` 分桶
2. 计算每个桶对应的 future `30 bar` 平均收益
3. 把当前 score 映射到对应桶收益
4. 再压缩成 bounded alpha 强度

优点：

- 简单
- 可解释
- 和当前第三层 rank/bucket 评估一脉相承
- 最符合当前单资产 BTC 4h 的噪音结构

问题：

- 分桶太多会不稳
- 需要 train/test 分离，不能全样本校准

结论：

- 当前最适合的 v1

### C. Isotonic / monotonic regression calibration

做法：

- 用单调回归把 score 映射到 future return

优点：

- 保证单调性
- 比硬分桶更平滑

问题：

- 依然需要 train-only 拟合
- 在当前阶段会把实现复杂度拉高

结论：

- 可作为 v2，不建议先上

## 对当前项目的建议

### 输出形态

v1 建议输出两个对象：

1. `forecast_return_30bar`
   - 由 bucket calibration 得到
   - 单位是 future return-like estimate

2. `scaled_alpha`
   - 再把 `forecast_return_30bar` 压到 `[-1, 1]`
   - 作为后续仓位层的标准输入

这样做的好处：

- 保留经济解释
- 同时给下游一个有界、稳定的输入

### 建议的 v1 流程

1. 输入：
   - 第三层最终 `official composite alpha score`
2. 用 expanding 或 rolling train window
   - 只用过去数据
3. 在 train window 上按 score 分成 5 桶
4. 估计每个桶的 future `30 bar` 平均收益
5. 对当前时点 score 做桶映射
6. 得到 `forecast_return_30bar`
7. 用历史 forecast 分布做轻度 clipping / scaling
8. 输出 `scaled_alpha in [-1, 1]`

### 当前不建议的做法

- 不建议直接全样本拟合 score -> return
- 不建议直接线性回归 expected return
- 不建议把第三层 score 直接当仓位

## 对实现顺序的判断

当前已经有：

- 第一层两条 generator 线
- 第二层统一 score/admission
- 第三层统一 rank horse race

所以 `scaled alpha` 现在已经可以开始设计为下一层。

最合理的顺序是：

1. 先实现 `bucket-calibrated scaled alpha v1`
2. 再做样本外 walk-forward 校准
3. 然后才接 position sizing

## 结论

`scaled alpha` 不是可选项，而是 alpha 层最后一步。

对当前项目，v1 最合理的做法不是高自由度 expected-return 回归，而是：

- `composite alpha score`
- `train-only monotonic bucket calibration`
- `forecast_return_30bar`
- `bounded scaled_alpha`

也就是：

`composite score -> bucket-mapped forecast -> scaled alpha`

这条路线最符合当前系统状态，也最容易和后续仓位层对接。
