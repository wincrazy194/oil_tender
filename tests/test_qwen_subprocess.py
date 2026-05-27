"""
测试本地 qwen CLI 是否可以在 subprocess 中调用
"""
import subprocess
import shutil
import os

print("=" * 60)
print("测试本地 qwen CLI")
print("=" * 60)

# 1. 查找 qwen 命令位置
print("\n[1] 查找 qwen 命令位置...")
qwen_path = shutil.which("qwen")
print(f"  shutil.which('qwen') = {qwen_path}")

# 2. 检查 npm 全局安装位置
print("\n[2] 检查 npm 全局安装...")
try:
    result = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=10)
    npm_global = result.stdout.strip()
    print(f"  npm 全局目录：{npm_global}")
    print(f"  qwen.cmd 路径：{npm_global}\\qwen\\bin\\qwen.cmd")
except Exception as e:
    print(f"  查询失败：{e}")

# 3. 尝试直接调用 qwen
print("\n[3] 尝试直接调用 qwen...")
try:
    result = subprocess.run(
        ["qwen", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"  返回码：{result.returncode}")
    print(f"  stdout: {result.stdout}")
    print(f"  stderr: {result.stderr}")
except FileNotFoundError:
    print("  FileNotFoundError: 找不到 qwen 命令")
except Exception as e:
    print(f"  错误：{e}")

# 4. 尝试使用 cmd /c 调用
print("\n[4] 尝试使用 cmd /c 调用...")
try:
    result = subprocess.run(
        "cmd /c qwen --version",
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"  返回码：{result.returncode}")
    print(f"  stdout: {result.stdout}")
    print(f"  stderr: {result.stderr}")
except Exception as e:
    print(f"  错误：{e}")

# 5. 尝试使用完整路径调用
print("\n[5] 尝试使用完整路径调用...")
try:
    appdata = os.environ.get('APPDATA', '')
    qwen_cmd = os.path.join(appdata, 'npm', 'qwen.cmd')
    print(f"  路径：{qwen_cmd}")
    if os.path.exists(qwen_cmd):
        result = subprocess.run(
            [qwen_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"  返回码：{result.returncode}")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
    else:
        print("  文件不存在")
except Exception as e:
    print(f"  错误：{e}")

# 6. 测试实际 prompt 调用
print("\n[6] 测试实际 prompt 调用...")
prompt = "你好，请回复'收到'两个字"

try:
    result = subprocess.run(
        ["qwen", prompt],
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"  返回码：{result.returncode}")
    print(f"  stdout: {result.stdout[:200] if result.stdout else '空'}")
    print(f"  stderr: {result.stderr[:200] if result.stderr else '空'}")
except FileNotFoundError:
    print("  FileNotFoundError: 找不到 qwen 命令")
except Exception as e:
    print(f"  错误：{e}")

print("\n" + "=" * 60)
