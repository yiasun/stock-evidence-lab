# 证据镜 · Stock Evidence Lab

以贵州茅台（600519.SH）为单标的，面向希望追问证据的个人研究者。核心任务是把自然语言问题转为研究维度，从财务事实进入矛盾证据，再沿公告、字段、算式和待验证问题继续研究。

这是**冻结证据研究MVP**，不是实时投研终端。没有API Key也能完整操作；LLM未启用时清晰标记规则模式。

## 启动

建议 Python 3.11（本地另在 Python 3.10.0 实测）。

```bash
python -m venv .venv
# 激活虚拟环境后
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

打开终端提示的本地地址。默认不访问外部接口。

## 操作主链路

1. 选择示例问题，或输入“利润下降，现金流为什么大增？”。
2. 检查关键词推荐维度，可修改经营、财务、估值、行情、行业及事件范围。
3. 生成证据诊断，查看模式标签和优先证据顺序。
4. 区分正面、负面、矛盾和未知；每张卡标记事实 / 推断 / 未知。
5. 展开“沿证据继续研究”，检查原始财务期次、字段、单位、算式和来源。
6. 点击后续研究任务继续追问，或下载JSON研究记录。
7. 行情沙盒可上传CSV，先校验字段、日期、空值和价格，再计算区间价格变化与样本最大回撤。

## 设计与AI角色

消费品模板重点关注盈利、现金回款和渠道事件。当前只支持贵州茅台，不伪装成全市场通用模型。

- `diagnosis.py`：确定性计算同比、营业收入口径毛利率、行情收益和最大回撤；校验可比期次和异常数据。
- `ai_layer.py`：可选的自然语言证据选择/排序。调用OpenAI Chat Completions JSON模式，只接受已存在的证据ID；不渲染模型自由文本，也不允许模型计算财务数字。
- `app.py`：用户修改诊断维度、查看反面证据和未知、钻取原始字段与公告。

即使LLM漏选反面证据，界面仍保留所选维度的全部证据。LLM异常、超时或非法引用时显示“规则回退”，不会把接口失败包装成正常AI输出。当前不提供自由生成财务解读；AI的角色限于证据导航。

## 环境变量与Secrets

可选：`OPENAI_API_KEY`、`AI_MODEL`（默认`gpt-4.1-mini`，沿用原仓库配置）。`.env.example`仅是模板，应用不会自动读取`.env`。本地通过环境变量或`.streamlit/secrets.toml`配置；Cloud使用Advanced settings的Secrets。不要把密钥提交到GitHub。

```toml
OPENAI_API_KEY = "your-key"
AI_MODEL = "gpt-4.1-mini"
```

默认关闭LLM。用户主动勾选时，研究问题和公开证据卡会发往固定的`https://api.openai.com/v1/chat/completions`。不支持任意Base URL，避免密钥被转发到未知服务。没有密钥时不发请求。用户上传的行情不会发送到LLM，也不会写入仓库；请勿输入个人敏感信息。

## 数据与证据

数据包核验日：2026-10-16。财务观察期：2026H1，对比2025H1。半年报未经审计，不能表示此后的实时经营情况。

|证据|来源与口径|核验范围|
|---|---|---|
|S1 财务|[2026年半年报公告全文转载](https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12496833&stockid=600519)，第二节七、第三节相关科目变动分析|逐字段核对营业收入、归母净利润、经营现金流和营业成本；人民币元、合并口径；2025H1来自同期对比列|
|S1 原始链接|[上交所PDF](https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-08-15/600519_20260815_UXBN.pdf)|本环境返回验证页面，未完成PDF逐页交叉核验，界面明确披露|
|S2 价格事件|[中国证券报B052公告](https://epaper.cs.com.cn/zgzqb/html/2026-07/18/nw.D110000zgzqb_20260718_1-B052.htm)，临2026-028|限定飞天产品、规格、渠道；披露/生效2026-07-18，晚于半年报期末|
|继承行情|`data/market_snapshot.csv`|原仓库未提供来源、复权和成交量单位；隔离为待核验样本，不纳入公司结论|
|同行与估值|缺失|显式未知，不输出PE/PB、行业排名或贵便宜结论|

未连接扶摇或iFinD，未声称使用其数据。缺少授权接口时使用公开公告，并如实标明核验渠道。没有补造实时数据。

关键口径：营业收入不等于营业总收入；归母净利润不等于合并净利润；现金流包含财务子公司资金变动，不能直接归因主业；半年EPS不能当TTM EPS；调价后业绩不能倒推解释此前半年报。

## 部署 Streamlit Community Cloud

1. 登录 [Streamlit Cloud](https://share.streamlit.io/)，按需由账户所有者完成条款同意和GitHub授权。
2. Create app → GitHub仓库`yiasun/stock-evidence-lab` → 分支`main` → 入口`app.py`。
3. Advanced settings选择Python 3.11；密钥非必需，可先以规则模式上线。
4. 部署完成后，实际打开分配的`streamlit.app` URL，测试问题、证据展开、CSV异常与导出。

Cloud Python版本以部署面板为准，不能只依赖`.python-version`。官方部署说明：[Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)。

## 验证

```bash
python -m compileall -q app.py diagnosis.py ai_layer.py
python -m unittest discover -s tests -v
```

测试覆盖计算基准、缺失数据、负数或零基数、日期异常、LLM超时与虚构引用、交易意图、页面主链路和缺少密钥回退。LLM成功路径使用模拟响应，不能视为真实在线模型验收。详见[测试记录](docs/TEST_REPORT.md)、[AI使用与验证](docs/AI_USAGE.md)、[演示脚本](docs/DEMO.md)。

## 已知边界与未做事项

不输出确定性涨跌、买卖、仓位或收益承诺；正面/负面为单项证据方向，非股票评级。只有两个可比半年期，不声称长期趋势。没有实时行情、完整TTM估值、同行横比、自动公告更新、OCR财报解析或多标的支持。CSV未验证交易日连续和复权；区间价格变化不包含股息，不等于投资总回报。

在线产品：[证据镜 · Stock Evidence Lab](https://stock-evidence-lab-yiasun.streamlit.app/)。已部署Streamlit Community Cloud，Python 3.11。自动化与公网实测记录见测试报告。

尚需外部验收：真实LLM调用需账户密钥。演示视频为可选项，仓库提供脚本，尚未录制。
