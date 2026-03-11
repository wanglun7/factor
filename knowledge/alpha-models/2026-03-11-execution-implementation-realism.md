# Execution / Implementation Realism：Position Mapping 之后做什么

Date: 2026-03-11
Category: alpha-models

## 研究问题

在当前链路里，已经打通：

- `raw generation`
- `standardized score + admission`
- `composite alpha`
- `scaled alpha`
- `position mapping`

下一层需要回答 4 个问题：

1. 更真实的成本模型该怎么做
2. `position -> execution` 该怎么映射
3. 这一层该怎么评估
4. 为什么当前优先做 `execution realism`，而不是先做完整 `risk model / optimizer`

## 核心结论

调研后，更稳的结论是：

1. 下一层应先做 **execution / implementation realism**
2. v1 不应直接上完整冲击模型或 optimizer
3. 对当前 `BTC 4h single-asset`，最合理的是：
   - `realized_position`
   - 加 `execution lag`
   - 加 `implementation shortfall style cost decomposition`
   - 加 `vol/liquidity-aware slippage proxy`
4. 这一层的正式目标不是“更优仓位”，而是：
   - **验证当前仓位路径在更真实执行条件下还能否成立**

## 1. 更真实的成本模型

### 1.1 基础概念：Implementation Shortfall

Perold (1988) 把 implementation shortfall 定义为：

- 理论组合收益
- 与真实执行后收益之间的差

这意味着执行成本不只是：

- commission
- spread
- market impact

还包括：

- 从生成目标仓位到真正开始交易之间的机会成本

Source:

- Perold, *The Implementation Shortfall: Paper versus Reality*
  - https://cir.nii.ac.jp/crid/1360011143955136384

### 1.2 机构和实务里怎么量化交易成本

Frazzini, Israel, Moskowitz 在真实机构交易数据上把成本拆成：

- implementation shortfall
- market impact
- execution cost
- opportunity cost

并强调真实策略实现里：

- 风格差异很大
- 交易成本和策略换手、流动性、交易规模密切相关

Source:

- Frazzini, Israel, Moskowitz, *Trading Costs of Asset Pricing Anomalies*
  - https://pages.stern.nyu.edu/~afrazzin/pdf/Trading%20Cost%20of%20Asset%20Pricing%20Anomalies%20-%20Frazzini%2C%20Israel%20and%20Moskowitz.pdf

### 1.3 对当前项目最合理的 v1 成本模型

对 `BTC 4h single-asset`，v1 不适合直接上完整 Almgren-Chriss 冲击优化，但应把成本从单一 `10bps` 升级成分层模型：

#### A. Base explicit cost

- `commission + fees + spread proxy`

仍可保留成一个基础 bps 参数。

#### B. Slippage / impact proxy

对当前研究层，更合理的是做**简化的状态相关成本**：

- 成本随 `turnover` 增加
- 成本随 `realized_vol` 增加
- 成本随 `illiquidity proxy` 增加

也就是：

`effective_cost_bps = base_cost + f(volatility, liquidity, turnover)`

其中 liquidity proxy 当前最自然的是：

- `avg_dollar_volume`
- `amihud`

#### C. Opportunity cost / execution lag

这一部分不能再忽略。

执行 realism 的第一版，至少应显式建模：

- `signal at t`
- `execute at t+1 bar`

这就是 implementation shortfall 里最核心的“paper vs reality”差。

## 2. Position -> Execution 该怎么映射

### 2.1 不应假设目标仓位当期瞬时实现

当前 position mapping 隐含的是：

- 当期目标仓位
- 当期 realized position

这对研究 `signal-to-position` 没问题，但对 execution realism 不够。

更真实的 v1 应拆成：

- `target_position_t`
- `submitted_trade_t`
- `executed_position_{t+1}`

最简单的实现就是：

### 2.2 Execution lag v1

- 用 `t` 时刻的 `realized_position`
- 在 `t+1` 才真正生效

这样能直接检验：

