"""
测试中海油所有 JSON 响应
"""
from playwright.sync_api import sync_playwright
import time

def test_all_json():
    playwright = sync_playwright().start()

    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="playwright_test_")

    responses = []

    def handle_response(response):
        try:
            url = response.url
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                responses.append({
                    'url': url,
                    'content_type': content_type
                })
                print(f"\n[JSON 响应] URL: {url}")
                print(f"Content-Type: {content_type}")
                try:
                    data = response.json()
                    print(f"数据前 300 字符：{str(data)[:300]}...")
                except Exception as e:
                    print(f"JSON 解析失败：{e}")
        except Exception as e:
            print(f"错误：{e}")

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=temp_dir,
        channel="msedge",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    context.on("response", handle_response)

    page = context.pages[0] if context.pages else context.new_page()

    base_url = "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD"
    print(f"访问：{base_url}")

    page.goto(base_url, wait_until="networkidle", timeout=60000)
    print("\n页面加载完成，等待 5 秒...")
    time.sleep(5)

    print(f"\n=== 最终结果 ===")
    print(f"捕获到 {len(responses)} 个 JSON 响应")

    context.close()
    playwright.stop()
    print("\n测试完成")

if __name__ == "__main__":
    test_all_json()
