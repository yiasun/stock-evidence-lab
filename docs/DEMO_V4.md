# 三分钟演示 / Three-minute walkthrough

这是建议脚本，未经招聘人员计时或用户实验验证。v4尚未部署；使用本地版本或经批准的独立预览，旧线上地址不代表本次升级。

准备：按README启动，打开`http://localhost:8501/?lang=en`。无需密钥，保持AI关闭。中文可在侧栏切换。不要在演示中输入个人持仓或敏感信息。

| 时间 | 操作 | 中文讲解 | English narration |
|---|---|---|---|
| 0:00–0:20 | 看首屏指标及FROZEN标识 | “这是单标的研究原型。收入增长、利润下降、现金流大增同时出现，值得追问原因。” | “This single-company research prototype starts with a tension: revenue up, parent profit down, operating cash flow sharply up.” |
| 0:20–0:45 | 看E4推断和现金流说明 | “现金流含财务子公司资金变化，不能直接证明白酒主业回款改善。观察期与未经审计状态都明确展示。” | “Finance-subsidiary fund movements affect consolidated cash flow. It does not establish better collections in the liquor business.” |
| 0:45–1:10 | 点击Explore链接→Generate evidence brief | “规则模式不调用模型；问题驱动排序，但相反证据和未知仍保留。” | “Rule mode works without a key. It prioritises evidence without hiding contrary facts or unknowns.” |
| 1:10–1:45 | 展开Trace evidence · E4 | “这里可以核对三项原始字段、联合判断口径、S1公告链接、PDF第5和7页以及包内哈希记录。” | “Follow E4 to raw fields, reasoning, S1's filing URL, page locators and recorded file hash. Citation validity is not causal proof.” |
| 1:45–2:20 | Human review→Insufficient evidence→填缺少材料→Save | “我认为还缺少主业销售收现与财务公司资金的拆分。系统记录人工意见，不把它升级成事实认证。” | “I would request a split of core-business collections and finance-subsidiary movements. This records a human judgement, not system certification.” |
| 2:20–2:40 | 在复核页导出JSON和Markdown | “导出包含完整研究范围与复核历史，展示筛选不会截断引用。” | “The note carries the scoped evidence, assumptions and review history, even if the view is filtered.” |
| 2:40–3:00 | 切换中文，打开Tools & boundaries | “语言切换保留研究记录；行情、估值、同行和CSV校验在工具中。没有虚构实时接口或用户指标。” | “Language changes preserve research state. Historical prices, assumption-bound valuation, peers and CSV validation remain available. No live feeds or invented usage metrics.” |

## 可选AI分支 / Optional AI path

只有配置了服务端密钥且用户开启AI后，再点生成才会发出请求。可介绍“AI选择、引用并解释既有证据；程序负责数字，人工负责语义核验”。模型原文仍为中文，英文界面会明确提示。认证、限流、超时、非法引用均显示规则回退，不应将演示失败称作AI成功。真实调用延迟可能超出演示窗口，因此三分钟脚本采用离线规则模式。

可选择“估值便宜吗？”展示未知边界，或“调价能改善业绩吗？”说明事件在半年期之后，不能反推解释此前业绩。不必把次要工具逐一演示。

## 复核填写示例 / Functional-test example

选择E4的本地推断。判定“证据不足 / Insufficient evidence”。缺失材料填：

> Functional demo only: need a breakdown of cash collected from liquor sales and finance-subsidiary fund movements.

该内容是功能演示，不是第三方研究人员的独立结论或真实用户反馈。若选择支持/部分支持/不支持，必须选引用来源并填写页码、说明，不能用空白依据保存。

复核仅本会话保存，请导出后退出。修改问题会使旧记录标为失效；切换语言或证据类型筛选不会。
