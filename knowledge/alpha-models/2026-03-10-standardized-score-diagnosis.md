# Standardized Score：连续型信号信息损失、实现对照与 Gate 诊断

Date: 2026-03-10
Category: alpha-models

## 研究问题

围绕当前 `standardized score` 层，回答 3 个问题：

1. 为什么连续型 predictor 的 score 方法会吃掉 funding / basis 信息，机构通常怎么处理这类信号
2. 我们现在的 score 方法是否做对了
3. 当前评估 gate 到底是门槛太严，还是方法/实现本身有问题

## 当前代码事实

当前实现见：

- [standardized_scores.py](/Users/lun/Desktop/manifex/factor/research/standardized_scores.py)

关键逻辑是：

- 连续型 predictor：
  - `rolling_winsorized_zscore`
  - `time-series per asset`
  - `z_window = 1512`
  - `z_min_periods = 360`
  - `winsor_clip_z = 3`
- 规则型 predictor：
  - `binary_rule: 0/1 -> -1/+1`
  - `ternary_rule: -1/0/+1` 保持不变
- score gate：
  - `direction_alignment_ok`
  - `delay_alignment_ok`
  - `distribution_ok`
  - `spread_preservation_ratio >= 0.7`

当前真实结果：

- rule-based trend scores 几乎全部 `preservation_ratio = 1.0`
- 连续型 funding / basis / reversal / liquidity scores 大多只有：
  - `0.28` 到 `0.66`

对应真实产物：

- [standardized_score_summary.csv](/tmp/standardized_scores_real_v1/standardized_score_summary.csv)
- [standardized_score_alignment.csv](/tmp/standardized_scores_real_v1/standardized_score_alignment.csv)
- [standardized_score_distribution.csv](/tmp/standardized_scores_real_v1/standardized_score_distribution.csv)

## Source-Backed

### 1. `winsorization + z-score` 是公开方法论支持的通用标准化方案

MSCI 等公开方法明确支持：

- winsorize
- 然后 z-score
- 再合成更高层 score

这说明：

- 我们当前对连续型 predictor 先做标准化，本身不是乱做
- 这是一个合理的通用起点

来源：

- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf

### 2. 公开文献并没有说“所有连续型金融 predictor 都应统一用同一种 moving-window z-score”

现有公开方法论支持的是：

- z-score 是常见标准化方式

但没有直接支持：

- funding
- basis
- carry
- liquidity

这类时间序列连续信号都应一律采用同一个 rolling moving-moment z-score 口径。

也就是说：

- `z-score` 作为 generic normalization 是有证据的
- `同一套 moving z-score 适配所有连续型 alpha predictor` 没有被同等强度证据支持

### 3. 时间变化 z-score 的构造方式本身会显著影响结果

关于 time-varying z-score 的研究表明：

- 用 exponentially weighted moments 构造的 z-score
- 可能优于简单 moving moments

这至少说明：

- 当前我们用的 rolling moving mean/std 不是唯一合理方式
- z-score 的时间窗口构造本身就会改变信号质量

来源：

- Time-varying Z-score measures for bank insolvency risk: Best practice
  - https://www.sciencedirect.com/science/article/pii/S0927539823000610
  - https://econpapers.repec.org/RePEc:eee:empfin:v:73:y:2023:i:c:p:170-179

### 4. funding / basis 研究里，经济含义通常直接落在“水平”或“价差”本身

我们知识库已有 funding / basis 相关研究支持的是：

- `funding rate level`
- `realized funding rate`
- `premium`
- `relative basis`
- `log basis`

这些 predictor 在研究里本身就是以“原始 level / spread / basis”形式出现，而不是先被解释为“偏离自身长期均值多少个标准差”。

这说明：

- 对 funding / basis 来说，raw level 可能就是经济含义的一部分
- 如果把它们过度 recentre / rescale，可能会把这部分经济含义压掉

来源：

- Anatomy of Perpetual Futures Returns
- ETH price / funding rate 相关研究
- Perpetual Futures Pricing
  - https://www.nber.org/papers/w32936

### 5. simple average / equal-weight 之所以常见，是因为更复杂变换常常不稳定

forecast combination 文献反复说明：

- simple average 是强基准
- refined transformation / weighting 并不稳定地赢

这个结论虽然不直接针对 z-score，但它支持一个重要方法论态度：

- 不应默认“更复杂的变换一定更好”

来源：

- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Combining expert forecasts: Can anything beat the simple average?
  - https://www.sciencedirect.com/science/article/pii/S016920701200088X

## Industry-Standard

### 1. 连续型信号的标准化通常是“让它可比较”，不是“必须保留原始经济量级”

所以：

- z-score 本身更像比较坐标
- 而不是对原始 carry / basis level 的忠实复刻

这意味着：

- 如果一个连续型 predictor 的 alpha 主要来自原始 level 本身
- 标准化后表现变弱并不奇怪

### 2. 对 carry / basis / spread 类信号，实务中常保留 level / sign / bucket 含义

虽然公开机构不会细讲每个信号的具体代码，但从大量 carry / spread 实务可看出：

- 这类信号常直接用 level
- 或阈值 / bucket
- 或百分位 / rank

