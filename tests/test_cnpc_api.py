"""
中石油 API 拦截测试 - 修复版
正确拦截 /cms/article/page API
"""
import os
import time
import json
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"


def check_captcha(page):
    """检测是否有验证码弹窗"""
    selectors = ['.geetest_panel', '[class*="captcha"]', '.layui-layer-content',
                 'iframe[src*="captcha"]', 'iframe[src*="geetest"]', '[id*="captcha"]']
    for sel in selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return True
        except:
            pass
    return False


def wait_for_captcha(page, timeout=300):
    """等待用户处理验证码"""
    print("\n" + "="*60)
    print("检测到验证码！请在浏览器中手动处理...")
    print(f"最长等待时间：{timeout}秒")
    print("="*60 + "\n")

    start = time.time()
    last_check = True
    while time.time() - start < timeout:
        time.sleep(2)
        is_captcha = check_captcha(page)

        # 验证码消失后，再等 1 秒确认
        if not is_captcha and not last_check:
            print("\n验证码已处理！等待 1 秒确认...\n")
            time.sleep(1)
            return True
        elif is_captcha:
            # 显示倒计时
            elapsed = int(time.time() - start)
            remaining = timeout - elapsed
            if remaining > 0 and remaining % 30 == 0:
                print(f"  已等待 {elapsed}秒，还剩{remaining}秒...")

        last_check = is_captcha

    print(f"\n等待超时 ({timeout}秒)，继续执行...\n")
    return False


