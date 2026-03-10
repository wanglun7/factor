# Composite Alpha V1：落地缺口与当前样本约束

Date: 2026-03-10
Category: alpha-models

## 研究问题

继续把 `composite alpha` 从概念层推进到 v1 落地层，重点补：

1. v1 应该怎么做 `score pruning`
2. v1 是否应优先用 equal weight
3. ridge 什么时候才值得介入
4. 当前真实样本是否已经具备做 composite 的条件

## 当前样本事实

基于当前真实 `standardized score` 结果，保留下来的 score 全部来自同一个家族：

- `price_trend`

具体包括：

- `trb_50d_score`
- `trb_150d_score`
- `trb_200d_score`
- `sma_price_crossover_12/24/72_score`
- `ema_price_crossover_12/24/72_score`
- `vma_20d/50d/100d/150d/200d_score`

而下面这些非 trend 家族 score 都没有通过保真门槛：

- `prev_day_return_score`
- `amihud_20w_score`
- `funding_rate_level_score`
- `lagged_funding_rate_1_score`
- `premium_score`
- `relative_basis_score`
- `log_basis_score`
- `funding_basis_rate_score`

这意味着：

- 当前不是“多个家族信号怎么合成”的问题
- 而是“同一 trend 家族里的一组高度相近 score 要不要合成”的问题

## Source-Backed

### 1. 简单平均是组合预测中的强基准

多篇 forecast combination 文献都指出：

- simple average 很难被稳定打败
- 更复杂加权往往需要强证据和足够样本

来源：

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Combining expert forecasts: Can anything beat the simple average?
  - https://www.sciencedirect.com/science/article/pii/S016920701200088X
- Multi-Factor Indexes Made Simple
  - https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/multi-factor-indexes-made-simple/Research_Insight_Multi_Factor_Indexes_Made_Simple_November_2014.pdf

### 2. 更复杂加权不一定能稳定优于简单组合

ECB / expert forecast combination 的研究显示：

- 很多 refined combinations 在伪样本外里并不能稳定赢过 simple average

来源：

- Combining the forecasts in the ECB survey of professional forecasters: can anything beat the simple average?
  - https://www.econstor.eu/handle/10419/153711

### 3. Ridge 更适合“弱但广泛”的信号环境

Shen 和 Xiu 的结论仍然成立：

- 如果是很多弱信号一起提供边际信息，ridge 往往优于 lasso
- 但这隐含前提是：
  - 候选 predictor 足够多
  - 不是几个高度相似的规则重复表达同一趋势

来源：

- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421

### 4. subset averaging 是合理中间形态

forecast combination 文献和多因子研究都支持一个中间路径：

- 不是“全收下”
- 也不是“只留一个”
- 而是先选一小组质量较高、重复性较低的 forecast / score，再做平均

这类做法虽然未必总用 `subset averaging` 这个统一术语，但方法精神是明确存在的。

来源：

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Portfolio Construction Matters
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes

## Industry-Standard

基于这轮补充调研，可以把下面这些判断视为行业常见：

### 1. v1 先用 equal weight，不要一开始学复杂权重

如果：

- 候选数不大
- 信号家族不多
- 样本外稳定性还没充分证明

那么 equal weight 通常是更稳的起点。

### 2. pruning 比权重优化更优先

在 v1 里，更重要的是：

- 先去掉明显重复和弱信号

而不是：

- 试图靠复杂权重去修补重复信号

### 3. 同一家族内应先去重

如果保留项几乎全来自同一 family：

- 先 family 内去重
- 再决定是否值得合成

比“全部直接平均”更合理。

## Project-Specific Inference

### 1. 当前真实样本下，`composite alpha v1` 其实还没到最佳实现时点

原因很具体：

- 当前通过 score 层的全部都是 `price_trend`
- 没有第二家族通过保真门槛
- 这时做 composite，实质上只是“在一堆趋势规则里做重复加权”

所以当前最合理的判断不是“马上合成一个 composite”，而是：

- 先在 trend family 内做 pruning
- 看 family 内 subset 是否真的优于 best single score

### 2. 当前 v1 更像“subset-of-trend composite”，不是完整多家族 composite

也就是说，如果立刻进入实现，正确命名应是：

- `trend composite v1`

而不是：

- `full composite alpha v1`

### 3. 当前最值得留下的 trend 子集，按已有真实结果看，应优先围绕 breakout

当前真实 score 排名最强的是：

- `trb_200d_score`
- `trb_150d_score`
- `trb_50d_score`

而：

- crossover 类只是中等强度
- `vma_100d/150d/200d` 甚至 raw 层本身就是负的

所以即便进入 composite 研究，v1 也不该把所有 trend score 等权塞进去。

### 4. 当前最该补的不是 ridge 实现，而是 pruning rule

因为现在最大的风险不是权重不够聪明，而是：

- 候选里高度重复
- 还有本体偏弱甚至反向的 trend rule 混在里面

所以 composite 前更应该先补：

- 同 family 内按 raw 和 score 双重结果筛选
- 去掉负向或极弱 trend rule

## 当前收敛结论

如果只基于现在的知识库和真实样本，最硬的结论是：

1. `composite alpha` 这一层还需要继续调研后再实现
2. v1 默认加权应优先考虑 `equal weight`
3. 但在当前样本下，真正更优先的是 `pruning`
4. 当前样本还不适合直接做“完整多家族 composite alpha”
5. 如果下一步要推进，正确目标应是：
   - `trend family pruning`
   - 再比较：
     - `best single breakout score`
     - `subset equal-weight trend composite`

## 仍未解决的问题

当前还没被知识库收敛清楚的有：

- family 内 redundancy threshold 到底怎么定
- current sample 下 subset 选几个最合理
- composite 的晋级标准应定义为：
  - 绝对超过 best single
  - 还是只要求更稳

## Sources

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Combining expert forecasts: Can anything beat the simple average?
  - https://www.sciencedirect.com/science/article/pii/S016920701200088X
- Combining the forecasts in the ECB survey of professional forecasters: can anything beat the simple average?
  - https://www.econstor.eu/handle/10419/153711
- Portfolio Construction Matters: A Simple Example Using Value and Momentum Themes
  - https://www.aqr.com/Insights/Research/Working-Paper/Portfolio-Construction-Matters-A-Simple-Example-Using-Value-and-Momentum-Themes
- Can Machines Learn Weak Signals?
  - https://www.nber.org/papers/w33421
- Multi-Factor Indexes Made Simple
  - https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/multi-factor-indexes-made-simple/Research_Insight_Multi_Factor_Indexes_Made_Simple_November_2014.pdf
