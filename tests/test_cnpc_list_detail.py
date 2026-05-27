"""
中石油列表页详情数据测试
检查列表页是否已经包含详情数据（JS 动态渲染）
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
    print("\n" + "="*60)
    print("检测到验证码！请在浏览器中手动处理...")
    print(f"最长等待时间：{timeout}秒")
    print("="*60 + "\n")

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
    print("中石油列表页详情数据测试")
    print("="*60)
    print("\n测试目的：检查列表页是否已经包含详情数据")
    print("="*60 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # 访问列表页
        print("访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        if check_captcha(page):
            wait_for_captcha(page)

        # 等待数据加载
        print("\n等待数据加载...")
        for i in range(10, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)
        print("  完成！\n")

        # 检查列表页的数据
        print("="*60)
        print("【检查列表页数据】")
        print("="*60)

        result = page.evaluate(r"""
        () => {
            const info = {
                pageTitle: document.title,
                pageUrl: window.location.href,
                localStorageKeys: Object.keys(localStorage).length
            };

            // 检查是否有全局数据对象
            const globalKeys = ['__vue_app__', '__NUXT__', 'axios', 'Vue'];
            globalKeys.forEach(key => {
                if (window[key]) {
                    info[key + 'Exists'] = true;
                }
            });

            // 检查 .box_data 元素
            const boxDataElements = document.querySelectorAll('.box_data');
            info.boxDataCount = boxDataElements.length;

            // 检查每个 box_data 的详细信息
            info.boxDataDetails = [];
            boxDataElements.forEach((el, index) => {
                if (index >= 5) return;

                const item = {
                    index: index,
                    text: (el.innerText || '').replace(/\s+/g, ' ').substring(0, 150),
                    attributes: {},
                    dataAttrs: {}
                };

                // 获取 data-* 属性
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-')) {
                        item.dataAttrs[attr.name] = attr.value;
                    }
                }

                // 检查是否有点击事件
                item.onclick = !!el.onclick;
                item.cursor = el.style.cursor || 'default';

                info.boxDataDetails.push(item);
            });

            // 检查页面中的脚本数据
            const scripts = document.querySelectorAll('script[type="application/json"]');
            info.jsonScripts = scripts.length;

            // 尝试查找隐藏的详情数据
            const hiddenData = document.querySelectorAll('[style*="display:none"], [style*="visibility:hidden"]');
            info.hiddenElements = hiddenData.length;

            // 检查所有包含"content"、"detail"、"body"等关键词的元素
            const contentKeywords = ['content', 'detail', 'body', 'description', '摘要', '正文'];
            const contentElements = [];
            document.querySelectorAll('*').forEach(el => {
                const tagName = el.tagName.toLowerCase();
                const className = String(el.className || '').toLowerCase();
                const id = String(el.id || '').toLowerCase();

                for (const kw of contentKeywords) {
                    if (className.includes(kw) || id.includes(kw) || tagName.includes(kw)) {
                        if (el.innerText && el.innerText.length > 50) {
                            contentElements.push({
                                tag: tagName,
                                class: el.className,
                                textLength: el.innerText.length,
                                textPreview: el.innerText.substring(0, 100)
                            });
                            break;
                        }
                    }
                }
            });
            info.contentElements = contentElements.slice(0, 10);

            // 检查是否有详情数据存储在 window 对象中
            const windowDataKeys = ['detailData', 'articleData', 'pageData', 'listData'];
            windowDataKeys.forEach(key => {
                if (window[key]) {
                    info[key] = JSON.stringify(window[key]).substring(0, 200);
                }
            });

            return info;
        }
        """)

        print(f"\n页面标题：{result.get('pageTitle', 'N/A')}")
        print(f"页面 URL: {result.get('pageUrl', 'N/A')}")
        print(f"localStorage 键数量：{result.get('localStorageKeys', 0)}")

        print(f"\n.box_data 元素数量：{result.get('boxDataCount', 0)}")

        box_details = result.get('boxDataDetails', [])
        if box_details:
            print("\n列表项详情:")
            for item in box_details:
                print(f"\n  [{item.get('index', 0)+1}] {item.get('text', '')[:100]}")
                if item.get('dataAttrs'):
                    print(f"      data-* 属性：{item.get('dataAttrs')}")
                print(f"      cursor: {item.get('cursor', 'default')}, onclick: {item.get('onclick', False)}")

        print(f"\nJSON 脚本数量：{result.get('jsonScripts', 0)}")
        print(f"隐藏元素数量：{result.get('hiddenElements', 0)}")

        content_els = result.get('contentElements', [])
        if content_els:
            print(f"\n包含内容关键词的元素 ({len(content_els)} 个):")
            for el in content_els[:5]:
                print(f"  - <{el.get('tag', '')}> class={el.get('class', '')[:50]}")
                print(f"    文本长度：{el.get('textLength', 0)}, 预览：{el.get('textPreview', '')[:60]}...")

        # 检查 window 对象中的数据
        for key in ['detailData', 'articleData', 'pageData', 'listData']:
            if result.get(key):
                print(f"\nwindow.{key}: {result[key][:200]}...")

        print("\n" + "="*60)

        # 尝试拦截网络请求获取详情数据
        print("\n【网络请求分析】")
        print("正在监听网络请求...")

        captured_requests = []

        def handle_request(request):
            url = request.url
            if 'cms' in url and ('detail' in url or 'article' in url):
                captured_requests.append({
                    'url': url,
                    'method': request.method
                })

        page.on('request', handle_request)

        # 模拟点击第一个列表项
        print("\n模拟点击第一个列表项...")
        first_item = page.query_selector('.box_data')
        if first_item:
            print("  点击列表项...")
            first_item.click()
            time.sleep(3)

            print("\n等待详情数据加载...")
            for i in range(5, 0, -1):
                print(f"  {i}...", end='\r')
                time.sleep(1)
            print("  完成！\n")

            # 检查捕获的请求
            print(f"捕获到 {len(captured_requests)} 个相关请求:")
            for req in captured_requests:
                print(f"  - {req['method']} {req['url'][:100]}")

            # 检查点击后的页面状态
            after_click = page.evaluate("""
            () => {
                const info = {
                    newUrl: window.location.href,
                    newTitle: document.title,
                    boxDataCount: document.querySelectorAll('.box_data').length
                };

                // 检查是否有详情内容出现
                const contentSelectors = ['.content', '.detail', '.article-body', '.main-content'];
                for (const sel of contentSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText && el.innerText.length > 100) {
                        info.hasContent = true;
                        info.contentLength = el.innerText.length;
                        info.contentPreview = el.innerText.substring(0, 200);
                        break;
                    }
                }

                return info;
            }
            """)

            print(f"\n点击后状态:")
            print(f"  新 URL: {after_click.get('newUrl', 'N/A')}")
            print(f"  新标题：{after_click.get('newTitle', 'N/A')}")
            print(f"  .box_data 数量：{after_click.get('boxDataCount', 0)}")
            print(f"  找到详情内容：{after_click.get('hasContent', False)}")
            if after_click.get('hasContent'):
                print(f"  内容长度：{after_click.get('contentLength', 0)}")
                print(f"  内容预览：{after_click.get('contentPreview', '')[:100]}...")
        else:
            print("  未找到列表项")

        print("\n" + "="*60)
        input("\n按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()
