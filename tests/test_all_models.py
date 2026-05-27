#!/usr/bin/env python
"""
测试所有可用模型 - 验证每个模型是否能正常调用
"""

import requests
import json
import os
import sys

# 添加父目录到路径以便导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL

# 测试用的简单 prompt
TEST_PROMPT = "1+1 等于几？请直接回复数字。"

# 使用 ASCII 符号避免 Windows 控制台编码问题
OK = "[OK]"
FAIL = "[FAIL]"

print("=" * 80)
print("模型可用性测试")
print("=" * 80)
print(f"测试 Prompt: {TEST_PROMPT}")
print(f"API 地址：{DASHSCOPE_BASE_URL}")
print(f"模型总数：{len(MODELS)}")
print("=" * 80)

results = {"success": [], "failed": [], "error_details": {}}

for i, model in enumerate(MODELS):
    print(f"\n[{i+1}/{len(MODELS)}] 测试模型：{model}")

    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个助手，请直接简短回答。"},
                {"role": "user", "content": TEST_PROMPT}
            ],
            "max_tokens": 10
        }

        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }

        api_url = DASHSCOPE_BASE_URL.rstrip('/') + '/chat/completions'
        resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
        resp_data = resp.json()

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"].strip()
            print(f"  {OK} 成功 - 回复：{content[:30]}")
            results["success"].append(model)
        else:
            error_msg = resp_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
            print(f"  {FAIL} 失败 - {error_msg[:50]}")
            results["failed"].append(model)
            results["error_details"][model] = error_msg

    except requests.exceptions.Timeout:
        print(f"  {FAIL} 失败 - 请求超时")
        results["failed"].append(model)
        results["error_details"][model] = "Timeout"
    except Exception as e:
        print(f"  {FAIL} 失败 - {str(e)[:50]}")
        results["failed"].append(model)
        results["error_details"][model] = str(e)

# 统计结果
print("\n" + "=" * 80)
print("测试结果汇总")
print("=" * 80)
print(f"成功：{len(results['success'])} 个")
print(f"失败：{len(results['failed'])} 个")
print(f"成功率：{len(results['success'])/len(MODELS)*100:.1f}%")

print("\n" + "=" * 80)
print("成功的模型列表")
print("=" * 80)
for model in results["success"]:
    print(f"  {OK} {model}")

if results["failed"]:
    print("\n" + "=" * 80)
    print("失败的模型及错误信息")
    print("=" * 80)
    for model in results["failed"]:
        error = results["error_details"].get(model, "Unknown")
        print(f"  {FAIL} {model}: {error}")

# 保存结果到文件
with open("model_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到：model_test_results.json")
