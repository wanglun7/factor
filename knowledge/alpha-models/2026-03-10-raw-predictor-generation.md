# Raw Predictor Generation：第一层因子怎么生成

Date: 2026-03-10
Category: alpha-models

## 研究问题

第一层 `raw predictor` 不应该靠手工拍脑袋堆指标。那机构和学界通常如何“生成”候选因子，哪些生成方式在 crypto 场景里有证据支撑。

## 核心结论

第一层因子生成不应理解为“随便发明更多公式”，而应是 **受约束的候选生成流程**：

1. 先从可解释机制出发，确定 descriptor 家族
2. 再对每个 descriptor 做有限的变换族生成
3. 再对不同 horizon / scale 做系统映射
4. 再让第二层和第三层去淘汰，而不是在第一层人工拍脑袋定生死

对我们当前项目，第一层最合理的生成方式不是继续扩 `trend`，而是定向扩充：

- `reversal`
- `volatility_liquidity`
- `derivatives_carry_funding`

## Source-Backed

### 1. 原始预测力主要来自少数稳定 descriptor 家族，而不是无限多自造指标

Gu, Kelly, Xiu 的研究表明，机器学习带来的优势主要来自 **非线性和交互项**，但所有模型最终都指向一个较小的主导信号集合，核心包括：

- momentum / reversal
- liquidity
- volatility

来源：

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
  - https://academic.oup.com/rfs/article/33/5/2223/5758276

### 2. 高维因子世界里，关键不是更多候选，而是从 characteristics 中提炼有效结构

Lettau 关于 factor zoo 的研究强调，面对大量候选 characteristic，应该做的是从 characteristic 信息中提炼更少、更有效的结构，而不是继续扩 zoo。

来源：

- High-Dimensional Factor Models and the Factor Zoo
  - https://www.nber.org/papers/w31719

### 3. 机器学习有价值，但主要价值在“发现交互和非线性”，不是替代机制

Gu, Kelly, Xiu 以及后续 crypto 研究都支持：

- 先有 descriptor
- 再让机器学习发现非线性和交互

而不是先让模型在无约束特征池里乱搜。

来源：

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
- Predicting cryptocurrency returns with machine learning: Evidence from high-dimensional factor modeling
  - https://doi.org/10.1016/j.pacfin.2025.103033

### 4. crypto 的有效 descriptor 不是只剩 trend，短期 reversal / liquidity / basis / funding 都有证据

crypto 文献目前较一致支持以下方向具备预测力：

- short-term reversal
- momentum
- liquidity
- intraday momentum / reversal
- basis / futures-spot deviations
- funding / perpetual pricing variables

来源：

- Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets
  - https://doi.org/10.1016/j.irfa.2021.101908
- Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both
  - https://doi.org/10.1016/j.najef.2022.101733
- Beyond Basis Basics: Liquidity Demand and Deviations from the Law of One Price
  - https://www.nber.org/papers/w26773
- Perpetual Futures Pricing
  - https://www.nber.org/papers/w32936

### 5. 在 crypto out-of-sample 预测里，经济机制驱动的方法优于“通用万能法”

一篇专门比较 crypto 预测器和算法的研究发现：

- 很多常见预测器样本外并不稳
- 受经济机制启发的方法优于通用 shrinkage / universal forecasting methods

这意味着第一层扩库不能走“通用 feature zoo”路线，而要按机制定向扩。

来源：

- Out-of-sample forecasting of cryptocurrency returns: A comprehensive comparison of predictors and algorithms
  - https://doi.org/10.1016/j.physa.2022.127379

## Industry-Standard

基于上面的证据，可以把第一层因子生成总结成 3 条行业常见原则：

### 1. Descriptor first, transform second

先确定少数 descriptor 家族，再从每个家族系统生成候选，而不是先写大堆公式。

### 2. 有限变换族，而不是无限搜索

每个 descriptor 家族只允许有限变换，例如：

- level
- change
- deviation
- rank / percentile
- short / medium / long horizon
- pairwise interaction

### 3. 交互项是第二波生成，而不是第一波

先验证单 descriptor 和单变换族，再补：

- trend x liquidity
- reversal x liquidity
- funding x basis

而不是一开始就爆炸式组合。

## Project-Specific Inference

### 1. 我们现在不该继续扩 trend

当前三层实验已经证明：

- trend 是强主线
- non-trend family 还弱
- 第三层失败不是 trend 不够，而是非 trend 不够强

所以第一层下一轮扩库不该再给 `price_trend` 加更多 raw predictor。

### 2. 第一层扩库应按“descriptor x transform x horizon”生成

对当前项目，最合理的原始因子生成骨架是：

- `descriptor`
  - last return
  - multi-bar return
  - realized volatility
  - Amihud / dollar volume
  - funding level
  - funding change
  - spot-perp basis

- `transform`
  - level
  - change
  - ratio
  - deviation from rolling norm
  - relative-to-volatility
  - interaction / conditioning

- `horizon`
  - short
  - medium
  - long

### 3. 下一轮扩库的正确对象是三组

#### A. Reversal

- multi-horizon lagged return
- intraday / multi-bar reversal
- reversal scaled by recent volatility
- reversal conditioned on jump / liquidity state

#### B. Volatility / Liquidity

- realized vol level / change
- Amihud variants
- dollar volume shock
- volatility compression / expansion
- liquidity-conditioned reversal or trend

#### C. Derivatives / Carry / Funding

- funding level
- funding change
- funding dispersion over windows
- basis level
- basis change
- funding-basis interaction

### 4. 第一层应允许“系统生成 + 自动淘汰”，但不能无约束

下一轮 raw predictor 生成可以自动化，但候选空间必须被明确限制在：

- 少数 descriptor
- 少数 transform
- 少数 horizon

不能直接让程序对任意算子和任意窗口乱拼。

## 对本项目的直接含义

下一轮第一层扩库最合理的方向不是“手动加几个新指标试试”，而是：

1. 先定义 descriptor 库
2. 再定义允许的 transform 库
3. 再定义允许的 horizon 库
4. 程序化生成小规模候选池
5. 继续走现有第二层和第三层自动淘汰链路

## 结论

第一层 raw predictor 的正确做法不是“继续想更多公式”，而是：

- 用研究先锁 descriptor 家族
- 用有限变换族系统生成候选
- 让后续层自动筛选

对当前项目，最值得扩的是：

- reversal
- volatility_liquidity
- derivatives_carry_funding

而不是继续扩 trend。
