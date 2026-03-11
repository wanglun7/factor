# Filter Rule Thresholds

Date: 2026-03-10
Category: alpha-models

## 研究问题

`filter_rule` 的 threshold 应该怎么定。公开资料有没有支持的 threshold 选择方式，能不能形成 v1 whitelist。

## 核心结论

1. 公开技术交易规则文献明确支持 **small discrete threshold grids**，而不是连续自由搜索。
2. filter rule 的阈值通常用少数经典百分比档位表示，而不是动态学习出来。
3. 对当前项目，最稳的 v1 不是单一 threshold，也不是大范围网格，而是**少数经典 thresholds 的离散 whitelist**。

## Source-Backed

### 1. Filter rules 的经典定义就是 percent filter

技术交易规则文献中的 filter rule 通常定义为：

- 价格上涨超过某个百分比阈值时做多
- 价格下跌超过某个百分比阈值时做空
- 否则中性

这说明：

- threshold 本身就是规则家族的核心参数
- 而且通常是显式 percent threshold

来源：

- The predictive ability of technical trading rules: an empirical analysis of developed and emerging equity markets
  - https://link.springer.com/article/10.1007/s11408-023-00433-2
- Further evidence on the returns to technical trading rules: Insights from fourteen currencies
  - https://doi.org/10.1016/j.mulfin.2023.100808

### 2. 文献支持 threshold 用少数离散档位

技术规则研究里，filter threshold 不是连续调优，而通常使用少数经典百分比档位，如：

- `0.5%`
- `1%`
- `2%`

有些研究还会更广，但核心做法都是：

- 用少量离散 thresholds
- 然后比较规则表现

这支持 v1 用 whitelist，而不是自由网格搜索。

来源：

- 经典 technical trading rules 文献综述与实证（filter rule 部分）
- 货币技术交易规则研究

## What Is Supported vs Not Fixed

### Source-backed

- threshold 应是显式 percent threshold
- threshold 应使用少数离散档位
- 不应在第一轮就用连续大网格乱扫

### Not fully fixed by public sources

- 对 `crypto 4h` 最优 threshold 是多少
- threshold 是否应按 volatility state 动态缩放
- 同一 threshold 是否适用于 short / medium / long horizons

这些都没有公开资料给出唯一答案。

## Project-Specific Inference

如果要形成一个稳的 v1 whitelist，最合理的是：

- `0.5%`
- `1.0%`
- `2.0%`

原因：

- 足够覆盖小、中、较大三个显式 filter 强度
- 仍然是小规模离散集合
- 与公开 technical trading rules 研究的经典用法一致

## 结论

filter threshold 现在已经可以收敛到 v1 whitelist：

- `0.5%`
- `1.0%`
- `2.0%`

这不是“研究已经证明这三个对 crypto 4h 最优”，而是：

- 这三个属于经典、source-consistent、适合第一轮 generator 的阈值集合。
