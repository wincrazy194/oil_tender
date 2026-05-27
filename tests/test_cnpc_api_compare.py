"""
中石油详情 API 深度测试
对比网站原始请求和手动构造的请求
"""
import os
import time
import json
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"


def check_captcha(page):
    selectors = ['.geetest_panel', '[class*="captcha"]', '.layui-layer-content']
    for sel in selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return True
        except:
            pass
    return False


def wait_for_captcha(page, timeout=300):
    print("\n检测到验证码！请手动处理...\n")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if not check_captcha(page):
            print("\n验证码已处理！\n")
            time.sleep(1)
            return True
    print(f"\n等待超时\n")
    return False


def main():
    print("="*60)
    print("中石油详情 API 深度测试")
    print("="*60)

    captured_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # 拦截详情 API 请求和响应
        print("设置 API 拦截器...")

        def handle_request(request):
            if 'cms/article/details' in request.url:
                print(f"\n[请求] POST /cms/article/details")
                try:
                    post_data = request.post_data
                    print(f"  请求体长度：{len(post_data) if post_data else 0}")
                    print(f"  请求体预览：{post_data[:200] if post_data else 'N/A'}")
                    print(f"  请求头:")
                    for key, value in request.headers.items():
                        if key.lower() not in ['cookie', 'authorization']:
                            print(f"    {key}: {value[:100]}...")
                except:
                    pass

        def handle_response(response):
            if 'cms/article/details' in response.url:
                print(f"\n[响应] POST /cms/article/details")
                try:
                    text = response.text()
                    print(f"  响应长度：{len(text)}")
                    print(f"  响应状态：{response.status}")
                    print(f"  响应预览：{text[:200]}")

                    captured_requests.append({
                        'status': response.status,
                        'response': text,
                        'length': len(text)
                    })
                except Exception as e:
                    print(f"  读取响应失败：{e}")

        page.on('request', handle_request)
        page.on('response', handle_response)

        # 访问列表页
        print("\n访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        if check_captcha(page):
            wait_for_captcha(page)

        # 等待数据加载
        print("\n等待列表数据加载...")
        for i in range(5, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)
        print("  完成！\n")

        # 获取第一个文章 ID（从列表 API 拦截中获取）
        print("获取文章列表...")
        list_api_result = page.evaluate("""
        () => {
            // 尝试从页面获取文章 ID
            const boxDataElements = document.querySelectorAll('.box_data');
            const items = [];

            // 由于 DOM 中没有 ID，我们尝试从 Vue 组件获取
            // 或者直接返回列表数量
            return {
                count: boxDataElements.length,
                hasVue: !!window.__vue_app__
            };
        }
        """)
        print(f"  列表项数量：{list_api_result.get('count', 0)}")

        # 模拟点击第一个列表项
        print("\n点击第一个列表项触发详情 API...")
        first_item = page.query_selector('.box_data')
        if first_item:
            first_item.click()
            time.sleep(3)

            # 检查响应
            if captured_requests:
                print("\n" + "="*60)
                print("【API 响应分析】")
                print("="*60)

                for i, req in enumerate(captured_requests):
                    print(f"\n响应 {i+1}:")
                    print(f"  状态码：{req['status']}")
                    print(f"  响应长度：{req['length']}")

                    # 尝试解密
                    response_text = req['response']
                    print(f"  响应预览：{response_text[:100]}...")

                    # 检查是否是加密数据
                    is_encrypted = not response_text.startswith('{') and not response_text.startswith('[')
                    print(f"  是否加密：{is_encrypted}")

                    # 尝试在浏览器中解密
                    decrypt_result = page.evaluate(f"""
                    () => {{
                        try {{
                            const key = localStorage.getItem('logo2');
                            if (!key) {{
                                return {{ error: '未找到 logo2' }};
                            }}

                            const encryptedText = `{response_text[:1000]}`;

                            const crypt = new JSEncrypt();
                            crypt.setKey(key);
                            const decrypted = crypt.decryptLong(encryptedText);

                            if (!decrypted) {{
                                return {{ error: 'decryptLong 返回 null' }};
                            }}

                            // 解码
                            try {{
                                const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                                ).join(''));
                                return {{ success: true, decrypted: decoded.substring(0, 500) }};
                            }} catch (e) {{
                                return {{ error: 'decode failed: ' + e.message }};
                            }}
                        }} catch (e) {{
                            return {{ error: e.message }};
                        }}
                    }}
                    """)

                    if decrypt_result.get('success'):
                        print(f"\n  ✅ 解密成功！")
                        print(f"  解密内容：{decrypt_result['decrypted'][:300]}...")
                    else:
                        print(f"\n  解密失败：{decrypt_result.get('error', '未知')}")

            # 检查页面是否显示详情内容
            content_check = page.evaluate("""
            () => {
                // 检查是否有详情内容
                const contentSelectors = ['.content', '.article-body', '.zwgk-content', '.detail-content', '[class*="detail"]', '[class*="article"]'];

                for (const sel of contentSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText && el.innerText.length > 500) {
                        return {
                            found: true,
                            selector: sel,
                            length: el.innerText.length,
                            preview: el.innerText.substring(0, 200)
                        };
                    }
                }

                // 检查所有 div
                const allDivs = document.querySelectorAll('div');
                for (const div of allDivs) {
                    const text = div.innerText;
                    if (text && text.length > 500 && !text.includes('招标公告')) {
                        return {
                            found: true,
                            selector: `div.${div.className.split(' ')[0]}`,
                            length: text.length,
                            preview: text.substring(0, 200)
                        };
                    }
                }

                return { found: false };
            }
            """)

            print("\n" + "="*60)
            print("【页面内容检测】")
            print("="*60)
            if content_check.get('found'):
                print(f"✅ 找到详情内容！")
                print(f"  选择器：{content_check.get('selector', 'N/A')}")
                print(f"  内容长度：{content_check.get('length', 0)}")
                print(f"  内容预览：{content_check.get('preview', '')[:100]}...")
            else:
                print("❌ 未找到详情内容")

        else:
            print("未找到列表项")

        print("\n" + "="*60)
        input("\n按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()
