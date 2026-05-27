"""
测试中海油页面 DOM 选择器
"""
from playwright.sync_api import sync_playwright

def test_selector():
    playwright = sync_playwright().start()

    # 使用临时目录避免缓存问题
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

    # 访问中海油招标公告列表
    base_url = "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD"
    print(f"访问：{base_url}")

    page.goto(base_url, wait_until="networkidle", timeout=60000)
    print("页面加载完成")

    # 等待列表出现
    try:
        page.wait_for_selector('.table_page li', timeout=10000)
        print("找到列表项")
    except:
        print("未找到列表项 .table_page li")

    # 测试不同的选择器
    selectors = [
        '.table_page li',
        '.table_page .item',
        '[class*="news-item"]',
        '[class*="list-item"]',
        '.news-list li',
        '.page-content li',
    ]

    for sel in selectors:
        try:
            elements = page.query_selector_all(sel)
            print(f"{sel}: {len(elements)} 个元素")
        except Exception as e:
            print(f"{sel}: 错误 - {e}")

    # 获取实际数据
    result = page.evaluate("""
    () => {
        const items = [];
        const selectors = [
            '.table_page li',
            '.table_page .item',
            '[class*="news-item"]',
            '.news-list li',
        ];

        const allRows = [];
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (!allRows.includes(el)) allRows.push(el);
            });
        });

        console.log('找到列表项数量:', allRows.length);

        for (const row of allRows) {
            const titleEl = row.querySelector('.table_title span') ||
                           row.querySelector('[class*="title"]') ||
                           row.querySelector('span');
            const dateEl = row.querySelector('.table_time') ||
                          row.querySelector('[class*="date"]') ||
                          row.querySelector('[class*="time"]');

            if (titleEl && dateEl) {
                items.push({
                    title: titleEl.textContent.trim().substring(0, 30),
                    date: dateEl.textContent.trim()
                });
            }
        }
        return items;
    }
    """)

    print(f"\n提取到 {len(result)} 条数据:")
    for i, item in enumerate(result[:10]):
        print(f"  {i+1}. [{item['date']}] {item['title']}...")

    # 测试翻页
    print("\n\n测试翻页...")

    # 滚动到底部
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    import time
    time.sleep(1)

    # 尝试点击第 2 页
    result2 = page.evaluate("""
    () => {
        const pagers = document.querySelectorAll('.el-pager');
        console.log('找到分页组件数量:', pagers.length);

        if (pagers.length === 0) return { error: '未找到分页组件' };

        const targetPager = pagers[pagers.length - 1];

        // 获取所有页码
        const numberLis = targetPager.querySelectorAll('li.number');
        const pages = [];
        for (const li of numberLis) {
            pages.push({
                text: li.innerText.trim(),
                active: li.classList.contains('active')
            });
        }

        return { pages: pages };
    }
    """)

    print(f"分页信息：{result2}")

    # 点击第 2 页
    if result2.get('pages'):
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
            return { success: false, reason: 'page 2 not found' };
        }
        """)

        print(f"点击第 2 页结果：{page2_result}")

        # 等待数据加载
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
        time.sleep(2)

        # 再次获取数据
        result_page2 = page.evaluate("""
        () => {
            const items = [];
            const selectors = ['.table_page li'];

            const allRows = [];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    if (!allRows.includes(el)) allRows.push(el);
                });
            });

            for (const row of allRows) {
                const titleEl = row.querySelector('.table_title span');
                const dateEl = row.querySelector('.table_time');

                if (titleEl && dateEl) {
                    items.push({
                        title: titleEl.textContent.trim().substring(0, 30),
                        date: dateEl.textContent.trim()
                    });
                }
            }
            return items;
        }
        """)

        print(f"\n第 2 页提取到 {len(result_page2)} 条数据:")
        for i, item in enumerate(result_page2[:10]):
            print(f"  {i+1}. [{item['date']}] {item['title']}...")

    context.close()
    playwright.stop()
    print("\n测试完成")

if __name__ == "__main__":
    test_selector()
