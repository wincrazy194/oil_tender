"""
中石油（CNPC）专属测试脚本 - 简化版本
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
    keywords = ['软件', '系统', '平台', '信息化', '数字化', '网络', '云', 'AI', '人工智', '大模', '服务器', '存储', '数据']
    return any(kw in title.lower() for kw in keywords)

def decrypt_api_response(page, body: str) -> dict:
    try:
        result = page.evaluate(f"""
            () => {{
                try {{
                    const bodyStr = {json.dumps(body)};
                    const key = localStorage.getItem('logo2');
                    if (!key) return {{ success: false, error: '未找到私钥' }};
                    const JSEncrypt = window.JSEncrypt;
                    if (!JSEncrypt) return {{ success: false, error: 'JSEncrypt 未加载' }};
                    const crypt = new JSEncrypt();
                    crypt.setKey(key);
                    const decrypted = crypt.decryptLong(bodyStr);
                    if (!decrypted) return {{ success: false, error: 'decryptLong 失败' }};
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
            try:
                search_btn = page.locator('button:has-text("搜索")').first
                if search_btn.is_visible(timeout=5000):
                    search_btn.click(timeout=5000)
                    time.sleep(3)
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)
            except:
                pass

        return content.strip() if content else ""
    except Exception as e:
        print(f"   [详情] 失败：{e}")
        return ""

def test_cnpc():
    print("=" * 70)
    print("中石油（CNPC）采集测试 - 简化版")
    print("=" * 70)

    with sync_playwright() as p:
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

        print("\n[2] 请在 10 秒内手动点击搜索按钮和处理验证码...")
        for i in range(10, 0, -1):
            print(f"  倒计时：{i} 秒", end='\r')
            time.sleep(1)
        print()

        all_records = []

        for page_num in range(MAX_PAGES):
            print(f"\n=== 第 {page_num + 1} 页 ===")

            # 第 1 页点击搜索，后续页翻页后会自动加载
            if page_num == 0:
                print("[第 1 页] 点击搜索按钮...")
                try:
                    with page.expect_response(lambda r: '/cms/article/page' in r.url and r.status == 200, timeout=20000) as resp_info:
                        search_btn = page.locator('button:has-text("搜索")').first
                        search_btn.click(timeout=10000)
                    body = resp_info.value.text()
                    print(f"  [API] 响应长度={len(body)}")
                except Exception as e:
                    print(f"  [API] 失败：{e}")
                    continue
            else:
                # 翻页后等待 API
                print(f"[第{page_num+1}页] 等待翻页后 API...")
                try:
                    with page.expect_response(lambda r: '/cms/article/page' in r.url and r.status == 200, timeout=20000) as resp_info:
                        # 翻页操作在下面
                        pass
                    body = resp_info.value.text()
                    print(f"  [API] 响应长度={len(body)}")
                except Exception as e:
                    print(f"  [API] 失败：{e}")
                    # 尝试点击搜索
                    try:
                        with page.expect_response(lambda r: '/cms/article/page' in r.url and r.status == 200, timeout=20000) as resp_info:
                            search_btn = page.locator('button:has-text("搜索")').first
                            search_btn.click(timeout=5000)
                        body = resp_info.value.text()
                        print(f"  [API] 响应长度={len(body)} (搜索触发)")
                    except:
                        continue

            # 解密
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
                if not item_title:
                    continue

                is_it = is_it_related(item_title)
                safe_title = item_title[:40].encode('gbk', 'ignore').decode('gbk')
                print(f"  [{'IT' if is_it else '非 IT'}] {safe_title}")

                record = {"title": item_title, "date": publish_date, "is_it": is_it, "content": ""}
                if is_it:
                    content = fetch_detail_content(page, str(item_id))
                    if content:
                        record["content"] = content[:500]
                        print(f"    -> 详情：{len(content)} 字")
                all_records.append(record)

            # 翻页
            if page_num < MAX_PAGES - 1:
                print("\n[翻页] ", end='')
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
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
                        print(f"{result['from']} -> {result['to']}")
                    else:
                        print(f"失败：{result.get('reason')}")
                        break
                except Exception as e:
                    print(f"异常：{e}")
                    break

        print("\n" + "=" * 70)
        print(f"测试完成！总记录：{len(all_records)}, IT: {sum(1 for r in all_records if r['is_it'])}")
        context.close()

if __name__ == "__main__":
    test_cnpc()
