"""
验证 .box_data 选择器可以点击并获取详情
"""
import os
import time
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"

def main():
    print("="*60)
    print("验证 .box_data 选择器")
    print("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # 访问列表页
        print("\n[1] 访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        print("\n[2] 请手动完成：")
        print("  - 点击【搜索】按钮")
        print("  - 处理验证码（如有）")
        print("\n完成后按回车键继续...")
        input()
        time.sleep(2)

        # 查找 .box_data 元素
        print("\n[3] 查找 .box_data 元素...")
        box_data_items = page.query_selector_all('.box_data')
        print(f"  找到 {len(box_data_items)} 个 .box_data 元素")

        if len(box_data_items) == 0:
            print("  未找到 .box_data，尝试其他选择器...")
            # 备用选择器
            box_data_items = page.query_selector_all('[class*="box"]')
            print(f"  [class*='box'] 找到 {len(box_data_items)} 个")

        if len(box_data_items) == 0:
            print("  仍未找到，退出")
            browser.close()
            return

        # 检查元素内容
        print("\n[4] 检查元素内容...")
        for i, item in enumerate(box_data_items[:3]):
            text = item.inner_text()
            text_safe = text[:50].encode('gbk', 'ignore').decode('gbk')
            print(f"  [{i+1}] {text_safe}...")

        # 点击第一个元素
        print("\n[5] 点击第一个 .box_data 元素...")
        first_item = box_data_items[0]

        try:
            first_item.scroll_into_view_if_needed()
            time.sleep(1)
            first_item.click(timeout=5000)
            print("  点击成功")
        except Exception as e:
            print(f"  点击失败：{e}")
            # 尝试 JavaScript 点击
            page.evaluate("(el) => el.click()", first_item)
            print("  已使用 JS 点击")

        # 等待详情内容加载
        print("\n[6] 等待详情内容加载 (3 秒)...")
        time.sleep(3)

        # 检查详情内容
        print("\n[7] 检查详情内容...")

        # 尝试多种选择器
        content_selectors = [
            '.content',
            '.article-content',
            '.detail-content',
            '.main-body',
            '[class*="content"]',
        ]

        content_text = ""
        for sel in content_selectors:
            try:
                elem = page.query_selector(sel)
                if elem:
                    text = elem.inner_text()
                    print(f"  找到 '{sel}': {len(text)} 字符")
                    if len(text) > 100:
                        content_text = text
                        break
            except:
                pass

        if content_text:
            print(f"\n[成功] 获取到详情内容：{len(content_text)} 字符")
            print(f"\n[预览] (前 300 字):")
            print("-" * 50)
            safe_preview = content_text[:300].encode('gbk', 'ignore').decode('gbk')
            print(safe_preview)
            print("-" * 50)
        else:
            print("\n[失败] 未找到详情内容")

        # 检查页面状态
        print("\n[8] 检查页面状态...")
        state = page.evaluate("""
            () => {
                const listItems = document.querySelectorAll('.box_data').length;
                const hasContent = document.querySelector('.content') !== null;
                const pagers = document.querySelectorAll('.el-pager');
                const hasPager = pagers.length > 0;
                return { listItems, hasContent, hasPager };
            }
        """)
        print(f"  列表项 (.box_data): {state['listItems']}")
        print(f"  详情内容 (.content): {state['hasContent']}")
        print(f"  分页组件：{state['hasPager']}")

        # 测试返回列表
        print("\n[9] 尝试返回列表...")

        # 方法 1: 点击搜索按钮
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=3000):
                search_btn.click(timeout=3000)
                print("  已点击搜索按钮")
                time.sleep(3)
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass
                time.sleep(2)
        except Exception as e:
            print(f"  点击搜索失败：{e}")

        # 检查返回后的状态
        state_after = page.evaluate("""
            () => {
                const listItems = document.querySelectorAll('.box_data').length;
                const hasContent = document.querySelector('.content') !== null;
                return { listItems, hasContent };
            }
        """)
        print(f"\n[返回后状态]")
        print(f"  列表项 (.box_data): {state_after['listItems']}")
        print(f"  详情内容 (.content): {state_after['hasContent']}")

        if state_after['listItems'] >= 5:
            print("  [成功] 已返回列表页")
        else:
            print("  [失败] 仍停留在详情页")

        print("\n" + "="*60)
        input("按回车退出...")
        browser.close()

if __name__ == "__main__":
    main()
