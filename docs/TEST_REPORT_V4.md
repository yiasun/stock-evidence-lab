# v4.0 测试报告 / Validation report

日期：2026-11-11，香港时间。基线：`e7791f5e1bbe35ccbcff21b7dd36a9ad5db5853b`。
分支：`codex/international-research-experience`。本报告不表示已经部署。

## 结果 / Results

| 检查 | 结果 | 可核对材料 |
|---|---|---|
| 升级前完整基线 | 69/69通过 | 从最新远端main运行原始测试；旧测试文件保留 |
| 升级后完整测试 | **75/75通过**，原69项+新6项 | [完整日志](validation/v4-unit.txt) |
| 应用模块编译 | 通过 | [编译记录](validation/v4-compile.txt) |
| 原有离线校验集 | 12/12通过，模型调用0次 | [逐案例结果](validation/v4-analysis.json) |
| 原有边界挑战集 | 12/12通过；8个不安全样本均拒绝，4个安全样本均接受 | [逐案例结果](validation/v4-boundary.json) |
| Git空白检查 | 通过 | [diff检查](validation/v4-whitespace.txt) |
| 浏览器验收 | 英/中桌面、390px窄屏、证据展开、规则诊断、保存复核、实际下载、往返语言切换通过 | 本文后续记录与截图 |

环境：Windows，Python 3.10.0、Streamlit 1.65.0、pandas 2.2.3、numpy 2.1.2、requests 2.32.3。CI沿用Ubuntu / Python 3.11；本地结果不能替代远端CI，远端本分支实际运行结果以GitHub Actions为准。机器可读的命令、退出码、包版本和LF归一化代码/数据哈希在[v4-checks.json](validation/v4-checks.json)。

## 覆盖 / Coverage

原69项继续覆盖财务复算、期次与字段异常、现金流口径、行情哈希及日期、TTM假设、同行样本边界、API错误、密钥隔离、非法引用、数字与交易边界、调价时序、缓存/并发/冷却、部分解读隐藏、完整笔记、逐主张复核及历史失效。

新增6项覆盖：

1. 英文呈现不修改数据、E/S编号、URL、SHA、字段、证据类型和范围；三项同比与原值一致。
2. 英文关键词识别及PE词边界；未知问题保持原有全部范围回退；英文交易意图。
3. `?lang=en`离线完整主流程；类型筛选隐藏E4时导出仍包含E4和来源。
4. 自定义问题、任务和已保存复核跨语言往返保持；修改问题仍使旧复核失效。
5. 英文缺少密钥时明确规则模式，不调用网络，不声称AI成功。
6. 浏览器可能回传旧的格式化标签时先恢复内部稳定值，不丢失证据范围或筛选结果。

## 浏览器记录 / Browser QA

使用本机回环预览`127.0.0.1:8511`，未部署到任何云端。默认桌面1280×720，窄屏390×844。窄屏观测`innerWidth=390`、`body.scrollWidth=390`；指标纵向排列，示例按钮可点，案例锚点保留固定页头间距。已恢复默认视口。

- 英文首屏：90.70bn / 44.52bn / 70.69bn，+1.47% / −1.95% / +438.84%，均有E→S引用、冻结期和未经审计标识。
- 规则生成显示“Rule mode / No LLM call”，E4展开能看到原始字段表、联合判断口径、S1 URL、PDF页码和哈希入口。
- 保存一条“Insufficient evidence”功能演示复核，当前状态从Pending变为Insufficient evidence；缺失材料明确含“Functional demo only”。不是独立研究者评价。
- 实际点击JSON及英文Markdown下载，确认文件在宿主Downloads落盘，随后复制为[演示JSON](../output/v4-demo-en.json)和[演示笔记](../output/v4-demo-en.md)。解析检查全部12个证据ID及复核历史存在，review_origin为user_manual，没有把人工意见标为系统认证。
- 中文切换后可见同一条“证据不足 · E4”；英文→中文→英文最终复测证据不消失。自动化另验证任务勾选及自定义问题保持。
- 曾发现浏览器格式化标签在往返切换后进入筛选内部值，导致空展示。修复为显式归一化，补回归后重跑全部75项；浏览器实际往返复测不再出现空展示。
- 本地热更新时新增模块符号曾需重启预览进程，已重新启动并核对清洁加载。不是线上部署操作。

截图：[英文桌面](images/v4-en-desktop.jpg)、[中文桌面](images/v4-zh-desktop.jpg)、[窄屏首屏](images/v4-en-mobile.jpg)、[窄屏案例入口](images/v4-mobile-case.jpg)、[复核表单](images/v4-review.jpg)。

## 复现 / Reproduce

```bash
python tools/validate_release.py
```

该脚本运行完整编译、全部测试和两套原有评估，保留逐项日志、环境版本和代码哈希；任何检查失败时返回非零。也可以分别运行README中的命令。

## 边界 / Limits

两套24个案例是作者构造的离线校验回归，不是独立留出集、完整语义核验或真实模型准确率。没有新增真实AI请求、付费模型验收、用户访谈、招聘人员计时或产品转化指标。既有中文模型输出策略保留，英文AI自由文本校验未实现，因此UI与英文笔记明确保留中文模型原文。

原始财报来源与PDF哈希沿用冻结包，不表示本次重新下载或认证。行情包内一致性和原始响应哈希由原测试检查。来源链接未来可能失效；依赖版本仍为原范围而非锁定；复核状态仍为会话内存，须导出保存。

2026-11-11线上页面处于Streamlit休眠状态；只读记录该状态，没有唤醒、重启、配置Secrets、发布或覆盖。旧线上历史AI验收不作为v4验收依据。

## English note

All 69 original tests were retained; six locale and state-integrity regressions bring the full local suite to 75 passing tests. Both existing 12-case offline validators pass with zero model calls. Browser QA verified desktop and narrow layouts, traceable E4 evidence, rule-mode generation, a clearly labelled functional-test review and actual JSON/Markdown downloads. These results establish the tested behaviour, not user validation, financial truth or live-model accuracy. The upgrade remains a branch deliverable until deployment is approved.
