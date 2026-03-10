# Alpha 层评估、去冗余与校准

Date: 2026-03-10
Category: alpha-models

## 研究问题

如果已经确认 alpha 层是第一步，那么这一层内部到底该怎么做尽调。

重点问题有三个：

1. 机构会怎么评估 predictor / alpha score
2. 多个 predictor 怎么去冗余
3. score 进入组合层之前怎么校准

## 核心结论

调研后，这一层可以收敛成 3 个判断标准：

1. `predictive strength`
   - 有没有可复制的预测力
2. `implementation quality`
   - 这种预测力能不能穿过换手、延迟、容量和非目标暴露
3. `portfolio transferability`
   - 这个 score 能不能干净地传递到组合权重，而不是在优化器里变形

这意味着，机构不会只看一个 Sharpe 或一个 IC。

更接近实务的检查集是：

- 预测力
- 延迟衰减
- 换手/成本
- 因子纯度
- 非目标暴露
- 容量/可投资性
- 与风险模型的一致性

## 1. Predictor / score 该怎么评估

### 1.1 先看预测力，但不是只看一个统计量

学术文献关于 return prediction 的共同点是：

- 要看样本外
- 要看 forecast-implied performance
- 不能只看 in-sample 拟合

例如 Chinco, Clark-Joseph, Ye 的研究里，LASSO 是否有用，不只是看拟合，而是看：

- out-of-sample fit
- forecast-implied Sharpe

Source:

- Sparse Signals in the Cross-Section of Returns
  - https://www.nber.org/papers/w23933

对我们项目的含义：

- 单 predictor 不应只看相关系数
- 还要看把它变成 canonical signal 后的 out-of-sample strategy metrics

### 1.2 要看成本后的预测力

Novy-Marx 和 Velikov 说明了一个实务里非常硬的事实：

- 很多 anomaly 在成本后显著变差
- 高换手策略尤其容易失效
- buy/hold spread 这类简单成本缓释机制很重要

Source:

- A Taxonomy of Anomalies and their Trading Costs
  - https://www.nber.org/papers/w20721

对我们项目的含义：

- alpha 层研究不能把成本放到最后
- predictor 评估里必须同时记录 turnover、成本后收益、以及持有区间设计

### 1.3 要看实现延迟后的衰减

MSCI 关于 time-sensitive factors 的研究指出：

- 因子有明显的时间敏感性差异
- 一些因子延迟 1 天到 1 个月后 IR 衰减很小
- 另一些因子则依赖快速实施

Source:

- Which Factors Are More Time-Sensitive?
  - https://www.msci.com/research-and-insights/blog-post/which-factors-are-more-time-sensitive

对我们项目的含义：

- 4h predictor 不能只看“当根 bar 立即执行”的结果
- 必须看 delay sensitivity
- 例如：
  - `t` 形成信号，`t+1 bar` 才执行
  - 或 `t+2 bars` 才执行

如果一延迟就失效，这种 alpha 的工程价值会显著下降。

### 1.4 要看 signal 能否有效传递到权重

MSCI 在单因子组合构建研究里用 `transfer coefficient (TC)` 来衡量：

- 因子洞见能多有效地传到组合权重

其定义是：

- 证券目标因子暴露与相对基准主动权重之间的横截面相关

同一研究还显示：

- 不同 weighting scheme 会显著改变 TC、非目标暴露、换手和容量

Source:

- How Portfolio-Weighting Schemes Affected Factor Exposures
  - https://www.msci.com/research-and-insights/blog-post/how-portfolio-weighting-schemes-affected-factor-exposures

对我们的含义：

- alpha 层不能只看 predictor 对 future returns 的关系
- 还要看 predictor 在仓位映射后是否还能保留原始方向性

对时间序列项目，我的推论是可以引入一个对应概念：

- `signal-to-position correlation`
- 或 `score-to-weight transfer`

这不是源文直接给出的术语，而是把 TC 的思想迁移到我们当前项目的合理推论。

## 2. 多 predictor 怎么去冗余

### 2.1 不要假设每个 predictor 都贡献独立信息

Kelly, Malamud, Pedersen 的 `Principal Portfolios` 说明：

- 更一般的问题不是“每个资产只用自己的信号”
- 而是所有 signals 联合预测所有 returns
- 预测问题可以写成一个 prediction matrix

Source:

- Principal Portfolios
  - https://www.nber.org/papers/w27388

这对我们项目的直接含义是：

- 多个 predictor 往往表达的是重叠信息
- 简单叠加可能只是重复下注同一个 latent dimension

### 2.2 高维弱信号环境下，稀疏或收缩比“全收下”更合理

两个方向的证据都指向这一点：

1. `Sparse Signals`
   - LASSO 在高维预测里通过识别少量短命、稀疏 predictor 改善样本外 fit 与 forecast-implied Sharpe
2. `Can Machines Learn Weak Signals?`
   - 在弱信号环境下，Ridge 往往比 Lasso 更适合利用弱但广泛的信号

