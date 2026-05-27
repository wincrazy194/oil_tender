#!/usr/bin/env python
"""
年度数据采集配置验证脚本

验证配置：
- 日期范围：近 365 天
- 模型列表：103 个模型
- Token 不足自动切换
"""

import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MODELS,
    DATE_RANGE_ENABLED,
    DATE_START,
    DATE_END,
    DASHSCOPE_API_KEY,
    AI_IT_CLASSIFIER_ENABLED,
    AI_SUMMARY_ENABLED,
)

print("=" * 80)
print("年度数据采集配置验证")
print("=" * 80)

# 1. 验证日期范围配置
print("\n[1] 日期范围配置")
print(f"  启用状态：{'是' if DATE_RANGE_ENABLED else '否'}")
print(f"  开始日期：{DATE_START}")
print(f"  结束日期：{DATE_END}")

try:
    start = datetime.datetime.strptime(DATE_START, "%Y-%m-%d")
    end = datetime.datetime.strptime(DATE_END, "%Y-%m-%d")
    days = (end - start).days
    print(f"  采集天数：{days} 天")

    if days >= 365:
        print(f"  状态：[OK] 配置为年度采集（{days} 天）")
    elif days >= 30:
        print(f"  状态：[OK] 配置为中期采集（{days} 天）")
    else:
        print(f"  状态：[WARNING] 采集天数较短（{days} 天）")
except Exception as e:
    print(f"  状态：[ERROR] 日期格式错误 - {e}")

# 2. 验证模型列表
print("\n[2] 模型列表配置")
print(f"  模型总数：{len(MODELS)} 个")

if len(MODELS) >= 50:
    print(f"  状态：[OK] 模型数量充足（{len(MODELS)} 个）")
elif len(MODELS) >= 10:
    print(f"  状态：[OK] 模型数量基本充足（{len(MODELS)} 个）")
else:
    print(f"  状态：[WARNING] 模型数量较少（{len(MODELS)} 个）")

# 显示前 5 个首选模型
print("\n  首选模型（前 5 个）:")
for i, model in enumerate(MODELS[:5], 1):
    print(f"    {i}. {model}")

# 3. 验证 API 配置
print("\n[3] API 配置")
if DASHSCOPE_API_KEY:
    key_prefix = DASHSCOPE_API_KEY[:8] + "..." if len(DASHSCOPE_API_KEY) > 8 else DASHSCOPE_API_KEY
    print(f"  DashScope API Key: {key_prefix}")
    print(f"  状态：[OK] 已配置")
else:
    print(f"  状态：[ERROR] 未配置 DashScope API Key")

# 4. 验证 AI 功能
print("\n[4] AI 功能配置")
print(f"  IT 分类器：{'已启用' if AI_IT_CLASSIFIER_ENABLED else '已禁用'}")
print(f"  AI 摘要：{'已启用' if AI_SUMMARY_ENABLED else '已禁用'}")

# 5. Token 不足切换逻辑说明
print("\n[5] Token 不足自动切换逻辑")
print("""
  当遇到以下错误时，系统会自动切换到下一个模型：
  - HTTP 402: Payment Required（余额不足）
  - HTTP 429: Too Many Requests（限流）
  - HTTP 503: Service Unavailable（服务不可用）
  - 错误消息包含："insufficient", "quota", "token 不足", "耗尽" 等

  切换顺序：按 MODELS 列表顺序依次尝试
  当前配置：{0} 个模型可用
  最坏情况：全部尝试失败后降级为关键词匹配
""".format(len(MODELS)))

# 6. 预估 Token 消耗
print("\n[6] Token 消耗预估（仅供参考）")
print("""
  假设采集 365 天数据：
  - 中石油：约 300-500 条/年
  - 中石化：约 200-400 条/年
  - 中海油：约 150-300 条/年
  - 总计：约 650-1200 条/年

  AI 分类消耗（按每条标题约 50 tokens）:
  - IT 分类：650-1200 条 × 50 tokens ≈ 32,500-60,000 tokens
  - AI 摘要（仅 IT 相关，假设 20%）: 130-240 条 × 500 tokens ≈ 65,000-120,000 tokens
  - 总计：约 100,000-180,000 tokens

  参考：
  - qwen-plus: 输入￥0.002/1K tokens
  - 100K tokens 约 ￥200-360
""")

print("=" * 80)
print("配置验证完成！")
print("=" * 80)
