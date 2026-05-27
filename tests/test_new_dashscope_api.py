"""
测试新的 DashScope API Key（compatible-mode）
"""
import requests

API_KEY = "sk-f374422e47de47ecb731a3e16e03a7eb"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen-turbo",
    "messages": [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "你好，请回复'收到'两个字"}
    ],
    "max_tokens": 20
}

print("正在测试 API Key...")
print(f"API Key: {API_KEY[:15]}...")
print(f"URL: {BASE_URL}")
print()

try:
    resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
    print(f"状态码：{resp.status_code}")

    resp_data = resp.json()
    print(f"响应：{resp_data}")

    if resp.status_code == 200 and resp_data.get("choices"):
        content = resp_data["choices"][0]["message"]["content"]
        print(f"\n✅ API Key 有效！")
        print(f"AI 回复：{content}")
    else:
        print(f"\n❌ 请求失败")
        print(f"错误：{resp_data.get('error', {}).get('message', resp_data)}")

except Exception as e:
    print(f"\n❌ 请求异常：{e}")
