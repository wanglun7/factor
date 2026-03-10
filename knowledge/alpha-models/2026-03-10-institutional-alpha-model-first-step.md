# 机构 Alpha 模型的第一步

Date: 2026-03-10
Category: alpha-models

## 研究问题

机构在系统化投资链路里，第一步的 `alpha model` 到底在做什么。

重点不是 regime、优化器、执行，而是：

- 输入是什么
- 输出是什么
- 为什么这一步先做
- 它和后面的 risk / portfolio / execution 怎么衔接

## 核心结论

机构的第一步 alpha 模型，本质上是一个 `expected return engine` 或 `alpha score engine`。

它做的事情通常是：

1. 把原始信息分成几类信号
2. 在统一 horizon 上把信号映射成可比较的预测值
3. 合成单一的 alpha score 或 expected return forecast
4. 把这个 forecast 交给风险模型和组合优化器

它不是最终仓位决策器，也不是 regime 模型。

## 直接证据

### BlackRock

BlackRock 官方系统化投资页面明确展示了一个非常标准的结构：

- 先分别构造 `fundamental`、`sentiment`、`macro` 信号
- 再把这些信号做加权组合
- 形成每个证券的 `final alpha score`
- 再进入组合构建
- 组合构建时同时考虑预期收益、风险、交易成本和约束

这说明：

- alpha 模型的产物是 `score` 或 `expected return`
- 后面的 portfolio construction 才决定仓位大小

Source:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing

### MSCI / Barra

MSCI 的公开材料强调两件事：

1. 因子模型与投资策略要整合
2. 不同持有期限要用不同 horizon 的模型

这意味着：

- alpha 模型不是脱离期限独立存在的
- 你先定义的是 `forecast horizon`
- 然后风险模型、组合模型、交易假设都要和它对齐

Source:

- MSCI Factor Allocation Model
  - https://www.msci.com/research-and-insights/paper/factor-allocation-model-integrating-factor-models-and-strategies-into-the-asset-allocation-process
- MSCI Multiple-Horizon Equity Models
  - https://app2-nv.msci.com/products/analytics/models/multiple-horizon_equity_models/

### 学术证据

Gu, Kelly, Xiu 的研究把 alpha 模型问题定义得很直接：

- 资产定价里的核心问题之一，就是把大量 predictors 映射成 expected returns
- 机器学习提升，主要来自非线性和交互项的利用
- 但最终重要的 predictor 家族依然集中在动量、流动性、波动率等大类

我的推论是：

- 机构 alpha 模型的重点不是“多发明几个名字花哨的因子”
- 而是“把一组有经济逻辑的 predictors 更稳定地映射成 forecast”

Source:

- NBER: Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398

## 机构式链路里，alpha model 这一层的定义

### 输入

- 价格特征
- 成交和流动性特征
- 基本面特征
- 情绪和文本特征
- 宏观特征
- 另类数据

### 中间处理

- 特征标准化
- 缺失和异常值处理
- 按 horizon 对齐
- 单信号 forecast
- 多信号合成
- shrinkage / regularization / ensemble

### 输出

- `alpha score`
- `expected return forecast`
- 某些机构也会输出 forecast confidence

### 下一层怎么接

- risk model 吃 `forecast + exposures + covariance`
- optimizer 吃 `forecast + risk + cost + constraints`
- execution 不直接吃 raw factor，而是吃 target weights

## 对本项目的直接含义

当前项目如果要按机构方法做，第一步不是继续讨论复杂 regime。

第一步应该先明确：

1. 我们的交易 horizon 是什么
2. 我们要输出的是 `score` 还是 `expected return`
3. 哪些原始特征进入 alpha 层
4. 这些特征如何被标准化和合成

对现在的 4h 项目，更合理的 v1 是：

- 目标 horizon 先固定，例如 `6 / 18 / 30 bars`
- 每个资产、每根 4h bar 输出一个 `alpha score`
- 先用少量、可解释的价格类特征做第一版 forecast engine
- 之后再决定是否引入 funding、OI、regime

## 现在不该先做什么

- 不先做复杂 regime switching
- 不先做庞大的优化器
- 不先做黑盒深度网络

原因不是这些没用，而是：

- 这些模块是服务 alpha 的
- 不能替一个还没被证实的 alpha 本体遮羞

## 对当前 `ema_gap_120_360` 的定位

`ema_gap_120_360` 现在还只是一个 `candidate predictor`。

离机构意义上的 alpha model 还差两层：

1. 变成统一 forecast 的映射层
2. 和其他同 horizon predictors 做合成层

所以它现在最多说明：

- 趋势类 predictor 可能有用

它还不能说明：

- 我们已经有一个完整 alpha model

## 我们下一步该做什么

### v1 alpha model

先做一个明确的 4h `expected return engine`：

- 输入：
  - `ema_gap_120_360`
  - `breakout_360bar`
  - `rev_18bar_voladj`
  - `realized_vol_120bar`
  - `amihud_120bar`
- 处理：
  - 统一标准化
  - horizon 对齐
  - 简单线性合成或 shrinkage 合成
- 输出：
  - 每个币每根 bar 一个 `alpha_score_t`

### v1 研究顺序

1. 明确 alpha 层的输出定义
2. 做单 predictor 稳健性审计
3. 做同 horizon predictor 合成
4. 再评估是否需要 regime-conditioned alpha

## 待验证问题

- 对 crypto 4h 来说，输出 `score` 还是直接输出 `expected return` 更稳
- 价格类 predictor 的合成是否比单一 `ema_gap_120_360` 更稳
- funding / OI 数据不足时，第一版 alpha 层是否先只做 price + liquidity

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI Factor Allocation Model
  - https://www.msci.com/research-and-insights/paper/factor-allocation-model-integrating-factor-models-and-strategies-into-the-asset-allocation-process
- MSCI Multiple-Horizon Equity Models
  - https://app2-nv.msci.com/products/analytics/models/multiple-horizon_equity_models/
- NBER: Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
