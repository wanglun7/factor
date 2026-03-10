# Alpha 层蓝图：标准化、合成、校准

Date: 2026-03-10
Category: alpha-models

## 研究目标

把“机构 alpha model 的第一步”继续拆开，回答下面 5 个问题：

1. predictor 怎么先变成可比较对象
2. 多个 predictor 怎么组合
3. 组合后的分数怎么校准
4. 进入优化器之前要做什么处理
5. 对我们当前 4h crypto 项目，应该怎么定义 v1 alpha layer

## 总结结论

调研后，一个更接近机构实务的 alpha 层可以抽象成：

`raw predictors -> standardized scores -> composite alpha -> scaled/calibrated alpha -> optimizer input`

这条链路里最关键的不是某个单独公式，而是：

- 所有 predictor 必须先被放到同一 horizon
- 合成通常优于孤立单 predictor
- 进入优化器前，alpha 往往要做 rescale / alignment / shrinkage

## 1. 标准化为什么是必要步骤

### 直接证据

BlackRock 的公开链路说明：

- 不同来源的 signals 会被加权组合成 `final alpha score`

这件事本身意味着：

- 原始 predictor 不能保持各自原量纲直接相加
- 组合前一定存在某种形式的标准化或映射

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### 我的推论

虽然公开页面不会披露具体公式，但从“多源 signals -> weighted combination”这个结构出发，标准化是不可省略的。

对于我们这种 4h crypto 系统，标准化的目标至少有三个：

1. 不同 predictor 可比
2. 不同资产可比
3. 不同时间窗口下的数值稳定

### 实务上可接受的 v1 做法

当前更稳妥的是：

- 每个 predictor 先做滚动稳健标准化
- 用 median / MAD，而不是只用 mean / std
- 再做必要的 volatility scaling

这一步我现在把它定义为：

`standardized score`

而不是直接叫 expected return。

## 2. 多 predictor 合成通常优于单 predictor

### 直接证据 1：AQR 的 integrated score

AQR 关于组合价值和动量主题的论文指出，实务里长期存在两种做法：

- 先各自选最高分再混合
- 先把价值和动量分数整合成 average composite / integrated score，再建组合

Source:

- AQR: Portfolio Construction Matters
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes

这说明：

- 机构会把 predictor 先合成为 integrated score
- 合成本身就是 alpha 层的一部分，不是附属工作

### 直接证据 2：forecast combination 文献

Diebold 和 Lopez 的综述说明：

- forecast evaluation 和 forecast combination 是 forecasting workflow 的核心部分
- 多个 forecast 是否应被组合，是标准问题

Source:

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192

2022 年关于股票回报预测的研究也发现：

- `mean combination forecast` 的样本外表现优于其他预测模型

Source:

- Stock market return predictability: A combination forecast perspective
  - https://www.sciencedirect.com/science/article/abs/pii/S105752192200326X

### 对我们的直接含义

当前项目不能继续把 `ema_gap_120_360` 当作“alpha 层本体”。

它更应该是：

- 一个候选 predictor

然后进入一个 predictor 集合，例如：

- `ema_gap_120_360`
- `breakout_360bar`
- `rev_18bar_voladj`
- `liquidity-aware trend adjustment`

最后合成一个 composite alpha score。

## 3. 高维场景下，合成通常要配 shrinkage

### 直接证据

Kozak, Nagel, Santosh 的研究说明：

- 大量 predictors 的联合信息可以有用
- 但需要 shrink 掉低信息量方向
- 他们通过压缩 candidate factors 的低方差主成分贡献，获得更稳健的样本外表现

Source:

- Shrinking the Cross Section
  - https://www.nber.org/papers/w24070

### 对我们的含义

这不是说我们现在就该上大规模 PCA。

更合理的 v1 含义是：

- predictor 数量控制得很小
- 合成时不要给每个 predictor 随意自由权重
- 优先用简单、保守、带 shrinkage 味道的方法

例如：

