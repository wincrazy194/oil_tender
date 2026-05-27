"""
测试使用 AI 判断招标公告是否属于 IT 相关
替代关键词匹配方案
"""
import requests
import json

# 配置
API_KEY = "sk-f374422e47de47ecb731a3e16e03a7eb"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 从 config.py 复制的关键词（用于对比）
IT_KEYWORDS = [
    "软件", "软件开发", "系统开发", "应用开发", "平台开发",
    "SaaS", "PaaS", "微服务", "低代码",
    "APP", "小程序", "电子商务","AI","ai",
    "信息化", "数字化", "智能化", "IT", "信息技术", "信息系统",
    "工业互联网", "物联网", "IoT",
    "数据治理", "数据资产", "主数据",
    "数据湖", "数据仓库", "BI", "商业智能", "可视化",
    "数据中心", "云计算", "云服务", "服务器", "数据存储", "数据库",
    "网络安全", "系统集成", "网络平台",
    "VPN", "网络设备","安全运维",
    "人工智能", "大数据",
    "交换机", "路由器", "防火墙", "计算机",
    "IT 运维", "系统运维", "运维",
    "系统维保", "技术支持", "软件维护",
]

IT_EXCLUDE_KEYWORDS = [
    "管道", "电气", "供水", "电力", "机械",
    "施工", "土建", "检修", "大修",
    "物资", "泵", "阀", "电缆",
    "船舶", "车辆", "运输", "物流",
    "家具", "空调", "电梯", "消防",
    "绿化", "保洁", "物业", "食堂", "宿舍",
]


def is_it_related_by_keyword(title: str) -> bool:
    """关键词匹配方式（旧方案）"""
    # 检查是否包含 IT 关键词
    has_keyword = any(kw in title for kw in IT_KEYWORDS)
    if not has_keyword:
        return False

    # 检查是否包含排除关键词
    has_exclude = any(kw in title for kw in IT_EXCLUDE_KEYWORDS)
    if has_exclude:
        return False

    return True


