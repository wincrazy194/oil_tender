"""
中石油（CNPC）专属测试脚本
测试翻页和详情获取功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime

# 配置
USER_DATA_DIR = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BASE_URL = "https://www.cnpcbidding.com"
LIST_URL = f"{BASE_URL}/#/tenders"
MAX_PAGES = 5

def is_it_related(title: str) -> bool:
    """检查标题是否与 IT 相关"""
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
                    if (!key) return {{ success: false, error: '未找到私钥 (logo2)' }};

                    const JSEncrypt = window.JSEncrypt;
                    if (!JSEncrypt) return {{ success: false, error: 'JSEncrypt 未加载' }};

                    const crypt = new JSEncrypt();
                    crypt.setKey(key);
                    const decrypted = crypt.decryptLong(bodyStr);

                    if (!decrypted) return {{ success: false, error: 'decryptLong 返回 null' }};

                    const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                        '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                    ).join(''));

                    const data = JSON.parse(decoded);
                    return {{ success: true, data: data }};
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
        # 查找并点击列表项
        selector = f'[data-id="{item_id}"]'
        item = page.query_selector(selector)

        if not item:
            item = page.query_selector('.el-collapse-item, .el-card__body, [class*="tender"], [class*="item"]')

        if not item:
            print("   [详情] 未找到列表项")
            return ""

        # 记录当前页码
        current_page_before = page.evaluate("""
            () => {
                const pagers = document.querySelectorAll('.el-pager');
                if (pagers.length === 0) return 1;
                const pager = pagers[pagers.length - 1];
                const active = pager.querySelector('li.number.active');
                if (active) return parseInt(active.innerText.trim()) || 1;
                return 1;
            }
        """)
        print(f"   [详情] 当前页码：{current_page_before}")

        # 点击
        item.scroll_into_view_if_needed()
        time.sleep(0.5)
        item.click(timeout=5000)
        time.sleep(2)

        # 提取内容
        content_elem = page.query_selector('.content')
        content = ""
        if content_elem:
            content = content_elem.inner_text()
            content = content.strip() if content else ""

        # 检查是否需要返回
        is_list = page.evaluate("""
            () => document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0
        """)

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

                    # 检查是否恢复列表
                    is_list_now = page.evaluate("""
                        () => document.querySelectorAll('.el-collapse-item, [class*="tender"]').length > 0
                    """)
                    if not is_list_now:
                        print("   [返回] 搜索刷新未恢复列表，尝试重新导航...")
                        # 重新导航到列表页
                        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
                        time.sleep(3)
                        # 重新点击搜索
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
                print(f"   [返回] 刷新失败：{e}")

        return content if content else ""

    except Exception as e:
        print(f"   [详情] 获取失败：{e}")
        # 尝试恢复
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=3000):
                search_btn.click(timeout=3000)
                time.sleep(2)
        except:
            pass
        return ""

def test_cnpc():
    print("=" * 70)
    print("中石油（CNPC）采集测试")
    print("=" * 70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标：{LIST_URL}")
    print(f"最大页数：{MAX_PAGES}")
    print("=" * 70)

    with sync_playwright() as p:
        # 启动浏览器
        print("\n[1] 启动浏览器...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else context.new_page()

        # 访问列表页
        print("\n[2] 访问列表页...")
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # 用户手动操作
        print("\n" + "=" * 60)
        print("[3] 请手动完成以下操作：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码，请手动完成")
        print("\n程序将在 10 秒后自动继续...")
        print("=" * 60)

        for i in range(10, 0, -1):
            print(f"  倒计时：{i} 秒", end='\r')
            time.sleep(1)
        print("  \n开始采集！")
        time.sleep(2)

        all_records = []

        # 循环翻页
        for page_num in range(MAX_PAGES):
            print(f"\n{'=' * 50}")
            print(f"=== 第 {page_num + 1} 页 ===")
            print(f"{'=' * 50}")

            # 获取列表数据 - 拦截 API 响应
            # 注意：翻页会自动触发 API，第一页需要点击搜索
            print("\n[数据] 等待列表 API 响应...")

            body = None
            try:
                # 设置响应监听
                with page.expect_response(
                    lambda r: '/cms/article/page' in r.url and r.status == 200,
                    timeout=15000
                ) as response_info:
                    # 第一页需要点击搜索按钮
                    if page_num == 0:
                        search_btn = page.locator('button:has-text("搜索")').first
                        search_btn.wait_for(state='visible', timeout=10000)
                        print("  [第 1 页] 点击搜索按钮...")
                        search_btn.click(timeout=5000)
                        print("  等待 API 响应...")
                    else:
                        # 翻页后等待自动触发的 API
                        print("  [第{}页] 等待翻页后自动 API...".format(page_num + 1))

                response = response_info.value
                body = response.text()
                print(f"  [API] 响应长度={len(body)}")

            except Exception as e:
                print(f"  [API] 等待失败：{e}")
                # 尝试点击搜索按钮
                try:
                    print("  尝试点击搜索按钮...")
                    search_btn = page.locator('button:has-text("搜索")').first
                    search_btn.wait_for(state='visible', timeout=5000)
                    search_btn.click(timeout=5000)
                    time.sleep(3)
                except:
                    pass
                continue

            # 解密 API 响应
            print("  [解密] API 响应...")
            decrypt_result = decrypt_api_response(page, body)

            if not decrypt_result.get('success'):
                print(f"  [解密] 失败：{decrypt_result.get('error', '未知错误')}")
                continue

            data = decrypt_result['data']
            # 处理嵌套结构
            if 'data' in data and isinstance(data.get('data'), dict):
                data = data.get('data')

            records = data.get('records', [])
            print(f"  [数据] 获取到 {len(records)} 条记录")

            # 处理每条记录
            for item in records:
                item_id = item.get('id')
                item_title = item.get('title', '')
                publish_date = item.get('publishedTime', '')

                if not item_title or len(item_title) < 5:
                    continue

                is_it = is_it_related(item_title)

                safe_title = item_title[:40].encode('gbk', 'ignore').decode('gbk')
                print(f"\n  [{'IT' if is_it else '非 IT'}] {safe_title}...")
                print(f"    日期：{publish_date}")

                record = {
                    "title": item_title,
                    "date": publish_date,
                    "is_it": is_it,
                    "content": "",
                }

                # IT 相关获取详情
                if is_it:
                    print(f"    [详情] 获取中...")
                    content = fetch_detail_content(page, str(item_id))
                    if content:
                        record["content"] = content[:500]
                        print(f"    [详情] 成功，{len(content)} 字")
                    else:
                        print(f"    [详情] 失败")

                all_records.append(record)

            # 翻页（在数据处理完成后）
            if page_num < MAX_PAGES - 1:
                print("\n[翻页] 尝试翻到下一页...")

                try:
                    # 滚动到底部
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)

                    # 点击页码
                    result = page.evaluate("""
                        () => {
                            const pagers = document.querySelectorAll('.el-pager');
                            if (pagers.length === 0) return { success: false, reason: 'no pager' };

                            const pager = pagers[pagers.length - 1];
                            const active = pager.querySelector('li.number.active');
                            let currentPage = 1;
                            if (active) {
                                currentPage = parseInt(active.innerText.trim()) || 1;
                            }

                            const targetPage = currentPage + 1;

                            // 点击下一页按钮
                            const nextBtn = pager.querySelector('li.next');
                            if (nextBtn && !nextBtn.classList.contains('disabled')) {
                                nextBtn.click();
                                return { success: true, from: currentPage, to: targetPage };
                            }

                            // 点击页码数字
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
                        print(f"  [翻页] {result['from']} -> {result['to']}")
                        # 翻页后等待 API 响应（已经在上层循环中处理）
                    else:
                        print(f"  [翻页] 失败：{result.get('reason')}")
                        break

                except Exception as e:
                    print(f"  [翻页] 异常：{e}")
                    break

            # 检查是否还有下一页
            total = data.get('total', 0)
            current = data.get('current', 1)
            if current >= MAX_PAGES:
                print("\n[结束] 已达到最大页数")
                break

        # 总结
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        print(f"总记录数：{len(all_records)}")
        it_count = sum(1 for r in all_records if r['is_it'])
        print(f"IT 相关：{it_count}")
        print(f"非 IT：{len(all_records) - it_count}")

        context.close()

if __name__ == "__main__":
    test_cnpc()
