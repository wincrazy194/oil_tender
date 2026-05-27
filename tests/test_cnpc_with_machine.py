"""
中石油详情 API 测试 - 添加 machine_code 请求头
"""
import os
import time
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
    print("中石油详情 API 测试 - 添加 machine_code")
    print("="*60)

    captured_responses = []

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
        print("\n等待列表数据加载...")
        for i in range(5, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)
        print("  完成！\n")

        # 获取 machine_code（从 localStorage 或其他地方）
        machine_code = page.evaluate("localStorage.getItem('machine_code')")
        print(f"machine_code: {machine_code}")

        # 获取第一个文章 ID
        article_id = page.evaluate("""
        () => {
            // 尝试从全局变量或 Vue 组件获取文章 ID
            // 或者从 URL 参数获取
            const url = new URL(window.location.href);
            return url.searchParams.get('id') || '';
        }
        """)

        if not article_id:
            # 从列表 API 响应中获取（需要之前拦截过）
            print("从页面获取文章 ID...")
            # 简单测试，使用已知 ID
            article_id = "335291"  # 之前测试成功的 ID

        print(f"使用文章 ID: {article_id}")

        # 测试详情 API
        print("\n测试详情 API（添加 machine_code）...")

        result = page.evaluate(f"""
        (async () => {{
            try {{
                const articleId = '{article_id}';
                const key = localStorage.getItem('logo2');
                const machineCode = localStorage.getItem('machine_code') || '';

                const debug = {{
                    keyExists: !!key,
                    keyLength: key ? key.length : 0,
                    machineCodeExists: !!machineCode,
                    machineCodeLength: machineCode ? machineCode.length : 0,
                    articleId
                }};

                if (!key) {{
                    return {{ error: '未找到 logo2', debug }};
                }}

                const crypt = new JSEncrypt();
                crypt.setKey(key);
                const encrypted = crypt.encryptLong(articleId);

                debug.encryptedExists = !!encrypted;
                debug.encryptedPreview = encrypted ? encrypted.substring(0, 50) : null;

                if (!encrypted) {{
                    return {{ error: 'encryptLong 失败', debug }};
                }}

                // 添加 machine_code 请求头
                const headers = {{
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*'
                }};

                if (machineCode) {{
                    headers['machine_code'] = machineCode;
                }}

                const resp = await fetch('https://www.cnpcbidding.com/cms/article/details', {{
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(encrypted)
                }});

                debug.status = resp.status;
                debug.ok = resp.ok;

                const text = await resp.text();
                debug.responseLength = text.length;
                debug.responsePreview = text.substring(0, 100);

                // 尝试解密
                const decryptCrypt = new JSEncrypt();
                decryptCrypt.setKey(key);
                const decrypted = decryptCrypt.decryptLong(text);

                debug.decryptedExists = !!decrypted;
                debug.decryptedLength = decrypted ? decrypted.length : 0;

                if (decrypted) {{
                    try {{
                        const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                            '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                        ).join(''));
                        const parsed = JSON.parse(decoded);
                        debug.finalData = JSON.stringify(parsed).substring(0, 300);
                        debug.hasContent = !!(parsed.data?.content || parsed.content);
                    }} catch (e) {{
                        debug.decodeError = e.message;
                    }}
                }}

                return {{ success: true, debug }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }})()
        """)

        print("\n" + "="*60)
        print("【API 测试结果】")
        print("="*60)

        debug = result.get('debug', {})
        print(f"文章 ID: {debug.get('articleId', 'N/A')}")
        print(f"私钥存在：{debug.get('keyExists', False)}")
        print(f"私钥长度：{debug.get('keyLength', 0)}")
        print(f"machine_code 存在：{debug.get('machineCodeExists', False)}")
        print(f"machine_code 长度：{debug.get('machineCodeLength', 0)}")
        print(f"加密成功：{debug.get('encryptedExists', 'N/A')}")
        print(f"加密预览：{debug.get('encryptedPreview', 'N/A')}")
        print(f"API 状态：{debug.get('status', 'N/A')}")
        print(f"API 正常：{debug.get('ok', False)}")
        print(f"响应长度：{debug.get('responseLength', 'N/A')}")
        print(f"响应预览：{debug.get('responsePreview', 'N/A')}")
        print(f"解密成功：{debug.get('decryptedExists', 'N/A')}")
        print(f"解密长度：{debug.get('decryptedLength', 'N/A')}")

        if debug.get('finalData'):
            print(f"\n✅ 解密成功！")
            print(f"有内容数据：{debug.get('hasContent', False)}")
            print(f"数据预览：{debug['finalData'][:200]}...")
        if debug.get('decodeError'):
            print(f"\n解码错误：{debug['decodeError']}")
        if result.get('error'):
            print(f"\n错误：{result['error']}")

        print("\n" + "="*60)
        input("\n按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()
