"""
快速测试中石油详情点击获取
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

# 导入主脚本中的函数
from collect_all_companies_API_NEW import fetch_cnpc_detail_by_click

def quick_test():
    print("=" * 60)
    print("快速测试中石油详情点击")
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

        # 点击搜索
        print("\n[2] 点击搜索按钮...")
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=10000):
                search_btn.click()
                time.sleep(3)
                print("  搜索完成")
        except Exception as e:
            print(f"  搜索失败：{e}")

        # 获取第一个列表项的 ID（从 API 响应或者 DOM）
        print("\n[3] 获取列表项...")
        item_id = page.evaluate("""
            () => {
                // 尝试从列表项中获取 ID
                const item = document.querySelector('.el-collapse-item, [class*="tender"], [class*="item"]');
                if (item) {
                    // 尝试从 onclick 或者其他属性中提取 ID
                    console.log('Item HTML:', item.outerHTML.substring(0, 500));
                    return item.getAttribute('data-id') || 'unknown';
                }
                return null;
            }
        """)

        print(f"  获取到的 ID: {item_id}")

        if item_id and item_id != 'unknown':
            # 测试 fetch_cnpc_detail_by_click
            print(f"\n[4] 测试 fetch_cnpc_detail_by_click({item_id})...")
            content = fetch_cnpc_detail_by_click(page, item_id)

            if content:
                print(f"\n[成功] 获取到 {len(content)} 字符")
                print(f"\n[预览]:")
                print("-" * 50)
                print(content[:300].encode('gbk', 'ignore').decode('gbk'))
                print("-" * 50)
            else:
                print("\n[失败] 未获取到内容")
        else:
            print("  无法获取有效 ID，跳过测试")

        context.close()
        print("\n测试完成")

if __name__ == "__main__":
    quick_test()
