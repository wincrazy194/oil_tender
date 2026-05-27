"""
测试阿里云 DashScope API Key 是否有效
"""
import requests

# 您的 API Key
API_KEY = "sk-sp-b80f91e7823e4c04aa3b53cb8ef87315"

# DashScope API
url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
payload = {
    "model": "qwen-turbo",  # 使用基础模型测试
    "input": {
        "messages": [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "你好，请回复'收到'"}
        ]
    },
    "parameters": {
        "max_tokens": 20
    }
}

print("正在测试 API Key...")
print(f"API Key: {API_KEY[:15]}...")
print()

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"状态码：{resp.status_code}")
    print(f"响应头：{dict(resp.headers)}")
    print()

    resp_data = resp.json()
    print(f"响应内容：{resp_data}")

    if resp.status_code == 200 and resp_data.get("output"):
        print("\n✅ API Key 有效！")
        print(f"AI 回复：{resp_data['output'].get('text', '')}")
    else:
        print("\n❌ API Key 无效或请求失败")
        print(f"错误信息：{resp_data.get('message', resp_data.get('output', ''))}")

except Exception as e:
    print(f"\n❌ 请求失败：{e}")
