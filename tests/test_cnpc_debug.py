"""
中石油（CNPC）第 4 页翻页问题调试脚本
使用与主脚本完全相同的逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if os.name == 'nt':
    import msvcrt

from playwright.sync_api import sync_playwright
import time
import json

USER_DATA_DIR = r"E:\nandaoshuo\oil_tender\api_test\browser_data_cnpc_test"
BASE_URL = "https://www.cnpcbidding.com"
LIST_URL = f"{BASE_URL}/#/tenders"
MAX_PAGES = 5

def is_it_related(title: str) -> bool:
    keywords = ['软件', '系统', '平台', '信息化', '数字化', '网络', '云', 'AI', '人工智', '大模', '服务器', '存储', '数据']
    return any(kw in title.lower() for kw in keywords)

def decrypt_api_response(page, body: str) -> dict:
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

def fetch_cnpc_detail_by_click(page, item_id: str) -> str:
    """获取中石油详情页内容 - 与主脚本完全一致"""
    if not item_id:
        return ""

    try:
        # 1. 查找并点击对应 ID 的列表项
        selector = f'[data-id="{item_id}"]'
        item = page.query_selector(selector)

        if not item:
            item = page.query_selector('.el-collapse-item, .el-card__body, [class*="tender"], [class*="item"]')
            if not item:
                print("   [详情] 未找到列表项")
                return ""

        # 2. 滚动并点击
        item.scroll_into_view_if_needed()
        time.sleep(0.5)
        item.click(timeout=5000)

        # 3. 等待详情内容加载
        time.sleep(2)

        # 4. 提取 .content 元素文本
        content_elem = page.query_selector('.content')
        content = ""
        if content_elem:
            content = content_elem.inner_text()
            content = content.strip() if content else ""
            print(f"   [详情] 内容长度={len(content)}")

        # 5. 返回列表页状态
        time.sleep(0.5)

        # 检查是否还在列表页
        is_list_visible = page.evaluate("""
            () => {
                const items = document.querySelectorAll('.el-collapse-item, [class*="tender"]');
                return items.length > 0;
            }
        """)

        if is_list_visible:
            print("   [返回] 已在列表页")
            return content if content else ""

        # 不在列表页，尝试点击返回按钮
        try:
            back_clicked = page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button, .el-button, [role="button"], a[role="button"]'));
                    for (const btn of buttons) {
                        const text = (btn.innerText || btn.textContent || '').toLowerCase();
                        if (text.includes('返回') || text.includes('back')) {
                            btn.click();
                            return 'text:' + text;
                        }
                    }
                    const icons = document.querySelectorAll('.el-icon-arrow-left, .el-icon-back');
                    for (const icon of icons) {
                        const btn = icon.closest('button, .el-button, [role="button"], a');
                        if (btn) {
                            btn.click();
                            return 'icon:' + btn.tagName;
                        }
                    }
                    const crumbs = document.querySelectorAll('.el-breadcrumb__item a');
                    if (crumbs.length > 1) {
                        crumbs[crumbs.length - 2].click();
                        return 'crumb:true';
                    }
                    return 'none';
                }
            """)

            print(f"   [返回] 点击类型：{back_clicked}")

            if back_clicked != 'none':
                time.sleep(2)
                for i in range(5):
                    is_list = page.evaluate("""
                        () => document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0
                    """)
                    if is_list:
                        print("   [返回] 已返回列表页")
                        break
                    time.sleep(0.5)
            else:
                print("   [返回] 未找到返回按钮，尝试重新搜索")
                try:
                    search_btn = page.locator('button:has-text("搜索")').first
                    if search_btn.is_visible(timeout=5000):
                        search_btn.click(timeout=5000)
                        time.sleep(3)
                        try:
                            page.wait_for_load_state('networkidle', timeout=10000)
                        except:
                            pass
                        time.sleep(2)
                        print("   [返回] 已重新点击搜索")
                except Exception as search_err:
                    print(f"   [返回] 重新搜索失败：{search_err}")

        except Exception as back_err:
            print(f"   [返回] 返回操作失败：{back_err}")

        # 最终检查：如果仍然不在列表页，强制重新搜索
        final_check = page.evaluate("""
            () => document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0
        """)
        if not final_check:
            print(f"   [返回] 未检测到列表，强制重新搜索...")
            try:
                search_btn = page.locator('button:has-text("搜索")').first
                if search_btn.is_visible(timeout=5000):
                    search_btn.click(timeout=5000)
                    print("   [返回] 已点击搜索，等待列表渲染...")
                    time.sleep(3)
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        pass
                    time.sleep(2)
            except Exception as e:
                print(f"   [返回] 重新搜索失败：{e}")

        return content if content else ""

    except Exception as e:
        print(f"   [详情] 失败：{e}")
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=5000):
                search_btn.click(timeout=5000)
                time.sleep(2)
        except:
            pass
        return ""

def wait_for_enter():
    """等待回车输入"""
    print("等待回车输入...")
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

