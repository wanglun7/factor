# Standardized Score：方法层调研

Date: 2026-03-10
Category: alpha-models

## 研究问题

`standardized score` 这一层具体怎么做。

重点是：

- 常见标准化方法是什么
- 公开资料里能确认到什么程度
- 哪些做法可以直接支持我们后续实现
- 哪些地方还不能直接照搬

## 目前能明确确认的内容

### 1. 标准化的核心目的

公开方法论里都很一致：

- 标准化是为了让不同 descriptor / signal 进入同一比较空间
- 不标准化，就没法做后续组合

来源：

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf

### 2. 公开资料里最明确的方法是 z-score

MSCI FactorLab 明确写到：

- standardized values 是 derived values 的 `z-score` 版本

来源：

- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf

MSCI 各类 methodology 也反复使用：

- 先算 descriptor value
- 再标准化成 `z-score`
- 再用于更高层 factor score

来源：

- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf
- China A Style Index Series Methodology
  - https://www.msci.com/documents/10199/88bb0ea7-2301-4456-99b4-9623b62c0616

### 3. Winsorization 是标准化前的常规步骤

MSCI 公开 methodology 里能明确看到两类处理：

- 先对原始变量 winsorize
- 再计算 z-score

典型公开做法包括：

- 将极端值截到 5% / 95% 分位
- 或将 z-score 截到 `+/-3`

来源：

- China A Style Index Series Methodology
  - https://www.msci.com/documents/10199/88bb0ea7-2301-4456-99b4-9623b62c0616
- Franklin Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_Franklin_Global_Equity_Index.pdf

### 4. 标准化范围经常不是“全局一次性”

MSCI 公开方法里还明确有：

- sector-relative z-score
- region-relative z-score

这说明标准化范围本身就是设计的一部分，不是固定只有一种。

来源：

- Franklin Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_Franklin_Global_Equity_Index.pdf

## 对我们现在能得出的硬结论

### 可以明确说的

- `z-score` 是公开资料最明确支持的标准化方法
- `winsorization + z-score` 是公开资料里最标准的组合
- 标准化范围需要被单独定义，不能默认

### 还不能直接说的

- 我们应该直接用普通 z-score 还是 robust z-score
- 我们应该做 time-series per asset 还是 cross-sectional per bar
- `binary / ternary rule` predictor 该怎么进入同一 score 空间
- crypto 4h 时间序列里是否应直接沿用股票 cross-sectional 的 sector-relative 标准化

这些现在还没有被知识库调研到足够细。

## 当前最合理的阶段性判断

如果只按目前公开资料和知识库能确认到的内容：

- `standardized score` 层一定需要
- 最安全的起点是：
  - `winsorization`
  - `z-score`
- 但具体要做：
  - `time-series z-score`
  - `cross-sectional z-score`
  - 还是混合做法

这件事还需要继续调研，不能直接拍板

## 下一步还要补的 4 个问题

1. `time-series vs cross-sectional`
   - 对我们这种 crypto 4h alpha 层，哪种更合适

2. `binary / ternary predictor handling`
   - `trb_200d`、`sma crossover`、`ema crossover` 怎样进入 standardized score

3. `direction alignment`
   - `prev_day_return`、`amihud`、`funding`、`basis` 统一成什么符号方向

4. `robustness choice`
   - 是不是要用 median/MAD 这类 robust 标准化，而不是普通 mean/std

## Sources

- BlackRock Systematic Investing
  - https://www.blackrock.com/us/financial-professionals/investments/systematic-investing
- MSCI FactorLab factsheet
  - https://www.msci.com/downloads/web/msci-com/data-and-analytics/factor-lab/MSCI-FactorLab-Fact_sheet.pdf
- MSCI Diversified Multiple-Factor Indexes Methodology
  - https://www.msci.com/indexes/documents/methodology/2_MSCI_Diversified_Multi-Factor_Indexes_Methodology_20220524.pdf
- China A Style Index Series Methodology
  - https://www.msci.com/documents/10199/88bb0ea7-2301-4456-99b4-9623b62c0616
- Franklin Global Equity Index Methodology
  - https://www.msci.com/eqb/methodology/meth_docs/Methodology_Book_Franklin_Global_Equity_Index.pdf
