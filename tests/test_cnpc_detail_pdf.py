"""
中石油详情页获取和 PDF 保存测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 输入修复
if os.name == 'nt':
    import msvcrt

from playwright.sync_api import sync_playwright
import time
import json

USER_DATA_DIR = r"E:\nandaoshuo\oil_tender\api_test\browser_data_cnpc_test_new"
BASE_URL = "https://www.cnpcbidding.com"
LIST_URL = f"{BASE_URL}/#/tenders"

def decrypt_api_response(page, body: str) -> dict:
    """在浏览器中解密 API 响应"""
    try:
        result = page.evaluate(f"""
            () => {{
                try {{
                    const bodyStr = {json.dumps(body)};
                    const key = localStorage.getItem('logo2');
                    if (!key) return {{ success: false, error: 'no key' }};
                    const JSEncrypt = window.JSEncrypt;
                    if (!JSEncrypt) return {{ success: false, error: 'no JSEncrypt' }};
                    const crypt = new JSEncrypt();
                    crypt.setKey(key);
                    const decrypted = crypt.decryptLong(bodyStr);
                    if (!decrypted) return {{ success: false, error: 'decrypt failed' }};
                    const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                        '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                    ).join(''));
                    return {{ success: true, data: JSON.parse(decoded) }};
                }} catch (e) {{
                    return {{ success: false, error: e.message }};
                }}
            }}
        """)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def fetch_detail_content(page, item_id: str) -> str:
    """获取详情内容（点击方式）"""
    try:
        # 查找并点击对应 ID 的列表项
        selector = f'[data-id="{item_id}"]'
        item = page.query_selector(selector)

        if not item:
            item = page.query_selector('.el-collapse-item, [class*="tender"]')
            if not item:
                print("   [详情] 未找到列表项")
                return ""

        print("   [点击] 点击列表项...")
        item.scroll_into_view_if_needed()
        time.sleep(0.5)
        item.click(timeout=5000)

        # 等待详情内容加载
        print("   [等待] 等待详情加载...")
        time.sleep(2)

        # 检查是否在详情页
        is_detail = page.evaluate("() => document.querySelector('.content') !== null")
        print(f"   [状态] 是否详情页：{is_detail}")

        # 提取 .content 元素文本
        content_elem = page.query_selector('.content')
        content = ""
        if content_elem:
            content = content_elem.inner_text()
            content = content.strip() if content else ""
            print(f"   [内容] 从 .content 获取到 {len(content)} 字")

        # 降级：尝试其他选择器
        if not content or len(content) < 50:
            for sel in ['.article-content', '.main-body', '.detail-content']:
                elem = page.query_selector(sel)
                if elem:
                    content = elem.inner_text()
                    content = content.strip() if content else ""
                    print(f"   [内容] 从 {sel} 获取到 {len(content)} 字")
                    break

        # 检查是否在列表页
        is_list = page.evaluate("() => document.querySelectorAll('.el-collapse-item').length > 0")
        print(f"   [状态] 是否列表页：{is_list}")

        # 如果在详情页，尝试返回
        if not is_list:
            print("   [返回] 尝试返回列表页...")
            try:
                search_btn = page.locator('button:has-text("搜索")').first
                if search_btn.is_visible(timeout=5000):
                    search_btn.click(timeout=5000)
                    print("   [返回] 已点击搜索刷新")
                    time.sleep(3)
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        pass
                    time.sleep(2)
            except Exception as e:
                print(f"   [返回] 刷新失败：{e}")

        return content.strip() if content else ""
    except Exception as e:
        print(f"   [详情] 获取失败：{e}")
        return ""

def save_detail_pdf(page, page_title: str, detail_content: str) -> str:
    """保存详情为 PDF"""
    if not detail_content:
        return ""

    output_dir = r"E:\nandaoshuo\oil_tender\output\cnpc_pdf"
    os.makedirs(output_dir, exist_ok=True)

    # 清理文件名中的非法字符
    safe_title = "".join(c for c in page_title[:50] if c not in ':*?"<>|')
    safe_title = safe_title.replace(' ', '_').strip('_')

    import re
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', page_title[:50])

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{safe_title}.pdf"
    pdf_path = os.path.join(output_dir, filename)

    try:
        # 生成 HTML 内容用于转 PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{page_title[:200]}</title>
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; padding: 40px; }}
                h1 {{ color: #333; border-bottom: 2px solid #4472C4; padding-bottom: 10px; }}
                .content {{ white-space: pre-wrap; line-height: 1.8; color: #555; }}
            </style>
        </head>
        <body>
            <h1>{page_title[:200]}</h1>
            <div class="content">{detail_content}</div>
        </body>
        </html>
        """

        # 创建新标签页生成 PDF
        pdf_page = page.context.new_page()
        pdf_page.set_content(html_content, wait_until="networkidle")
        time.sleep(1)

        # 生成 PDF
        pdf_page.pdf(path=pdf_path, format="A4", print_background=True)
        pdf_page.close()

        print(f"   [PDF] 已保存：{filename}")
        return pdf_path

    except Exception as e:
        print(f"   [PDF] 保存失败：{e}")
        return ""