def main():
    print("="*60)
    print("中石油 API 拦截测试 - 修复版")
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

        print("设置 API 拦截器...")

        def handle_response(response):
            try:
                url = response.url
                # 拦截所有 CMS API
                if 'cms' in url:
                    print(f"\n[API 拦截] {url}")
                    try:
                        text = response.text()
                        print(f"  响应长度：{len(text)} 字符")
                        print(f"  响应预览：{text[:150]}...")

                        # 尝试解析 JSON
                        try:
                            data = json.loads(text)
                            captured_responses.append({
                                'url': url,
                                'data': data,
                                'text': text
                            })
                            # 检查是否是文章数据（不是图片）
                            if isinstance(data, dict):
                                data_str = str(data.get('data', ''))
                                if not data_str.startswith('iVBOR') and not data_str.startswith('/9j/'):
                                    print(f"  ✅ JSON 解析成功 - 可能是文章数据")
                                else:
                                    print(f"  JSON 解析成功 - 可能是图片/验证码")
                            else:
                                print(f"  ✅ JSON 解析成功")
                        except json.JSONDecodeError:
                            print(f"  JSON 解析失败")
                            captured_responses.append({
                                'url': url,
                                'data': {'raw': text[:500]},
                                'text': text
                            })
                    except Exception as e:
                        print(f"  读取响应失败：{e}")
            except Exception as e:
                pass

        page.on('response', handle_response)

        print("\n访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        # 检测并等待处理验证码
        if check_captcha(page):
            wait_for_captcha(page, timeout=300)

        # 额外等待时间，确保页面数据加载完成
        print("\n等待页面数据加载...")
        for i in range(5, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)
        print("  完成！\n")

        # 再次检测验证码（可能在页面加载后出现）
        if check_captcha(page):
            wait_for_captcha(page, timeout=300)

        print("\n等待 API 响应（最多 15 秒）...")
        for i in range(30):
            if captured_responses:
                print(f"  ✅ 捕获到 API 响应！")
                break
            time.sleep(0.5)
            print(f"  等待中... ({i+1}/30)")

        print("\n" + "="*60)
        print("【API 拦截结果】")
        print("="*60)

        if captured_responses:
            for resp in captured_responses:
                print(f"\nURL: {resp['url']}")
                data = resp.get('data', {})
                text = resp.get('text', '')

                # 检查是否是加密响应（字符串）
                if isinstance(data, str):
                    print(f"响应是加密字符串 (前 100 字):")
                    print(f"  {data[:100]}...")
                    print(f"  总长度：{len(data)} 字符")
                    print(f"\n尝试解密...")

                    # 在浏览器中解密 - 使用完整的 text
                    decrypt_result = page.evaluate(f"""
                    () => {{
                        try {{
                            const key = localStorage.getItem('logo2');
                            if (!key) {{
                                return {{ error: '未找到 logo2' }};
                            }}

                            const encryptedText = `{text}`;

                            const crypt = new JSEncrypt();
                            crypt.setKey(key);
                            const decrypted = crypt.decryptLong(encryptedText);

                            if (!decrypted) {{
                                return {{ error: 'decryptLong 返回 null' }};
                            }}

                            // 解码
                            const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                                '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                            ).join(''));

                            return {{ success: true, decrypted: decoded }};
                        }} catch (e) {{
                            return {{ error: e.message }};
                        }}
                    }}
                    """)

                    if decrypt_result.get('success'):
                        print(f"\n✅ 解密成功！")
                        print(f"解密内容：{decrypt_result['decrypted'][:500]}...")
                        try:
                            parsed = json.loads(decrypt_result['decrypted'])
                            print(f"\n解密后数据结构:")
                            print(f"  顶层键：{list(parsed.keys()) if isinstance(parsed, dict) else '不是字典'}")

                            # 尝试不同路径获取列表
                            items = None
                            for key in ['data', 'list', 'items', 'records', 'result']:
                                if key in parsed:
                                    val = parsed[key]
                                    if isinstance(val, (list, dict)):
                                        items = val
                                        print(f"  从 '{key}' 获取到数据，类型：{type(val)}")
                                        break

                            if items:
                                # 如果是字典，尝试获取列表
                                if isinstance(items, dict):
                                    for key in ['list', 'items', 'records', 'data']:
                                        if key in items and isinstance(items[key], list):
                                            items = items[key]
                                            break

                                if isinstance(items, list):
                                    print(f"\n找到 {len(items)} 条文章:")
                                    for i, item in enumerate(items[:10], 1):
                                        if isinstance(item, dict):
                                            item_id = item.get('id', 'N/A')
                                            title = item.get('title', 'N/A')[:60] if isinstance(item.get('title'), str) else str(item.get('title', 'N/A'))[:60]
                                            print(f"  {i}. ID={item_id} | {title}")
                                        else:
                                            print(f"  {i}. {str(item)[:80]}")

                                    # 测试第一篇的详情 API
                                    first_item = next((i for i in items if isinstance(i, dict) and i.get('id')), None)
                                    if first_item:
                                        test_id = str(first_item.get('id'))
                                        print(f"\n" + "="*60)
                                        print(f"【测试详情 API】")
                                        print(f"使用 ID: {test_id}")
                                        print("="*60)

                                        # 测试详情 API 前检测验证码
                                        if check_captcha(page):
                                            wait_for_captcha(page, timeout=300)

                                        # 先访问详情页 URL 建立会话（不等待加载完成）
                                        print(f"\n先访问详情页建立会话...")
                                        detail_url = f"https://www.cnpcbidding.com/#/tenders/detail?id={test_id}"
                                        page.goto(detail_url, wait_until="domcontentloaded", timeout=10000)
                                        time.sleep(2)

                                        # 再次检测验证码
                                        if check_captcha(page):
                                            wait_for_captcha(page, timeout=300)

                                        print("开始调用详情 API...\n")

                                        detail_result = page.evaluate(f"""
                                        (async () => {{
                                            try {{
                                                const articleId = '{test_id}';
                                                const key = localStorage.getItem('logo2');

                                                const debug = {{
                                                    keyExists: !!key,
                                                    keyLength: key ? key.length : 0,
                                                    articleId: articleId
                                                }};

                                                if (!key) {{
                                                    return {{ error: '未找到 logo2', debug }};
                                                }}

                                                const crypt = new JSEncrypt();
                                                crypt.setKey(key);
                                                const encrypted = crypt.encryptLong(articleId);

                                                debug.encryptedExists = !!encrypted;
                                                debug.encryptedType = typeof encrypted;
                                                debug.encryptedPreview = encrypted ?
                                                    (typeof encrypted === 'string' ? encrypted.substring(0, 50) : 'not a string')
                                                    : null;

                                                if (!encrypted) {{
                                                    return {{ error: 'encryptLong 失败', debug }};
                                                }}

                                                // 尝试不同的请求体格式
                                                const resp = await fetch('https://www.cnpcbidding.com/cms/article/details', {{
                                                    method: 'POST',
                                                    headers: {{
                                                        'Content-Type': 'application/json',
                                                        'Accept': 'application/json, text/plain, */*'
                                                    }},
                                                    body: JSON.stringify(encrypted)
                                                }});

                                                debug.status = resp.status;
                                                debug.ok = resp.ok;

                                                const text = await resp.text();
                                                debug.responsePreview = text;
                                                debug.responseLength = text.length;

                                                // 检查响应是否是错误信息
                                                if (text.length < 100 && !text.startsWith('"')) {{
                                                    debug.isError = true;
                                                }}

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

                                        print(f"\n【详情 API 调试信息】")
                                        debug = detail_result.get('debug', {})
                                        print(f"  文章 ID: {debug.get('articleId', 'N/A')}")
                                        print(f"  私钥存在：{debug.get('keyExists', False)}")
                                        print(f"  私钥长度：{debug.get('keyLength', 0)}")
                                        print(f"  加密成功：{debug.get('encryptedExists', 'N/A')}")
                                        print(f"  加密数据类型：{debug.get('encryptedType', 'N/A')}")
                                        print(f"  加密数据预览：{debug.get('encryptedPreview', 'N/A')}")
                                        print(f"  API 状态：{debug.get('status', 'N/A')}")
                                        print(f"  API 正常：{debug.get('ok', False)}")
                                        print(f"  响应长度：{debug.get('responseLength', 'N/A')}")
                                        print(f"  响应预览：{debug.get('responsePreview', 'N/A')}")
                                        print(f"  是错误响应：{debug.get('isError', False)}")
                                        print(f"  解密成功：{debug.get('decryptedExists', 'N/A')}")
                                        print(f"  解密长度：{debug.get('decryptedLength', 'N/A')}")

                                        if debug.get('finalData'):
                                            print(f"\n  ✅ 解密成功！内容预览:")
                                            print(f"  {debug['finalData'][:300]}...")
                                        if debug.get('decodeError'):
                                            print(f"\n  解码错误：{debug['decodeError']}")
                                        if detail_result.get('error'):
                                            print(f"\n  错误：{detail_result['error']}")
                                elif isinstance(items, dict):
                                    print(f"\n数据是字典：{items}")
                        except json.JSONDecodeError as e:
                            print(f"JSON 解析错误：{e}")
                    else:
                        print(f"\n解密失败：{decrypt_result.get('error', '未知错误')}")

                    continue

                # 检查 raw 字段
                raw = data.get('raw') if isinstance(data, dict) else None
                if raw:
                    print(f"原始响应 (前 500 字): {raw[:500]}")
                    continue

                # 尝试获取文章列表
                items = data.get('data', []) or data.get('items', []) or data.get('list', []) or data.get('records', [])

                # 检查嵌套结构
                if not items and 'data' in data and isinstance(data['data'], dict):
                    items = data['data'].get('list', []) or data['data'].get('items', []) or data['data'].get('records', [])

                if not items and isinstance(data, list):
                    items = data

                if items:
                    print(f"\n✅ 找到 {len(items)} 条数据")

                    # 检查数据类型
                    first_item = items[0] if items else None
                    print(f"  第一条数据类型：{type(first_item)}")
                    if isinstance(first_item, str):
                        print(f"  数据是字符串列表，预览：{first_item[:100]}...")
                        # 可能是 ID 列表
                        print(f"\n假设这是 ID 列表，测试第一个 ID: {first_item[:50]}")
                        test_id = first_item
                    elif isinstance(first_item, dict):
                        item_id = first_item.get('id', first_item.get('articleId', first_item.get('publishId', 'N/A')))
                        title = first_item.get('title', first_item.get('subject', first_item.get('name', 'N/A')))
                        print(f"  ID={item_id}")
                        print(f"  标题：{title[:60]}")
                        test_id = first_item.get('id', first_item.get('articleId', first_item.get('publishId')))
                    else:
                        print(f"  未知数据类型，跳过")
                        test_id = None

                    if test_id:
                        print(f"\n" + "="*60)
                        print(f"【测试详情 API】")
                        print(f"使用 ID: {str(test_id)[:50]}")
                        print("="*60)
                        detail_result = page.evaluate(f"""
                        (async () => {{
                            try {{
                                const articleId = '{test_id}';
                                const key = localStorage.getItem('logo2');

                                const debug = {{
                                    keyExists: !!key,
                                    keyLength: key ? key.length : 0
                                }};

                                if (!key) {{
                                    return {{ error: '未找到 logo2', debug }};
                                }}

                                const crypt = new JSEncrypt();
                                crypt.setKey(key);
                                const encrypted = crypt.encryptLong(articleId);

                                debug.encryptedExists = !!encrypted;

                                if (!encrypted) {{
                                    return {{ error: 'encryptLong 失败', debug }};
                                }}

                                const resp = await fetch('https://www.cnpcbidding.com/cms/article/details', {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify(encrypted)
                                }});

                                debug.status = resp.status;
                                debug.ok = resp.ok;

                                const text = await resp.text();
                                debug.responsePreview = text.substring(0, 200);
                                debug.responseLength = text.length;

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
                                        debug.finalData = JSON.stringify(parsed).substring(0, 200);
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

                        print(f"\n【详情 API 调试信息】")
                        debug = detail_result.get('debug', {})
                        print(f"  私钥存在：{debug.get('keyExists', False)}")
                        print(f" 私钥长度：{debug.get('keyLength', 0)}")
                        print(f"  加密成功：{debug.get('encryptedExists', 'N/A')}")
                        print(f"  API 状态：{debug.get('status', 'N/A')}")
                        print(f"  API 正常：{debug.get('ok', False)}")
                        print(f"  响应长度：{debug.get('responseLength', 'N/A')}")
                        print(f"  解密成功：{debug.get('decryptedExists', 'N/A')}")
                        print(f"  解密长度：{debug.get('decryptedLength', 'N/A')}")

                        if debug.get('finalData'):
                            print(f"\n  ✅ 解密成功！数据预览:")
                            print(f"  {debug['finalData'][:200]}")
                        if debug.get('decodeError'):
                            print(f"\n  解码错误：{debug['decodeError']}")
                        if detail_result.get('error'):
                            print(f"\n  错误：{detail_result['error']}")

                else:
                    print(f"\n数据结构:")
                    print(f"  顶层键：{list(data.keys())[:10]}")
        else:
            print("未捕获到任何 API 响应")
            print("\n可能原因:")
            print("  1. API 路径不是 /cms/article/page 或 /cms/publish/page")
            print("  2. 数据是静态 HTML 不是 API")
            print("  3. 页面使用 WebSocket 或其他通信方式")

        print("\n" + "="*60)
        input("\n按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()
