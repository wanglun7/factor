# Rule / Grammar Generator 与开源框架

Date: 2026-03-10
Category: alpha-models

## 研究问题

`trading range breakout` 这类 rule-based raw predictor 不是单纯 `descriptor x transform x horizon` 能自然生成的。那第一层是否还需要一条 `rule / grammar generator`，以及我们应不应该直接采用开源框架，而不是自己手写。

## 核心结论

1. `trb`、MA rule、crossover 这类信号更接近 **rule / grammar generator**，不是单纯的 descriptor-style continuous predictor。
2. 第一层更合理的结构不是单生成器，而是**两条并行线**：
   - descriptor-based generator
   - rule / grammar-based generator
3. 开源框架是有的，但大多数更适合：
   - 股票截面
   - 日频
   - 通用 OHLCV expression
   而不是直接适配 crypto perpetual 的 `funding / basis / premium`。
4. 对当前项目，最合理的不是直接整套接管某个开源框架，而是：
   - **借开源框架的表达式/DSL/算子设计**
   - 自己做一个小型、受约束的 rule/grammar generator
5. 如果后面要扩性能或更大规模搜索，可以优先借：
   - Qlib 的 expression / feature-engineering 思路
   - KunQuant 的 expression engine / execution
   - AlphaGen / AlphaForge 的搜索框架

## Source-Backed

### 1. Formulaic alpha 本身就是 rule / grammar 路线

`101 Formulaic Alphas` 明确展示了：

- alpha 可以被写成一套显式公式
- 这套公式背后有可复用的 operator grammar

常见 operator 包括：

- rolling mean / std / rank / ts_rank
- delta / lag
- correlation / covariance
- sign / abs / scale
- max / min

来源：

- 101 Formulaic Alphas
  - https://arxiv.org/abs/1601.00991

### 2. Qlib 提供了成熟的表达式和特征工程思路

Qlib 的 Alpha158 / Alpha360 路线，本质上也是：

- 先定义特征表达式
- 再通过 DataHandler 批量生成

公开材料和社区资料里能看到：

- Alpha158 / Alpha360 是预构建 feature zoo
- 可用表达式 operator 包括：
  - Ref
  - Mean / Std / Var
  - Rank / Quantile
  - EMA / WMA
  - Corr / Cov
  - Delta
  - Sign / Log / Power

来源：

- Qlib GitHub
  - https://github.com/microsoft/qlib
- Datasets and Feature Engineering（Qlib 资料索引）
  - https://deepwiki.com/microsoft/qlib/4.6-datasets-and-feature-engineering

### 3. 更自动化的 formulaic alpha 挖掘框架已经存在

公开开源里已经有几条很明确的路线：

- AlphaGen
  - 强化学习生成 formulaic alpha
  - 自带表达式结构和 AlphaCalculator 接口
- AlphaForge
  - 挖掘并动态组合 formulaic alpha
- alpha-gfn
  - 用 GFlowNet 做 alpha mining

来源：

- AlphaGen
  - https://github.com/RL-MLDM/alphagen
- AlphaForge
  - https://github.com/DulyHao/AlphaForge
- alpha-gfn
  - https://github.com/nshen7/alpha-gfn

### 4. KunQuant 更像 expression engine / compiler，不是研究框架

KunQuant 的定位很明确：

- financial expressions and factors 的 optimizer / code generator / executor
- 目标包括 Alpha101、Alpha158 这类表达式库

这说明：

- 它适合做**表达式执行层**
- 不直接替我们决定第一层研究逻辑

来源：

- KunQuant
  - https://github.com/Menooker/KunQuant
  - https://pypi.org/project/kunquant/

## Industry-Standard

基于这些公开资料，可以把开源生态分成三层：

### A. Formula Library

代表：

- 101 Formulaic Alphas
- alpha101 Python implementation

作用：

- 提供现成公式模板
- 提供 operator grammar 例子

### B. Expression / Feature Engine

代表：

- Qlib
- KunQuant

作用：

- 定义表达式
- 批量生成
- 优化执行

### C. Mining / Search Framework

代表：

- AlphaGen
- AlphaForge
- alpha-gfn

作用：

- 在给定 grammar / expression space 里做搜索
- 自动挖因子

## 对当前项目的直接判断

### 1. `trb` 属于 rule / grammar generator

`trb` 不是简单 characteristic 的 level/change/deviation。

它更像：

- past range / support / resistance rule
- ternary event signal

所以它应该和：

- MA rule
- crossover
- breakout

归到同一条 `rule / grammar generator` 线上。

### 2. 不建议直接让某个开源框架整套接管

原因不是框架差，而是我们场景特殊：

- `BTC/crypto perpetual`
- `4h`
- 有 `funding / basis / premium`

而现有大多数框架默认更偏：

- 股票
- 截面
- 日频
- 纯 OHLCV

所以直接整套搬 Qlib / AlphaGen / AlphaForge，不是最省事的路。

### 3. 但也不该继续纯手写

最合理的折中是：

- 不手工一个个写最终因子
- 也不直接把整个框架搬进来
- 而是借它们的结构：
  - expression grammar
  - operator whitelist
  - candidate generation / screening flow

### 4. 当前最合适的实现形态

对当前项目，第一层更合理的目标结构是：

#### Line 1: descriptor-based generator

负责 continuous predictors：

- reversal
- volatility / liquidity
- funding / basis / premium

#### Line 2: rule / grammar-based generator

负责 rule-based predictors：

- trading range breakout
- moving average rules
- price crossover
- 未来其他 path-dependent technical rules

这两条线再统一接：

- second layer standardized score
- third layer composite alpha

## 开源框架怎么用才合理

### 短期

不直接引入整套外部框架作为主系统。

更合理的是：

- 参考 Qlib / Alpha101 / KunQuant 的 operator 和 expression 设计
- 在本项目里实现一个**小型受约束 DSL**

### 中期

如果 rule / grammar generator 跑通，且表达式数量明显变多，再考虑：

- 用 KunQuant 接执行层
- 用 AlphaGen / AlphaForge 接搜索层

### 长期

如果我们真的要做自动化 alpha mining，再考虑：

- RL / GFlowNet / evolutionary search

但那是后续升级，不是当前第一层该直接上的东西。

## 结论

`trb` 这类强信号说明：

- 第一层不能只有 `descriptor x transform x horizon`
- 还需要一条 `rule / grammar generator`

对当前项目，最合理的路线不是：

- 继续纯手写
- 也不是直接接管某个现成大框架

而是：

- 借鉴开源框架的 expression / grammar 思路
- 自己实现一条受约束的 `rule / grammar generator`
- 和 `descriptor-based generator` 并行
