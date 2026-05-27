# 石油行业招投标情报采集系统

自动采集三桶油（中石油、中石化、中海油）招投标公告，AI 筛选 IT/信息化项目，生成 Excel 报表并邮件推送。

## 目录结构

```
oil_tender/
├── scheduler.py         # 定时调度入口
├── collector.py         # 核心采集逻辑（三桶油并行抓取）
├── config.py            # 全局配置（API、邮箱、关键词等）
├── storage.py           # SQLite 去重存储 + Excel 导出
├── notifier.py          # QQ 邮箱 SMTP 日报推送
├── model_switcher.py    # AI 模型自动切换
├── ai_review.py         # AI 代码审查助手
├── utils.py             # 关键词匹配等工具函数
├── generate_html_archive.py  # 本地 HTML 存档生成
├── start_scheduler.bat  # Windows 一键启动脚本
├── requirements.txt     # Python 依赖
├── index_template.html  # HTML 存档索引模板
│
├── tools/               # 运维工具脚本
│   ├── check_db_final.py    # 数据库查询
│   ├── purge_db.py          # 数据清理
│   └── parse_cnpc.py        # 中石油数据解析
│
├── api_test/            # 运行时数据
│   ├── browser_data_*/      # 浏览器持久化 profile
│   └── output/              # 采集中间结果
│
├── data/                # 运行时生成（不上传 git）
│   ├── oil_tender.db        # SQLite 数据库
│   └── exports/             # Excel 报表
│
└── logs/                # 运行日志（不上传 git）
```

## 功能

**采集**
- 中石油：API 请求拦截 + RSA 解密，绕过前端加密
- 中石化：DOM 提取 + Element UI 分页自动翻页
- 中海油：API 响应拦截 + DOM 降级双模式，优先用 API 数据
- 并行采集，三家同时进行（ThreadPoolExecutor）

**AI 处理**
- 批量判断 IT/信息化项目（支持任意 OpenAI 兼容 API）
- 自动生成项目摘要（20-60 字）
- AI 不可用时自动降级为关键词匹配
- 关键词复核：AI 误判时用强关键词纠正
- 多模型自动切换（Token 不足 / 配额耗尽时）

**输出**
- SQLite 去重存储（url 唯一约束）
- Excel 导出（openpyxl，带超链接）
- QQ 邮箱 SMTP 日报推送（带附件，3 次重试）
- 本地 HTML 存档（IT 项目详情页镜像）

**调度**
- Windows 定时任务 / schedule 库两种模式
- 日期范围过滤，按日期翻页策略

## 环境要求

- Python 3.10+
- Microsoft Edge 浏览器
- 任意 OpenAI 兼容 API Key（DeepSeek / 阿里百炼 / OpenAI 等）

## 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

## 配置

复制 `.env` 文件并填入真实配置：

```env
# 邮件配置
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_password     # QQ邮箱授权码
EMAIL_RECEIVERS=receiver@qq.com

# AI API 配置（兼容任意 OpenAI 格式的 API）
DASHSCOPE_API_KEY=sk-xxxxxxxxx        # API Key
DASHSCOPE_BASE_URL=https://api.deepseek.com/v1   # 接口地址
```

其他兼容的 API 示例：

| 平台 | Base URL | 模型 |
|------|----------|------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 阿里百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2.5-7B-Instruct`

`config.py` 中的关键配置项：

| 配置 | 说明 | 默认值 |
|------|------|--------|
| `SCHEDULE_TIME` | 每日定时运行时间 | `"11:00"` |
| `FLIP_STRATEGY` | 翻页策略 `"date"` / `"pages"` | `"date"` |
| `FETCH_PAGES` | 最大翻页数 | `10000` |
| `DATE_START` | 采集起始日期 | 7 天前 |
| `EMAIL_ENABLED` | 是否启用邮件通知 | `True` |
| `AI_IT_CLASSIFIER_ENABLED` | 是否启用 AI 分类 | `True` |

## 使用

**定时调度模式**（推荐）：
```bash
python scheduler.py
```

**单次运行**：
```bash
python -c "from collector import main; main()"
```

**采集指定页数测试**：
```bash
python -c "from collector import collect_cnpc; r = collect_cnpc(max_pages=3); print(len(r))"
```

## 关键词过滤

AI 分类降级时使用关键词匹配，定义在 `config.py`：

- **IT 关键词**（`IT_KEYWORDS`）：软件、信息系统、AI、网络安全、数据中心等
- **排除关键词**（`IT_EXCLUDE_KEYWORDS`）：管道、电气、施工、机械等

AI 分类器负责精确判断，关键词仅作为 AI 不可用时的降级方案和被 AI 误判时的纠正。

## 数据存储

- 数据库：`data/oil_tender.db`（SQLite）
- Excel 报表：`data/exports/tender_report_YYYYMMDD.xlsx`
- 日志：`logs/` 目录

## 中石油反爬机制

中石油（cnpcbidding.com）的反爬措施较为严格，以下是其反爬机制与程序的应对方式：

| 反爬措施 | 说明 | 应对方式 |
|----------|------|----------|
| 会话冷却 | 直接访问列表页 URL 一段时间后页面不再加载内容 | 首次运行手动操作：先跳转到其他页面再点回搜索页，触发正常流程 |
| 滑块验证码 | 搜索前弹出滑块/点选验证码 | 程序等待 30 秒，用户手动完成验证后自动继续采集 |
| API 响应加密 | 列表和详情接口返回 RSA 加密的密文 | 从 `localStorage.logo2` 获取私钥，JSEncrypt 解密 |
| JS 动态渲染 | 详情页内容由 JavaScript 动态加载，无法直接通过 URL 访问页面内容 | 通过 API 拦截获取加密响应后解密，而非直接抓取 HTML |
| 浏览器指纹检测 | 检测 `navigator.webdriver` 等自动化特征 | 持久化 Edge profile + stealth 脚本隐藏自动化标记 |
| 频率限制 | 短时间大量请求会被封 IP | 单个请求间隔 1-2 秒，避免触发风控 |

**首次使用流程：**
1. 程序启动 Edge 浏览器并打开中石油列表页
2. 等待 30 秒，用户点击搜索 → 完成验证码 → 确保列表数据出现
3. 程序自动拦截 API 请求、解密响应、翻页采集
4. 浏览器 profile 保存在 `api_test/browser_data_api/`，下次启动无需重新登录

## 后续更新

- 自动攻克验证码 OCR
- 内容镶嵌在 JS 动态加载，无法直接读取

> 注：内容镶嵌在 JS 动态加载，无法直接读取。方案涉及rsa解密更新可能不会实装，涉及法律风险。

## 注意事项

1. 首次运行中石油采集需手动完成验证码，后续使用已有浏览器 profile 可自动加载
2. 第一次点击中石油网站会对直接访问 URL 进行限制，若页面空白需手动导航到其他页面再返回
3. 需要安装 Edge 浏览器，首次运行后浏览器 profile 保存在 `api_test/browser_data_*/`
4. AI API 按量计费，建议定期检查用量
