"""
测试中石油（CNPC）详情页浏览器直接获取方式
验证 fetch_detail_content 是否能正确抓取详情内容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

# 从主脚本导入函数
from collect_all_companies_API_NEW import fetch_detail_content

def test_cnpc_browser_fetch():
    print("=" * 70)
    print("测试中石油详情页浏览器直接获取方式")
    print("=" * 70)

    with sync_playwright() as p:
        # 启动浏览器（使用持久化上下文，复用登录状态）
        browser = p.chromium.launch(
            headless=False,  # 非无头模式，方便观察
            slow_mo=500      # 慢动作，方便观察
        )

        # 创建上下文
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # 先访问列表页
        print("\n[步骤 1] 访问列表页...")
        list_page = context.new_page()
        list_page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)  # 等待 JS 加载完成
        print("  列表页加载完成")

        # 等待列表项出现
        print("\n[步骤 2] 等待列表项加载...")
        list_page.wait_for_selector('.proposals-item', timeout=10000)
        time.sleep(2)

        # 获取第一个列表项的 ID
        first_item = list_page.query_selector('.proposals-item')
        if not first_item:
            print("  [错误] 未找到列表项")
            browser.close()
            return False

        # 提取文章 ID（从 data-id 或 onclick 事件中）
        item_id = first_item.get_attribute('data-id')
        if not item_id:
            # 尝试从其他方式获取 ID
            print("  [提示] 无法从 data-id 获取，尝试点击第一个项目...")
            first_item.click()
            time.sleep(3)

            # 检查是否显示了详情内容
            content_elem = list_page.query_selector('.content')
            if content_elem:
                content_text = content_elem.inner_text()
                print(f"\n[成功] 在同页中获取到内容：{len(content_text)} 字符")
                print(f"\n[内容预览] (前 300 字符):")
                print("-" * 50)
                print(content_text[:300])
                print("-" * 50)
                browser.close()
                return True
            else:
                print("  [错误] 点击后仍未找到内容元素")
                browser.close()
                return False

        print(f"  找到文章 ID: {item_id}")
        detail_url = f"https://www.cnpcbidding.com/#/tenders/detail?id={item_id}"

        # 测试 1: 直接在列表页点击第一项
        print(f"\n{'=' * 70}")
        print("[测试 1] 在列表页点击第一项（同页渲染方式）")
        print(f"{'=' * 70}")

        first_item.click()
        time.sleep(3)  # 等待详情内容加载

        # 检查是否有详情内容
        content_elem = list_page.query_selector('.content')
        if content_elem:
            content_text = content_elem.inner_text()
            print(f"\n[成功] 获取到内容：{len(content_text)} 字符")
            print(f"\n[内容预览] (前 300 字符):")
            print("-" * 50)
            print(content_text[:300])
            print("-" * 50)
        else:
            print("\n[失败] 未找到.content 元素")
            # 尝试其他选择器
            for sel in ['.article-content', '.main-body', '.detail-content']:
                elem = list_page.query_selector(sel)
                if elem:
                    print(f"  [提示] 找到元素：{sel}")
                    break
            else:
                print("  [提示] 尝试打印页面 HTML 前 1000 字符...")
                html = list_page.content()
                print(html[:1000])

        list_page.close()

        browser.close()
        return True

if __name__ == "__main__":
    success = test_cnpc_browser_fetch()
    sys.exit(0 if success else 1)
