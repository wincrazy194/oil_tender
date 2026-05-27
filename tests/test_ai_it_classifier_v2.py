"""
测试使用 AI 判断招标公告是否属于 IT 相关（严格版本）
替代关键词匹配方案
"""
import requests

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
    has_keyword = any(kw in title for kw in IT_KEYWORDS)
    if not has_keyword:
        return False
    has_exclude = any(kw in title for kw in IT_EXCLUDE_KEYWORDS)
    if has_exclude:
        return False
    return True


def is_it_related_by_ai(title: str) -> bool:
    """AI 判断方式（新方案）- 严格模式"""
    prompt = f"""判断以下标题是否属于 IT/信息化项目（严格模式）。

标题：{title}

【是】仅当以下情况：
1. 明确提到"软件"、"信息系统"、"管理平台"
2. 数据中心、服务器、数据库采购
3. 网络安全、网络设备
4. 纯 IT 运维服务

【否】以下情况都不是 IT：
- 含"管道"、"电气"、"机械"、"船舶"、"物资"、"泵"、"阀"、"电缆"
- 含"监控"、"自动化"、"控制"（属于工控/安防）
- 含"通信"（属于通信工程）
- 含"智能"但修饰的是设备（如"智能管道"、"电气设备智能化"）
- 生产数据、工业数据采集

严格原则：不确定就回复"否"。

只需回复"是"或"否"。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 5
    }

    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
        resp_data = resp.json()
        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"].strip()
            return "是" in content and "否" not in content
        return False
    except:
        return False


# 测试用例：(标题，预期结果)
TEST_CASES = [
    # 明确 IT
    ("数字化转型 - 信息管理系统升级改造", True),
    ("海洋石油信息化 - 数据中心网络设备采购", True),
    ("信息系统运维服务框架协议", True),
    ("网络安全设备采购及集成服务", True),
    ("云计算平台扩容项目", True),
    ("大数据分析和可视化系统", True),
    ("IT 运维服务 - 桌面支持", True),
    ("软件开发 - 物资管理信息系统", True),
    ("工业互联网平台建设", True),

    # 明确非 IT
    ("管道工程专业承包", False),
    ("电气设备检修服务", False),
    ("供水系统改造项目", False),
    ("机械设备采购", False),
    ("船舶租赁服务", False),
    ("车辆运输服务", False),
    ("办公楼物业服务", False),
    ("食堂承包服务", False),
    ("绿化养护服务", False),
    ("消防设施维护", False),
    ("泵阀电缆采购", False),
    ("土建工程施工", False),
    ("中央空调维保", False),
    ("电梯维护保养", False),
    ("保洁服务", False),

    # 边界案例（希望 AI 能正确判断）
    ("视频监控系统采购", False),  # 弱电安防
    ("自动化控制系统", False),  # 工业控制
    ("通信系统服务", False),  # 通信工程
    ("智能管道监测系统", False),  # 管道
    ("电气设备智能化改造", False),  # 电气
    ("网络系统管道铺设", False),  # 管道
    ("生产数据采集与监控系统", False),  # 工业 SCADA
    ("物资管理信息系统", True),  # 信息系统
    ("信息系统监理服务", True),  # IT 监理
]


def main():
    print("=" * 90)
    print("AI IT 分类器测试（严格模式）")
    print("=" * 90)
    print()

    correct = 0
    total = len(TEST_CASES)
    ai_it_count = 0
    keyword_it_count = 0

    for i, (title, expected) in enumerate(TEST_CASES, 1):
        keyword_result = is_it_related_by_keyword(title)
        ai_result = is_it_related_by_ai(title)

        keyword_match = keyword_result == expected
        ai_match = ai_result == expected

        if ai_match:
            correct += 1
        if ai_result:
            ai_it_count += 1
        if keyword_result:
            keyword_it_count += 1

        # 显示结果
        kw_str = "IT" if keyword_result else "非 IT"
        ai_str = "IT" if ai_result else "非 IT"
        exp_str = "IT" if expected else "非 IT"
        kw_mark = "OK" if keyword_match else "FAIL"
        ai_mark = "OK" if ai_match else "FAIL"

        print(f"[{i:2d}] {title}")
        print(f"     预期：{exp_str} | 关键词：{kw_str} {kw_mark} | AI: {ai_str} {ai_mark}")
        print()

    # 统计
    keyword_correct = sum(1 for t, e in TEST_CASES if is_it_related_by_keyword(t) == e)

    print("=" * 90)
    print("统计结果")
    print("=" * 90)
    print(f"总样本数：{total}")
    print()
    print(f"关键词方案：{keyword_correct}/{total} ({keyword_correct/total*100:.1f}%)")
    print(f"AI  方案：    {correct}/{total} ({correct/total*100:.1f}%)")
    print()
    print(f"关键词判定为 IT: {keyword_it_count} 个")
    print(f"AI  判定为 IT: {ai_it_count} 个")


if __name__ == "__main__":
    main()
