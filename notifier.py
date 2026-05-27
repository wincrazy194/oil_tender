"""
邮件通知模块 - 负责整理每日情报并发送邮件
"""
import smtplib
import os
import time
import logging
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config import (
    EMAIL_ENABLED, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVERS, EMAIL_SUBJECT
)

logger = logging.getLogger(__name__)

class Notifier:
    def send_daily_report(self, records: list[dict], excel_path: str = "", zip_path: str = ""):
        """发送每日情报汇总邮件（只发送 IT 相关）"""
        if not EMAIL_ENABLED:
            logger.info("邮件通知已禁用。")
            return

        # 只保留 IT 相关记录（使用 AI 判断结果）
        it_records = []
        for r in records:
            if r.get("is_it_related", False) or r.get("category", "").startswith("IT 业务"):
                it_records.append(r)

        if not it_records:
            logger.info("今日无 IT 相关新记录，跳过邮件发送。")
            return

        try:
            msg = MIMEMultipart()
            msg["Subject"] = EMAIL_SUBJECT
            msg["From"] = EMAIL_SENDER
            msg["To"] = ", ".join(EMAIL_RECEIVERS)

            # 构建 HTML 内容
            html_content = "<h3>每日情报汇总（IT 业务）</h3>"
            html_content += self._build_section("💻 IT 业务", it_records)
            html_content += "<p>注：详细内容请查看附件 Excel 文件及 HTML 存档压缩包。</p>"

            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 添加 Excel 附件
            if excel_path and os.path.exists(excel_path):
                with open(excel_path, "rb") as f:
                    part = MIMEApplication(f.read())
                    part.add_header("Content-Disposition", "attachment", filename=os.path.basename(excel_path))
                    msg.attach(part)
                logger.info(f"已添加 Excel 附件：{excel_path}")

            # 添加 HTML 存档 ZIP 附件
            if zip_path and os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    zip_part = MIMEApplication(f.read())
                    zip_part.add_header("Content-Disposition", "attachment", filename=os.path.basename(zip_path))
                    msg.attach(zip_part)
                logger.info(f"已添加 HTML 存档 ZIP 附件：{zip_path}")

            # 发送邮件 (使用 SSL)，最多重试 3 次
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    with smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=30) as server:
                        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                        server.send_message(msg)
                    logger.info(f"邮件已成功发送至：{EMAIL_RECEIVERS}")
                    return
                except Exception as send_err:
                    if attempt < max_retries:
                        wait = attempt * 5
                        logger.warning(f"邮件发送失败 (尝试 {attempt}/{max_retries})，{wait}秒后重试：{send_err}")
                        time.sleep(wait)
                    else:
                        logger.error(f"邮件发送失败（已重试 {max_retries} 次）：{send_err}")
        except Exception as e:
            logger.error(f"邮件准备失败：{e}")

    def _build_section(self, section_title: str, records: list[dict]) -> str:
        """构建一个分类板块的 HTML"""
        section = f"<h4 style='background-color: #e3f2fd; padding: 10px; margin: 20px 0 10px 0;'>{section_title}</h4>"
        section += """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>来源</th><th>标题</th><th>分类</th><th>日期</th><th>摘要</th><th>链接</th>
            </tr>
        """
        for r in records:
            company = html.escape(r.get('company', ''))
            title = html.escape(r['title'][:80])
            category = html.escape(r['category'])
            publish_date = html.escape(r.get('publish_date', ''))

            # 获取摘要逻辑：优先使用 summary，其次使用 content 前 100 字，最后使用标题
            summary = r.get('summary', '')
            if not summary:
                content = r.get('content', '')
                if content and len(content) > 100:
                    # 从详情内容中提取前 100 字作为摘要
                    summary = content[:100].replace('\n', '').strip() + '...'
                else:
                    # 没有详情内容，使用标题作为摘要
                    summary = r['title']
            summary = html.escape(summary.replace('\n', '').strip())
            summary_display = summary[:150] + ('...' if len(summary) > 150 else '')

            # 处理 URL，防止 QQ 邮件安全拦截
            # 注意：不要对 # 进行编码，因为中海油/中石化使用哈希路由（#/...）
            # 如果 # 被编码成 %23，浏览器会当作普通路径而不是哈希路由，导致 400 错误
            url = r.get('url', '')
            safe_url = url.replace('"', '&quot;')  # 只转义双引号，防止 HTML 注入

            section += f"""
            <tr>
                <td>{company}</td>
                <td>{title}</td>
                <td>{category}</td>
                <td>{publish_date}</td>
                <td style="max-width: 300px; font-size: 12px;">{summary_display}</td>
                <td><a href="{safe_url}" target="_blank">查看</a></td>
            </tr>
            """
        section += "</table>"
        return section
