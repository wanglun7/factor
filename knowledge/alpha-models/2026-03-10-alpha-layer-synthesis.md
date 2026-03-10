# Alpha 层阶段性总览

Date: 2026-03-10
Category: alpha-models

## 本阶段研究范围

本阶段只回答一个问题：

机构式系统里，`alpha layer` 到底是什么，以及对我们当前 4h crypto 项目该如何落地。

## 已完成的子问题

### 1. Alpha 层是不是第一步

结论：

- 是
- 它先于 regime、风险模型、优化器
- 本质上是 `expected return engine / alpha score engine`

文件：

- [2026-03-10-institutional-alpha-model-first-step.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-institutional-alpha-model-first-step.md)

### 2. Alpha 层输出什么

结论：

- 研究层常输出 `alpha score`
- 进入组合层前通常还会做 `forecast mapping / alpha scaling`
- 更接近优化器输入的是 `expected-return-like alpha`

文件：

- [2026-03-10-score-vs-expected-return-and-forecast-mapping.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-score-vs-expected-return-and-forecast-mapping.md)

### 3. Alpha 层内部结构是什么

结论：

- 更合理的抽象是：
  - `raw predictors`
  - `standardized scores`
  - `composite alpha`
  - `scaled/calibrated alpha`
  - `optimizer input`

文件：

- [2026-03-10-alpha-layer-blueprint-standardize-combine-calibrate.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-alpha-layer-blueprint-standardize-combine-calibrate.md)

### 4. Alpha 层如何评估、去冗余、校准

结论：

- 不能只看 Sharpe 或 IC
- 需要同时看：
  - predictive strength
  - implementation quality
  - portfolio transferability
- predictor 变多后必须考虑 shrinkage 和冗余控制

文件：

- [2026-03-10-alpha-layer-evaluation-redundancy-and-calibration.md](/Users/lun/Desktop/manifex/factor/knowledge/alpha-models/2026-03-10-alpha-layer-evaluation-redundancy-and-calibration.md)

## 对当前项目的统一定义

当前 4h crypto 项目的 alpha 层，建议定义为：

### 目标

输出每个币、每根 4h bar 的 `scaled alpha`

### 推荐 v1 结构

1. `raw predictors`
   - `ema_gap_120_360`
   - `breakout_360bar`
   - `rev_18bar_voladj`

2. `standardized scores`
   - rolling robust z-score
   - clipping / winsorization
   - volatility adjustment

3. `composite alpha score`
   - 先用 equal-weight 或带轻微 shrinkage 的线性合成

4. `scaled alpha`
   - 用 score bucket 的 future-return 关系做单调映射

5. `handoff object`
   - 交给仓位映射层或后续优化器

## 这一层现在最该补的工程对象

- `predictor_report`
- `redundancy_report`
- `calibration_report`
- `alpha_object`

## 下一层研究问题

alpha 层本身目前已经基本调研清楚。

下一层自然问题是：

1. `alpha -> regime`
   - regime 怎样作为条件信息进入 alpha
2. `alpha -> risk model`
   - scaled alpha 怎样与正式风险模型对齐
3. `alpha -> portfolio`
   - 没有过度复杂化的情况下，第一版仓位映射怎么设计

## 当前判断

现在不该继续泛泛找新因子，也不该先上复杂 HMM。

更合理的是：

- 先把 alpha 层工程化定义完成
- 再进入下一层：conditional alpha / risk alignment