def test_cnpc():
    print("=" * 70)
    print("中石油（CNPC）第 4 页翻页问题调试")
    print("=" * 70)

    with sync_playwright() as p:
        print("[浏览器] 启动 Edge...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="msedge",
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("\n[1] 访问列表页...")
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        print("\n[2] 请手动完成：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码请处理")
        print("\n完成后按【回车键】继续...")
        wait_for_enter()
        time.sleep(2)

        all_records = []
        seen_keys = set()

        for page_num in range(MAX_PAGES):
            print(f"\n{'='*60}")
            print(f"=== 第 {page_num + 1} 页 ===")
            print(f"{'='*60}")

            # 翻页（从第 2 页开始）
            if page_num > 0:
                print("\n[翻页] ", end='')

                # 先检查页面状态 - 与主脚本一致
                page_status = page.evaluate("""
                    () => {
                        const hasList = document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0;
                        const hasDetail = document.querySelector('.content') !== null;
                        const pagers = document.querySelectorAll('.el-pager');
                        const hasPager = pagers.length > 0;
                        let currentPage = 1;
                        if (hasPager) {
                            const pager = pagers[pagers.length - 1];
                            const active = pager.querySelector('li.number.active');
                            if (active) currentPage = parseInt(active.innerText.trim()) || 1;
                        }
                        return { hasList, hasDetail, hasPager, currentPage };
                    }
                """)
                print(f"\n  [状态] 列表={page_status['hasList']}, 详情={page_status['hasDetail']}, 分页={page_status['hasPager']}, 当前页={page_status['currentPage']}")

                # 如果在详情页，尝试返回
                if page_status.get('hasDetail') and not page_status.get('hasList'):
                    print("  [返回] 检测到详情页状态，尝试返回...")
                    try:
                        search_btn = page.locator('button:has-text("搜索")').first
                        if search_btn.is_visible(timeout=3000):
                            search_btn.click(timeout=3000)
                            time.sleep(3)
                            print("  [返回] 已点击搜索刷新列表")
                    except:
                        pass

                # 如果分页消失，尝试恢复
                if not page_status['hasPager']:
                    print("  [恢复] 分页消失，点击搜索刷新...")
                    try:
                        search_btn = page.locator('button:has-text("搜索")').first
                        if search_btn.is_visible(timeout=3000):
                            search_btn.click(timeout=3000)
                            time.sleep(3)
                            print("  [恢复] 已点击搜索")
                    except Exception as e:
                        print(f"  [恢复] 失败：{e}")

                # 执行翻页
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
                            return { success: true, from: currentPage, to: targetPage, method: 'next' };
                        }
                        const numbers = pager.querySelectorAll('li.number');
                        for (const li of numbers) {
                            const num = parseInt(li.innerText.trim());
                            if (num === targetPage) {
                                li.click();
                                return { success: true, from: currentPage, to: targetPage, method: 'number' };
                            }
                        }
                        return { success: false, reason: 'no next' };
                    }
                """)

                if result.get('success'):
                    print(f"  {result['from']} -> {result['to']} ({result['method']})")
                    time.sleep(1)
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        time.sleep(2)
                else:
                    print(f"  失败：{result.get('reason')}")
                    break

            # 获取列表数据
            print("\n[数据] 点击搜索获取数据...")
            try:
                with page.expect_response(
                    lambda r: '/cms/article/page' in r.url and r.status == 200,
                    timeout=30000
                ) as response_info:
                    search_btn = page.locator('button:has-text("搜索")').first
                    if search_btn.is_visible(timeout=10000):
                        search_btn.click(timeout=10000)
                    response = response_info.value
                    body = response.text()

                decrypt_result = decrypt_api_response(page, body)
                if not decrypt_result.get('success'):
                    print(f"  [解密] 失败：{decrypt_result.get('error')}")
                    continue

                data = decrypt_result['data']
                if 'data' in data and isinstance(data.get('data'), dict):
                    data = data.get('data')
                records = data.get('records', [])
                print(f"  [数据] 获取到 {len(records)} 条记录")

            except Exception as e:
                print(f"  [API] 失败：{e}")
                continue

            # 处理记录
            it_items = []
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
                safe_title = item_title[:30]
                print(f"  [{'IT' if is_it else '非 IT'}] {safe_title}")

                if is_it:
                    it_items.append({"id": item_id, "title": item_title})

                all_records.append({"title": item_title, "is_it": is_it})

            # 获取 IT 详情
            for it_item in it_items:
                print(f"\n  [IT 详情] {it_item['title'][:30]}")
                content = fetch_cnpc_detail_by_click(page, str(it_item['id']))
                if content:
                    print(f"  [IT 详情] 成功：{len(content)} 字")

        print("\n" + "=" * 70)
        print(f"测试完成！总记录：{len(all_records)}, IT: {sum(1 for r in all_records if r['is_it'])}")
        context.close()

if __name__ == "__main__":
    test_cnpc()
