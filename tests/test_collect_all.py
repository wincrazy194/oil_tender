#!/usr/bin/env python
"""
三家公司同时采集测试 - 监控 Token 使用
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS, DATE_START, DATE_END

print("=" * 80)
print("三家公司并发采集测试")
print("=" * 80)

print(f"\n采集配置:")
print(f"  日期范围：{DATE_START} 至 {DATE_END}")
print(f"  可用模型：{len(MODELS)} 个")
print(f"  首选模型：{MODELS[0]}")

print(f"\n采集目标:")
print(f"  1. 中石油 - https://www.cnpcbidding.com")
print(f"  2. 中石化 - https://ebidding.sinopec.com")
print(f"  3. 中海油 - https://bid.cnooc.com.cn")

print("\n" + "=" * 80)
print("Token 监控说明")
print("=" * 80)
print("""
Token 消耗监控点:
1. AI IT 分类：每条标题约 50-100 tokens
2. AI 摘要生成：每条 IT 记录约 300-500 tokens

预计消耗（按 365 天估算）:
- 中石油：~400 条 × 50 tokens = 20,000 tokens（分类）
- 中石化：~300 条 × 50 tokens = 15,000 tokens（分类）
- 中海油：~250 条 × 50 tokens = 12,500 tokens（分类）
- IT 相关摘要（假设 20%）: 190 条 × 400 tokens = 76,000 tokens

总计：约 123,500 tokens
""")

print("\n" + "=" * 80)
print("模型切换策略")
print("=" * 80)
print("""
当 Token 不足时，按以下顺序切换:

第 1 梯队（性价比）:
  → qwen-plus, qwen-plus-2025-07-28, qwen-plus-2025-12-01...

第 2 梯队（高性能）:
  → qwen-max, qwen-max-2025-01-25, qwen-max-0428...

第 3 梯队（Qwen3 新模型）:
  → qwen3-max, qwen3-235b-a22b-instruct, qwen3-coder-plus...

第 4 梯队（Qwen2.5 系列）:
  → qwen2.5-14b-instruct, qwen2.5-32b-instruct...

第 5 梯队（快速版）:
  → qwen-turbo, qwen-flash, qwen-long...

第 6 梯队（第三方）:
  → deepseek-r1, glm-5, MiniMax-M2.5, kimi-k2.5...
""")

print("=" * 80)
print("准备开始采集...")
print("=" * 80)
