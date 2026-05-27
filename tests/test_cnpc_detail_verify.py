"""
中石油详情获取验证脚本
验证是否真的获取到了详情内容
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

# 测试用的 IT 相关项目 ID（从第 3 页）
TEST_ITEM_ID = "335274"
TEST_ITEM_TITLE = "AI 私有化平台开发部署服务项目"

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

def check_page_state(page):
    """检查页面状态"""
    state = page.evaluate("""
        () => {
            const listItems = document.querySelectorAll('.el-collapse-item, [class*="tender"]').length;
            const hasDetail = document.querySelector('.content') !== null;
            const pagers = document.querySelectorAll('.el-pager');
            const hasPager = pagers.length > 0;
            let currentPage = 1;
            if (hasPager) {
                const pager = pagers[pagers.length - 1];
                const active = pager.querySelector('li.number.active');
                if (active) currentPage = parseInt(active.innerText.trim()) || 1;
            }
            return { listItems, hasDetail, hasPager, currentPage };
        }
    """)
    return state

def wait_for_enter():
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

def test_detail_fetch():
    print("=" * 70)
    print("中石油详情获取验证")
    print("=" * 70)

    with sync_playwright() as p:
        print("\n[浏览器] 启动 Edge...")
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
        print("  2. 翻页到第 3 页（如果有）")
        print("  3. 如有验证码请处理")
        print("\n完成后按【回车键】继续...")
        wait_for_enter()
        time.sleep(2)

        # 检查初始状态
        state = check_page_state(page)
        print(f"\n[初始状态] 列表项={state['listItems']}, 详情={state['hasDetail']}, 分页={state['hasPager']}, 当前页={state['currentPage']}")

        # 如果初始状态不正常，先刷新
        if state['listItems'] < 3 or state['hasDetail']:
            print("\n[刷新] 初始状态不正常，尝试恢复列表...")

            # 方案 1：尝试点击返回按钮
            back_clicked = page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button, .el-button, [role="button"]'));
                    for (const btn of buttons) {
                        const text = (btn.innerText || '').toLowerCase();
                        if (text.includes('返回') || text.includes('back')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            print(f"  [返回] 点击返回按钮：{back_clicked}")
            time.sleep(2)

            state = check_page_state(page)
            print(f"  [返回后] 列表项={state['listItems']}, 详情={state['hasDetail']}")

            # 方案 2：如果返回失败，尝试重新搜索
            if state['listItems'] < 3:
                print("  [刷新] 返回无效，尝试重新搜索...")
                try:
                    search_btn = page.locator('button:has-text("搜索")').first
                    if search_btn.is_visible(timeout=5000):
                        search_btn.click(timeout=5000)
                        print("    [搜索] 已点击搜索")
                        time.sleep(3)
                        try:
                            page.wait_for_load_state('networkidle', timeout=10000)
                        except:
                            pass
                        time.sleep(2)

                        state = check_page_state(page)
                        print(f"    [搜索后] 列表项={state['listItems']}, 详情={state['hasDetail']}")
                except Exception as e:
                    print(f"    [搜索] 失败：{e}")

            # 方案 3：如果还是失败，重新导航到纯列表页（不带 detail）
            if state['listItems'] < 3:
                print("  [刷新] 搜索无效，强制导航到纯列表页...")
                current_url = page.url
                print(f"  [当前 URL] {current_url}")

                # 导航到不带 detail 的 URL
                page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)

                # 检查导航后的状态
                state = check_page_state(page)
                print(f"  [导航后] 列表项={state['listItems']}, 详情={state['hasDetail']}, URL={page.url}")

                # 如果还是详情，尝试刷新页面
                if state['hasDetail'] and state['listItems'] < 3:
                    print("  [刷新] 导航后仍在详情，尝试刷新页面...")
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    time.sleep(5)

                    # 重新点击搜索
                    try:
                        search_btn = page.locator('button:has-text("搜索")').first
                        if search_btn.is_visible(timeout=5000):
                            search_btn.click(timeout=5000)
                            print("    [搜索] 已点击搜索")
                            time.sleep(3)
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            time.sleep(2)

                            state = check_page_state(page)
                            print(f"    [刷新后] 列表项={state['listItems']}, 详情={state['hasDetail']}")
                    except Exception as e:
                        print(f"    [搜索] 失败：{e}")

        # 尝试直接访问第 3 页
        if state['hasPager'] and state['currentPage'] == 1:
            print("\n[翻页] 尝试翻到第 3 页...")
            for i in range(2):
                result = page.evaluate("""
                    () => {
                        const pagers = document.querySelectorAll('.el-pager');
                        if (pagers.length === 0) return { success: false };
                        const pager = pagers[pagers.length - 1];
                        const nextBtn = pager.querySelector('li.next');
                        if (nextBtn && !nextBtn.classList.contains('disabled')) {
                            nextBtn.click();
                            return { success: true };
                        }
                        return { success: false };
                    }
                """)
                if result.get('success'):
                    time.sleep(2)
                    print(f"  已翻到第 {i+2} 页")

        # 获取列表数据，找到测试项目
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
            if decrypt_result.get('success'):
                data = decrypt_result['data']
                if 'data' in data and isinstance(data.get('data'), dict):
                    data = data.get('data')
                records = data.get('records', [])
                print(f"  [数据] 获取到 {len(records)} 条记录")

                # 查找 IT 项目
                target_item = None
                for item in records:
                    if 'AI' in item.get('title', '') or '私有化' in item.get('title', ''):
                        target_item = item
                        break

                if not target_item and records:
                    # 没有找到 AI 项目，使用第一个
                    target_item = records[6] if len(records) > 6 else records[0]

                print(f"  [目标] ID={target_item.get('id')}, 标题={target_item.get('title', '')[:50]}")

                # 测试详情获取
                print("\n" + "=" * 50)
                print("[测试] 开始获取详情...")
                print("=" * 50)

                # 先检查当前状态
                pre_state = check_page_state(page)
                print(f"  [当前状态] 列表项={pre_state['listItems']}, 详情={pre_state['hasDetail']}")

                item_id = target_item.get('id')

                # 等待列表渲染
                print("  [等待] 等待列表渲染 (3 秒)...")
                time.sleep(3)

                # 尝试多种选择器
                selector = f'[data-id="{item_id}"]'
                item = page.query_selector(selector)
                print(f"  [查找] data-id 选择器：{'找到' if item else '未找到'}")

                if not item:
                    item = page.query_selector('.el-collapse-item')
                    print(f"  [查找] .el-collapse-item: {'找到' if item else '未找到'}")

                if not item:
                    item = page.query_selector('.el-collapse-item > .el-collapse-item__header')
                    print(f"  [查找] .el-collapse-item__header: {'找到' if item else '未找到'}")

                if not item:
                    # 尝试所有可能的列表项
                    all_items = page.query_selector_all('.el-collapse-item')
                    print(f"  [查找] .el-collapse-item 总数：{len(all_items)}")

                    if len(all_items) == 0:
                        # 尝试其他选择器
                        all_items = page.query_selector_all('[class*="article"], [class*="tender-item"], .el-card')
                        print(f"  [查找] 备用选择器总数：{len(all_items)}")

                if not item and len(all_items) > 0:
                    # 使用第一个列表项测试
                    item = all_items[0]
                    print(f"  [查找] 使用第一个列表项测试")

                if not item:
                    # 输出页面 HTML 片段用于调试
                    html_info = page.evaluate("""
                        () => {
                            const items = document.querySelectorAll('.el-collapse-item, [class*="tender"], [class*="article"], .el-card');
                            const containers = document.querySelectorAll('.tenders, .article-list, .el-collapse');
                            return {
                                count: items.length,
                                containerCount: containers.length,
                                firstItem: items[0] ? items[0].outerHTML.substring(0, 200) : 'none',
                                container: containers[0] ? containers[0].outerHTML.substring(0, 200) : 'none'
                            };
                        }
                    """)
                    print(f"\n  [调试] 列表元素数量：{html_info['count']}")
                    print(f"  [调试] 容器数量：{html_info['containerCount']}")
                    print(f"  [调试] 第一个元素：{html_info['firstItem'][:150]}...")
                    print(f"  [调试] 容器：{html_info['container'][:150]}...")

                    # 检查是否在详情页
                    detail_check = page.evaluate("""
                        () => {
                            const content = document.querySelector('.content');
                            const title = document.querySelector('.title');
                            return {
                                hasContent: content !== null,
                                hasTitle: title !== null,
                                contentLength: content ? content.innerText.length : 0
                            };
                        }
                    """)
                    print(f"  [调试] 详情页状态：content={detail_check['hasContent']}, title={detail_check['hasTitle']}, 长度={detail_check['contentLength']}")
                    return

                print(f"  [点击] 找到列表项，准备点击...")
                item.scroll_into_view_if_needed()
                time.sleep(0.5)
                item.click(timeout=5000)

                print("  [等待] 等待详情内容加载...")
                time.sleep(3)

                # 检查点击后的状态
                state_after_click = check_page_state(page)
                print(f"\n[点击后状态] 列表项={state_after_click['listItems']}, 详情={state_after_click['hasDetail']}, 分页={state_after_click['hasPager']}")

                # 提取详情内容
                content_elem = page.query_selector('.content')
                if content_elem:
                    content = content_elem.inner_text()
                    print(f"\n[详情内容]")
                    print(f"  长度：{len(content)} 字符")
                    print(f"  前 200 字：{content[:200]}...")
                    print(f"  后 100 字：...{content[-100:]}")

                    # 验证是否真的是详情内容
                    if len(content) > 100:
                        print("\n[验证] 成功获取详情内容！")
                    else:
                        print("\n[验证] 内容过短，可能获取失败")
                else:
                    print("\n[验证] 未找到.content 元素")

                # 测试返回
                print("\n" + "=" * 50)
                print("[测试] 尝试返回列表...")
                print("=" * 50)

                # 尝试点击返回按钮
                back_clicked = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button, .el-button, [role="button"]'));
                        for (const btn of buttons) {
                            const text = (btn.innerText || '').toLowerCase();
                            if (text.includes('返回') || text.includes('back')) {
                                btn.click();
                                return 'text:' + text;
                            }
                        }
                        return 'none';
                    }
                """)
                print(f"  [返回] 点击类型：{back_clicked}")
                time.sleep(2)

                # 检查返回后的状态
                state_after_back = check_page_state(page)
                print(f"\n[返回后状态] 列表项={state_after_back['listItems']}, 详情={state_after_back['hasDetail']}, 分页={state_after_back['hasPager']}")

                # 如果返回失败，尝试重新搜索
                if state_after_back['listItems'] < 3:
                    print("\n[返回] 列表未恢复，尝试重新搜索...")
                    try:
                        search_btn = page.locator('button:has-text("搜索")').first
                        if search_btn.is_visible(timeout=5000):
                            search_btn.click(timeout=5000)
                            print("  [搜索] 已点击搜索")
                            time.sleep(3)
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            time.sleep(2)

                            state_after_search = check_page_state(page)
                            print(f"\n[搜索后状态] 列表项={state_after_search['listItems']}, 详情={state_after_search['hasDetail']}, 分页={state_after_search['hasPager']}, 当前页={state_after_search['currentPage']}")
                    except Exception as e:
                        print(f"  [搜索] 失败：{e}")

        except Exception as e:
            print(f"  [错误] {e}")

        print("\n" + "=" * 70)
        print("测试完成！")
        context.close()

if __name__ == "__main__":
    test_detail_fetch()
