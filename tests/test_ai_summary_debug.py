"""
调试 AI 摘要功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, AI_SUMMARY_ENABLED

TEST_CONTENT = """
项目名称：海洋石油数字化转型 - 信息管理系统升级改造
预算金额：500 万元
招标编号：CNOOC-2026-IT-001
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

TEST_TITLE = "海洋石油数字化转型 - 信息管理系统升级改造"


def test_generate_ai_summary():
    """测试 generate_ai_summary 函数"""
    print("=" * 80)
    print("AI 摘要功能调试")
    print("=" * 80)
    print()

    print(f"配置检查:")
    print(f"  AI_SUMMARY_ENABLED = {AI_SUMMARY_ENABLED}")
    print(f"  DASHSCOPE_API_KEY = {DASHSCOPE_API_KEY[:10]}...{DASHSCOPE_API_KEY[-5:]}")
    print(f"  DASHSCOPE_BASE_URL = {DASHSCOPE_BASE_URL}")
    print()

    # 导入函数
    from collect_all_companies_API_NEW import generate_ai_summary

    print("开始生成摘要...")
    print()

    summary = generate_ai_summary(TEST_CONTENT, TEST_TITLE)

    print()
    print("=" * 80)
    print("结果")
    print("=" * 80)
    if summary:
        print(f"摘要生成成功:")
        print(f"  {summary}")
        print(f"  长度：{len(summary)} 字")
    else:
        print("摘要生成失败（返回空字符串）")


if __name__ == "__main__":
    test_generate_ai_summary()
