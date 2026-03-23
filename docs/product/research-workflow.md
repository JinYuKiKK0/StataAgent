# Research Workflow

This document captures the domain workflow from user request to empirical result. It complements `Requirements.md` by expressing each stage in terms of agent inputs, outputs, and gates.

## Invariants

- Data source is CSMAR only.
- The final analysis dataset must be one merged long table at a single analysis grain.
- Regression execution happens only after the data quality gate passes.
- Automatic adjustment is bounded and auditable; the agent must not freely rewrite the research question.

## Stage Overview

| Stage | Goal | Required Output | Gate to Next Stage |
| --- | --- | --- | --- |
| S1 需求解析与数据定义 | Turn the topic and empirical requirements into a structured research spec | Variable definition list and data requirement list | Core variables, panel grain, and time scope are explicit |
| S2 理论预判与模型构建 | Define expected sign, baseline model, and empirical logic | Model design outline and baseline equation | Baseline regression design and safe retry boundaries are explicit |
| S3 数据清洗与拼接 | Fetch CSMAR data, standardize fields, and merge sources | One standardized long table | Keys, frequencies, and joins are consistent |
| S4 描述统计与质量拦截 | Validate the merged panel before running regressions | Descriptive statistics and quality findings | No blocking data issues remain |
| S5 核心回归与反馈循环 | Run regression, compare with expectation, and decide whether bounded retries are allowed | Regression outputs, robustness outputs, heterogeneity outputs, and judgment summary | Result package is complete or explicitly failed |

## Stage Details

### S1: Requirement Parsing and Variable Definition

- Input: user topic, empirical steps, entity hints, time range hints
- Agent work:
  - identify `Y`, `X`, and control candidates
  - determine the target analysis grain and data frequency
  - define the required raw data domains
- Output:
  - variable definition sheet
  - data requirement sheet
  - initial research specification

### S2: Theory and Model Design

- Input: research specification from S1
- Agent work:
  - assign expected sign or direction for the core relationship
  - define the baseline regression family
  - select candidate fixed effects and control strategy
- Output:
  - model design summary
  - baseline equation
  - allowed retry envelope

### S3: CSMAR Fetch, Standardization, and Merge

- Input: variable bindings and query plans
- Agent work:
  - fetch only the needed CSMAR fields
  - normalize ids, dates, units, and missing-value encodings
  - merge all sources to the target analysis grain
- Output:
  - one merged long panel
  - fetch log
  - lineage and coverage summary

### S4: Descriptive Statistics and Quality Gate

- Input: merged long panel
- Agent work:
  - run descriptive statistics
  - detect impossible values, duplicate keys, invalid ratios, and large missingness
  - winsorize continuous variables when appropriate
- Output:
  - descriptive statistics
  - data quality report
  - pass/fail decision for regression readiness

### S5: Baseline Regression and Feedback Loop

- Input: validated dataset and baseline model plan
- Agent work:
  - generate Stata code from the locked model plan
  - execute through `stata-executor-mcp`
  - compare coefficient sign and significance with the theoretical expectation
  - run bounded retries only inside the approved retry envelope
- Output:
  - baseline regression tables
  - robustness and heterogeneity outputs when allowed
  - final judgment summary with retry audit