def test():
    print("=" * 70)
    print("中石油详情页获取和 PDF 保存测试")
    print("=" * 70)

    with sync_playwright() as p:
        # 启动浏览器 - 使用 try-except 处理
        context = None
        errors = []

        # 尝试 Edge
        try:
            print("[浏览器] 尝试启动 Edge...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="msedge",
                headless=False,
                viewport={"width": 1920, "height": 1080},
                args=["--disable-gpu", "--no-sandbox"],
            )
            print("[浏览器] Edge 启动成功")
        except Exception as e:
            errors.append(f"Edge: {e}")
            print(f"[浏览器] Edge 启动失败：{e}")

        # 尝试 Chrome
        if not context:
            try:
                print("[浏览器] 尝试启动 Chrome...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                    args=["--disable-gpu", "--no-sandbox"],
                )
                print("[浏览器] Chrome 启动成功")
            except Exception as e:
                errors.append(f"Chrome: {e}")
                print(f"[浏览器] Chrome 启动失败：{e}")

        # 默认启动
        if not context:
            print("[浏览器] 使用默认方式启动...")
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                    args=["--disable-gpu", "--no-sandbox"],
                )
                print("[浏览器] 默认启动成功")
            except Exception as e:
                print(f"[浏览器] 所有启动方式均失败：{e}")
                context.close()
                return

        page = context.pages[0] if context.pages else context.new_page()

        # 访问列表页
        print("\n[1] 访问列表页...")
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # 用户手动操作
        print("\n[2] 请手动完成以下操作：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码，请手动完成")
        print("\n完成后按【回车键】继续...")
        try:
            if os.name == 'nt':
                while True:
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key in (b'\r', b'\n'):
                            break
                    time.sleep(0.1)
            else:
                input()
        except:
            print("未检测到输入，等待 10 秒...")
            time.sleep(10)

        time.sleep(2)

        # 获取第一页数据
        print("\n[3] 获取列表数据...")
        body = None
        try:
            with page.expect_response(
                lambda r: '/cms/article/page' in r.url and r.status == 200,
                timeout=30000
            ) as response_info:
                search_btn = page.locator('button:has-text("搜索")').first
                if search_btn.is_visible(timeout=10000):
                    search_btn.click(timeout=10000)
                    print("  已点击搜索按钮")

            response = response_info.value
            body = response.text()
            print(f"  [API] 响应长度={len(body)}")
        except Exception as e:
            print(f"  [API] 等待失败：{e}")
            context.close()
            return

        # 解密
        print("  [解密] API 响应...")
        decrypt_result = decrypt_api_response(page, body)
        if not decrypt_result.get('success'):
            print(f"  [解密] 失败：{decrypt_result.get('error')}")
            context.close()
            return

        data = decrypt_result['data']
        if 'data' in data and isinstance(data.get('data'), dict):
            data = data.get('data')
        records = data.get('records', [])
        print(f"  [数据] 获取到 {len(records)} 条记录")

        # 查找第一个 IT 相关的记录
        keywords = ['软件', '系统', '平台', '信息化', '数字化', '网络', '云', 'AI', '人工智', '大模', '服务器', '存储', '数据']
        target_item = None
        for item in records:
            item_title = item.get('title', '')
            is_it = any(kw in item_title.lower() for kw in keywords)
            if is_it:
                target_item = item
                break

        if not target_item:
            # 如果没有 IT 相关，使用第一个
            target_item = records[0] if records else None

        if not target_item:
            print("\n没有可用的记录")
            context.close()
            return

        item_id = target_item.get('id')
        item_title = target_item.get('title', '')
        print(f"\n[4] 测试目标：{item_title[:50]}...")
        print(f"    ID: {item_id}")

        # 获取详情内容
        print("\n[5] 获取详情页内容...")
        detail_content = fetch_detail_content(page, str(item_id))

        if detail_content:
            print(f"\n[详情] 成功获取 {len(detail_content)} 字")
            print(f"[预览] {detail_content[:200]}...")

            # 保存 PDF
            print("\n[6] 保存 PDF...")
            pdf_path = save_detail_pdf(page, item_title, detail_content)
            if pdf_path:
                print(f"[PDF] 保存成功：{pdf_path}")
            else:
                print("[PDF] 保存失败")
        else:
            print("\n[详情] 获取失败")

        print("\n测试完成！")
        context.close()

if __name__ == "__main__":
    test()
