# Working Principles

Date: 2026-03-10

## Core Rule

涉及量化研究、因子设计、alpha 设计、regime、risk model、portfolio construction 等专业问题时：

1. 先检查知识库里是否已经有被调研过的结论
2. 如果知识库没有覆盖到足够细的层级，就先继续搜索和调研
3. 只基于已调研到的内容给方案
4. 不允许用个人经验、当前代码状态、已有实现去反推“应该怎么做”
5. 不允许把行业常见做法、工程化推论、文献直接结论混在一起不加区分

## Output Rule

每次调研后都必须把结果整理进普通 Markdown 文件，并明确区分：

- `source-backed`
- `industry-standard`
- `project-specific inference`

如果某个点还没有被调研到，就必须明确写：

- `not yet researched`
- 或 `insufficient evidence`

不能把未调研清楚的内容直接写成方案。

## Design Rule

做方案时，以“应该怎么做”为准，不以“当前项目里已经有什么代码”为准。

当前代码只能用于：

- 识别现状
- 发现偏差
- 判断是否与研究结论一致

不能作为设计依据本身。