而不是一律做深度去均值处理

### 3. moving-window 标准化容易压平慢变量

对：

- carry
- basis
- funding
- liquidity

这类缓慢变化、但 level 本身有经济含义的 predictor，

如果用长窗口滚动均值/方差去 recentre：

- 强信号可能只剩“相对历史异常程度”
- 不再保留“绝对水平是否有利”的信息

## Project-Specific Inference

### 1. 为什么当前 continuous predictor 的 score 方法会吃掉 funding / basis 信息

基于当前真实结果和上面证据，最合理的解释不是代码算错，而是：

#### A. 我们把“level signal”变成了“deviation-from-own-history” signal

funding / basis 这类 predictor 原本的经济含义可能是：

- funding 高就是一种状态
- basis 高就是一种状态

但 current score 方法把它们改成了：

- 相对过去 1512 bars 均值和方差的标准化偏离

这会改变信号定义本身。

#### B. 长窗口 moving moments 会进一步稀释慢变量

当前窗口：

- `1512` bars，大约 252 天

对 funding / basis 这种慢变量来说，这会让 score 更像：

- 当前是否是相对自己一年历史的异常值

而不是：

- 当前绝对 carry / basis 水平是否高

#### C. clipping + z-score 对厚尾 spread 类信号会压缩极端区间

当前真实分布里：

- `log_basis_score` 最小值接近 `-39`
- `premium_score` 最小值接近 `-32`
- funding 类最小值接近 `-20`

这说明：

- 这些信号分布本身厚尾且不稳定
- moving z-score 后仍然存在很强形状问题
- 其原始极端区间很可能正是预测力来源之一

### 2. 我们当前的 score 方法是不是“对的”

答案应分成两层：

#### 对于规则型 trend predictor

大体是对的。

原因：

- 规则型原本就是 bounded signal
- 我们只是把 `0/1` 中心化成 `-1/+1`
- 结果也证明几乎是无损转换

#### 对于连续型 predictor

只能说：

- **作为 generic v1 默认方法，是合理的**
- **但作为 funding / basis / liquidity / reversal 的当前最终方案，不够对**

也就是说：

- 不是“完全错”
- 也不是“已经证明最合适”
- 更准确是：
  - `source-backed generic normalization`
  - 但不是 `source-backed optimal method for these predictors`

### 3. 当前 gate 的问题在哪里

当前 gate 核心问题不是 bug，而是：

#### A. 它对 rule-based 和 continuous predictor 不对称

rule-based：

- 近乎 identity transform
- 很容易做到 `preservation_ratio = 1`

continuous：

- 经历真正的分布变换
- 自然更容易丢 raw spread

所以同一个 `0.7 preservation` 门槛，对两类信号并不公平。

#### B. `spread_preservation_ratio >= 0.7` 是项目规则，不是公开证据给出的标准

目前知识库没有找到公开来源说：

- standardized score 必须保住 raw spread 的 70% 才算合格

这个门槛是我们自己的保真 gate，不是 source-backed canon。

#### C. 这个 gate 更适合检查“变换是否近似 identity”

对 rule-based 它很合适。  
但对 continuous predictor：

- 如果标准化的目的是让它进入共同坐标系
- 那么“还保不保留 70% 的 raw spread”
- 未必是最好的唯一标准

### 4. 现在问题更像“方法和 gate 共同导致 continuous predictor 被系统性压制”

所以当前正确诊断不是：

- raw alpha 不存在

而是：

- `continuous predictor` 的 score 方法和 gate 组合
- 当前不利于 funding / basis / liquidity 这类信号通过

## 当前最硬的结论

1. 现在 continuous predictor 被筛掉，不是代码 bug 导致的假结果
2. 但也不能据此得出“funding / basis raw alpha 不存在”
3. 当前 `rolling moving-moment z-score` 更适合 generic normalization，不一定适合 carry / basis / spread level signals
4. 当前 `0.7 preservation gate` 是项目自定且偏严格，且对 continuous predictor 明显更苛刻
5. 因此现在最该继续研究的，不是直接否定这些 continuous signals，而是：
   - 它们应使用什么 score 方法
   - 它们应使用什么单独的 gate

## 对下一步的直接含义

如果继续推进，这一层不该立刻修改代码，而应先补两项研究：

1. `continuous score alternatives`
   - raw level preserve
   - percentile / rank transform
   - EW-moment z-score
   - bucketed / thresholded score

2. `score gate redesign`
   - rule-based 与 continuous 分开验收
   - continuous 不再只看 `preservation_ratio`
   - 增加 monotonicity / direction / delay stability 权重

## Sources

- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf
- Time-varying Z-score measures for bank insolvency risk: Best practice
  - https://www.sciencedirect.com/science/article/pii/S0927539823000610
  - https://econpapers.repec.org/RePEc:eee:empfin:v:73:y:2023:i:c:p:170-179
- Perpetual Futures Pricing
  - https://www.nber.org/papers/w32936
- Forecast Evaluation and Combination
  - https://www.nber.org/papers/t0192
- Combining expert forecasts: Can anything beat the simple average?
  - https://www.sciencedirect.com/science/article/pii/S016920701200088X
