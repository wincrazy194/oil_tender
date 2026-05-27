"""
单独测试中海油采集并发送邮件
"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
from config import (
    IT_KEYWORDS, IT_EXCLUDE_KEYWORDS, DATE_START, DATE_END, FLIP_STRATEGY, FETCH_PAGES,
    DETAIL_URL_TEMPLATES
)
from utils import is_it_related_by_keywords

# 强 IT 关键词列表
STRONG_IT_KEYWORDS = ["信息安全", "网络安全", "软件", "信息系统", "数据库", "服务器", "AI", "人工智能", "大模型"]

def is_it_related_batch_with_correction(titles):
    """批量判断 IT 相关性，包含关键词复核"""
    result = {}
    for i, title in enumerate(titles):
        # 先用关键词判断
        keyword_result = is_it_related_by_keywords(title, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS)
        result[i] = keyword_result

        # 如果关键词判断为非 IT，但包含强 IT 关键词，则纠正
        if not keyword_result:
            title_lower = title.lower()
            has_strong_it = any(kw.lower() in title_lower for kw in STRONG_IT_KEYWORDS)
            if has_strong_it:
                has_exclude = any(kw.lower() in title_lower for kw in IT_EXCLUDE_KEYWORDS)
                if not has_exclude:
                    result[i] = True
                    print(f"    [关键词纠正] {title[:50]}... -> 非 IT 改为 IT")

    return result


def construct_cnooc_url(article_id: str) -> str:
    """构造中海油 URL"""
    base = "https://bid.cnooc.com.cn/home/#/newsAlertDetails"
    params = {
        "index": "0",
        "childrenActive": "4",
        "id": article_id,
        "type": "null"
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{query}"


def collect_cnooc_test(max_pages=5):
    """采集中海油数据（测试版，限制页数）"""
    print("\n" + "=" * 80)
    print("开始采集 中海油 数据（测试版）")
    print("=" * 80)

    base_url = "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD"
    user_data_dir = r"E:\nandaoshuo\oil_tender\api_test\browser_data_cnooc_test"

    # 清理 SingletonLock
    lock_file = os.path.join(user_data_dir, "SingletonLock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print(f"   [Lock 清理] 已删除：{lock_file}")
        except:
            pass

    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="msedge",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )
    page = context.pages[0] if context.pages else context.new_page()

    all_records = []
    category_name = "招标公告"

    print(f"\n正在采集：{category_name}")
    page.goto(base_url, wait_until="networkidle", timeout=60000)

    print("   等待数据加载...")
    try:
        page.wait_for_selector('.table_page li, [class*="news-item"], .news-list li', timeout=10000)
        time.sleep(0.5)
    except:
        time.sleep(2)

    seen_keys = set()
    current_page = 1

    while current_page <= max_pages:
        print(f"\n  [招标公告] 第 {current_page} 页...")

        articles = page.evaluate(r"""
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

            let rowIndex = 0;
            for (const row of allRows) {
                const titleEl = row.querySelector('.table_title span') ||
                               row.querySelector('[class*="title"]') ||
                               row.querySelector('span');
                const dateEl = row.querySelector('.table_time') ||
                              row.querySelector('[class*="date"]') ||
                              row.querySelector('[class*="time"]');

                if (titleEl && dateEl) {
                    const title = titleEl.textContent.trim();
                    const publishDate = dateEl.textContent.trim();

                    let id = '';
                    const link = row.querySelector('a');
                    let href = '';

                    if (link) {
                        href = link.getAttribute('href') || '';
                    }

                    id = row.getAttribute('data-id') ||
                        (link ? (link.getAttribute('data-id') || '') : '') ||
                        '';

                    if (!id && link) {
                        const idMatch = href.match(/[?&]id=([a-zA-Z0-9_-]+)/);
                        if (idMatch) {
                            id = idMatch[1];
                        }
                    }

                    if (title && publishDate) {
                        items.push({
                            id: id || '',
                            title: title,
                            publishDate: publishDate,
                            row_index: rowIndex,
                            href: href
                        });
                        rowIndex++;
                    }
                }
            }
            return items;
        }
        """)

        if articles:
            print(f"  获取到 {len(articles)} 条数据（DOM 提取）")

            # 批量 IT 判断
            print(f"  [关键词分类] 正在判断本页 {len(articles)} 条记录...")
            titles_to_check = [a.get('title', '') for a in articles]
            it_results = is_it_related_batch_with_correction(titles_to_check)

            # 打印 IT 相关结果
            it_selected = [(idx, titles_to_check[idx][:60]) for idx, is_it in it_results.items() if is_it]
            if it_selected:
                print(f"  [IT 相关] 共 {len(it_selected)} 条：")
                for idx, title in it_selected:
                    print(f"    [{idx+1}] {title}...")
            else:
                print(f"  [IT 相关] 本页无 IT 相关记录")

            for idx, article in enumerate(articles):
                key = f"{article['title']}{article.get('publishDate', '')}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                title = article.get('title', '')
                is_it = it_results.get(idx, False)

                detail_url = ""
                article_id = article.get('id', '')
                if article_id:
                    detail_url = construct_cnooc_url(article_id)

                record = {
                    "company": "中海油",
                    "title": title,
                    "category": "IT 业务 - 招标公告" if is_it else "招标公告",
                    "publish_date": article.get('publishDate', ''),
                    "url": detail_url,
                    "content": "",
                    "summary": "",
                    "fetched_at": datetime.now().isoformat(),
                    "is_it_related": is_it
                }

                all_records.append(record)

        # 翻页
        if current_page < max_pages:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

            next_clicked = False
            try:
                result = page.evaluate(f"""
                    () => {{
                        const pagers = document.querySelectorAll('.el-pager');
                        const targetPager = pagers[pagers.length - 1];
                        if (!targetPager) return {{ success: false }};

                        const numberLis = targetPager.querySelectorAll('li.number:not(.active)');
                        for (const li of numberLis) {{
                            const text = li.innerText.trim();
                            if (text === '{current_page + 1}') {{
                                const rect = li.getBoundingClientRect();
                                const event = new MouseEvent('click', {{
                                    bubbles: true,
                                    cancelable: true,
                                    view: window,
                                    clientX: rect.left + rect.width / 2,
                                    clientY: rect.top + rect.height / 2
                                }});
                                li.dispatchEvent(event);
                                return {{ success: true, clicked: text }};
                            }}
                        }}
                        return {{ success: false }};
                    }}
                """)
                if result.get('success'):
                    next_clicked = True
                    print(f"  点击页码 {result.get('clicked')} 翻页")
            except:
                pass

            if not next_clicked:
                try:
                    result = page.evaluate("""
                        () => {
                            const pagers = document.querySelectorAll('.el-pager');
                            const targetPager = pagers[pagers.length - 1];
                            if (!targetPager) return { success: false };

                            const moreBtn = targetPager.querySelector('.btn-quicknext, li.more, .el-icon-more');
                            if (moreBtn) {
                                const rect = moreBtn.getBoundingClientRect();
                                const event = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window,
                                    clientX: rect.left + rect.width / 2,
                                    clientY: rect.top + rect.height / 2
                                });
                                moreBtn.dispatchEvent(event);
                                return { success: true };
                            }
                            return { success: false };
                        }
                    """)
                    if result.get('success'):
                        next_clicked = True
                        print("  点击 '>' 翻页")
                except:
                    pass

            if next_clicked:
                time.sleep(2)

            if not next_clicked:
                print("  已到达最后一页")
                break

        current_page += 1

    context.close()
    playwright.stop()
    print(f"\n中海油采集完成！共 {len(all_records)} 条")

    # 统计 IT 相关
    it_count = sum(1 for r in all_records if r.get('is_it_related', False))
    print(f"IT 相关记录：{it_count} 条")

    return all_records


def send_test_email(records, company_name):
    """发送测试邮件"""
    from config import (
        EMAIL_ENABLED, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
        EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVERS, EMAIL_SUBJECT
    )
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not EMAIL_ENABLED:
        print("邮件通知已禁用")
        return

    it_records = [r for r in records if r.get("is_it_related", False)]

    if not it_records:
        print(f"无 IT 相关记录，跳过邮件发送")
        return

    print(f"\n准备发送邮件：{len(it_records)} 条 IT 相关记录")

    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"【测试邮件】{company_name}IT 招标数据"
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(EMAIL_RECEIVERS)

        # 构建 HTML 内容
        html_content = f"<h3>{company_name} IT 招标数据（测试）</h3>"
        html_content += f"<p>采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        html_content += f"<p>IT 相关记录数：{len(it_records)}</p>"
        html_content += """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>来源</th><th>标题</th><th>分类</th><th>日期</th><th>链接</th>
            </tr>
        """
        for r in it_records:
            html_content += f"""
            <tr>
                <td>{r.get('company', '')}</td>
                <td>{r['title'][:80]}</td>
                <td>{r.get('category', '')}</td>
                <td>{r.get('publish_date', '')}</td>
                <td><a href="{r.get('url', '#')}">查看</a></td>
            </tr>
            """
        html_content += "</table>"

        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # 发送邮件
        with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"邮件已成功发送至：{EMAIL_RECEIVERS}")
    except Exception as e:
        print(f"邮件发送失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    records = collect_cnooc_test(max_pages=3)

    # 保存结果
    output_file = r"E:\nandaoshuo\oil_tender\api_test\cnooc_test_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到：{output_file}")

    # 发送邮件
    send_test_email(records, "中海油")
