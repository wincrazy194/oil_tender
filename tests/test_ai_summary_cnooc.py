"""
测试 AI 摘要功能 - 使用中海油招标公告
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, AI_SUMMARY_ENABLED

# 中海油真实招标公告测试用例
TEST_CASES = [
    {
        "title": "海洋石油数字化转型 - 信息管理系统升级改造项目",
        "content": """
项目名称：海洋石油数字化转型 - 信息管理系统升级改造项目
招标编号：CNOOC-2026-IT-001
预算金额：人民币 500 万元
投标截止时间：2026 年 4 月 15 日 10:00

一、项目概况
为推进海洋石油数字化转型，现采购信息管理系统升级改造服务。
包括 ERP 系统升级、数据中台建设、移动端应用开发等内容。

二、服务内容
1. 现有 ERP 系统功能模块升级
2. 数据中台架构设计与实施
3. 移动端 APP 开发（iOS/Android）
4. 系统运维支持服务（1 年）

三、资质要求
1. 具有软件企业认证证书
2. 具有 CMMI3 及以上资质
3. 近三年有类似项目业绩
"""
    },
    {
        "title": "网络安全设备采购及集成服务",
        "content": """
项目名称：网络安全设备采购及集成服务
招标编号：CNOOC-2026-SEC-002
预算金额：人民币 300 万元
投标截止时间：2026 年 4 月 20 日 14:00

一、采购内容
1. 防火墙设备 5 台
2. 入侵检测系统 2 套
3. 安全运维平台 1 套
4. 设备安装调试及集成服务

二、技术要求
1. 防火墙吞吐量≥100Gbps
2. 支持 IPv4/IPv6 双栈
3. 提供 3 年原厂质保服务
"""
    },
    {
        "title": "大数据分析和可视化系统",
        "content": """
项目名称：大数据分析和可视化系统
招标编号：CNOOC-2026-DATA-003
预算金额：人民币 800 万元
投标截止时间：2026 年 4 月 25 日 09:30

一、建设目标
构建企业级大数据分析平台，实现生产数据、经营数据的集中分析和可视化展示。

二、功能要求
1. 数据采集与存储
2. 数据清洗与加工
3. BI 商业智能分析
4. 数据可视化大屏展示
5. 移动端数据查询

三、交付物
1. 大数据分析平台软件
2. 可视化大屏 3 套
3. 移动端 APP
4. 系统文档及培训
"""
    }
]


def test_http_api(content: str, title: str) -> str:
    """测试 DashScope HTTP API"""
    import requests

    prompt = f"""请为以下招标公告生成一个 20-60 字的精炼摘要，包含项目名称、预算金额（如有）、截止日期（如有）等关键信息：

标题：{title}

公告内容：
{content[:2000]}

请用一句话概括，20-60 字以内，不要多余说明。"""

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

    dashscope_url = DASHSCOPE_BASE_URL.rstrip('/') + '/chat/completions'

    try:
        resp = requests.post(dashscope_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        resp_data = resp.json()

        if resp_data.get("choices") and len(resp_data["choices"]) > 0:
            summary = resp_data["choices"][0]["message"]["content"].strip()
            return summary
        else:
            return f"API 返回错误：{resp_data}"
    except Exception as e:
        return f"API 调用异常：{e}"


def test_cli(content: str, title: str) -> str:
    """测试本地 qwen CLI"""
    import subprocess
    import shutil

    prompt = f"""请为以下招标公告生成一个 20-60 字的精炼摘要，包含项目名称、预算金额（如有）、截止日期（如有）等关键信息：

标题：{title}

公告内容：
{content[:2000]}

请用一句话概括，20-60 字以内，不要多余说明。"""

    qwen_path = shutil.which("qwen")
    if not qwen_path:
        return "未找到 qwen CLI"

    try:
        result = subprocess.run(
            f'cmd /c "{qwen_path} {prompt}"',
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            return f"CLI 返回错误：{result.stderr}"
    except Exception as e:
        return f"CLI 调用异常：{e}"


def main():
    print("=" * 80)
    print("AI 摘要功能测试 - 中海油招标公告")
    print("=" * 80)
    print()

    print(f"配置检查:")
    print(f"  AI_SUMMARY_ENABLED = {AI_SUMMARY_ENABLED}")
    print(f"  DASHSCOPE_API_KEY = {DASHSCOPE_API_KEY[:10]}...{DASHSCOPE_API_KEY[-5:]}")
    print(f"  DASHSCOPE_BASE_URL = {DASHSCOPE_BASE_URL}")
    print()

    # 检查 qwen CLI
    import shutil
    qwen_path = shutil.which("qwen")
    print(f"  qwen CLI 路径：{qwen_path if qwen_path else '未安装'}")
    print(f"  注：生产代码已改用 HTTP API，CLI 方式已弃用")
    print()

    for i, case in enumerate(TEST_CASES, 1):
        print("=" * 80)
        print(f"测试用例 {i}: {case['title']}")
        print("=" * 80)

        # 测试 HTTP API
        print("\n[HTTP API 测试]")
        summary_http = test_http_api(case['content'], case['title'])
        print(f"结果：{summary_http[:100]}..." if len(summary_http) > 100 else f"结果：{summary_http}")
        print()


if __name__ == "__main__":
    main()
