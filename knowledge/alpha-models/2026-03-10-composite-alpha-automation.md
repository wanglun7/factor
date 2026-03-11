# Composite Alpha V1：自动化选择与组合

Date: 2026-03-10
Category: alpha-models

## 研究问题

第三层 `composite alpha` 应该靠人工判断，还是应做自动化筛选和自动化组合。对于我们当前 4h 时间序列 alpha 流程，自动化应该做到哪一层，哪些环节必须受约束。

## 核心结论

第三层应采用 **受约束的自动化**，而不是人工拍脑袋，也不是无限制搜索。

更具体地说：

1. `composite alpha` 的候选池应由前两层自动产出，而不是人工挑
2. 第三层应自动做 pruning / subset selection / combination
3. 自动化的搜索空间必须被研究先约束住，不能无限尝试方法和权重
4. v1 的默认组合形式应优先是：
   - family-aware subset averaging
   - family-neutral equal weighting
5. ridge 或更复杂加权不应作为 v1 默认，只有在候选显著增多且弱信号广泛存在时才值得介入

## 当前样本更新

在第二层重构后，当前真实样本里已进入 `retain_for_composite_v1 = True` 的分数不再只有 `price_trend`，而是包含：

- `price_trend`
- `reversal_mean_reversion`
- `volatility_liquidity`
- `derivatives_carry_funding`

这意味着第三层已经具备了做跨 family 自动化组合的条件。旧的“当前只能做 trend family pruning”判断已经过时。

## Source-Backed

### 1. 简单平均和 subset averaging 是强基准

MSCI 关于多因子组合的研究指出，在缺乏强主动观点和技能时，简单等权组合 historically 非常有效，并且很多更复杂动态方法在考虑换手成本后并不占优。

Sources:

- MSCI, Multi-Factor Indexes Made Simple
  - https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/multi-factor-indexes-made-simple/Research_Insight_Multi_Factor_Indexes_Made_Simple_November_2014.pdf
  - https://www.msci.com/research-and-insights/blog-post/multi-factor-indexes-made-simple

### 2. 组合预测的一个成熟自动化思路是“先删大多数，再对剩余平均”

Diebold 和 Shin 的研究给出的核心结论很直接：

- 大多数候选 forecast 应被丢弃
- 剩余 forecast 做平均
- subset averaging 是简单平均和复杂稀疏权重之间的强中间路径

Source:

- Machine Learning for Regularized Survey Forecast Combination: Partially-Egalitarian LASSO and its Derivatives
  - https://www.nber.org/papers/w24967

### 3. 自动化 subset 组合本身是正式方法

Complete subset regressions 的研究表明，可以对一组候选 predictor 的子集系统性组合，并利用子集复杂度控制 bias-variance tradeoff。其结果在 return prediction 场景中优于若干常见基准，包括 simple average、univariate combinations、ridge、bagging 等。

Source:

- Complete subset regressions
  - https://www.sciencedirect.com/science/article/abs/pii/S0304407613000948

### 4. bottom-up / top-down factor combination 都是正式路径

MSCI 关于多因子组合的研究表明：

- 可以先在底层标的/score 层合成
- 也可以先形成单因子组合再上层组合
- 关键不在“是否自动化”，而在是否有清晰、可重复、可约束的组合规则

Source:

- How can Factors be Combined?
  - https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/how-can-factors-be-combined/ff891dc6-61ac-9d77-1f39-aeb0113a767d.pdf

## Industry-Standard

基于上面的证据，可以把下面这些判断视为行业常见：

### 1. 候选池自动生成，但先验受约束

通常不是人工手挑最终信号，而是：

- 先由前序层自动给出合格候选
- 再在有限方法空间内自动比较

### 2. pruning 比复杂权重优化更优先

对于候选数不大、而且存在明显重复的情形：

- 先自动 pruning
- 再对存活项做简单组合

比直接上 ridge / optimizer 更合理。

### 3. family-neutral 组合是合理的自动化防偏机制

如果一个 family 天生 predictor 数量更多，直接全体等权会让它自动占更大权重。更稳妥的 v1 做法是：

- family 内先聚合
- family 间再等权

## Project-Specific Inference

### 1. 我们的第三层应是自动化的，但不是自由搜索

对当前项目，最合理的 v1 形式是：

- 输入：第二层 `retain_for_composite_v1 = True` 的 score
- 第一步：自动 pruning
- 第二步：family 内 subset averaging
- 第三步：family 间 equal weight

不应做：

- 任意自由权重搜索
- per-score 连续优化
- 直接 ridge 作为默认主路径

### 2. pruning 应采用双重自动规则

自动 pruning 至少应同时看：

- raw 层是否同号且非弱负
- 第二层是否通过并保留
- 同 family 内相关性/重复度

也就是说，不是只凭第二层 `pass_tier` 决定。

### 3. 第三层 v1 的正确自动化目标是“subset average with family neutrality”

这比两种极端都更合理：

- 比“所有 survive score 全平均”更稳
- 比“人工只挑一个 best single”更系统

### 4. v1 的验收应是自动化 horse race

第三层不应人工说哪个更好，而应自动比较至少三类对象：

- `best_single_score`
- `family_subcomposites`
- `full_family_neutral_composite`

然后看哪个在相同评估协议下更好。

## 对本项目的直接含义

第三层现在已经可以按下面的骨架推进：

1. 候选池自动读取第二层结果
   - 仅保留 `retain_for_composite_v1 = True`
2. 自动第一轮过滤
   - 去掉 raw 层为负或极弱的 score
3. family 内自动去冗余
   - 以相关性或相似度阈值做聚类/去重
4. family 内自动 subset average
5. family 间 equal weight
6. 自动比较：
   - best single
   - trend-only subset composite
   - cross-family family-neutral composite

## 仍待定稿的问题

还需要继续收敛的，不是“要不要自动化”，而是自动化规则的具体参数：

- raw 弱负的淘汰阈值
- family 内冗余阈值
- family 内最多保留几个 score
- composite 的晋级标准应定义为：
  - 绝对优于 best single
  - 或只要求更稳

## 结论

第三层现在不该再按人工判断推进。正确方向是：

- 研究约束候选空间
- 自动 pruning
- 自动 family-aware subset averaging
- 自动 horse race 比较

也就是说，第三层的本质不是“人工组合分数”，而是 **受约束的自动化 forecast combination**。
