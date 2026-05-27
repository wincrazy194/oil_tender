"""
诊断中石油网站结构
"""
import logging
import sys
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

def main():
    print("=" * 60)
    print("诊断中石油网站结构")
    print("=" * 60)

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page()

        # 注入 stealth 脚本
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        """)

        # 访问列表页
        url = "https://www.cnpcbidding.com/#/tenders"
        logger.info(f"访问：{url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(15)  # 等待更长时间

        # 获取页面 HTML 长度
        html_length = page.evaluate("() => document.documentElement.outerHTML.length")
        logger.info(f"页面 HTML 长度：{html_length}")

        # 检查各种可能的选择器
        selectors = [
            '.item-card',
            '.el-table__body tr',
            '.el-table__row',
            '.tender-item',
            '.list-item',
            '.item-box',
            '.data-row',
            'table tr',
            '.commodityDetails-contail-header-left',
            '.left_top',
            '.item-card-conent-title',
            '.el-table',
            '.el-table__body',
            'tbody tr',
            '.publicity-item',
            '.result-item',
            'a[href*="tender"]',
            'a[href*="detail"]',
            'div[class*="tender"]',
            'div[class*="item"]',
        ]

        logger.info("检查各选择器匹配的元素数量:")
        for sel in selectors:
            try:
                count = page.locator(sel).count()
                logger.info(f"  {sel}: {count} 个元素")
            except Exception as e:
                logger.info(f"  {sel}: 错误 - {e}")

        # 查找包含日期格式的文本
        logger.info("查找包含日期的元素...")
        date_elements = page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('div, span, p, a, td, th').forEach(el => {
                const text = el.innerText?.trim();
                if (text && text.length > 5 && /202[0-9]-[0-9]{2}-[0-9]{2}/.test(text)) {
                    result.push({
                        tag: el.tagName,
                        className: String(el.className || ''),
                        text: text.substring(0, 150).replace(/\n/g, ' | ')
                    });
                }
            });
            return result.slice(0, 15);
        }""")

        for el in date_elements:
            logger.info(f"  找到：tag={el['tag']}, class={el['className'][:50]}, text={el['text'][:80]}")

        # 查找所有链接
        logger.info("查找页面中的链接...")
        links = page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.getAttribute('href');
                const text = a.innerText?.trim() || '';
                if (href && href.length > 5 && text.length > 0) {
                    result.push({ href, text: text.substring(0, 50) });
                }
            });
            return result.slice(0, 20);
        }""")

        for link in links:
            logger.info(f"  链接：{link['href'][:60]} - {link['text']}")

        # 截图
        page.screenshot(path='debug/cnpc_structure.png', full_page=True)
        logger.info("已保存截图：debug/cnpc_structure.png")

        # 获取并打印部分 HTML 结构
        html_sample = page.evaluate("""() => {
            const body = document.body.innerHTML;
            return body.substring(0, 5000);
        }""")
        logger.info(f"页面 HTML 样本（前 5000 字符）: {html_sample[:500]}...")

        browser.close()

    print("=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
