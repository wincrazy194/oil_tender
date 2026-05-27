"""
综合测试脚本 - 测试本地 qwen CLI 和 DashScope HTTP API
"""
import subprocess
import shutil
import requests
import time

# 配置
API_KEY = "sk-f374422e47de47ecb731a3e16e03a7eb"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

TEST_PROMPT = "你好，请只用'收到'两个字回复我，不要说其他内容。"

def test_cli():
    """测试本地 qwen CLI"""
    print("=" * 70)
    print("【测试 1】本地 qwen CLI")
    print("=" * 70)

    # 查找 qwen 路径
    qwen_path = shutil.which("qwen")
    print(f"\nqwen 路径：{qwen_path}")

    if not qwen_path:
        print("❌ 未找到 qwen 命令")
        return False

    print(f"\n测试 Prompt: {TEST_PROMPT}")
    print("\n正在调用 qwen CLI...")

    try:
        start_time = time.time()
        result = subprocess.run(
            f'cmd /c "{qwen_path} {TEST_PROMPT}"',
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        elapsed = time.time() - start_time

        print(f"\n返回码：{result.returncode}")
        print(f"耗时：{elapsed:.2f}秒")
        print(f"stdout: {result.stdout[:500] if result.stdout else '空'}")
        if result.stderr:
            print(f"stderr: {result.stderr[:200]}")

        if result.returncode == 0 and result.stdout.strip():
            print("\n[PASS] CLI 调用成功！")
            return True
        else:
            print("\n[FAIL] CLI 调用失败")
            return False

    except subprocess.TimeoutExpired:
        print("\n[FAIL] 调用超时（>120 秒）")
        return False
    except Exception as e:
        print(f"\n[FAIL] 调用异常：{e}")
        return False


def test_http_api():
    """测试 DashScope HTTP API"""
    print("\n" + "=" * 70)
    print("【测试 2】DashScope HTTP API (compatible-mode)")
    print("=" * 70)

    print(f"\nAPI Key: {API_KEY[:15]}...")
    print(f"Base URL: {BASE_URL}")
    print(f"测试 Prompt: {TEST_PROMPT}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-turbo",
        "messages": [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": TEST_PROMPT}
        ],
        "max_tokens": 20
    }

    print("\n正在调用 HTTP API...")

    try:
        start_time = time.time()
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
        elapsed = time.time() - start_time

        print(f"\n状态码：{resp.status_code}")
        print(f"耗时：{elapsed:.2f}秒")

        resp_data = resp.json()
        print(f"完整响应：{resp_data}")

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"]
            print(f"\n[PASS] HTTP API 调用成功！")
            print(f"AI 回复：{content}")
            return True
        else:
            print(f"\n[FAIL] HTTP API 调用失败")
            error_msg = resp_data.get('error', {}).get('message', resp_data)
            print(f"错误：{error_msg}")
            return False

    except requests.exceptions.Timeout:
        print("\n[FAIL] 请求超时（>30 秒）")
        return False
    except Exception as e:
        print(f"\n[FAIL] 请求异常：{e}")
        return False


def test_cli_with_long_prompt():
    """测试 CLI 处理长文本"""
    print("\n" + "=" * 70)
    print("【测试 3】CLI 处理长文本（模拟真实场景）")
    print("=" * 70)

    long_prompt = """请为以下招标公告生成一个 20-60 字的精炼摘要：

标题：长庆油田分公司第一采油厂 2026 年信息化办公设备维修服务项目

公告内容：
一、项目基本情况
1. 项目名称：长庆油田分公司第一采油厂 2026 年信息化办公设备维修服务项目
2. 项目编号：ZYY-2026-XM-001
3. 预算金额：人民币 150 万元
4. 最高限价：150 万元
5. 合同履行期限：自合同签订之日起至 2026 年 12 月 31 日
6. 本项目不接受联合体投标

二、申请人资格要求
1. 满足《中华人民共和国政府采购法》第二十二条规定
2. 具有独立的法人资格，持有有效的营业执照
3. 具有电子与智能化工程专业承包二级及以上资质
4. 本项目专门面向中小企业采购

三、获取招标文件
1. 时间：2026 年 3 月 25 日至 2026 年 4 月 5 日
2. 地点：中国石油招标投标网
3. 方式：网上下载

四、投标文件递交
1. 截止时间：2026 年 4 月 15 日 09 时 30 分
2. 地点：西安市未央区长庆油田分公司第一采油厂会议室

五、开标信息
1. 开标时间：2026 年 4 月 15 日 09 时 30 分
2. 开标地点：西安市未央区长庆油田分公司第一采油厂会议室

请用一句话概括，20-60 字以内，包含项目名称、预算金额、截止日期。"""

    qwen_path = shutil.which("qwen")
    if not qwen_path:
        print("❌ 未找到 qwen 命令，跳过测试")
        return False

    print(f"\n测试长文本 Prompt（{len(long_prompt)} 字）...")
    print("\n正在调用 qwen CLI...")

    try:
        start_time = time.time()
        result = subprocess.run(
            f'cmd /c "{qwen_path} """{long_prompt}""" "',
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        elapsed = time.time() - start_time

        print(f"\n返回码：{result.returncode}")
        print(f"耗时：{elapsed:.2f}秒")
        print(f"输出：{result.stdout[:500] if result.stdout else '空'}")

        if result.returncode == 0 and result.stdout.strip():
            print("\n[PASS] CLI 长文本测试成功！")
            return True
        else:
            print("\n[FAIL] CLI 长文本测试失败")
            return False

    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        return False


def test_http_with_long_prompt():
    """测试 HTTP API 处理长文本"""
    print("\n" + "=" * 70)
    print("【测试 4】HTTP API 处理长文本（模拟真实场景）")
    print("=" * 70)

    long_prompt = """请为以下招标公告生成一个 20-60 字的精炼摘要：

标题：长庆油田分公司第一采油厂 2026 年信息化办公设备维修服务项目

公告内容：
一、项目基本情况
1. 项目名称：长庆油田分公司第一采油厂 2026 年信息化办公设备维修服务项目
2. 项目编号：ZYY-2026-XM-001
3. 预算金额：人民币 150 万元
4. 最高限价：150 万元
5. 合同履行期限：自合同签订之日起至 2026 年 12 月 31 日
6. 本项目不接受联合体投标

二、申请人资格要求
1. 满足《中华人民共和国政府采购法》第二十二条规定
2. 具有独立的法人资格，持有有效的营业执照
3. 具有电子与智能化工程专业承包二级及以上资质
4. 本项目专门面向中小企业采购

三、获取招标文件
1. 时间：2026 年 3 月 25 日至 2026 年 4 月 5 日
2. 地点：中国石油招标投标网
3. 方式：网上下载

四、投标文件递交
1. 截止时间：2026 年 4 月 15 日 09 时 30 分
2. 地点：西安市未央区长庆油田分公司第一采油厂会议室

五、开标信息
1. 开标时间：2026 年 4 月 15 日 09 时 30 分
2. 开标地点：西安市未央区长庆油田分公司第一采油厂会议室

请用一句话概括，20-60 字以内，包含项目名称、预算金额、截止日期。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-turbo",
        "messages": [
            {"role": "system", "content": "你是一个专业的招投标信息分析助手。"},
            {"role": "user", "content": long_prompt}
        ],
        "max_tokens": 100
    }

    print(f"\n测试长文本 Prompt（{len(long_prompt)} 字）...")
    print("\n正在调用 HTTP API...")

    try:
        start_time = time.time()
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
        elapsed = time.time() - start_time

        print(f"\n状态码：{resp.status_code}")
        print(f"耗时：{elapsed:.2f}秒")

        resp_data = resp.json()

        if resp.status_code == 200 and resp_data.get("choices"):
            content = resp_data["choices"][0]["message"]["content"]
            print(f"\n[PASS] HTTP API 长文本测试成功！")
            print(f"AI 回复：{content}")
            return True
        else:
            print(f"\n[FAIL] HTTP API 长文本测试失败")
            return False

    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        return False


def main():
    print("#" * 70)
    print("#  Qwen AI 摘要功能综合测试")
    print("#" * 70)
    print()

    results = {
        "CLI 短文本": test_cli(),
        "HTTP 短文本": test_http_api(),
        # "CLI 长文本": test_cli_with_long_prompt(),
        # "HTTP 长文本": test_http_with_long_prompt(),
    }

    print("\n" + "=" * 70)
    print("【测试结果汇总】")
    print("=" * 70)

    for test_name, result in results.items():
        status = "[通过]" if result else "[失败]"
        print(f"  {test_name}: {status}")

    # 判断推荐方案
    print("\n" + "=" * 70)
    print("【推荐方案】")
    print("=" * 70)

    if results.get("CLI 短文本") and results.get("HTTP 短文本"):
        print("[OK] CLI 和 HTTP API 都可用")
        print("   建议：优先使用 CLI（免费），HTTP 作为备用")
    elif results.get("HTTP 短文本"):
        print("[OK] HTTP API 可用")
        print("   建议：使用 HTTP API 方式（需要 API Key）")
    elif results.get("CLI 短文本"):
        print("[OK] CLI 可用")
        print("   建议：使用 CLI 方式（免费，但速度较慢）")
    else:
        print("[FAIL] 两种方式都不可用")
        print("   建议：检查网络连接或重新配置 API Key")

    print()


if __name__ == "__main__":
    main()
