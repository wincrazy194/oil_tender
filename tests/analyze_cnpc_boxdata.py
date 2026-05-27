"""
中石油 box_data 结构分析脚本
找出文章 ID 的存储位置
"""
import os
import time
from playwright.sync_api import sync_playwright

BROWSER_USER_DATA = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"
BROWSER_CHANNEL = "msedge"


def check_captcha(page):
    selectors = ['.geetest_panel', '[class*="captcha"]', '.layui-layer-content']
    for sel in selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=1000):
                return True
        except:
            pass
    return False


def wait_for_captcha(page, timeout=300):
    print("\n检测到验证码！请手动处理...\n")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if not check_captcha(page):
            print("\n验证码已处理！\n")
            time.sleep(1)
            return True
    print(f"\n等待超时\n")
    return False


def main():
    print("="*60)
    print("中石油 box_data 结构分析")
    print("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_USER_DATA,
            channel=BROWSER_CHANNEL,
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        print("访问列表页...")
        page.goto("https://www.cnpcbidding.com/#/tenders", wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        if check_captcha(page):
            wait_for_captcha(page)

        print("等待 8 秒让数据加载...\n")
        for i in range(8, 0, -1):
            print(f"  {i}...", end='\r')
            time.sleep(1)

        print("\n按回车分析 box_data 结构...")
        input()

        # 深入分析 box_data
        print("\n" + "="*60)
        print("【box_data 元素分析】")
        print("="*60)

        result = page.evaluate("""
        () => {
            const boxDataElements = document.querySelectorAll('.box_data');
            const info = {
                count: boxDataElements.length,
                items: []
            };

            boxDataElements.forEach((el, index) => {
                if (index >= 10) return;

                const item = {
                    index: index,
                    className: el.className,
                    id: el.id,
                    text: (el.innerText || '').substring(0, 100),
                    attributes: {},
                    children: [],
                    hasClick: !!el.onclick,
                    role: el.getAttribute('role'),
                    style: el.getAttribute('style')?.substring(0, 50)
                };

                for (const attr of el.attributes) {
                    if (!['class', 'id', 'style'].includes(attr.name)) {
                        item.attributes[attr.name] = attr.value;
                    }
                }

                const children = el.children;
                for (let i = 0; i < children.length && i < 5; i++) {
                    const child = children[i];
                    item.children.push({
                        tag: child.tagName,
                        class: child.className,
                        id: child.id,
                        text: (child.innerText || '').substring(0, 50)
                    });
                }

                const links = el.querySelectorAll('a');
                if (links.length > 0) {
                    item.links = Array.from(links).map(link => ({
                        href: link.href,
                        text: (link.innerText || '').substring(0, 50),
                        id: link.id,
                        className: link.className
                    }));
                }

                const dataIdEls = el.querySelectorAll('[data-id]');
                if (dataIdEls.length > 0) {
                    item.dataIds = Array.from(dataIdEls).map(el => ({
                        tag: el.tagName,
                        dataId: el.getAttribute('data-id'),
                        text: (el.innerText || '').substring(0, 30)
                    }));
                }

                const buttons = el.querySelectorAll('button');
                if (buttons.length > 0) {
                    item.buttons = Array.from(buttons).map(btn => ({
                        text: btn.innerText,
                        type: btn.type,
                        className: btn.className
                    }));
                }

                info.items.push(item);
            });

            info.localStorage = {
                logo2Length: localStorage.getItem('logo2')?.length || 0,
                logo1Length: localStorage.getItem('logo1')?.length || 0
            };

            return info;
        }
        """)

        print(f"\n找到 {result.get('count', 0)} 个 .box_data 元素")
        print(f"localStorage logo2 长度：{result.get('localStorage', {}).get('logo2Length', 0)}")
        print(f"localStorage logo1 长度：{result.get('localStorage', {}).get('logo1Length', 0)}")

        items = result.get('items', [])
        for item in items[:5]:
            print("\n" + "-"*60)
            print(f"【第 {item.get('index', 0)+1} 个 box_data】")
            print(f"类名：{item.get('className', '')}")
            print(f"ID: {item.get('id', '')}")
            print(f"文本：{item.get('text', '')[:80]}")
            print(f"hasClick: {item.get('hasClick', False)}")
            print(f"role: {item.get('role', '')}")
            print(f"style: {item.get('style', '')}")

            attrs = item.get('attributes', {})
            if attrs:
                print(f"其他属性：{attrs}")

            children = item.get('children', [])
            if children:
                print(f"子元素 ({len(children)} 个):")
                for c in children:
                    print(f"    <{c.get('tag', '')}> class={c.get('class', '')}: {c.get('text', '')[:40]}")

            links = item.get('links', [])
            if links:
                print(f"内部 <a> 标签 ({len(links)} 个):")
                for l in links:
                    print(f"    href={l.get('href', '')[:60]} text={l.get('text', '')[:30]}")

            data_ids = item.get('dataIds', [])
            if data_ids:
                print(f"data-id 元素 ({len(data_ids)} 个):")
                for d in data_ids:
                    print(f"    {d.get('tag', '')} data-id={d.get('dataId', '')} text={d.get('text', '')[:20]}")

            buttons = item.get('buttons', [])
            if buttons:
                print(f"button 元素 ({len(buttons)} 个):")
                for b in buttons:
                    print(f"    {b.get('text', '')} type={b.get('type', '')}")

        print("\n" + "="*60)

        print("\n【查找所有 data-* 属性】")
        data_attrs = page.evaluate("""
        () => {
            const allEls = document.querySelectorAll('[data-id], [data-index], [data-type], [data-key]');
            const results = [];
            allEls.forEach(el => {
                if (el.innerText && el.innerText.trim().length > 5) {
                    results.push({
                        tag: el.tagName,
                        'data-id': el.getAttribute('data-id'),
                        'data-index': el.getAttribute('data-index'),
                        class: (el.className || '').split(' ').slice(0, 3).join(' '),
                        text: (el.innerText || '').substring(0, 60)
                    });
                }
            });
            return results.slice(0, 20);
        }
        """)

        if data_attrs:
            for d in data_attrs:
                print(f"  {d.get('tag', '')} data-id={d.get('data-id', 'N/A')} : {d.get('text', '')[:50]}")
        else:
            print("  未找到 data-* 属性元素")

        print("\n" + "="*60)
        input("\n按回车退出...")
        browser.close()


if __name__ == "__main__":
    main()
