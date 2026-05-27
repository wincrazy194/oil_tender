"""
==============================================================================
中石油 HTML 存档生成与 ZIP 打包模块
==============================================================================

功能说明:
    本模块用于将数据库中存储的中石油 IT 招标公告数据生成为 HTML 存档文件，
    并打包成 ZIP 压缩包，便于通过邮件发送给收件人查看。

主要功能:
    1. 从 SQLite 数据库中读取 IT 相关的招标公告记录
    2. 为中石油记录生成独立的 HTML 详情页（含美观的样式）
    3. 生成索引文件 index.html（包含所有公司的招标公告列表）
    4. 将所有生成的 HTML 文件打包成 ZIP 压缩包

文件结构:
    output/
      html_archive/                    # 输出根目录 (OUTPUT_DIR)
        index.html                     # 索引/列表页
        archives/
          cnpc/
            20240325_xxx.html          # 中石油详情页

使用方式:
    1. 直接运行: python generate_html_archive.py
    2. 作为模块导入: from generate_html_archive import main

输出:
    - HTML 文件：output/html_archive/
    - ZIP 文件：output/tender_archive_YYYYMMDD_HHMMSS.zip

作者：招投标数据采集系统
版本：1.0
==============================================================================
"""

import os
import sqlite3
import re
import json
import zipfile
import html
from datetime import datetime
from shutil import rmtree

# ==============================================================================
# 路径配置
# ==============================================================================
# 数据库路径：存储招标公告数据的 SQLite 数据库
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "oil_tender.db")

# 输出目录：生成的 HTML 文件存放目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "html_archive")

# 索引模板：index.html 的模板文件路径
INDEX_TEMPLATE = os.path.join(BASE_DIR, "index_template.html")


def safe_filename(title: str) -> str:
    """
    生成安全的文件名

    作用:
        将招标公告标题转换为符合文件系统规范的文件名，
        移除可能导致问题的特殊字符，限制长度。

    参数:
        title: 招标公告标题字符串

    返回:
        str: 处理后的安全文件名（不含扩展名）

    处理规则:
        1. 移除 Windows 文件名非法字符：\\ / : * ? " < > |
        2. 限制长度最多 50 个字符
        3. 移除首尾的空格和下划线

    示例:
        >>> safe_filename("测试/标题：公告<重要>")
        '测试_标题_公告_重要'
    """
    # 移除非法字符（Windows 文件名不允许的字符）
    safe = re.sub(r'[\\/:*?"<>|]', '_', title)
    # 限制长度（防止文件名过长导致文件系统问题）
    safe = safe[:50]
    # 移除前后空格和下划线（美化文件名）
    safe = safe.strip('_ ')
    return safe


