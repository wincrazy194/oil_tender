"""
测试中石油点击详情后的 URL 和页面状态变化
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

def test_url_change():
    print("=" * 60)
    print("测试中石油点击详情后的 URL 变化")
    print("=" * 60)

    user_data_dir = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="msedge",
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )

        page = context.pages[0] if context.pages else context.new_page()

        # 访问列表页
        print("\n[1] 访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        print(f"  URL: {page.url}")

        # 点击搜索
        print("\n[2] 点击搜索...")
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=10000):
                search_btn.click()
                time.sleep(3)
        except Exception as e:
            print(f"  搜索失败：{e}")

        # 获取当前 URL 和页码
        print("\n[3] 点击前的状态...")
        url_before = page.url
        pager_info = page.evaluate("""
            () => {
                const pagers = document.querySelectorAll('.el-pager');
                if (pagers.length === 0) return { pager: 'none' };
                const pager = pagers[pagers.length - 1];
                const active = pager.querySelector('li.number.active');
                return {
                    activePage: active ? active.innerText : 'none',
                    hasList: document.querySelector('.el-collapse-item') !== null
                };
            }
        """)
        print(f"  URL: {url_before}")
        print(f"  分页信息：{pager_info}")

        # 点击第一个列表项
        print("\n[4] 点击第一个列表项...")
        item = page.query_selector('.el-collapse-item, [class*="tender"]')
        if item:
            item.click()
            time.sleep(3)

            # 获取点击后的状态
            url_after_click = page.url
            pager_info_after = page.evaluate("""
                () => {
                    const pagers = document.querySelectorAll('.el-pager');
                    if (pagers.length === 0) return { pager: 'none' };
                    const pager = pagers[pagers.length - 1];
                    const active = pager.querySelector('li.number.active');
                    return {
                        activePage: active ? active.innerText : 'none',
                        hasList: document.querySelector('.el-collapse-item') !== null,
                        hasDetail: document.querySelector('.content') !== null
                    };
                }
            """)
            print(f"  URL: {url_after_click}")
            print(f"  分页信息：{pager_info_after}")

            # 尝试点击返回按钮
            print("\n[5] 尝试返回...")

            # 方法 1: 查找返回按钮
            back_btn = page.query_selector('.el-button--text, .back-btn, [class*="back"]')
            if back_btn and back_btn.is_visible():
                print("  找到返回按钮，点击...")
                back_btn.click()
                time.sleep(2)
            else:
                print("  未找到返回按钮，使用 go_back()")
                page.go_back()
                time.sleep(2)

            # 获取返回后的状态
            url_after_back = page.url
            pager_info_back = page.evaluate("""
                () => {
                    const pagers = document.querySelectorAll('.el-pager');
                    if (pagers.length === 0) return { pager: 'none' };
                    const pager = pagers[pagers.length - 1];
                    const active = pager.querySelector('li.number.active');
                    return {
                        activePage: active ? active.innerText : 'none',
                        hasList: document.querySelector('.el-collapse-item') !== null,
                        hasDetail: document.querySelector('.content') !== null
                    };
                }
            """)
            print(f"  URL: {url_after_back}")
            print(f"  分页信息：{pager_info_back}")
        else:
            print("  未找到列表项")

        context.close()
        print("\n测试完成")

if __name__ == "__main__":
    test_url_change()