- alpha 半衰期
- 带执行延迟后还能否保住收益

这比一开始上复杂成交路径更有信息量。

### 2.3 不建议当前 v1 上的内容

对当前单资产 `BTC 4h`，v1 暂不建议直接上：

- TWAP/VWAP path simulation
- Almgren-Chriss trajectory optimization
- limit/market mixed fill model

原因：

- 现在还没有 order book 数据
- 也没有 intrabar execution data
- 直接上只会增加自由度，不增加可信度

## 3. 这一层该怎么评估

下一层不能只看净收益，还要看 implementation quality。

### 3.1 核心评估对象

需要并行评估三组路径：

- `paper_position`
  - 当前 position mapping 输出
- `lagged_execution_position`
  - 延迟一根 bar 执行
- `lagged_execution_with_cost`
  - 延迟 + 状态相关成本

### 3.2 核心指标

#### A. Return metrics

- `gross_total_return`
- `net_total_return`
- `annual_return`
- `sharpe`
- `max_drawdown`

#### B. Implementation metrics

- `implementation_shortfall`
  - `paper PnL - executed PnL`
- `execution_lag_drag`
  - 无延迟 vs 延迟执行的收益差
- `cost_drag`
  - 毛收益 vs 净收益差
- `fill_delay_sensitivity`
  - `t+1`、`t+2` 延迟下结果变化

#### C. Stability metrics

- `turnover`
- `trade_frequency`
- `mean_trade_size`
- `execution_adjusted_sharpe`

### 3.3 v1 verdict

这层最合理的 verdict 逻辑不是“收益最大”，而是：

- 延迟后仍然为正
- 成本后仍然为正
- implementation shortfall 不吞没大部分 alpha

也就是：

**execution realism 层是在验证可实现性，不是在重新找最强仓位参数。**

## 4. 为什么当前优先做 execution realism，而不是 risk model / optimizer

### 4.1 机构通用链路里 risk 和 execution 都在后面

机构公开流程一般是：

- alpha / forecast
- portfolio construction
- execution

这说明 risk 和 execution 都属于下游层，不属于 alpha 层本身。

Sources:

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- Boyd, *Markowitz Portfolio Construction at Seventy*
  - https://stanford.edu/~boyd/papers/markowitz.html

### 4.2 但对当前项目，execution 优先级更高

这不是说 risk layer 不重要，而是当前形态决定了先后顺序。

当前研究对象是：

- `BTC`
- `4h`
- 单资产

在这个设定下：

#### 完整 risk model / optimizer 的边际收益较低

因为当前没有：

- 多资产协方差
- 组合级风险预算
- 跨资产权重分配

很多 risk work 在单资产里会退化成：

- max position
- vol cap
- drawdown overlay

而这些其实已经部分出现在 `position mapping` 里。

#### execution realism 的边际收益更高

因为当前最重要的未验证问题是：

- 延迟执行后 alpha 还剩多少
- 更真实成本后 alpha 还剩多少
- 当前结论是不是“纸面成立、实盘不成立”

这正是 implementation 层该回答的问题。

## 对当前项目的直接实施顺序

最合理的下一步顺序：

1. 在现有 `position mapping` 之上加：
   - `execution lag`
   - `state-aware cost proxy`
2. 输出：
   - `paper_position`
   - `executed_position`
   - `implementation_shortfall`
3. 评估：
   - 延迟/成本后是否仍为正
   - alpha 被吃掉多少
4. 若这一步通过，再决定是否需要：
   - 更完整 risk overlay
   - 更复杂 optimizer

## 结论

对当前 `BTC 4h single-asset` 主路径：

- 下一层优先做的是：
  - **execution / implementation realism**
- v1 的最小但正式实现应包括：
  - `t+1 execution lag`
  - `implementation shortfall style cost decomposition`
  - `vol/liquidity-aware cost proxy`
- 当前不先做完整 risk model / optimizer，不是因为它们不重要，而是因为：
  - **在单资产形态下，execution realism 的边际信息量更大**