Sources:

- Sparse Signals in the Cross-Section of Returns
  - https://www.nber.org/papers/w23933
- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421

对我们项目的含义：

- 如果 predictor 很少且各自机制不同，可以先等权
- 如果 predictor 开始变多，必须进入 shrinkage
- 但 shrinkage 用什么，要看环境是“稀疏强信号”还是“广泛弱信号”

### 2.3 去冗余的 v1 实务做法

基于上面的研究，我对当前项目的建议是：

#### 第一层：相关性与共线检查

- predictor 之间的时序相关
- predictor 对同一 future return bucket 的边际贡献
- predictor 对持仓的相关性

#### 第二层：小规模 shrinkage

- predictor 很少时：equal weight / constrained linear blend
- predictor 稍多时：ridge 优先于 lasso，除非证据显示信号高度稀疏

这是基于文献对弱信号环境的结论做的推论。

## 3. Score 怎么校准成可用 alpha

### 3.1 组合层关心的不是 raw score，而是可优化输入

Boyd 对 Markowitz 组合构建的综述说明：

- 实务中的组合构建，核心仍是 expected return、risk、cost、constraints 的联合权衡

Source:

- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html

所以：

- raw predictor 不够
- raw z-score 也不够
- 进入组合层前，需要一个更接近 `expected-return-like input` 的对象

### 3.2 机构实务上会做 alignment / rescaling

MSCI 的研究非常直接：

- 如果 alpha 和 risk model 不对齐，优化器会放大不对齐部分
- 可行处理包括：
  - penalize residual alpha
  - rescale alphas

Source:

- Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned

这意味着：

- calibration 的核心不只是“把 score 变成一个新数值”
- 更重要的是让它成为一个风险模型和优化器能安全消费的输入

### 3.3 对我们项目，最现实的校准方式

基于公开资料，我认为当前项目最现实的 v1 校准方式是：

#### 第一步：score 分桶

- 看 standardized alpha score 在不同 bucket 下的未来 `6/18/30` bar 收益

#### 第二步：单调映射

- 如果 bucket mean 基本单调
- 再把 raw score 映射成 `scaled alpha strength`

#### 第三步：风险对齐

- 先做简单 volatility scaling
- 后续如果有正式风险模型，再做 residualization / alignment

这里的 `bucket -> scaled alpha strength` 是我基于上述文献和实务流程作出的工程化推论，不是某家机构公开披露的唯一标准做法。

## 4. Alpha 层应使用什么诊断面板

基于这轮调研，我建议把 alpha 层诊断固定成下面这组，而不是只看一个 Sharpe：

### 预测力

- out-of-sample Sharpe
- Newey-West t-stat
- bucket monotonicity
- score-to-return slope

### 可实现性

- turnover
- cost-adjusted return
- delay decay
- average holding duration

### 纯度与传递

- score-to-position transfer
- unintended exposure
- predictor redundancy
- contribution concentration

### 可投资性

- capacity proxy
- liquidity usage
- crowdedness proxy

其中后两项在我们现阶段数据里只能先做弱版本。

## 5. 对当前 4h 项目的具体含义

### 当前最缺的不是更多 predictor

而是 alpha 层的正式评估面板。

现在我们虽然有一些 strategy metrics，但还缺：

- delay decay
- score bucket monotonicity 的正式报告
- predictor redundancy 分析
- score-to-position transfer

### 下一版 alpha 层应该补的不是 HMM

而是下面 4 个对象：

1. `predictor_report`
   - 每个 predictor 的预测力、成本、延迟衰减
2. `redundancy_report`
   - predictor 相关、边际贡献、冗余度
3. `calibration_report`
   - score 分桶与映射稳定性
4. `alpha_object`
   - 真正交给仓位映射/优化层的 scaled alpha

## 6. Alpha 层到这里是否已经基本调研清楚

我的判断是：

- 对“第一步 alpha model 到底是什么”这件事，已经基本清楚
- 对“机构会怎么评估、合成、校准 alpha 输入”这件事，也已经足够形成 v1 设计

还没完全调透、但已经属于下一层的问题是：

- alpha 层和 regime 层怎么连接
- alpha 层和正式风险模型怎么连接

这已经不是“alpha 层定义”本身，而是下一层系统设计。

## Sources

- Sparse Signals in the Cross-Section of Returns
  - https://www.nber.org/papers/w23933
- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421
- Principal Portfolios
  - https://www.nber.org/papers/w27388
- A Taxonomy of Anomalies and their Trading Costs
  - https://www.nber.org/papers/w20721
- Which Factors Are More Time-Sensitive?
  - https://www.msci.com/research-and-insights/blog-post/which-factors-are-more-time-sensitive
- How Portfolio-Weighting Schemes Affected Factor Exposures
  - https://www.msci.com/research-and-insights/blog-post/how-portfolio-weighting-schemes-affected-factor-exposures
- Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned
- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html
