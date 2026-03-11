# Descriptor x Transform x Horizon

Date: 2026-03-10
Category: alpha-models

## 研究问题

`descriptor x transform x horizon` 到底是什么，知识库里哪些部分已经有来源支持，哪些还只是工程决策。

## 核心结论

1. `descriptor x transform x horizon` 作为**第一层受约束生成框架**，知识库已经支持。
2. 知识库支持的是**框架和边界**，不是我们已经有了某一张固定的 45 因子清单。
3. 公开资料更明确支持的是：
   - 先维护 descriptor / characteristic library
   - 再做有限 transform
   - 再做有限 horizon / scale
   - 然后标准化、评估、淘汰
4. 当前还没被知识库定死的，是：
   - descriptor whitelist
   - transform whitelist
   - horizon whitelist
   - 每个 descriptor 对应哪些 transform / horizon

## Source-Backed

### 1. 第一层更像 characteristics / descriptors library，而不是手工因子清单

MSCI FactorLab 公开材料直接写明：

- 197+ factor descriptors
- 12 factor groups
- descriptor 有 derived values 和 standardized values

这说明成熟平台先维护的是 descriptor 库，而不是零散公式列表。

来源：

- MSCI FactorLab
  - https://www.msci.com/our-solutions/analytics/factor-lab
- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf

### 2. descriptor first, transform second 的方向有实证支持

Gu, Kelly, Xiu 的研究显示：

- 机器学习优势主要来自非线性和交互
- 但主导预测力仍集中在少数稳定 characteristic / signal 家族
- 主导集合包括 momentum, liquidity, volatility

这支持“先锁 descriptor 家族，再做变换”，而不是无限发明新公式。

来源：

- Empirical Asset Pricing via Machine Learning
  - https://www.nber.org/papers/w25398
  - https://academic.oup.com/rfs/article/33/5/2223/5758276

### 3. 因子 zoo 问题支持从 characteristics 中提炼结构，而不是盲目扩库

Lettau 等关于 factor zoo 的研究强调：

- 面对大量候选 characteristic，关键是提炼更少、更有效的结构
- 不是继续扩 feature zoo

来源：

- High-Dimensional Factor Models and the Factor Zoo
  - https://www.nber.org/papers/w31719

### 4. Formulaic alpha 提供的是 grammar / operator 库，不是完整流程

`101 Formulaic Alphas` 的价值更像：

- 给出一套公式模板
- 给出一套 operator grammar
- 说明第一层可以程序化组合基础输入和算子

它并没有替我们定下 descriptor whitelist。

来源：

- 101 Formulaic Alphas
  - https://arxiv.org/abs/1601.00991

### 5. 更自动化的方向是先有 grammar，再做搜索

AutoAlpha 这类工作说明：

- 第一层可以进一步程序化甚至进化式搜索
- 但前提仍是先定义可搜索空间

来源：

- AutoAlpha
  - https://arxiv.org/abs/2002.08245

## 从知识库里能直接提取出的结构

### A. Descriptor

知识库里已经明确出现过的 descriptor / characteristic 家族：

- return / momentum / reversal
- liquidity
- volatility
- basis / futures-spot deviation
- funding / perpetual pricing variables

这来自：

- Empirical Asset Pricing via Machine Learning
- crypto 的 reversal / liquidity / intraday predictability 文献
- Beyond Basis Basics
- Perpetual Futures Pricing

### B. Transform

知识库里已经明确出现或被支持的 transform 类型：

- level
- change
- deviation
- ratio
- rank / percentile
- vol-adjusted
- interaction

但注意：

- “这些 transform 类型存在且合理”是知识库结论
- “哪些 transform 应该进入我们 v1 generator”还不是知识库结论

### C. Horizon

知识库只支持“应有 short / medium / long 等有限尺度”，但没有替我们定具体网格。

也就是说：

- horizon family 的概念是知识库支持的
- 具体用 `6/18/30/120` 还是别的，不是知识库直接定稿

## Industry-Standard

综合公开资料，第一层更像下面这条链：

1. 定义 descriptor / characteristic library
2. 定义允许的 transform family
3. 定义允许的 horizon / scale family
4. 程序化生成候选
5. 标准化、评估、淘汰

这条链是知识库支持的。

## 当前不能冒充“已经调研清楚”的部分

下面这些现在仍然属于工程决策，不是知识库直接给出的定稿答案：

1. 我们到底选哪些 descriptor 进入 whitelist
2. 每个 descriptor 对应哪些 transform
3. 每个 transform 对应哪些 horizon
4. 第一轮总共生成多少个 raw predictors
5. 第一轮是否只跑 BTC
6. 第一轮是否保留手工第一层并行对照

## 对当前项目的直接含义

如果严格按知识库来做，下一步不该说：

- “45 个因子已经是知识库结论”

更准确的做法是：

1. 承认知识库只把框架定清楚了
2. 再单独研究：
   - descriptor whitelist
   - transform whitelist
   - horizon whitelist
3. 然后再生成 v2 第一层

## 结论

`descriptor x transform x horizon` 已经可以作为本项目第一层的正式生成框架。

但当前只确定了：

- 框架
- 允许的结构形式
- 为什么这比手工堆公式更合理

还没有确定：

- 具体清单
- 具体窗口
- 具体规模

所以后面真正要继续研究的是：

- whitelist，而不是再讨论框架本身。
