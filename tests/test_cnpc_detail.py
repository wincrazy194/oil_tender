"""
中石油详情 API 测试脚本
正确等待列表页加载并拦截 API 获取文章 ID
"""
import os
import time
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"


def check_captcha(page):
    """检测验证码弹窗"""
    selectors = ['.geetest_panel', '[class*="captcha"]', '.layui-layer-content']
    for sel in selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return True
        except:
            pass
    return False


def wait_for_captcha(page, timeout=300):
    """等待用户处理验证码"""
    print("\n" + "="*50)
    print("检测到验证码！请在浏览器中手动处理...")
    print("="*50 + "\n")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if not check_captcha(page):
            print("\n验证码已处理！\n")
            time.sleep(1)
            return True
    print(f"\n等待超时 ({timeout}秒)\n")
    return False


def fetch_cnpc_detail_via_api(page, item_id: str) -> dict:
    """获取中石油详情页内容（通过 API + RSA 解密方式）"""
    if not item_id:
        return {"content": "", "attachments": [], "debug": {}}

    try:
        page.set_default_timeout(60000)

        result = page.evaluate(f"""
        (async () => {{
            try {{
                const articleId = '{item_id}';
                const key = localStorage.getItem('logo2');

                const debug = {{
                    articleId,
                    keyExists: !!key,
                    keyLength: key ? key.length : 0
                }};

                if (!key) {{
                    return {{ error: '未找到私钥 (logo2)', debug }};
                }}

                const crypt = new JSEncrypt();
                crypt.setKey(key);
                const encryptedId = crypt.encryptLong(articleId);

                debug.encryptedIdExists = !!encryptedId;

                if (!encryptedId) {{
                    return {{ error: 'encryptLong 返回 null', debug }};
                }}

                const response = await fetch('https://www.cnpcbidding.com/cms/article/details', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/plain, */*'
                    }},
                    body: JSON.stringify(encryptedId)
                }});

                debug.responseStatus = response.status;

                if (!response.ok) {{
                    return {{ error: 'API 请求失败：' + response.status, debug }};
                }}

                const responseBody = await response.text();
                debug.responseBodyLength = responseBody.length;

                const decryptCrypt = new JSEncrypt();
                decryptCrypt.setKey(key);
                const decrypted = decryptCrypt.decryptLong(responseBody);

                debug.decryptedExists = !!decrypted;
                debug.decryptedLength = decrypted ? decrypted.length : 0;

                if (!decrypted) {{
                    return {{ error: 'decryptLong 返回 null', debug, responseBody: responseBody.substring(0, 200) }};
                }}

                const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join(''));

                const data = JSON.parse(decoded);
                return {{
                    success: true,
                    content: data.data?.content || data.content || '',
                    attachments: data.data?.attachments || [],
                    debug
                }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }})()
        """)
        return result
    except Exception as e:
        return {"content": "", "attachments": [], "error": str(e)}
    finally:
        page.set_default_timeout(30000)


def main():
    print("="*60)
    print("中石油详情 API 测试脚本")
    print("="*60)

    captured_articles = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # 设置 API 拦截器
        print("设置 API 拦截器...")
        def handle_response(response):
            try:
                if "/cms/publish/page" in response.url:
                    data = response.json()
                    items = data.get('data', [])
                    if items:
                        captured_articles.clear()
                        for item in items:
                            captured_articles.append({
                                'id': item.get('id', ''),
                                'title': item.get('title', '')[:80],
                                'publishedTime': item.get('publishedTime', '')
                            })
                        print(f"\n[API 拦截] 捕获到 {len(captured_articles)} 篇文章")
            except:
                pass

        page.on('response', handle_response)

        # 访问列表页
        print("正在访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        if check_captcha(page):
            wait_for_captcha(page)

        # **关键：等待 API 响应**
        print("等待文章列表 API 响应（最多 15 秒）...")
        for i in range(30):
            if captured_articles:
                print(f"  ✅ 捕获到文章列表！")
                break
            time.sleep(0.5)
            print(f"  等待中... ({i+1}/30)")

        if not captured_articles:
            print("\n未捕获到 API 响应，尝试从页面获取...")
            # 尝试从页面元素获取
            articles_el = page.query_selector_all('.tender-item, tr, .list-item')
            print(f"  找到 {len(articles_el)} 个列表项")

        # 显示捕获的文章
        if captured_articles:
            print("\n" + "="*60)
            print("【捕获的文章列表】")
            print("="*60)
            for i, art in enumerate(captured_articles[:5], 1):
                print(f"{i}. {art['title']}")
                print(f"   ID: {art['id']}")
                print(f"   时间：{art['publishedTime']}")
                print()

            # 测试第一篇
            test_article = next((a for a in captured_articles if a.get('id')), None)
            if test_article:
                print("="*60)
                print(f"【测试详情 API】")
                print(f"文章：{test_article['title']}")
                print(f"ID: {test_article['id']}")
                print("="*60)

                result = fetch_cnpc_detail_via_api(page, test_article['id'])

                print("\n【结果】")
                if result.get('success'):
                    print("✅ API 调用成功！")
                    content = result.get('content', '')
                    print(f"内容长度：{len(content)} 字")
                    print(f"\n内容预览 (前 200 字):")
                    print("-"*40)
                    print(content[:200] if content else "(空)")
                    print("-"*40)
                else:
                    print("❌ API 调用失败！")
                    print(f"错误：{result.get('error', '未知')}")

                    debug = result.get('debug', {})
                    if debug:
                        print("\n【调试信息】")
                        print(f"  私钥存在：{debug.get('keyExists', False)}")
                        print(f"  私钥长度：{debug.get('keyLength', 0)}")
                        print(f"  加密成功：{debug.get('encryptedIdExists', 'N/A')}")
                        print(f"  API 状态：{debug.get('responseStatus', 'N/A')}")
                        print(f"  响应长度：{debug.get('responseBodyLength', 'N/A')}")
                        print(f"  解密成功：{debug.get('decryptedExists', 'N/A')}")
                        print(f"  解密长度：{debug.get('decryptedLength', 'N/A')}")

                    if result.get('responseBody'):
                        print(f"\n响应体预览：{result['responseBody'][:200]}")

                input("\n按回车退出...")
            else:
                print("没有找到有效的文章 ID")
                input("\n按回车退出...")
        else:
            print("未获取到任何文章列表")
            input("\n按回车退出...")

        browser.close()


if __name__ == "__main__":
    main()