- equal weight
- equal weight after volatility normalization
- ridge / lasso 小规模线性合成

## 4. 校准：score 不等于 optimizer 能直接吃的 alpha

### 直接证据

MSCI 的研究明确指出：

- 机构常有自建 return forecasting model
- 但优化器里的 risk / cost 模型可能来自另一套体系
- 如果 alpha 与 risk model 不对齐，优化器会放大不对齐部分
- 可行方法包括：
  - penalize residual alpha
  - rescale alphas

Source:

- MSCI: Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned

### 这对 alpha 层的含义

进入优化器前，alpha 通常要经历至少一种处理：

- rescaling
- residualization
- alignment to risk factors
- confidence weighting

所以：

- `final score` 不是终点
- 更像是 `pre-optimization alpha object`

## 5. 组合优化器最自然吃的是 expected-return-like 输入

### 直接证据

Boyd 对 Markowitz 现代扩展的综述说明：

- 组合构建核心仍是 expected return 与 risk 的权衡
- 再加入交易成本、杠杆和现实约束

Source:

- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html

### 对我们的含义

因此最合理的分层不是：

`raw factor -> optimizer`

而是：

`raw factor -> standardized score -> scaled alpha -> expected-return-like optimizer input`

这里最后一步不一定要精确回归出真实 bps。

只要它满足：

- 量纲一致
- 单调性合理
- 能和风险模型、成本模型一起工作

它就已经具备 optimizer input 的资格。

## 6. 对当前 4h crypto 项目的 v1 定义

### 我建议的 v1 alpha layer 结构

#### 层 1：raw predictors

- `ema_gap_120_360`
- `breakout_360bar`
- `rev_18bar_voladj`
- 之后再考虑 `funding-aware predictor`

#### 层 2：standardized scores

- rolling robust z-score
- volatility adjustment
- winsorization / clipping

#### 层 3：composite alpha

第一版只允许：

- equal weight composite
- ridge-shrunk linear composite

不允许一开始就搞复杂 stack / boosting / regime-specific ensemble。

#### 层 4：scaled alpha

第一版更合理的做法：

- 看 score 分桶后的未来收益
- 用 bucket mean 或单调映射把 score 转成 `scaled alpha strength`

我这里刻意写成 `scaled alpha strength`，不是直接叫 exact expected return。

#### 层 5：handoff to optimizer

在还没有完整风险模型之前，先把它交给简单仓位映射层：

- gross cap
- vol targeting
- turnover penalty

等后面风险模型准备好，再升级为正式优化器输入。

## 7. 现在这一层最合理的研究顺序

### Alpha 层研究清单

1. predictor 稳健性审计
2. predictor 之间相关性和冗余分析
3. composite score 设计
4. score 到 future return bucket 的校准
5. scaled alpha 到仓位映射
6. 再考虑 regime-conditioned alpha

### 不该倒过来

不应该先做：

- HMM
- 大优化器
- 复杂深度网络

因为这些都依赖 alpha 层已经基本成立。

## 8. 对我们后续调研的自动拆解

alpha 层还剩下 3 个必须补齐的问题：

1. `predictor evaluation`
   - 机构更关注哪些 alpha-layer 诊断指标
2. `predictor redundancy`
   - predictor 之间如何去共线、去重复表达
3. `score calibration`
   - score 如何映射成可用的 scaled alpha / expected-return-like 输入

我下一步会继续按这三个问题往下调研，不再等用户逐条触发。

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- AQR: Portfolio Construction Matters
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes
- MSCI: Are Your Factors Aligned?
  - https://www.msci.com/research-and-insights/blog-post/are-your-factors-aligned
- Markowitz Portfolio Construction at Seventy
  - https://web.stanford.edu/~boyd/papers/markowitz.html
- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Shrinking the Cross Section
  - https://www.nber.org/papers/w24070
- Stock market return predictability: A combination forecast perspective
  - https://www.sciencedirect.com/science/article/abs/pii/S105752192200326X
