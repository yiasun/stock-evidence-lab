# v4.0 升级审计与修改清单 / Audit & changes

审计日期：2026-11-11（香港时间）。开发分支：`codex/international-research-experience`。
基线：远端main `e7791f5e1bbe35ccbcff21b7dd36a9ad5db5853b`。

## 检查结论

本地最初停在e02cea6。只读查询远端发现2026-11-03已合并PR #1，包含逐主张人工复核和边界校验升级。拉取后从最新main创建独立分支；本地main未切换或修改。基线完整69项测试通过。远端最近一次[Evidence checks](https://github.com/yiasun/stock-evidence-lab/actions/runs/41624410711)为success。

检查了应用、确定性计算、AI接口及校验、请求保护、复核记录、导出、全部原有测试、两套固定评估、证据包及行情哈希、README、既有产品/数据/AI/交接文档、CI与Streamlit配置、数据构建和交付脚本。已有财务计算、行情沙盒、同行比较、估值假设、复核及导出均可复用。

旧界面同时暴露八个平行入口，问题输入与范围设置先于核心案例说明。中文说明较完整，但国际招聘人员无法直接理解来源、推断和复核机制；旧README混合多个历史阶段的验收记录。没有证据支持真实用户验证、招聘转化或产品指标，故不作这些声明。

线上只读检查：原URL返回Streamlit休眠页“Zzzz / This app has gone to sleep due to inactivity”。没有唤醒、重启、部署、修改Secrets或覆盖该实例。无法据休眠页确认当前线上运行的具体代码版本或Secrets。

## 修改清单

| 文件 | 改动与目的 |
|---|---|
| `app.py` | 四个一级入口：案例与解读、来源核验、人工复核、工具与边界；首页三项背离指标、三分钟路径、深链入口；次要证据折叠；复核页可直接导出 |
| `styles.css` | 统一深青色金融研究视觉、清晰层级、等宽数字、键盘焦点和窄屏布局；无外部字体/CDN依赖 |
| `presentation.py` | 作者编写的英文证据/来源视图；金额由既有字段换算；保留E/S编号、URL、字段、数据类型和原始对象 |
| `diagnosis.py` | 增加英文关键词范围、词边界和交易意图识别；避免PE误命中operating/type；保留已有中文语义及计算 |
| `research_export.py` | 英文Markdown；中文默认兼容；英文保留模型原文、人工备注及历史判定 |
| `.streamlit/config.toml` | 主题与界面配色一致 |
| `.github/workflows/tests.yml` | 保留完整CI流程，增加新呈现模块编译检查；无部署任务 |
| `tests/test_international_experience.py` | 新增双语、离线入口、完整导出、身份稳定和英文范围回归 |
| `README.md` | 面向招聘人员的英文优先产品入口、中英文启动与诚实边界 |
| `docs/README_V3_ARCHIVE.md` | 完整保留升级前README，历史链接与记录不丢失 |
| `docs/*_V4.md`, `docs/validation/`, `docs/images/v4-*` | 新版演示、审计、测试、部署与浏览器验收材料 |
| `tools/package_submission.py` | 版本化打包，v4要求新交付材料，同时保留原参数兼容 |
| `tools/validate_release.py` | 完整检查、退出码、可移植日志及代码/数据哈希记录 |

原有测试文件、冻结数据目录、AI接口及其校验策略、请求保护、逐主张复核核心均未修改。未增加数据库、前端框架、行情服务商或后台任务。

## 数据与研究表述

首页数字由包内2026H1/2025H1字段复算：营收+1.47%、归母利润−1.95%、经营现金流+438.84%。金额在中文为亿元、英文为CNY bn，单位显式标注，不做汇率换算。

公司现金流说明包含财务子公司成员单位存款与同业款项变化，因此无法单凭现金流增幅证明白酒主业回款改善。调价晚于半年期末，不能解释此前业绩。历史PE/PB保留混用日期及未核验股本变化的假设；同行仅两家公司。原始PDF页码与哈希来自继承核验记录，本次没有重新认证披露或声称新核验日。

英文为作者编写的呈现文本，不是实时AI翻译。AI解读沿用既有中文校验策略，原文保留中文并标识；JSON中的证据、人工原文和身份信息保留原始结构。单独切换语言不改研究上下文或复核指纹，修改问题、维度、数据、模式、模型或策略仍按原机制失效。

## 验收与剩余限制

具体自动化与浏览器结果见[测试报告](TEST_REPORT_V4.md)。没有新增真实模型调用、独立人工语义标注、用户访谈或招聘人员计时实验。三分钟是设计的演示脚本，非实测产品指标。复核仅保留于Streamlit当前会话，仍须导出保存。依赖范围沿用原仓库，未改成锁文件，跨时间安装应重跑测试。

v4是在独立分支交付的候选版本。未合并main，未部署，旧PDF/截图仅历史存档。部署前按[部署与回滚](DEPLOY_V4.md)另建预览，并由用户确认最终线上切换。

AI助手参与代码、测试、说明和视觉取舍。候选人应复现并自行核查来源后再对外介绍。

## English handoff

This release keeps the Streamlit architecture, deterministic calculations, provider guards and human-review lifecycle. It prioritises the Moutai divergence case, traceable evidence and explicit uncertainty, adds authored bilingual presentation and readable English notes, and reorganises secondary tools through progressive disclosure. Original data and original test files are retained. Locale never participates in the claim-review fingerprint. No live data, new filing authentication, user validation or production deployment is claimed.