def is_it_related_by_ai(title: str, use_cache: dict = None, verbose: bool = False) -> bool:
    """AI 判断方式（新方案）"""
    if use_cache is None:
        use_cache = {}

    # 检查缓存
    if title in use_cache:
        return use_cache[title]

    prompt = f"""请判断以下招标公告标题是否属于 IT/信息化/数字化相关项目。

标题：{title}

【属于 IT 项目的情况】（回复"是"）：
1. 纯软件开发：ERP、OA、管理平台、业务系统等软件开发/升级
2. 信息化系统：信息管理、数据管理、物资管理等纯信息系统
3. 基础设施：数据中心、服务器、存储、数据库、云计算平台
4. 网络与安全：网络设备、网络安全、防火墙、系统集成
5. IT 运维：IT 系统运维、桌面支持、软件维护
6. 数据分析：大数据分析、BI 商业智能、数据可视化

【不属于 IT 项目的情况】（回复"否"）：
1. 工业控制：生产控制、DCS、PLC、SCADA、自动化控制（即使有"监控"、"自动化"）
2. 弱电/安防：视频监控、门禁、报警系统（属于安防工程）
3. 通信系统：电话、对讲机、电台、海缆通信（属于通信工程）
4. 智能设备：设备智能化改造、智能仪表（属于设备采购）
5. 传统工程：管道、电气、机械、船舶、土建、施工
6. 物资采购：泵、阀、电缆、家具、空调、电梯
7. 生活服务：物业、食堂、保洁、绿化、车辆运输

核心判断原则：
- 如果项目核心是"软件/数据/网络/IT 系统"，则是 IT 项目
- 如果项目核心是"硬件设备/工程/服务"，即使包含"系统"、"智能"、"监控"等词，也不是 IT 项目

只需回复"是"或"否"，不需要其他内容。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-turbo",
        "messages": [
            {"role": "system", "content": "你是一个专业的招投标信息分类助手，擅长判断项目是否属于 IT/信息化领域。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 10
    }

    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
        resp_data = resp.json()

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"].strip()
            # 解析回答
            result = "是" in content and "否" not in content
            use_cache[title] = result
            if verbose:
                print(f"     AI 原始回复：{content} -> {result}")
            return result
        else:
            print(f"  API 调用失败：{resp_data}")
            return False
    except Exception as e:
        print(f"  API 调用异常：{e}")
        return False


def test_cnooc_titles():
    """用中海油真实标题测试"""
    # 从之前的采集中提取的真实标题
    test_titles = [
        # IT 相关（应该判定为是）
        "数字化转型 - 信息管理系统升级改造项目",
        "海洋石油信息化 - 数据中心网络设备安装采购",
        "智能油田 - 生产数据采集与监控系统",
        "信息系统运维服务框架协议",
        "网络安全设备采购及集成服务",
        "云计算平台扩容项目",
        "工业互联网平台建设",
        "大数据分析和可视化系统",
        "IT 运维服务 - 桌面支持",
        "软件开发 - 物资管理信息系统",

        # 非 IT 相关（应该判定为否）
        "管道工程专业承包",
        "电气设备检修服务",
        "供水系统改造项目",
        "机械设备采购",
        "船舶租赁服务",
        "车辆运输服务",
        "办公楼物业服务",
        "食堂承包服务",
        "绿化养护服务",
        "消防设施维护",
        "管道、电气、供水、电力、机械检修",
        "泵阀电缆采购",
        "土建工程施工",
        "物资供应服务",
        "中央空调维保",
        "电梯维护保养",
        "保洁服务",
        "宿舍楼改造",

        # 边界案例（关键词可能会误判）
        "视频监控系统采购",  # 有"系统"但不是 IT
        "自动化控制系统",  # 有"系统"但可能是工业控制
        "通信系统服务",  # 边界
        "智能管道监测系统",  # 有"智能"、"系统"但本质是管道
        "电气设备智能化改造",  # 有"智能化"但是电气设备
        "信息系统监理服务",  # IT 相关
        "网络系统管道铺设",  # 有"网络"、"系统"但是管道工程
    ]

    print("=" * 80)
    print("AI IT 分类器测试 - 中海油真实标题")
    print("=" * 80)
    print()

    results = []
    cache = {}

    for i, title in enumerate(test_titles, 1):
        print(f"[{i:2d}] 标题：{title}")

        # 关键词判断
        keyword_result = is_it_related_by_keyword(title)

        # AI 判断
        ai_result = is_it_related_by_ai(title, cache)

        # 对比结果
        match = "一致" if keyword_result == ai_result else "不一致"

        print(f"     关键词：{'IT' if keyword_result else '非 IT'} | AI: {'IT' if ai_result else '非 IT'} | {match}")

        results.append({
            "title": title,
            "keyword": keyword_result,
            "ai": ai_result,
            "match": match
        })
        print()

    # 统计
    total = len(results)
    matches = sum(1 for r in results if r["match"] == "一致")
    keyword_it = sum(1 for r in results if r["keyword"])
    ai_it = sum(1 for r in results if r["ai"])

    print("=" * 80)
    print("统计结果")
    print("=" * 80)
    print(f"总样本数：{total}")
    print(f"一致：{matches} ({matches/total*100:.1f}%)")
    print(f"不一致：{total - matches} ({(total-matches)/total*100:.1f}%)")
    print()
    print(f"关键词判定为 IT: {keyword_it} 个")
    print(f"AI 判定为 IT: {ai_it} 个")

    # 显示不一致的案例
    mismatches = [r for r in results if r["match"] != "一致"]
    if mismatches:
        print()
        print("=" * 80)
        print("不一致的案例（需要人工确认）")
        print("=" * 80)
        for r in mismatches:
            kw_tag = "IT" if r["keyword"] else "非 IT"
            ai_tag = "IT" if r["ai"] else "非 IT"
            print(f"标题：{r['title']}")
            print(f"     关键词：{kw_tag} | AI: {ai_tag}")
            print()


def test_batch_from采集():
    """从实际采集中测试"""
    # 这里可以粘贴实际采集到的标题进行测试
    real_titles = [
        # 示例：从中海油 API 采集到的真实数据
        "数字化转型 - 信息管理系统升级改造项目",
        "海洋石油信息化 - 数据中心网络设备安装采购",
        "智能油田 - 生产数据采集与监控系统",
    ]

    if real_titles:
        print("\n" + "=" * 80)
        print("实际采集数据测试")
        print("=" * 80)
        cache = {}
        for title in real_titles:
            keyword = is_it_related_by_keyword(title)
            ai = is_it_related_by_ai(title, cache)
            print(f"标题：{title}")
            print(f"     关键词：{'IT' if keyword else '非 IT'} | AI: {'IT' if ai else '非 IT'}")
            print()


if __name__ == "__main__":
    test_cnooc_titles()
