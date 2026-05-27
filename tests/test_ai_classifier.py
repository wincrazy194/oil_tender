"""
AI IT 分类器测试脚本
测试 AI 判断招标公告是否属于 IT 相关的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS


def is_it_related_ai(title: str) -> bool:
    """使用 AI 判断是否是 IT 相关（严格模式）"""
    prompt = f"""判断以下标题是否属于 IT/信息化项目（严格模式）。

标题：{title}

【是】仅当以下情况：
1. 明确提到"软件"、"信息系统"、"管理平台"、"平台开发"
2. 数据中心、服务器、数据库采购
3. 网络安全、网络设备
4. 纯 IT 运维服务
5. AI/人工智能相关：AI 平台、大模型、算力租赁、私有化部署

【否】以下情况都不是 IT：
- 含"管道"、"电气"、"机械"、"船舶"、"物资"、"泵"、"阀"、"电缆"
- 含"监控"、"自动化"、"控制"（属于工控/安防），但"AI+ 监控"除外
- 含"通信"（属于通信工程）
- 含"智能"但修饰的是物理设备（如"智能管道"、"电气设备智能化"）
- 生产数据、工业数据采集（不含 AI 分析）
- 视频监控（不含 AI 分析的纯硬件）

严格原则：不确定就回复"否"。

只需回复"是"或"否"。"""

    try:
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 5
        }
        url = f"{DASHSCOPE_BASE_URL}/chat/completions"

        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp_data = resp.json()

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"].strip()
            print(f"    AI 回复：{content}")
            return "是" in content and "否" not in content

        print(f"    API 调用失败，降级为关键词判断")
        return is_it_related_keyword(title)

    except Exception as e:
        print(f"    异常：{e}，降级为关键词判断")
        return is_it_related_keyword(title)


def is_it_related_keyword(title: str) -> bool:
    """关键词判断（降级方案）"""
    title_lower = title.lower()
    for kw in IT_EXCLUDE_KEYWORDS:
        if kw.lower() in title_lower:
            return False
    return any(kw.lower() in title_lower for kw in IT_KEYWORDS)


def test():
    print("=" * 70)
    print("AI IT 分类器测试（严格模式）")
    print("=" * 70)
    print()

    # 测试用例：应该是 IT 相关
    it_cases = [
        "2026 年辽河油田视频 AI 赋能平台算力租赁服务招标公告",
        "中石油 AI 私有化平台开发部署服务项目",
        "数据中心服务器扩容采购项目",
        "网络安全设备采购及运维服务",
        "企业信息化管理系统开发项目",
        "数据库迁移与运维服务项目",
    ]

    # 测试用例：应该不是 IT 相关
    non_it_cases = [
        "四川页岩气公司 2025-2027 年执行机构运维（二次）",
        "管道电气设备检修项目",
        "船舶运输安全监管的智能化研究项目",  # 虽然有"智能化"，但本质是船舶运输
        "视频监控数据采集项目",  # 虽然是"视频"，但是监控类
        "工业自动化控制系统采购",  # 工控类
        "通信网络设备采购项目",  # 通信类
        "机械装备大修项目",
        "物资采购招标",
    ]

    print("【应该是 IT 相关】")
    print("-" * 60)
    ai_correct = 0
    for title in it_cases:
        print(f"\n标题：{title[:60]}...")
        result = is_it_related_ai(title)
        keyword_result = is_it_related_keyword(title)
        print(f"AI 判断：{'是 IT' if result else '非 IT'}  |  关键词：{'是 IT' if keyword_result else '非 IT'}")
        if result:
            ai_correct += 1
            print("[OK] 正确")
        else:
            print("[ERROR] 错误")

    print(f"\nAI 正确率：{ai_correct}/{len(it_cases)}")

    print("\n\n【应该不是 IT 相关】")
    print("-" * 60)
    non_ai_correct = 0
    for title in non_it_cases:
        print(f"\n标题：{title[:60]}...")
        result = is_it_related_ai(title)
        keyword_result = is_it_related_keyword(title)
        print(f"AI 判断：{'是 IT' if result else '非 IT'}  |  关键词：{'是 IT' if keyword_result else '非 IT'}")
        if not result:
            non_ai_correct += 1
            print("[OK] 正确")
        else:
            print("[ERROR] 错误（误判为 IT）")

    print(f"\nAI 正确率：{non_ai_correct}/{len(non_it_cases)}")

    print("\n\n" + "=" * 60)
    print("测试完成！")
    print(f"IT 类正确率：{ai_correct}/{len(it_cases)}")
    print(f"非 IT 类正确率：{non_ai_correct}/{len(non_it_cases)}")
    print("=" * 60)


if __name__ == "__main__":
    test()
