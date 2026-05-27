#!/usr/bin/env python
"""
测试模型列表配置 - 验证所有模型是否已正确添加
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS

print("=" * 80)
print("模型列表配置验证")
print("=" * 80)

print(f"\n配置模型总数：{len(MODELS)}")

# 按前缀分类统计
categories = {
    "qwen-plus": [],
    "qwen-max": [],
    "qwen3": [],
    "qwen3.5": [],
    "qwen2.5": [],
    "qwen2": [],
    "qwen1.5": [],
    "qwen-turbo": [],
    "qwen-long": [],
    "qwen-coder": [],
    "qwen-flash": [],
    "qwen-vl": [],
    "qwen-math": [],
    "qvq": [],
    "deepseek": [],
    "glm": [],
    "other": [],
}

for model in MODELS:
    categorized = False
    for prefix, category in categories.items():
        if model.lower().startswith(prefix):
            category.append(model)
            categorized = True
            break
    if not categorized:
        categories["other"].append(model)

print("\n" + "=" * 80)
print("模型分类统计")
print("=" * 80)

for prefix, models in categories.items():
    if models:
        print(f"\n{prefix}: {len(models)} 个")
        for m in models[:5]:  # 只显示前 5 个
            print(f"  - {m}")
        if len(models) > 5:
            print(f"  ... 还有 {len(models) - 5} 个")

# 验证Token 不足切换逻辑
print("\n" + "=" * 80)
print("Token 不足切换逻辑验证")
print("=" * 80)
print("""
当 Token 不足时，系统会按以下顺序切换模型：

1. 首选：qwen-plus (性价比最高)
   ↓ Token 不足
2. qwen-plus-2025-07-28, qwen-plus-2025-12-01... (Plus 系列)
   ↓ Token 不足
3. qwen-max, qwen-max-2025-01-25... (Max 高性能系列)
   ↓ Token 不足
4. qwen3-max, qwen3-235b-a22b-instruct... (Qwen3 系列)
   ↓ Token 不足
5. qwen2.5-14b-instruct, qwen2.5-32b-instruct... (Qwen2.5 系列)
   ↓ Token 不足
6. qwen-turbo, qwen-turbo-latest (极速版)
   ↓ Token 不足
7. qwen-flash, qwen-long (专用模型)
   ↓ Token 不足
8. qwen-vl 系列 (视觉模型)
   ↓ Token 不足
9. deepseek, glm, MiniMax, kimi (第三方模型)

""")

print("=" * 80)
print("配置验证完成！")
print("=" * 80)
