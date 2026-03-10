# Composite Alpha：研究与收敛状态

Date: 2026-03-10
Category: alpha-models

## 研究问题

`composite alpha` 这一层到底是做什么的，机构通常怎么做，当前知识库是否已经调研到可以直接实现。

## 核心结论

`composite alpha` 的职责是：

- 把多个 `standardized score` 合成一个统一 alpha 对象
- 在合成前控制冗余
- 在合成时避免过度复杂和过拟合

按当前知识库，已经可以明确三点：

1. `composite alpha` 是正式一层，不是附属步骤
2. v1 起点应是简单线性合成，而不是复杂模型
3. predictor 多起来后必须考虑 regularization / shrinkage

但当前知识库还**没有**把这一层调研到“完全可直接实现”的程度。  
还缺：

- 组合权重的 v1 具体规则
- 冗余阈值
- family 内/跨 family 的去重顺序
- v1 评估门槛

## Source-Backed

### 1. 多信号先合成 integrated score，是机构的常见正式路径

AQR 关于价值和动量主题的研究明确指出，现实里长期存在两种组合思路：

- 分别找 value 和 momentum 最强标的再混合
- 先把 value score 和 momentum score 合成一个 average composite / integrated score，再建组合

这说明：

- score 合成不是旁支
- 而是投资流程里的正式一层

Source:

- Portfolio Construction Matters: A Simple Example Using Value and Momentum Themes
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes

### 2. Forecast combination 本身就是一套成熟问题

Diebold 和 Lopez 的综述明确把下面问题列为 forecasting workflow 的核心：

- 如何比较不同 forecast
- 是否应组合 forecast
- 如何形成 superior composite forecast

这说明：

- 把多个 standardized score 组合成 composite alpha
- 在方法论上属于成熟问题

Source:

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192

### 3. predictor 变多后，需要 shrinkage / regularization

Kozak, Nagel, Santosh 的研究表明：

- 高维预测环境里，直接把所有候选信号平等塞进去不稳
- 通过对低信息量方向做 shrink，可得到更稳健的样本外表现

Source:

- Shrinking the Cross Section
  - https://www.nber.org/papers/w24070

Shen 和 Xiu 的研究进一步表明：

- 在弱信号环境下，Ridge 对弱但广泛的信号更有优势
- Lasso 不一定优于零基准

Source:

- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421

### 4. 简单平均在 forecast combination 里是强基准

Diebold 和 Shin 的研究指出：

- 组合权重是否需要 regularization 是核心问题
- 简单平均常是强基准
- 更复杂的方法也往往会 shrink toward equality

Source:

- Machine Learning for Regularized Survey Forecast Combination: Partially-Egalitarian LASSO and its Derivatives
  - https://www.nber.org/papers/w24967

### 5. bottom-up integrated factor combination 是正式多因子方法

MSCI 关于 multi-factor 组合的研究明确讨论：

- 自下而上的 bottom-up 组合
- 先在标的层合成多个 factor 暴露
- 再形成 multi-factor 结果

这说明：

- “先合成分数，再往下走” 是正式方法，不是工程妥协

Source:

- How can Factors be Combined?
  - https://www.msci.com/research-and-insights/paper/how-can-factors-be-combined

## Industry-Standard

基于上面的公开证据，可以认为下面这些属于行业常见而不是个人发明：

### 1. 简单线性合成是 v1 合理起点

当 predictor 数量不大时，行业里非常常见的起点是：

- equal weight average
- subset average
- 轻度 shrinkage 后的线性合成

### 2. 冗余分析在合成前做

通常会先看：

- predictor-to-predictor correlation
- predictor 家族内是否重复表达同一趋势
- 边际贡献是否显著重叠

### 3. shrinkage 应在 predictor 变多时介入

如果 predictor 很少、机制清楚：

- simple average 往往足够好

如果 predictor 开始变多或共线严重：

- ridge / constrained shrinkage 比自由优化权重更稳

## Project-Specific Inference

下面这些是基于上面证据，对我们当前 4h 时间序列项目的收敛推论。

### 1. `composite alpha v1` 不应该直接上机器学习或复杂加权

当前最合理的第一版只应考虑：

- equal-weight composite
- 小规模 ridge-shrunk linear composite

不应直接上：

- boosting
- neural net ensemble
- regime-specific stack
- 任意自由权重优化

### 2. v1 合成前必须先做 score pruning

我们已经有了 `standardized score` 层的保真结果。  
因此 composite alpha 不应吃全部 raw/score，而应只吃：

- score 层保真通过的
- 且 raw 层本身不是明显负向或弱得无意义的

### 3. v1 最好按 family 先去重，再做合成

因为现在通过 score 层的大量 predictor 集中在：

- breakout / moving-average / crossover 这一大类 trend family

如果不先按 family 去重，最终 composite 很容易只是重复加杠杆在同一趋势维度上。

### 4. v1 的核心是“少量高质量 score 合成”，不是“更多 score 一起上”

这一点和 forecast combination 文献是一致的：

- 少量优质 forecast 的 subset averaging
- 往往比把大量弱 forecast 一起塞进去更稳

## Insufficient Evidence

当前知识库还没有收敛清楚这些点：

### 1. 我们项目的 v1 组合权重规则

虽然已知：

- simple average 是强基准
- ridge 是弱信号环境下更稳的 regularization

但对当前项目还没定死：

- 是所有保留 score 等权
- 还是先 family 内等权、family 间再等权
- 还是先做 subset averaging

### 2. 冗余阈值还没定死

例如：

- 相关性超过多少视为重复
- 同 family 最多保留几个
- raw/score 表现冲突时怎么取舍

### 3. v1 的评估门槛还没定死

例如：

- composite 至少要超过 best single score 多少
- 是否允许只做到更稳但不更强
- 如何定义“值得进入 scaled alpha”

## 当前状态

所以，`composite alpha` 这一层当前的准确状态是：

- 已经调研清楚“它是什么、为什么需要、v1 应避免什么”
- 也已经调研清楚“simple average / shrinkage / redundancy control”是正确方向
- 但还没有调研到能直接无歧义实现的程度

换句话说：

- `raw predictor` 和 `standardized score` 两层已经可以算“调研后实现完成”
- `composite alpha` 还处在“研究框架清楚，但实现细则未收敛”的状态

## 对下一步的直接含义

如果继续推进，下一步调研不该再泛泛搜“composite alpha 是什么”，而应只补 4 个落地问题：

1. v1 的 `score selection / pruning` 规则
2. v1 的 `redundancy report` 和阈值
3. v1 的 `equal weight vs family-neutral average vs ridge` 选择
4. v1 的评估与晋级标准

## Sources

- Portfolio Construction Matters: A Simple Example Using Value and Momentum Themes
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes
- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Shrinking the Cross Section
  - https://www.nber.org/papers/w24070
- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421
- Machine Learning for Regularized Survey Forecast Combination: Partially-Egalitarian LASSO and its Derivatives
  - https://www.nber.org/papers/w24967
- How can Factors be Combined?
  - https://www.msci.com/research-and-insights/paper/how-can-factors-be-combined
