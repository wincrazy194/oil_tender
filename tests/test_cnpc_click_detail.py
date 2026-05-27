"""
测试中石油（CNPC）详情页点击和内容获取
验证同页渲染方式获取详情内容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

def test_cnpc_click_and_fetch():
    print("=" * 70)
    print("测试中石油详情页点击和内容获取")
    print("=" * 70)

    user_data_dir = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"

    with sync_playwright() as p:
        # 使用持久化上下文（复用登录状态和 Cookie）
        print("\n[步骤 0] 启动浏览器...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1920, "height": 1080},
        )

        page = context.pages[0] if context.pages else context.new_page()

        # 访问列表页
        print("\n[步骤 1] 访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        # 等待并点击搜索按钮
        print("\n[步骤 2] 点击搜索按钮...")
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=10000):
                print("  点击搜索按钮...")
                search_btn.click(timeout=10000)
                time.sleep(3)  # 等待 API 响应和列表渲染
            else:
                print("  搜索按钮不可见，等待...")
                page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  搜索失败：{e}")
            time.sleep(5)

        # 查找列表项（使用 API 响应数据渲染的 DOM）
        print("\n[步骤 3] 查找列表项...")

        # 尝试多种选择器
        selectors = [
            '.el-collapse-item',      # ElementUI 折叠面板
            '.el-card__body',
            '[class*="tender"]',
            '[class*="list-item"]',
            '.el-table__row',         # ElementUI 表格
            'tr',
            '[role="row"]',
        ]

        found_items = []
        for sel in selectors:
            try:
                items = page.query_selector_all(sel)
                if items:
                    print(f"  选择器 '{sel}' 找到 {len(items)} 个元素")
                    if len(items) > 0 and not found_items:
                        found_items = items
            except:
                pass

        if not found_items:
            print("  未找到列表项，尝试用 JavaScript 查找...")
            found_items = page.evaluate("""
                () => {
                    // 查找所有可能有内容的块级元素
                    const items = [];
                    const selectors = [
                        '.el-collapse-item',
                        '[class*="item"]',
                        '[class*="card"]',
                        'tr',
                        'li'
                    ];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        els.forEach(el => {
                            if (el.innerText.length > 20) {
                                items.push({
                                    tag: el.tagName,
                                    class: el.className,
                                    text: el.innerText.substring(0, 50)
                                });
                            }
                        });
                    }
                    return items.slice(0, 5);
                }
            """)
            print(f"  找到 {len(found_items)} 个项目:")
            for item in found_items:
                print(f"    <{item['tag']}> {item['class']}: {item['text']}...")
            browser.close()
            return False

        # 尝试点击第一项
        print(f"\n[步骤 4] 尝试点击第一个列表项...")
        first_item = found_items[0]

        try:
            first_item.scroll_into_view_if_needed()
            time.sleep(1)
            first_item.click(timeout=5000)
            print("  点击成功")
        except Exception as e:
            print(f"  点击失败：{e}")
            # 尝试点击内部的 a 标签
            a_tag = first_item.query_selector('a')
            if a_tag:
                print("  尝试点击内部 a 标签...")
                a_tag.click()
            else:
                print("  使用 page.click 坐标点击")
                box = first_item.bounding_box()
                if box:
                    page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)

        time.sleep(5)  # 等待详情内容加载

        # 查找详情内容
        print("\n[步骤 5] 查找详情内容...")

        # 检查是否出现详情内容元素
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
                    print(f"  找到元素 '{sel}': {len(text)} 字符")
                    if len(text) > 100:
                        content_text = text
                        break
            except:
                pass

        if content_text:
            print(f"\n[成功] 获取到详情内容：{len(content_text)} 字符")
            print(f"\n[内容预览] (前 500 字符):")
            print("-" * 50)
            # 处理编码问题
            safe_preview = content_text[:500].encode('gbk', 'ignore').decode('gbk')
            print(safe_preview)
            print("-" * 50)
        else:
            print("\n[失败] 未找到详情内容")

            # 检查是否还在列表页
            try:
                is_list_visible = page.is_visible('.el-collapse-item')
                print(f"  列表项是否可见：{is_list_visible}")
            except:
                print("  无法检查列表项")

            # 打印当前 URL
            current_url = page.url
            print(f"  当前 URL: {current_url}")

            # 尝试获取整个页面文本
            all_text = page.evaluate("() => document.body.innerText")
            print(f"  页面总文本长度：{len(all_text)}")

        context.close()
        return bool(content_text)

if __name__ == "__main__":
    success = test_cnpc_click_and_fetch()
    print(f"\n测试结果：{'成功' if success else '失败'}")
    sys.exit(0 if success else 1)
