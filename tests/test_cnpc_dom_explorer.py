"""
中石油 DOM 结构探索脚本
找到正确的列表项选择器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if os.name == 'nt':
    import msvcrt

from playwright.sync_api import sync_playwright
import time

USER_DATA_DIR = r"E:\nandaoshuo\oil_tender\api_test\browser_data_cnpc_test"
BASE_URL = "https://www.cnpcbidding.com"
LIST_URL = f"{BASE_URL}/#/tenders"

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

def explore_dom(page):
    """探索页面 DOM 结构"""
    dom_info = page.evaluate("""
        () => {
            const info = {};

            // 统计各种元素数量
            const selectors = [
                '.el-collapse-item',
                '.el-card',
                '.article-item',
                '[class*="article"]',
                '[class*="tender"]',
                '[class*="item"]',
                '[class*="list"]',
                '.el-table__row',
                'tr',
                '.content'
            ];

            selectors.forEach(sel => {
                const elements = document.querySelectorAll(sel);
                info[sel] = elements.length;
            });

            // 获取容器结构
            const tenders = document.querySelector('.tenders');
            if (tenders) {
                info.tendersChildren = tenders.children.length;
                info.tendersHTML = tenders.innerHTML.substring(0, 500);
            }

            // 获取 body 结构
            const app = document.querySelector('#app');
            if (app) {
                info.appChildren = app.children.length;
            }

            // 检查是否在列表页
            const hasList = document.querySelectorAll('.el-collapse-item, .el-card, [class*="article-item"]').length > 0;
            const hasDetail = document.querySelector('.content') !== null;
            info.isListPage = hasList;
            info.isDetailPage = hasDetail;

            return info;
        }
    """)
    return dom_info

def explore_dom():
    print("=" * 70)
    print("中石油 DOM 结构探索")
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
        print("  2. 如有验证码请处理")
        print("\n完成后按【回车键】继续...")
        wait_for_enter()
        time.sleep(3)

        print("\n" + "=" * 50)
        print("[探索] 初始 DOM 结构")
        print("=" * 50)
        dom_info = explore_dom(page)
        print(f"列表页={dom_info['isListPage']}, 详情页={dom_info['isDetailPage']}")
        print(f"\n元素统计:")
        for sel, count in dom_info.items():
            if isinstance(count, int) and sel not in ['tendersChildren', 'appChildren', 'isListPage', 'isDetailPage']:
                print(f"  {sel}: {count}")

        # 获取列表项的 HTML 结构
        list_html = page.evaluate("""
            () => {
                // 尝试找到列表容器
                const containers = document.querySelectorAll('.tenders, .article-list, .el-collapse');
                for (const container of containers) {
                    const children = container.children;
                    if (children.length > 0) {
                        return {
                            container: container.tagName + '.' + (container.className || '').split(' ')[0],
                            childCount: children.length,
                            firstChild: children[0] ? children[0].outerHTML.substring(0, 300) : 'none',
                            secondChild: children[1] ? children[1].outerHTML.substring(0, 300) : 'none'
                        };
                    }
                }
                return null;
            }
        """)

        if list_html:
            print(f"\n[列表结构]")
            print(f"  容器：{list_html['container']}")
            print(f"  子元素数量：{list_html['childCount']}")
            print(f"  第一个子元素:\n    {list_html['firstChild'][:200]}...")
            if list_html['secondChild'] != 'none':
                print(f"  第二个子元素:\n    {list_html['secondChild'][:200]}...")

        # 尝试点击第一个列表项
        print("\n" + "=" * 50)
        print("[测试] 点击第一个可见的项目")
        print("=" * 50)

        # 找到所有可能的项目
        items = page.query_selector_all('.tenders > * > * > [role="button"], .tenders .el-collapse-item, .tenders .el-card, .tenders > div > div')
        print(f"  找到项目数：{len(items)}")

        if len(items) == 0:
            # 尝试其他选择器
            items = page.query_selector_all('[class*="tender"] div[role="button"], [class*="article"] div[role="button"]')
            print(f"  备用选择器找到：{len(items)}")

        if len(items) > 0:
            print(f"  准备点击第 1 个项目...")
            items[0].scroll_into_view_if_needed()
            time.sleep(1)

            # 获取点击前的 HTML
            before_html = page.evaluate("""
                () => {
                    const container = document.querySelector('.tenders');
                    return container ? container.innerHTML.substring(0, 200) : 'none';
                }
            """)
            print(f"  [点击前] {before_html[:100]}...")

            items[0].click(timeout=5000)
            time.sleep(3)

            print("\n[探索] 点击后 DOM 结构")
            print("=" * 50)
            dom_info_after = explore_dom(page)
            print(f"列表页={dom_info_after['isListPage']}, 详情页={dom_info_after['isDetailPage']}")
            print(f"\n元素统计:")
            for sel, count in dom_info_after.items():
                if isinstance(count, int) and sel not in ['tendersChildren', 'appChildren', 'isListPage', 'isDetailPage']:
                    print(f"  {sel}: {count}")

            # 获取详情内容
            content = page.evaluate("""
                () => {
                    const content = document.querySelector('.content');
                    if (content) {
                        return {
                            found: true,
                            length: content.innerText.length,
                            preview: content.innerText.substring(0, 100)
                        };
                    }
                    return { found: false };
                }
            """)

            if content['found']:
                print(f"\n[详情内容]")
                print(f"  长度：{content['length']}")
                print(f"  预览：{content['preview']}...")

            # 检查点击后的容器
            after_html = page.evaluate("""
                () => {
                    const container = document.querySelector('.tenders');
                    return container ? container.innerHTML.substring(0, 200) : 'none';
                }
            """)
            print(f"\n  [点击后] {after_html[:100]}...")

        print("\n" + "=" * 70)
        print("探索完成！")
        context.close()

if __name__ == "__main__":
    explore_dom()
