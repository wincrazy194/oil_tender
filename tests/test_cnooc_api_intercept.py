"""
测试中海油 API 拦截
"""
from playwright.sync_api import sync_playwright
import time

def test_api_intercept():
    playwright = sync_playwright().start()

    # 使用临时目录避免缓存问题
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="playwright_test_")

    articles = []

    def handle_response(response):
        try:
            url = response.url
            if any(keyword in url for keyword in ['news', 'alert', 'list', 'api']):
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    print(f"\n[拦截] URL: {url[:150]}")
                    try:
                        data = response.json()
                        print(f"[拦截] 响应前 200 字符：{str(data)[:200]}...")

                        # 递归查找数组
                        def extract(obj, depth=0):
                            if depth > 5:
                                return
                            if isinstance(obj, list) and len(obj) > 0:
                                for item in obj:
                                    if isinstance(item, dict):
                                        article_id = item.get('articleId') or item.get('id') or item.get('newsId')
                                        title = item.get('title') or item.get('newsTitle')
                                        if article_id and title:
                                            exists = any(a['id'] == article_id for a in articles)
                                            if not exists:
                                                articles.append({
                                                    'id': article_id,
                                                    'title': title[:50],
                                                    'publishDate': item.get('publishDate') or item.get('createTime') or ''
                                                })
                                                print(f"  -> 新增：{title[:30]}...")
                            elif isinstance(obj, dict):
                                for v in obj.values():
                                    extract(v, depth + 1)

                        extract(data)
                        print(f"[拦截] 当前累计：{len(articles)} 条")
                    except Exception as e:
                        print(f"[拦截] JSON 解析失败：{e}")
        except Exception as e:
            print(f"[拦截] 错误：{e}")

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
    print("页面加载完成，等待 5 秒...")
    time.sleep(5)

    print(f"\n=== 最终结果 ===")
    print(f"拦截到 {len(articles)} 条数据")
    for i, a in enumerate(articles[:10]):
        print(f"  {i+1}. [{a['publishDate']}] {a['title']}...")

    context.close()
    playwright.stop()
    print("\n测试完成")

if __name__ == "__main__":
    test_api_intercept()
