# Alpha 层输出什么：Score 还是 Expected Return

Date: 2026-03-10
Category: alpha-models

## 研究问题

机构在 alpha model 这一层，最终输出的到底是什么：

- 相对排序用的 `alpha score`
- 还是绝对量纲的 `expected return forecast`

以及两者之间通常怎么连接。

## 核心结论

调研后更准确的结论是：

1. 机构没有单一标准输出
2. 横截面股票系统里，常先形成 `relative alpha score`
3. 进入优化器之前，通常还会做一层 `forecast mapping / alpha scaling`
4. 真正进入组合优化的对象，通常更接近“可比较、可缩放、可约束”的 `expected return-like alpha`

换句话说：

- `score` 常是研究层和排序层的输出
- `expected return` 或 `scaled alpha` 常是优化层的输入

## 直接证据

### BlackRock 的公开口径

BlackRock 官方页面给出的链路非常清楚：

- 各类 signals 先做加权组合
- 形成每个证券的 `final alpha score`
- 之后再进入组合构建
- 组合构建时同时考虑 expected return、风险、交易成本和约束

这说明：

- 研究层先输出 `final alpha score`
- 进入投资组合层时，这个分数不会裸用，而是要进入风险收益权衡框架

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

关键公开表述：

- “The final score for every security is a weighted combination of all signals”
- “The final alpha score represents our assessment of the return potential...”
- 之后 portfolio construction 会考虑 “expected return of a position” 与风险模型

我的推论：

- BlackRock 的公开表述更像是 `score -> expected return-like input -> optimizer`
- 这是基于公开流程的合理推断，不是它内部实现细节的直接披露

### MSCI / Barra 的公开口径

MSCI 关于 alpha 与 risk alignment 的研究说明了另一件很关键的事：

- 很多机构自己做 `return forecasting models`
- 风险与交易成本却用第三方模型
- 如果 alpha 与 risk model 不对齐，优化器会放大不对齐的那一部分 alpha
- 实务处理包括：
  - penalize residual alpha
  - rescale alphas

这说明：

- alpha 进入优化器前，经常不是原始 score
- 而是经过 rescale / alignment / residualization 的可优化输入

Source:

- MSCI: Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned

### 组合优化层的经典形式

Boyd 等人对 Markowitz 的现代扩展总结得很直接：

- 实务中的优化问题，本质上仍是在 expected return 与 risk 之间权衡
- 同时加入 transaction cost、leverage、各种现实约束

这意味着：

- 组合优化器最自然吃的是 `mu`，也就是 expected return 预测
- 就算研究层先产出的是分数，进入优化器前也往往要被映射到 `mu`

Source:

- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html

## 文献对 forecast mapping 的启发

### 1. 单个 predictor 往往不稳，组合 forecast 更常见

关于 return predictability 的研究，一个非常一致的现象是：

- 单 predictor 常不稳定
- 简单 forecast combination 往往比单模型更稳

一篇 2022 年研究直接发现：

- `mean combination forecast` 的样本外表现优于其他预测模型
- 在不同窗口、不同市场条件下也更稳

Source:

- Stock market return predictability: A combination forecast perspective
  - https://www.sciencedirect.com/science/article/abs/pii/S105752192200326X

对我们项目的含义：

- 第一版 alpha 层不要只靠一个 `ema_gap_120_360`
- 更合理的是几个同 horizon predictor 先形成组合 forecast

### 2. 机器学习的提升，本质是把 predictors 更好地映射到 expected returns

Gu, Kelly, Xiu 的工作把这个问题定义得很清楚：

- 资产定价里的 canonical problem，就是 `measuring asset risk premia`
- 机器学习提升来自：
  - 非线性
  - predictor interactions
  - 对 expected return 的更好映射

Source:

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398

进一步的研究也说明：

- 复杂模型常优于过于简单的 return prediction 模型
- 但复杂性真正服务的是 `expected return modeling`

Source:

- The Virtue of Complexity in Return Prediction
  - https://www.nber.org/papers/w30217

## 机构里常见的几种映射方式

下面这部分是基于上述公开资料和学术方法论的整理推论。

### A. 纯排序分数

做法：

- 每个 predictor 先标准化
- 合成一个横截面 score
- 直接用于 long/short 排名

优点：

- 简单
- 对量纲不敏感
- 适合先做研究

缺点：

- 难直接接入 mean-variance 类优化器
- 与风险模型、成本模型的耦合较弱

### B. 缩放后的 alpha

做法：

- 先得到 raw score
- 再做：
  - volatility scaling
  - cross-sectional rescaling
  - residualization
  - risk-model alignment

输出：

- `scaled alpha`

优点：

- 比纯排序更接近优化器输入
- 更容易做风险和成本控制

缺点：

- 仍然不一定有明确“bps expected return”解释

### C. 直接 expected return forecast

做法：

- 通过线性回归、shrinkage、树模型、神经网络等
- 直接预测未来 `h` bar return

输出：

- `mu_t = E[r_{t+h} | x_t]`

优点：

- 最自然接入优化器
- 最容易与 risk/cost/constraints 一起解一个统一问题

缺点：

- 对样本量、校准质量、误差分布更敏感
- 在小样本或高噪音场景下容易不稳

## 对我们 4h crypto 项目的判断

我基于调研的建议是：

### 现在不要直接做“绝对 expected return 回归”

原因：

- 我们目前样本不算大
- 数据源还偏窄，主要是价格
- 单个 predictor 还没经过充分稳健性审计

如果直接上绝对收益预测，风险是：

- 模型校准不稳
- 量纲看起来更高级，实质却更脆弱

### 更合适的是两阶段

第一阶段：

- 先输出 `standardized alpha score`
- 这是研究层主产物

第二阶段：

- 再把 score 映射成 `scaled alpha`
- 如果后面要接优化器，再进一步校准成 `expected return-like mu`

也就是说，当前最合理的路线不是二选一，而是：

`predictor -> score -> scaled alpha -> expected return-like input`

## 对当前项目的具体建议

### v1 alpha layer

输出先定义为：

- 每个币、每根 4h bar 的 `alpha_score`

不要先承诺这是精确的未来 30bar 收益预测。

### v1 mapping

建议做三层：

1. raw predictor
   - `ema_gap_120_360`
   - `breakout_360bar`
   - `rev_18bar_voladj`

2. standardized score
   - rolling robust z-score
   - volatility-aware rescaling

3. scaled alpha
   - 用历史 bucket return 或 isotonic / monotonic calibration
   - 映射成近似 future return strength

### 什么时候再升级到 expected return

满足下面条件后再升级更合理：

- 单 predictor 稳定
- 组合 predictor 稳定
- walkforward 稳定
- regime/条件切片清楚

否则先做绝对收益预测，容易只是让系统更复杂。

## 对我们下一步研究的直接结论

下一步不该直接做 HMM，也不该直接做大优化器。

更对的顺序是：

1. 定义 4h alpha 层输出为 `alpha_score`
2. 研究 `score -> future return bucket` 的映射
3. 建一个简单 `scaled alpha` 层
4. 再考虑是否需要 `expected return forecast`

## 待验证问题

- 对 crypto 4h，bucket calibration 是否比直接回归 future return 更稳
- `scaled alpha` 是否已经足够支持简单优化器
- funding / OI 数据补齐后，mapping 稳定性是否会明显提升

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI: Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned
- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html
- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
- The Virtue of Complexity in Return Prediction
  - https://www.nber.org/papers/w30217
- Stock market return predictability: A combination forecast perspective
  - https://www.sciencedirect.com/science/article/abs/pii/S105752192200326X
