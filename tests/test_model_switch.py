#!/usr/bin/env python
"""
测试模型切换逻辑 - 模拟 Token 不足时的切换
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS

print("=" * 80)
print("模型切换逻辑测试")
print("=" * 80)

# 模拟 Token 不足错误
def is_token_exhausted_error(status_code: int, error_msg: str) -> bool:
    """判断是否是 Token 不足错误"""
    if status_code == 402:  # 402 Payment Required
        return True
    if "insufficient_balance" in error_msg.lower():
        return True
    if "token" in error_msg.lower() and ("exhausted" in error_msg.lower() or "不足" in error_msg):
        return True
    return False

# 模拟尝试调用模型
def try_model(model_name: str, simulate_failure: bool = False, fail_count: int = 3) -> tuple[bool, str]:
    """
    模拟调用模型
    返回 (是否成功，消息)
    """
    # 模拟前 3 个模型失败
    if simulate_failure and try_model.call_index < fail_count:
        try_model.call_index += 1
        return False, "Token 不足"
    return True, f"成功使用 {model_name}"

try_model.call_index = 0

# 测试切换逻辑
print("\n开始测试模型切换逻辑...\n")

successful_model = None
for i, model in enumerate(MODELS):
    print(f"尝试模型 {i+1}/{len(MODELS)}: {model}")

    # 模拟调用（这里假设前 3 个会失败）
    success, msg = try_model(model, simulate_failure=True, fail_count=3)

    if success:
        print(f"  [OK] {msg}")
        successful_model = model
        break
    else:
        print(f"  [FAIL] {msg}，尝试下一个模型...\n")

print("\n" + "=" * 80)
if successful_model:
    print(f"最终成功切换到模型：{successful_model}")
else:
    print("所有模型都失败!")
print("=" * 80)

# 显示前 10 个模型作为参考
print("\n" + "=" * 80)
print("前 10 个优先使用的模型:")
print("=" * 80)
for i, model in enumerate(MODELS[:10], 1):
    print(f"  {i}. {model}")

print("\n" + "=" * 80)
print("测试完成!")
print("=" * 80)