def generate_html_archive(record: dict) -> str:
    """
    生成单条记录的 HTML 存档文件

    作用:
        将一条招标公告记录转换为一个独立的 HTML 详情页文件，
        包含完整的样式和格式，可在浏览器中直接查看。

    参数:
        record: 数据库记录字典，包含以下字段:
            - company: 公司名称（如"中石油"）
            - title: 招标公告标题
            - content: 招标公告正文内容
            - publish_date: 发布日期
            - url: 原始网页链接
            - summary: AI 生成的摘要

    返回:
        str: 生成的 HTML 文件相对路径（相对于 OUTPUT_DIR）
            例如："archives/cnpc/20240325_xxx.html"
            如果跳过或失败则返回空字符串

    处理逻辑:
        1. 只处理中石油的记录（其他公司不生成独立 HTML）
        2. 没有内容的记录会被跳过
        3. 生成的 HTML 文件存放在 archives/cnpc/ 子目录下
        4. 文件名格式：发布日期_标题.html

    样式特点:
        - 渐变背景头部
        - 响应式布局（支持移动端）
        - 元数据卡片展示（公司、日期、类别）
        - 摘要框高亮显示
        - 正文内容滚动区域
        - 返回列表按钮（../../index.html）
    """
    # 从记录中提取字段
    company = record.get('company', '')
    title = record.get('title', '')
    content = record.get('content', '')
    publish_date = record.get('publish_date', '')
    url = record.get('url', '')
    summary = record.get('summary', '')

    # 对 content 进行 HTML 转义，防止内容中的 HTML 标签破坏页面结构
    # 例如：</div> 会导致提前闭合，<script> 会执行恶意代码
    if content:
        content = html.escape(content)

    # 只处理中石油的记录（其他公司使用官网链接）
    if company != '中石油':
        return ""

    # 没有正文内容则跳过（生成无意义的空页面）
    if not content:
        print(f"  [警告] 跳过（无内容）: {title[:30]}...")
        return ""

    # 创建公司目录（中石油 = cnpc）
    company_dir = os.path.join(OUTPUT_DIR, "archives", "cnpc")
    os.makedirs(company_dir, exist_ok=True)

    # 生成文件名
    # 日期格式转换：2024-03-25 -> 20240325
    date_str = publish_date.replace('-', '') if publish_date else datetime.now().strftime('%Y%m%d')
    safe_title = safe_filename(title)
    filename = f"{date_str}_{safe_title}.html"
    filepath = os.path.join(company_dir, filename)
    # 相对路径（用于数据库记录和索引文件引用）
    relative_path = f"archives/cnpc/{filename}"

    # 生成 HTML 内容（使用 f-string 注入数据）
    # 注意：样式中的 { } 需要用 {{ }} 转义
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 中石油</title>
    <style>
        /* 全局重置 */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.8;
            color: #2c3e50;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
            animation: fadeIn 0.5s ease-out;
        }}
        /* 淡入动画 */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ========== 头部样式 ========== */
        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%);
            color: white;
            padding: 40px;
            position: relative;
            overflow: hidden;
        }}
        /* 装饰圆形背景 */
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 200px;
            height: 200px;
            background: rgba(255,255,255,0.1);
            border-radius: 50%;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: -30%;
            left: 5%;
            width: 150px;
            height: 150px;
            background: rgba(255,255,255,0.08);
            border-radius: 50%;
        }}
        .header h1 {{
            font-size: 26px;
            margin-bottom: 20px;
            line-height: 1.4;
            position: relative;
            z-index: 1;
        }}
        /* 元数据行 */
        .meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 14px;
            opacity: 0.95;
            position: relative;
            z-index: 1;
        }}
        /* 元数据项卡片 */
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.15);
            padding: 8px 15px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}
        .meta-icon {{
            font-size: 16px;
        }}
        /* 返回按钮 */
        .back-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 24px;
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            margin-top: 20px;
            font-size: 14px;
            transition: all 0.3s ease;
            position: relative;
            z-index: 1;
        }}
        .back-btn:hover {{
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }}

        /* ========== 内容区域 ========== */
        .content {{
            padding: 40px;
        }}

        /* 摘要框 */
        .summary-box {{
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 5px solid #3b82f6;
            padding: 20px 25px;
            margin-bottom: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(59,130,246,0.1);
        }}
        .summary-box h3 {{
            font-size: 15px;
            color: #1d4ed8;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }}
        .summary-box p {{
            font-size: 14px;
            color: #475569;
            line-height: 1.8;
        }}

        /* 正文内容标题 */
        .content-title {{
            font-size: 20px;
            color: #1e3a8a;
            margin: 30px 0 20px 0;
            padding-bottom: 12px;
            border-bottom: 2px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        /* 正文内容区域（带滚动条） */
        .content-body {{
            white-space: pre-wrap;
            font-size: 15px;
            color: #334155;
            line-height: 2;
            padding: 25px;
            background: #f8fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }}
        /* 自定义滚动条样式 */
        .content-body::-webkit-scrollbar {{
            width: 8px;
        }}
        .content-body::-webkit-scrollbar-track {{
            background: #f1f5f9;
            border-radius: 4px;
        }}
        .content-body::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 4px;
        }}
        .content-body::-webkit-scrollbar-thumb:hover {{
            background: #94a3b8;
        }}

        /* ========== 页脚 ========== */
        .footer {{
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            padding: 25px 40px;
            text-align: center;
            font-size: 13px;
            color: #64748b;
            border-top: 1px solid #e2e8f0;
        }}
        .footer p {{
            margin: 5px 0;
        }}
        .footer .divider {{
            display: inline-block;
            width: 40px;
            height: 2px;
            background: #cbd5e1;
            margin: 10px 0;
            border-radius: 2px;
        }}

        /* ========== 响应式设计（移动端适配） ========== */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .header {{ padding: 25px; }}
            .header h1 {{ font-size: 20px; }}
            .meta {{ flex-direction: column; gap: 10px; }}
            .content {{ padding: 25px; }}
            .content-body {{ font-size: 14px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 {title}</h1>
            <div class="meta">
                <div class="meta-item">
                    <span class="meta-icon">🏢</span>
                    <span>中国石油</span>
                </div>
                <div class="meta-item">
                    <span class="meta-icon">📅</span>
                    <span>{publish_date or '未知'}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-icon">📁</span>
                    <span>招标公告</span>
                </div>
            </div>
            <!--
                返回列表按钮
                路径说明：当前文件在 archives/cnpc/ 目录下
                使用绝对路径（相对于当前 HTML 文件位置）确保跳转可靠
            -->
            <a href="javascript:void(0)" class="back-btn" onclick="goBack(); return false;">
                <span>←</span>
                <span>返回列表</span>
            </a>
            <script>
                function goBack() {{
                    /* 方案 1：尝试使用浏览器历史记录返回 */
                    if (window.history.length > 1) {{
                        window.history.back();
                        /* 2 秒后如果还在详情页，强制跳转 */
                        setTimeout(function() {{
                            if (window.location.pathname.indexOf('cnpc') !== -1) {{
                                forceGoToIndex();
                            }}
                        }}, 2000);
                    }} else {{
                        forceGoToIndex();
                    }}
                }}
                function forceGoToIndex() {{
                    /* 方案 2：使用相对路径跳转
                       当前文件：archives/cnpc/xxx.html
                       目标文件：index.html（在 archives 的上一级，即 html_archive 目录）
                       路径：archives/cnpc/xxx.html → archives/ → html_archive/index.html
                       所以需要：../../index.html */
                    window.location.href = '../../index.html';
                }}
            </script>
        </div>

        <div class="content">
            <div class="summary-box">
                <h3><span>📝</span> 摘要</h3>
                <p>{summary or '无摘要'}</p>
            </div>

            <h2 class="content-title"><span>📄</span> 公告详情</h2>
            <div class="content-body">
{content}
            </div>
        </div>

        <div class="footer">
            <p>此文件由招投标数据采集系统自动生成</p>
            <span class="divider"></span>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""

    # 写入文件（使用 UTF-8 编码支持中文）
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  [OK] 已生成：{relative_path}")
    return relative_path


def generate_index(records: list, html_files: dict) -> str:
    """
    生成 index.html 索引文件（招标公告列表页）

    作用:
        读取模板文件，注入所有招标公告数据，生成包含完整列表的索引页面。
        用户打开此文件后可浏览所有公告并点击查看详情。

    参数:
        records: 数据库记录列表，每条记录包含:
            - id: 记录 ID
            - company: 公司名称
            - title: 标题
            - publish_date: 发布日期
            - category: 类别
            - url: 官网链接
        html_files: 中石油 HTML 文件映射字典
            格式：{record_id: "archives/cnpc/xxx.html"}

    返回:
        str: 索引文件的绝对路径

    处理逻辑:
        1. 读取 index_template.html 模板
        2. 为每条记录生成数据对象:
           - 中石油：使用本地生成的 HTML 文件路径
           - 中石化/中海油：使用官网 URL 链接
        3. 将数据注入模板的 JavaScript 变量
        4. 写入 output/html_archive/index.html

    模板注入方式:
        - 替换 'const records = [];' 为实际数据数组
        - 数据包含：标题、公司、日期、类别、HTML 文件路径、是否本地文件
    """
    # 读取模板文件
    with open(INDEX_TEMPLATE, 'r', encoding='utf-8') as f:
        template = f.read()

    # 准备注入数据
    data = []
    for r in records:
        record_id = r.get('id') or r.get('url', '')
        company = r.get('company', '')

        # 中石油：使用本地生成的 HTML 文件
        # 优点：内容已保存，无需联网即可查看
        if company == '中石油' and record_id in html_files:
            view_link = html_files[record_id]
        else:
            # 中石化/中海油：使用官网链接（需联网访问）
            view_link = r.get('url', '#')

        data.append({
            'title': r.get('title', ''),
            'company': company,
            'publish_date': r.get('publish_date', ''),
            'category': r.get('category', '招标公告'),
            'view_link': view_link,
            # 标记是否为本地 HTML（用于决定按钮文本："查看" vs "官网"）
            'is_local_html': company == '中石油' and record_id in html_files
        })

    # 用 json.dumps 安全序列化，避免 JS 注入
    js_records = []
    for d in data:
        js_records.append({
            'title': d['title'],
            'company': d['company'],
            'publish_date': d['publish_date'],
            'category': d['category'],
            'html_file': d['view_link'],
            'isLocalHtml': d['is_local_html']
        })
    records_json = json.dumps(js_records, ensure_ascii=False, indent=2)
    template = template.replace('const records = [];', 'const records = ' + records_json + ';')

    # 写入索引文件
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"[OK] 已生成索引文件：index.html")
    return index_path


def create_zip() -> str:
    """
    将生成的 HTML 文件打包成 ZIP 压缩包

    作用:
        将 output/html_archive/ 目录下的所有文件（包括 index.html
        和 archives/子目录）打包为一个 ZIP 文件，便于邮件发送。

    返回:
        str: ZIP 文件的绝对路径

    文件命名:
        tender_archive_YYYYMMDD_HHMMSS.zip
        例如：tender_archive_20240325_143022.zip

    压缩包结构:
        tender_archive_xxx.zip
        ├── index.html              # 索引页（入口文件）
        └── archives/
            └── cnpc/
                ├── 20240325_xxx.html
                └── ...

    使用说明:
        收件人下载 ZIP 后，解压并双击打开 index.html 即可查看所有公告
    """
    # 生成带时间戳的文件名（避免重复）
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    # ZIP 文件放在 OUTPUT_DIR 的父目录下（即 output/）
    zip_path = os.path.join(os.path.dirname(OUTPUT_DIR), f"tender_archive_{date_str}.zip")

    # 创建 ZIP 文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 递归遍历 OUTPUT_DIR 下的所有文件
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # 计算相对路径（作为 ZIP 内部路径）
                arcname = os.path.relpath(file_path, OUTPUT_DIR)
                zipf.write(file_path, arcname)

    # 获取并打印 ZIP 文件大小
    zip_size = os.path.getsize(zip_path)
    print(f"\\n[OK] 已打包：{zip_path}")
    print(f"  压缩包大小：{zip_size / 1024 / 1024:.2f} MB")

    return zip_path


def main():
    """
    主函数 - 执行完整的 HTML 存档生成和打包流程

    执行步骤:
        1. 清理旧的输出目录
        2. 从数据库读取 IT 相关的招标公告记录
        3. 为中石油记录生成 HTML 详情页
        4. 生成索引文件（包含所有公司）
        5. 打包成 ZIP

    数据库查询:
        - 只查询 IT 相关的记录 (is_it_related = 1)
        - 只查询有内容的记录 (content IS NOT NULL AND length > 0)
        - 按发布日期降序排列

    输出结果:
        - 控制台打印生成的文件路径
        - 返回 ZIP 文件路径

    使用方式:
        if __name__ == "__main__":
            main()
    """
    print("=" * 60)
    print("生成中石油 HTML 存档并打包")
    print("=" * 60)

    # 清理旧的输出目录（防止文件堆积）
    # 如果目录存在但无法删除（被占用），则直接使用
    if os.path.exists(OUTPUT_DIR):
        try:
            rmtree(OUTPUT_DIR)
        except:
            print("  [注意] 旧目录无法删除，将直接覆盖")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 从数据库获取数据
    print("\\n正在从数据库读取数据...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使用 Row 工厂，可通过列名访问
    cursor = conn.cursor()

    # 查询所有公司的 IT 相关记录（必须有内容）
    cursor.execute("""
        SELECT id, company, title, category, publish_date, url, content, summary, fetched_at
        FROM tenders
        WHERE is_it_related = 1
          AND content IS NOT NULL
          AND length(content) > 0
        ORDER BY publish_date DESC
    """)

    records = [dict(row) for row in cursor.fetchall()]
    conn.close()

    print(f"找到 {len(records)} 条记录（有内容）")

    # 生成 HTML 存档（只处理中石油）
    print("\\n正在生成 HTML 存档...")
    html_files = {}  # {record_id: relative_path}
    for r in records:
        if r.get('company') == '中石油':
            html_path = generate_html_archive(r)
            if html_path:
                # 使用 ID 或 URL 作为键
                html_files[r.get('id') or r.get('url', '')] = html_path

    # 生成索引文件
    print("\\n正在生成索引文件...")
    generate_index(records, html_files)

    # 打包成 ZIP
    print("\\n正在打包成 ZIP...")
    zip_path = create_zip()

    # 打印完成信息
    print("\\n" + "=" * 60)
    print("完成！")
    print(f"ZIP 文件位置：{zip_path}")
    print("\\n使用方式:")
    print("1. 将 ZIP 文件作为邮件附件发送")
    print("2. 收件人解压后打开 index.html 查看")
    print("=" * 60)

    return zip_path


if __name__ == "__main__":
    main()
