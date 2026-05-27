"""
测试中海油 DOM 提取日期格式
"""
from playwright.sync_api import sync_playwright
import time

def test_dom_date():
    playwright = sync_playwright().start()

    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="playwright_test_")

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=temp_dir,
        channel="msedge",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    page = context.pages[0] if context.pages else context.new_page()

    base_url = "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD"
    print(f"访问：{base_url}")

    page.goto(base_url, wait_until="networkidle", timeout=60000)
    print("页面加载完成")

    time.sleep(2)

    # 获取 DOM 数据
    result = page.evaluate("""
    () => {
        const items = [];
        const rows = document.querySelectorAll('.table_page li');
        console.log('找到 li 数量:', rows.length);

        for (const row of rows) {
            const titleEl = row.querySelector('.table_title span');
            const dateEl = row.querySelector('.table_time');

            if (titleEl && dateEl) {
                const title = titleEl.textContent.trim();
                const date = dateEl.textContent.trim();
                const link = row.querySelector('a');
                const href = link ? link.getAttribute('href') : '';

                // 从 href 提取 id
                let id = '';
                const idMatch = href.match(/[?&]id=([a-zA-Z0-9_-]+)/);
                if (idMatch) id = idMatch[1];

                items.push({
                    id: id,
                    title: title.substring(0, 50),
                    publishDate: date
                });
            }
        }
        return items;
    }
    """)

    print(f"\n提取到 {len(result)} 条数据:")
    for i, item in enumerate(result):
        print(f"  {i+1}. [{item['publishDate']}] {item['title']}... (id={item['id']})")

    # 测试翻页
    print("\n\n测试翻页到第 2 页...")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    page2_result = page.evaluate("""
    () => {
        const pagers = document.querySelectorAll('.el-pager');
        const targetPager = pagers[pagers.length - 1];
        const numberLis = targetPager.querySelectorAll('li.number:not(.active)');

        for (const li of numberLis) {
            const text = li.innerText.trim();
            if (text === '2') {
                li.click();
                return { success: true, clicked: text };
            }
        }
        return { success: false };
    }
    """)

    print(f"点击结果：{page2_result}")

    try:
        page.wait_for_load_state('networkidle', timeout=15000)
    except:
        pass
    time.sleep(2)

    # 再次获取数据
    result_page2 = page.evaluate("""
    () => {
        const items = [];
        const rows = document.querySelectorAll('.table_page li');

        for (const row of rows) {
            const titleEl = row.querySelector('.table_title span');
            const dateEl = row.querySelector('.table_time');

            if (titleEl && dateEl) {
                items.push({
                    title: titleEl.textContent.trim().substring(0, 50),
                    publishDate: dateEl.textContent.trim()
                });
            }
        }
        return items;
    }
    """)

    print(f"\n第 2 页提取到 {len(result_page2)} 条数据:")
    for i, item in enumerate(result_page2):
        print(f"  {i+1}. [{item['publishDate']}] {item['title']}...")

    context.close()
    playwright.stop()
    print("\n测试完成")

if __name__ == "__main__":
    test_dom_date()
