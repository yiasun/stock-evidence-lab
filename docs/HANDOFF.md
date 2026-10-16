# 提交与交接清单 · v3.0

## 入口

- 在线产品：https://stock-evidence-lab-yiasun.streamlit.app/
- GitHub：https://github.com/yiasun/stock-evidence-lab
- 运行说明：根目录README.md。
- 产品说明：docs/PRODUCT_REPORT.md；PDF构建于output/pdf/stock-evidence-lab-report.pdf。
- 演示与答辩：docs/DEMO.md；当前提供脚本，未录制视频。
- 验证证据：docs/TEST_REPORT.md、docs/DATA_VERIFICATION.md、docs/EVALUATION.md。

## 第三阶段范围

提交演示界面与模式说明、可读研究笔记导出、引用闭环、已知AI调价归因错误回归、产品说明PDF、演示脚本及可复现交付包。不扩展实时数据或多标的，不改变财务计算口径。

## 复现步骤

1. Python 3.11环境中安装requirements.txt。
2. 运行python -m streamlit run app.py，无密钥即可使用规则模式。
3. 智谱密钥只在环境变量或Streamlit Secrets配置AI_PROVIDER="zhipu"及ZHIPU_API_KEY；无需改代码或在聊天发送密钥。
4. 使用示例问题核对模式、来源与未知；导出JSON或Markdown保存。

## 开发检查

```bash
python -m unittest discover -s tests -v
python tools/evaluate_analysis.py --output artifacts/analysis-eval.json
```

PDF构建需开发依赖reportlab、pypdf和可嵌入的中文TrueType字体，不加入应用运行依赖。运行tools/build_submission_report.py时通过--font指定字体；截图在docs/images/submission-ui.png。

## 交付边界

冻结证据包、不保证实时性；估值为有时点假设的试算；两家公司样本不代表全行业。AI带引用仍可能存在因果错误，固定规则不能覆盖所有措辞。任务勾选不升级证据可信度。免费接口可能拥堵，页面会说明实际模型及回退。

Git归档包仅包含已跟踪源码、公开数据与文档，不包含.git、环境、服务端密钥或忽略的临时文件。根目录早期report.pdf是被忽略的无效下载文件，不作为交付材料。以output/pdf中的正式说明为准。

## 发布验收

本地自动化、离线校验、云端CI、提交版公网主链路及正式PDF视觉检查分别记录在测试报告；未完成的项目不会由早期截图替代。
