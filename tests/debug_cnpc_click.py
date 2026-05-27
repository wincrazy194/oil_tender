"""
诊断中石油网站 - 尝试点击和滚动
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
    print("诊断中石油网站 - 尝试点击和滚动")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled",
            "--window-size=1920,1080"
        ])
        page = browser.new_page()

        # 注入 stealth 脚本
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5], length: 5 });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'], length: 2 });
        """)

        # 直接访问招标公告 API 或路由
        # 尝试不同的 URL
        urls = [
            "https://www.cnpcbidding.com/#/tenders",
            "https://www.cnpcbidding.com/#/tenders/list",
            "https://www.cnpcbidding.com/#/tenderAnnouncement",
        ]

        for i, url in enumerate(urls[:1]):  # 只试第一个
            logger.info(f"尝试 URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(10)

            # 尝试滚动到底部
            logger.info("尝试滚动页面...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(3)

            # 检查元素
            div_count = page.locator('div').count()
            tr_count = page.locator('tr').count()
            td_count = page.locator('td').count()

            logger.info(f"元素统计：div={div_count}, tr={tr_count}, td={td_count}")

            # 查找所有按钮和链接
            buttons = page.locator('button, a, li[role="tab"], .el-tab-item').all()
            logger.info(f"找到 {len(buttons)} 个可点击元素")

            for j, btn in enumerate(buttons[:10]):
                try:
                    text = btn.inner_text(timeout=1000).strip()
                    if text and len(text) < 30:
                        logger.info(f"  [{j}] {text}")
                except:
                    pass

            # 尝试点击包含"招标"或"公告"的按钮
            for btn in buttons:
                try:
                    text = btn.inner_text(timeout=1000).strip().lower()
                    if '招标' in text or '公告' in text or 'tender' in text.lower():
                        logger.info(f"尝试点击：{text}")
                        btn.click()
                        time.sleep(5)
                        break
                except:
                    continue

            # 再次检查
            tr_count = page.locator('tr').count()
            td_count = page.locator('td').count()
            logger.info(f"点击后元素统计：tr={tr_count}, td={td_count}")

            if tr_count > 0:
                break

        # 截图
        screenshot_path = os.path.join(os.path.dirname(__file__), 'debug', 'cnpc_after_click.png')
        page.screenshot(path=screenshot_path)
        logger.info(f"已保存截图：{screenshot_path}")

        # 获取当前 URL
        current_url = page.url
        logger.info(f"当前 URL: {current_url}")

        # 获取页面 HTML 中的关键信息
        page_text = page.evaluate("() => document.body.innerText")
        logger.info(f"页面文本长度：{len(page_text)}")

        # 显示包含日期的行
        date_lines = [l for l in page_text.split('\n') if '202' in l and len(l) > 5]
        if date_lines:
            logger.info(f"找到 {len(date_lines)} 行包含日期的文本:")
            for line in date_lines[:10]:
                logger.info(f"  {line.strip()[:80]}")
        else:
            logger.info("没有找到包含日期的文本")

        browser.close()

    print("=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
