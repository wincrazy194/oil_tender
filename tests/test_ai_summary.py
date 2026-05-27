"""
AI 摘要功能测试脚本
测试通义千问 API 生成摘要的功能
"""

import sys
import os
# 添加父目录到路径，以便导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
import json
from config import DASHSCOPE_API_KEY

def generate_ai_summary(content: str, title: str, max_retries: int = 3) -> str:
    """
    使用通义千问 API 生成 AI 摘要
    """
    if not DASHSCOPE_API_KEY:
        print("[AI 摘要] 未配置 API Key")
        return ""

    prompt = f"""请为以下招标公告生成一段 20-60 字的摘要：
标题：{title}
内容：{content[:2000]}

摘要要求：
1. 简洁明了，突出核心信息
2. 包含项目主要内容
3. 不要包含"本文"、"本公告"等词汇
4. 直接输出摘要内容，不要有其他说明

摘要："""

    for attempt in range(max_retries):
        try:
            # 使用通义千问 HTTP 接口
            dashscope_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            payload = {
                "model": "qwen-turbo",
                "messages": [
                    {"role": "system", "content": "你是一个专业的招投标信息分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }

            headers = {
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            }

            print(f"    [AI 摘要] 正在请求 API (尝试 {attempt + 1}/{max_retries})...")
            resp = requests.post(dashscope_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            resp_data = resp.json()

            # compatible-mode 格式响应
            if resp_data.get("choices") and len(resp_data["choices"]) > 0:
                summary = resp_data["choices"][0]["message"]["content"].strip()
                if summary and len(summary) >= 10:
                    print(f"    [AI 摘要] 生成成功：{len(summary)} 字")
                    return summary

            print(f"    [AI 摘要] 返回内容为空")
            return ""

        except Exception as http_error:
            print(f"    [AI 摘要] 异常：{http_error}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
            continue

    return ""


def test():
    print("=" * 70)
    print("AI 摘要功能测试")
    print("=" * 70)
    print(f"API Key 配置：{'已配置' if DASHSCOPE_API_KEY else '未配置'}")
    print()

    # 测试用例
    test_cases = [
        {
            "title": "2026 年辽河油田视频 AI 赋能平台算力租赁服务招标公告",
            "content": """
                项目名称：2026 年辽河油田视频 AI 赋能平台算力租赁服务
                招标编号：ZB2026-001
                项目概况：为满足辽河油田视频监控系统的 AI 分析需求，拟采购 GPU 算力租赁服务，
                主要包括：1. 提供不少于 100 台高性能 GPU 服务器；2. 支持人脸识别、行为分析等
                AI 算法；3. 提供 7x24 小时技术支持服务；4. 服务期限 3 年。
                投标人资格要求：具有独立法人资格，具备相关资质证书。
            """
        },
        {
            "title": "中石油 AI 私有化平台开发部署服务项目",
            "content": """
                一、项目背景
                为推进集团公司数字化转型，提升智能化应用水平，现启动 AI 私有化平台开发部署项目。

                二、建设内容
                1. 搭建企业级 AI 开发平台，支持模型训练、推理部署
                2. 部署大语言模型本地化应用
                3. 提供 API 接口服务，支持与现有业务系统集成
                4. 建设数据标注和管理平台

                三、技术要求
                1. 平台需支持国产化部署
                2. 满足等保三级安全要求
                3. 提供完整的文档和培训服务
            """
        },
        {
            "title": "四川页岩气公司 2025-2027 年执行机构运维（二次）",
            "content": """
                招标条件
                本招标项目四川页岩气公司 2025-2027 年执行机构运维项目已批准建设，
                项目业主为四川页岩气公司，建设资金来自企业自筹。

                项目概况：
                1. 服务地点：四川省内江市、泸州市等地
                2. 服务范围：执行机构日常巡检、维护保养、故障处理
                3. 服务期限：2025 年 1 月 1 日至 2027 年 12 月 31 日
                4. 质量要求：符合国家及行业相关标准

                投标人资格要求：
                1. 具有独立法人资格
                2. 具有相关运维经验
            """
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n【测试用例 {i}】")
        print(f"标题：{case['title']}")
        print("-" * 60)

        summary = generate_ai_summary(case['content'], case['title'])

        if summary:
            print(f"\n【AI 摘要】{summary}")
        else:
            print("\n【AI 摘要】生成失败")

        print("-" * 60)

    print("\n测试完成！")


if __name__ == "__main__":
    test()
