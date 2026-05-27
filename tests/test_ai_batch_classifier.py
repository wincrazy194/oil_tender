"""
AI 批量 IT 分类器测试脚本
测试批量判断招标公告是否属于 IT 相关的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS


def is_it_related_batch(titles: list[str], batch_size: int = 10) -> dict[int, bool]:
    """
    批量判断多个标题是否是 IT 相关（一次请求判断最多 batch_size 条）
    """
    if not titles:
        return {}

    # AI 批量判断
    titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])

    prompt = f"""判断以下 {len(titles)} 个招标公告标题是否属于 IT/信息化项目（严格模式）。

标题列表：
{titles_text}

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

请按顺序回复，每条一行，格式：序号。是/否
例如：
1. 是
2. 否
3. 是
"""

    try:
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50
        }
        url = f"{DASHSCOPE_BASE_URL}/chat/completions"

        print(f"    [AI 批量分类] 正在判断 {len(titles)} 条标题...")
        start = time.time()
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        elapsed = time.time() - start
        print(f"    [AI 批量分类] 耗时：{elapsed:.2f} 秒")

        resp.raise_for_status()
        resp_data = resp.json()

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"].strip()
            print(f"    [AI 批量分类] AI 回复:\n{content}")

            # 解析回复
            result = {}
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                import re
                match = re.match(r'^(\d+)\s*[:.．]\s*(是 | 否)', line)
                if match:
                    idx = int(match.group(1)) - 1
                    is_it = "是" in match.group(2)
                    result[idx] = is_it

            return result

        print(f"    [AI 批量分类] API 调用失败")
        return {}

    except Exception as e:
        print(f"    [AI 批量分类] 异常：{e}")
        return {}


def test():
    print("=" * 70)
    print("AI 批量 IT 分类器测试")
    print("=" * 70)
    print()

    # 测试数据（10 条）
    test_titles = [
        "2026 年辽河油田视频 AI 赋能平台算力租赁服务招标公告",  # IT
        "中石油 AI 私有化平台开发部署服务项目",  # IT
        "数据中心服务器扩容采购项目",  # IT
        "网络安全设备采购及运维服务",  # IT
        "企业信息化管理系统开发项目",  # IT
        "数据库迁移与运维服务项目",  # IT
        "四川页岩气公司 2025-2027 年执行机构运维（二次）",  # 非 IT
        "管道电气设备检修项目",  # 非 IT
        "船舶运输安全监管的智能化研究项目",  # 非 IT
        "视频监控数据采集项目",  # 非 IT
    ]

    # 期望结果
    expected = [True, True, True, True, True, True, False, False, False, False]

    print(f"测试数据：{len(test_titles)} 条")
    print(f"期望 IT 相关：6 条，非 IT：4 条")
    print()

    # 批量判断
    result = is_it_related_batch(test_titles)

    # 统计结果
    print()
    print("=" * 60)
    print("判断结果：")
    print("-" * 60)

    correct = 0
    for i, title in enumerate(test_titles):
        is_it = result.get(i, False)
        expect = expected[i]
        status = "✓" if is_it == expect else "✗"
        if is_it == expect:
            correct += 1
        print(f"  {status} [{i+1}] {'IT' if is_it else '非 IT'} (期望：{'IT' if expect else '非 IT'})")
        print(f"      {title[:50]}...")

    print()
    print("=" * 60)
    accuracy = correct / len(test_titles) * 100
    print(f"正确率：{correct}/{len(test_titles)} ({accuracy:.1f}%)")
    print("=" * 60)

    # 性能对比
    print()
    print("性能对比（估算）：")
    print(f"  批量判断（10 条）：~3-5 秒")
    print(f"  逐条判断（10 条）：~30-50 秒")
    print(f"  提速：约 80-90%")
    print("=" * 70)


if __name__ == "__main__":
    test()
