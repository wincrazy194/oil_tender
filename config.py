"""
全局配置文件
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_PATH = os.path.join(DATA_DIR, "oil_tender.db")

# 如果目录不存在则创建
for d in [DATA_DIR, EXPORT_DIR, LOG_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# ===== 采集目标配置 =====
# 三桶油官方招投标入口
SCRAPERS = {
    "中石油": {
        "name": "中石油",
        "base_url": "https://www.cnpcbidding.com/#/",
        "tender_url": "https://www.cnpcbidding.com/#/tenders",
        "result_url": "https://www.cnpcbidding.com/#/candidate",
        "enabled": True,
    },
    "中石化": {
        "name": "中石化",
        "base_url": "https://ebidding.sinopec.com",
        "tender_url": "https://ebidding.sinopec.com/v3/portal/#/category/NOTICE/TENDER",
        "result_url": "https://ebidding.sinopec.com/v3/portal/#/category/NOTICE/RESULT",
        "enabled": True,
    },
    "中海油": {
        "name": "中海油",
        "base_url": "https://bid.cnooc.com.cn",
        "tender_url": "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD",
        "result_url": "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E4%B8%AD%E6%A0%87%E5%80%99%E9%80%89%E4%BA%BA",
        "enabled": True,
    },
}

# ===== 采集与推送配置 =====
import datetime
SCHEDULE_TIME = "11:00"    # 每日运行时间

# ===== 日期范围配置 =====
# 设置采集的日期范围（格式：YYYY-MM-DD）
# 默认采集近一年的数据（自动计算）
DATE_RANGE_ENABLED = True   # 是否启用日期范围筛选
DATE_END = datetime.datetime.now().strftime("%Y-%m-%d")
DATE_START = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

# 翻页策略配置
# "date" - 根据日期判断是否继续翻页（推荐）
# "pages" - 根据固定页数翻页
FLIP_STRATEGY = "date"      # 翻页策略
FETCH_PAGES = 10000          # 最大页数保护（日期策略会在数据旧时提前停止）
                            # 设置为 None 表示不限制页数

# ===== IT 相关检测关键词 =====
# 核心关键词（标题包含这些词会被判定为 IT 相关）
IT_KEYWORDS = [
    # 软件开发类
    "软件", "软件开发", "系统开发", "应用开发", "平台开发",
    "SaaS", "PaaS", "微服务", "低代码",
    "APP", "小程序", "电子商务","AI","ai",

    # 信息技术类
    "信息化", "数字化", "智能化", "IT", "信息技术", "信息系统",

    # 信息化专项（扩展）
    "工业互联网", "物联网", "IoT",
    "数据治理", "数据资产", "主数据",
    "数据湖", "数据仓库", "BI", "商业智能", "可视化",

    # 基础设施类
    "数据中心", "云计算", "云服务", "服务器", "数据存储", "数据库",

    # 网络与安全
    "网络安全", "系统集成", "网络平台",
    "VPN", "网络设备","安全运维",

    # 前沿技术
    "人工智能", "大数据",

    # 硬件设备类（明确 IT 硬件）
    "交换机", "路由器", "防火墙", "计算机",

    # 运维与服务
    "IT运维", "系统运维", "运维",
    "系统维保", "技术支持",
    "软件维护",
]

# 排除关键词（标题包含这些词时，即使有关键词也不判定为 IT 相关）
IT_EXCLUDE_KEYWORDS = [
    # 非 IT 系统工程
    "管道", "电气", "供水", "电力", "机械",
    "施工", "土建", "检修", "大修",
    "物资", "泵", "阀", "电缆",
    "船舶", "车辆", "运输", "物流",
    "家具", "空调", "电梯", "消防",
    "绿化", "保洁", "物业", "食堂", "宿舍",
]

# ===== 邮件通知配置 =====
# 从环境变量读取敏感信息（优先）.env，否则使用默认值
EMAIL_ENABLED = True               # 开启通知
EMAIL_SMTP_HOST = "smtp.qq.com"     # SMTP 服务器
EMAIL_SMTP_PORT = 465               # SSL 端口
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVERS_RAW = os.environ["EMAIL_RECEIVERS"]
EMAIL_RECEIVERS = [r.strip() for r in EMAIL_RECEIVERS_RAW.split(",") if r.strip()]
EMAIL_SUBJECT = "【招投标助手】每日行业情报汇总"

# ===== AI 摘要 API 配置 =====
# 用于生成招标公告摘要
# 阿里云 DashScope Qwen API
# 从环境变量读取敏感信息，否则使用默认值
DASHSCOPE_API_KEY = os.environ["DASHSCOPE_API_KEY"]
DASHSCOPE_BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://api.deepseek.com/v1")

# ===== 多模型配置 =====
# 当当前模型的 Token 不足时，按顺序切换到下一个模型
# 系统使用 OpenAI 兼容格式 (/chat/completions)，兼容以下平台：
#   DeepSeek:  https://api.deepseek.com/v1     模型: deepseek-chat, deepseek-reasoner
#   阿里百炼:  https://dashscope.aliyuncs.com/compatible-mode/v1  模型: qwen-plus, qwen-max ...
#   OpenAI:    https://api.openai.com/v1         模型: gpt-4o, gpt-4o-mini ...
#   硅基流动:  https://api.siliconflow.cn/v1      模型: Qwen/Qwen2.5-7B-Instruct ...
# 切换平台只需改 .env 的 DASHSCOPE_BASE_URL 和此处的 MODELS 列表
MODELS = [
    "deepseek-chat",       # DeepSeek V3 (首选)
    "deepseek-reasoner",   # DeepSeek R1 (推理)
]
# 旧的配置（已废弃）
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_SUMMARY_ENABLED = True  # 是否启用 AI 摘要（默认关闭，需要时开启）
AI_SUMMARY_MAX_LENGTH = 100  # 摘要最大长度

# ===== AI IT 分类器配置 =====
# 用于判断招标公告是否属于 IT/信息化相关项目
# 替代关键词匹配方案，更准确地识别 IT 项目
AI_IT_CLASSIFIER_ENABLED = True  # 是否启用 AI IT 分类器
# 严格模式：只捕获明确的 IT 项目，边界案例判定为非 IT
# 属于 IT：软件开发、信息系统、数据中心、网络安全、IT 运维
# 不属于 IT：工业控制、安防监控、通信设备、管道电气、物资采购

# ===== 详情页 URL 配置 =====
# 三家公司详情页 URL 模板
# 中海油：使用 newsAlertDetails 路由，必须包含 index 和 childrenActive 参数
DETAIL_URL_TEMPLATES = {
    "中石油": "https://www.cnpcbidding.com/#/tenders",
    "中石化": {
        "TENDER": "https://ebidding.sinopec.com/v3/portal/#/article/TENDER/{id}",
        "RESULT": "https://ebidding.sinopec.com/v3/portal/#/article/RESULT/{id}",
    },
    "中海油": "https://bid.cnooc.com.cn/home/#/newsAlertDetails?index=0&childrenActive=4&id={id}&type=null",
}

# ===== 反爬请求头 =====
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}


# ===== 中石油爬虫配置 =====
# 用于 cnpc_scraper_final.py
CNPC_SCRAPER = {
    "enabled": True,                    # 是否启用爬虫
    "max_pages": 50,                    # 最大翻页数
    "fetch_all": False,                 # False=只采集 IT 相关，True=采集全部
    "it_filter_enabled": True,          # 是否启用 IT 关键词过滤
    "max_details_per_run": 20,          # 每次运行最多获取的详情数量

    # 浏览器配置
    "browser_user_data": os.path.join(BASE_DIR, "api_test", "browser_data_api"),
    "browser_channel": "msedge",        # 使用 Edge 浏览器
    "headless": False,                  # 是否无头模式（建议 False，避免被检测）

    # 输出配置
    "output_dir": os.path.join(BASE_DIR, "api_test", "output"),

    # 等待时间配置（毫秒）
    "page_load_timeout": 60000,         # 页面加载超时
    "api_wait_timeout": 30000,          # API 响应等待超时
    "click_delay": 3000,                # 点击后等待时间

    # 翻页配置
    "flip_strategy": "pages",           # "pages"=按页数，"date"=按日期
    "stop_if_no_new": True,             # 如果没有新数据是否停止

}