"""
中石油（CNPC）专属测试脚本 - 使用主脚本相同逻辑
测试第 4 页翻页修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 添加 Windows 输入修复
if os.name == 'nt':
    import msvcrt

from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime

USER_DATA_DIR = r"E:\nandaoshuo\oil_tender\api_test\browser_data_cnpc_test"
BASE_URL = "https://www.cnpcbidding.com"
LIST_URL = f"{BASE_URL}/#/tenders"
MAX_PAGES = 5

def is_it_related(title: str) -> bool:
    keywords = ['软件', '系统', '平台', '信息化', '数字化', '网络', '云', 'AI', '人工智', '大模', '服务器', '存储', '数据']
    return any(kw in title.lower() for kw in keywords)

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
    """获取详情内容（点击列表项方式）"""
    try:
        item = page.query_selector(f'[data-id="{item_id}"]')
        if not item:
            item = page.query_selector('.el-collapse-item, [class*="tender"]')
        if not item:
            return ""

        item.scroll_into_view_if_needed()
        time.sleep(0.5)
        item.click(timeout=5000)
        time.sleep(2)

        content_elem = page.query_selector('.content')
        content = content_elem.inner_text() if content_elem else ""

        # 返回列表页
        is_list = page.evaluate("() => document.querySelectorAll('.el-collapse-item').length > 0")
        if not is_list:
            print("   [返回] 检测到详情页状态，尝试刷新列表...")
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

def test_cnpc():
    print("=" * 70)
    print("中石油（CNPC）采集测试 - 第 4 页翻页修复")
    print("=" * 70)

    with sync_playwright() as p:
        # 尝试多种浏览器启动方式
        context = None
        errors = []

        # 1. 尝试 Edge
        try:
            print("[浏览器] 尝试启动 Edge...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="msedge",
                headless=False,
                viewport={"width": 1920, "height": 1080},
            )
            print("[浏览器] Edge 启动成功")
        except Exception as e:
            errors.append(f"Edge: {e}")
            print(f"[浏览器] Edge 启动失败：{e}")

        # 2. 尝试 Chrome
        if not context:
            try:
                print("[浏览器] 尝试启动 Chrome...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                )
                print("[浏览器] Chrome 启动成功")
            except Exception as e:
                errors.append(f"Chrome: {e}")
                print(f"[浏览器] Chrome 启动失败：{e}")

        # 3. 默认启动
        if not context:
            print("[浏览器] 使用默认方式启动...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                viewport={"width": 1920, "height": 1080},
            )
            print("[浏览器] 默认启动成功")

        page = context.pages[0] if context.pages else context.new_page()

        print("\n[1] 访问列表页...")
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        print("\n[2] 请手动完成以下操作：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码，请手动完成")
        print("\n完成后按【回车键】继续，程序将自动开始采集数据...")
        print("=" * 60)
        try:
            if os.name == 'nt':
                # Windows: 使用 msvcrt 避免输入缓冲问题
                print("等待回车输入...")
                while True:
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key in (b'\r', b'\n'):
                            break
                    time.sleep(0.1)
            else:
                input()
        except Exception as e:
            print(f"未检测到输入，等待 10 秒...")
            time.sleep(10)

        time.sleep(2)

        all_records = []
        seen_keys = set()

        for page_num in range(MAX_PAGES):
            print(f"\n=== 第 {page_num + 1} 页 ===")

            # 翻页（从第 2 页开始）
            if page_num > 0:
                print("[翻页] ", end='')
                flip_success = False
                flip_retry = 0

                while not flip_success and flip_retry < 3:
                    flip_retry += 1
                    if flip_retry > 1:
                        print(f"\n  [重试 {flip_retry}/3] 尝试翻页...")

                    try:
                        # 滚动到底部
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1)

                        # 检查页面状态
                        page_status = page.evaluate("""
                            () => {
                                const hasList = document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0;
                                const pagers = document.querySelectorAll('.el-pager');
                                const hasPager = pagers.length > 0;
                                let currentPage = 1;
                                if (hasPager) {
                                    const pager = pagers[pagers.length - 1];
                                    const active = pager.querySelector('li.number.active');
                                    if (active) currentPage = parseInt(active.innerText.trim()) || 1;
                                }
                                return { hasList, hasPager, currentPage };
                            }
                        """)

                        print(f"\n  [状态] 列表={page_status['hasList']}, 分页={page_status['hasPager']}, 当前页={page_status['currentPage']}")

                        # 如果分页组件消失，尝试恢复
                        if not page_status['hasPager']:
                            print("  [恢复] 分页组件消失，尝试刷新...")
                            try:
                                search_btn = page.locator('button:has-text("搜索")').first
                                if search_btn.is_visible(timeout=3000):
                                    search_btn.click(timeout=3000)
                                    time.sleep(3)

                                    # 检查是否恢复
                                    check_again = page.evaluate("""
                                        () => document.querySelectorAll('.el-pager').length > 0
                                    """)
                                    if not check_again:
                                        print("  [恢复] 搜索刷新无效，重新导航...")
                                        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=30000)
                                        time.sleep(3)
                                        search_btn = page.locator('button:has-text("搜索")').first
                                        if search_btn.is_visible(timeout=5000):
                                            search_btn.click(timeout=5000)
                                            time.sleep(3)
                                            try:
                                                page.wait_for_load_state('networkidle', timeout=10000)
                                            except:
                                                pass
                                            time.sleep(2)
                            except Exception as e:
                                print(f"  [恢复] 失败：{e}")
                                break

                        # 翻页
                        result = page.evaluate("""
                            () => {
                                const pagers = document.querySelectorAll('.el-pager');
                                if (pagers.length === 0) return { success: false, reason: 'no pager' };
                                const pager = pagers[pagers.length - 1];
                                const active = pager.querySelector('li.number.active');
                                let currentPage = 1;
                                if (active) currentPage = parseInt(active.innerText.trim()) || 1;
                                const targetPage = currentPage + 1;
                                const nextBtn = pager.querySelector('li.next');
                                if (nextBtn && !nextBtn.classList.contains('disabled')) {
                                    nextBtn.click();
                                    return { success: true, from: currentPage, to: targetPage };
                                }
                                const numbers = pager.querySelectorAll('li.number');
                                for (const li of numbers) {
                                    const num = parseInt(li.innerText.trim());
                                    if (num === targetPage) {
                                        li.click();
                                        return { success: true, from: currentPage, to: targetPage };
                                    }
                                }
                                return { success: false, reason: 'no next' };
                            }
                        """)

                        if result.get('success'):
                            print(f"  {result['from']} -> {result['to']}")
                            time.sleep(1)
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                time.sleep(2)
                            flip_success = True
                        else:
                            print(f"  失败：{result.get('reason')}")
                            break

                    except Exception as e:
                        print(f"  异常：{e}")
                        break

                if not flip_success:
                    print("  翻页失败，停止采集")
                    break

            # 获取列表数据 - 每次循环都点击搜索
            print("[数据] 等待列表 API 响应...")
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
                    else:
                        print("  搜索按钮不可见...")
                        time.sleep(5)

                response = response_info.value
                body = response.text()
                print(f"  [API] 响应长度={len(body)}")

            except Exception as e:
                print(f"  [API] 等待失败：{e}")
                continue

            # 解密
            print("  [解密] API 响应...")
            decrypt_result = decrypt_api_response(page, body)
            if not decrypt_result.get('success'):
                print(f"  [解密] 失败：{decrypt_result.get('error')}")
                continue

            data = decrypt_result['data']
            if 'data' in data and isinstance(data.get('data'), dict):
                data = data.get('data')
            records = data.get('records', [])
            print(f"  [数据] 获取到 {len(records)} 条记录")

            # 处理记录
            for item in records:
                item_id = item.get('id')
                item_title = item.get('title', '')
                publish_date = item.get('publishedTime', '')
                if not item_title or len(item_title) < 5:
                    continue

                key = f"{item_title}{publish_date}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                is_it = is_it_related(item_title)
                safe_title = item_title[:40].encode('gbk', 'ignore').decode('gbk')
                print(f"  [{'IT' if is_it else '非 IT'}] {safe_title}")

                record = {"title": item_title, "date": publish_date, "is_it": is_it, "content": ""}
                if is_it:
                    print(f"    -> 获取详情...")
                    content = fetch_detail_content(page, str(item_id))
                    if content:
                        record["content"] = content[:500]
                        print(f"    -> 成功：{len(content)} 字")
                all_records.append(record)

        print("\n" + "=" * 70)
        print(f"测试完成！总记录：{len(all_records)}, IT: {sum(1 for r in all_records if r['is_it'])}")
        context.close()

if __name__ == "__main__":
    test_cnpc()
