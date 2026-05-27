"""
诊断中石油网站结构 - 简化版
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
        # 启动浏览器 - 使用有头模式
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

        # 访问列表页
        url = "https://www.cnpcbidding.com/#/tenders"
        logger.info(f"访问：{url}")

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            logger.warning(f"页面加载超时，继续：{e}")

        # 等待更长时间
        logger.info("等待 30 秒让数据加载...")
        for i in range(30, 0, -1):
            time.sleep(1)
            count = page.locator('div, span, tr, td, a').count()
            if i % 5 == 0:
                logger.info(f"  等待中...{i}秒，当前元素数量：{count}")

        # 获取页面 HTML 长度
        html_length = page.evaluate("() => document.documentElement.outerHTML.length")
        logger.info(f"页面 HTML 长度：{html_length}")

        # 尝试查找所有 div 和 tr 元素
        div_count = page.locator('div').count()
        tr_count = page.locator('tr').count()
        td_count = page.locator('td').count()
        a_count = page.locator('a').count()

        logger.info(f"元素统计：div={div_count}, tr={tr_count}, td={td_count}, a={a_count}")

        # 获取页面文本内容
        page_text = page.evaluate("() => document.body.innerText")
        logger.info(f"页面文本长度：{len(page_text)}")

        # 显示前 50 行文本
        lines = page_text.split('\n')
        logger.info("页面前 30 行文本:")
        for i, line in enumerate(lines[:30]):
            if line.strip():
                logger.info(f"  {line.strip()[:80]}")

        # 截图
        try:
            screenshot_path = os.path.join(os.path.dirname(__file__), 'debug', 'cnpc_page.png')
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"已保存截图：{screenshot_path}")
        except Exception as e:
            logger.warning(f"截图失败：{e}")
            page.screenshot(path='cnpc_page.png')
            logger.info("已保存截图到当前目录：cnpc_page.png")

        browser.close()

    print("=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
