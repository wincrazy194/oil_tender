"""
测试中石油（CNPC）列表页结构和点击行为
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import time

def test_cnpc_list_page():
    print("=" * 70)
    print("测试中石油列表页结构")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500
        )

        page = browser.new_page()

        # 访问列表页
        print("\n[步骤 1] 访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        # 保存截图查看页面状态
        page.screenshot(path="cnpc_list_page.png")
        print("  已保存截图：cnpc_list_page.png")

        # 打印页面 HTML 结构
        print("\n[步骤 2] 分析页面结构...")

        # 获取页面所有带 class 的元素
        structure = page.evaluate("""
            () => {
                const result = {
                    body_classes: document.body.className,
                    main_containers: [],
                    list_items: [],
                    all_classes: {}
                };

                // 查找可能的列表容器
                const containers = document.querySelectorAll('[class*="list"], [class*="item"], [class*="tender"], [class*="proposal"]');
                containers.forEach(el => {
                    if (el.className && typeof el.className === 'string') {
                        result.main_containers.push({
                            tag: el.tagName,
                            class: el.className,
                            id: el.id,
                            children: el.children.length
                        });
                    }
                });

                // 查找所有可能有内容的 div
                const divs = document.querySelectorAll('div');
                divs.forEach(div => {
                    if (div.className && typeof div.className === 'string') {
                        const cls = div.className.split(' ').find(c => c.length > 3);
                        if (cls && !result.all_classes[cls]) {
                            result.all_classes[cls] = (result.all_classes[cls] || 0) + 1;
                        }
                    }
                });

                return result;
            }
        """)

        print(f"\nBody classes: {structure['body_classes']}")
        print(f"\n找到的列表容器:")
        for container in structure['main_containers'][:10]:
            print(f"  <{container['tag']}> class=\"{container['class']}\" children={container['children']}")

        print(f"\n出现频率最高的 class (前 20):")
        sorted_classes = sorted(structure['all_classes'].items(), key=lambda x: x[1], reverse=True)[:20]
        for cls, count in sorted_classes:
            print(f"  {cls}: {count} 次")

        # 尝试查找列表项
        print("\n[步骤 3] 查找列表项...")

        # 尝试多种可能的选择器
        selectors = [
            '[class*="item"]',
            '[class*="list-item"]',
            '[class*="tender"]',
            '[class*="card"]',
            'li',
            '.el-collapse-item',  # ElementUI 常见选择器
            '.el-card',
            '.ant-list-item',     # Ant Design 常见选择器
        ]

        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements:
                print(f"\n  选择器 '{sel}' 找到 {len(elements)} 个元素")
                if len(elements) > 0:
                    elem = elements[0]
                    print(f"    第一个元素：{elem.inner_html()[:200]}")
                    break

        # 等待一段时间观察页面
        print("\n[步骤 4] 等待 10 秒，请观察浏览器中的页面内容...")
        time.sleep(10)

        # 再次尝试查找
        print("\n[步骤 5] 再次分析...")
        html_preview = page.evaluate("() => document.body.innerHTML.substring(0, 2000)")
        print(f"Body HTML 前 2000 字符:\n{html_preview}")

        browser.close()
        print("\n测试完成")
        return True

if __name__ == "__main__":
    success = test_cnpc_list_page()
    sys.exit(0 if success else 1)
