"""
测试使用 subprocess 调用 qwen 命令
"""
import subprocess
import time

prompt = """请为以下招标公告生成一个 20-60 字的精炼摘要：

标题：长庆油田分公司第一采油厂 2026 年信息化办公设备安装项目

公告内容：
本项目计划采购办公电脑 50 台，打印机 10 台，网络设备等。
预算金额：150 万元
截止日期：2026 年 4 月 15 日

请用一句话概括，20-60 字以内。"""

print("正在调用 qwen 命令...")
print(f"Prompt: {prompt[:100]}...")
print()

try:
    result = subprocess.run(
        ["qwen", prompt],
        capture_output=True,
        text=True,
        timeout=120,
        encoding="utf-8"
    )

    print(f"返回码：{result.returncode}")
    print(f"stdout: {result.stdout}")
    print(f"stderr: {result.stderr}")

    if result.returncode == 0 and result.stdout.strip():
        print("\n✅ 调用成功！")
        print(f"AI 回复：{result.stdout.strip()}")
    else:
        print("\n❌ 调用失败")

except subprocess.TimeoutExpired:
    print("\n❌ 超时")
except FileNotFoundError:
    print("\n❌ 未找到 qwen 命令")
except Exception as e:
    print(f"\n❌ 错误：{e}")
