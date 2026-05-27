"""
中石油网站列表项查找脚本
找出正确的文章列表项选择器
"""
import os
import time
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"


def check_captcha(page):
    """检测验证码弹窗"""
    selectors = ['.geetest_panel', '[class*="captcha"]', '.layui-layer-content']
    for sel in selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return True
        except:
            pass
    return False


def wait_for_captcha(page, timeout=300):
    """等待用户处理验证码"""
    print("\n" + "="*50)
    print("检测到验证码！请在浏览器中手动处理...")
    print("="*50 + "\n")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if not check_captcha(page):
            print("\n验证码已处理！\n")
            time.sleep(1)
            return True
    print(f"\n等待超时 ({timeout}秒)\n")
    return False


def main():
    print("="*60)
    print("中石油网站列表项查找脚本")
    print("="*60)
    print("\n请在浏览器打开后：")
    print("1. 处理验证码（如有）")
    print("2. 确保进入了招标公告列表页")
    print("3. 按回车键分析页面结构")
    print("="*60 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # 访问列表页
        print("正在访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        if check_captcha(page):
            wait_for_captcha(page)

        print("\n等待 5 秒让数据加载...")
        for i in range(5, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)

        print("\n等待 3 秒后自动分析页面结构...")
        time.sleep(3)

        # 深入分析页面结构
        print("\n" + "="*60)
        print("【页面结构分析】")
        print("="*60)

        result = page.evaluate("""
        () => {
            const info = {
                url: window.location.href,
                title: document.title
            };

            // 找所有包含"招标"、"公告"、"项目"等关键词的元素
            const keywords = ['招标', '公告', '项目', '采购', '中标'];
            const matches = [];

            document.querySelectorAll('*').forEach(el => {
                const text = el.innerText?.trim() || '';
                if (text.length > 10 && text.length < 200) {
                    for (const kw of keywords) {
                        if (text.includes(kw)) {
                            matches.push({
                                tag: el.tagName,
                                className: el.className?.split(' ').slice(0, 3).join('.'),
                                id: el.id,
                                text: text.substring(0, 50),
                                hasClick: !!el.onclick || !!el.getAttribute('@click')
                            });
                            break;
                        }
                    }
                }
            });

            info.matchedItems = matches.slice(0, 20);

            // 找表格行
            const rows = document.querySelectorAll('tr');
            info.trCount = rows.length;
            info.trSamples = Array.from(rows).slice(0, 5).map(tr => ({
                className: tr.className?.split(' ').slice(0, 3).join('.'),
                text: tr.innerText?.substring(0, 80)
            }));

            // 找 div 中包含列表的
            const divs = document.querySelectorAll('div');
            info.divCount = divs.length;

            // 找有特定类名的元素
            const classPatterns = ['tender', 'list', 'item', 'row', 'data', 'content'];
            for (const pattern of classPatterns) {
                const els = document.querySelectorAll(`[class*="${pattern}"]`);
                info[pattern + 'Count'] = els.length;
                if (els.length > 0 && els.length < 50) {
                    info[pattern + 'Samples'] = Array.from(els).slice(0, 3).map(el => ({
                        tag: el.tagName,
                        class: el.className,
                        text: (el.innerText || '').substring(0, 50)
                    }));
                }
            }

            // 检查是否有 tbody
            const tbody = document.querySelector('tbody');
            info.tbodyExists = !!tbody;
            if (tbody) {
                info.tbodyRows = tbody.querySelectorAll('tr').length;
            }

            return info;
        }
        """)

        print(f"\n当前 URL: {result.get('url', '')[:100]}")
        print(f"页面标题：{result.get('title', '')[:50]}")

        print(f"\n<tr> 数量：{result.get('trCount', 0)}")
        if result.get('trSamples'):
            print("表格行示例:")
            for row in result['trSamples']:
                print(f"  - {row.get('text', '')[:60]}")

        print(f"\n<tbody> 存在：{result.get('tbodyExists', False)}")
        if result.get('tbodyExists'):
            print(f"<tbody> 内行数：{result.get('tbodyRows', 0)}")

        print(f"\n<div> 总数：{result.get('divCount', 0)}")

        for pattern in ['tender', 'list', 'item', 'row', 'data', 'content']:
            count = result.get(pattern + 'Count', 0)
            print(f"[class*='{pattern}'] 数量：{count}")
            samples = result.get(pattern + 'Samples', [])
            if samples:
                for s in samples[:2]:
                    print(f"    - {s.get('tag', '')}.{s.get('class', '')}: {s.get('text', '')[:40]}")

        print("\n" + "="*60)
        print("【匹配到招标关键词的元素】")
        print("="*60)
        matched = result.get('matchedItems', [])
        if matched:
            for i, item in enumerate(matched[:10], 1):
                print(f"{i}. {item.get('tag', '')}.{item.get('className', '')}: {item.get('text', '')[:50]}")
        else:
            print("未找到匹配元素")

        print("\n" + "="*60)
        input("\n按回车退出（或等待 10 秒）...")
        time.sleep(10)
        browser.close()


if __name__ == "__main__":
    main()
