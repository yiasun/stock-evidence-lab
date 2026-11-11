# 启动、部署与回滚 / Run, deploy & roll back

**本次交付未部署、未覆盖线上、未合并main。以下是待用户确认后执行的步骤。**
Existing public app was asleep during the 2026-11-11 audit. Do not infer a currently running revision from that page.

## 本地运行 / Local run

```bash
git clone https://github.com/yiasun/stock-evidence-lab.git
cd stock-evidence-lab
git switch codex/international-research-experience
python -m venv .venv
```

Windows PowerShell激活：`.\.venv\Scripts\Activate.ps1`；macOS/Linux：`source .venv/bin/activate`。

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python tools/evaluate_analysis.py
python tools/evaluate_boundary_challenge.py
python -m streamlit run app.py
```

使用终端给出的地址，加`?lang=en`或`?lang=zh`。默认端口8501；如果被占用，可加`--server.port 8511`。This is a local process, not a cloud deployment. No API key is required.

## 独立预览 / Separate preview (after approval)

1. 用户批准后在Streamlit Community Cloud新建**独立应用**，不要编辑旧应用的分支或入口。
2. 仓库`yiasun/stock-evidence-lab`；分支`codex/international-research-experience`；入口`app.py`。选择Python 3.11，设独立预览URL。
3. 首次不复制任何Secrets，先验收规则模式。不会在启动时访问财报、行情或模型接口。
4. 打开预览的`?lang=en`。核对三项指标、S1链接及页码、E4推断、语言切换、复核保存、问题改变后失效、JSON/Markdown下载、窄屏和CSV异常。
5. 如需AI，由账户所有者配置Secrets；仅在了解服务商当前模型价格、权限和地区可用性后开启。密钥不提交GitHub。OpenAI/智谱按原仓库配置方式，英文界面保留中文AI原文。
6. 将本次**实际**预览验收结果记入交付记录，不把原仓库历史成功记录当成本次验收。

Preview creation is itself a deployment and requires the user's confirmation. These instructions do not authorise the agent to execute it.

## 线上切换 / Production cutover (separate confirmation)

预览通过后，记录旧应用当前部署commit、分支、Python版本及回滚入口，请用户审阅具体预览并确认。再选择合并经审阅的分支，或由所有者按其发布流程切换应用。不要仅为演示而直接推main。

仓库CI仅运行测试和离线评估，没有新增自动部署任务。提交分支不会在本次任务中改变旧线上应用配置。

## 回滚 / Rollback

- 只有独立预览：暂停或删除预览即可，旧生产应用无需改动。
- 如未来已切生产：由所有者将应用恢复至切换前记录的已知版本并按平台流程重启；保留Secrets原配置，不在日志中输出。
- 如未来已合并代码：通过普通revert提交恢复，不强推main、不删除用户后续工作。复跑完整测试并重新核对页面。

## 打包 / Source bundle

在工作树干净且交付文件已提交后运行：

```bash
python tools/package_submission.py --version 4.0
```

生成`output/stock-evidence-lab-v4.zip`及`output/submission-manifest.json`。仅包含当前Git提交的跟踪文件，记录commit、SHA-256和条目数，排除密钥、虚拟环境、临时产物。旧PDF作为明确标注的历史材料保留，新版文档和截图必须随包提供。
