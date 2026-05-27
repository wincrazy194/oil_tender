"""
三家公司（中石油、中石化、中海油）API 统一采集脚本
使用浏览器采集数据
"""
import os
import json
import time
import re
import subprocess
import requests
import logging

from datetime import datetime
from typing import Optional

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from playwright.sync_api import sync_playwright
from config import (
    IT_KEYWORDS, IT_EXCLUDE_KEYWORDS, DATE_START, DATE_END, FLIP_STRATEGY, FETCH_PAGES,
    DETAIL_URL_TEMPLATES, ANTHROPIC_API_KEY, AI_SUMMARY_ENABLED, AI_SUMMARY_MAX_LENGTH
)
from utils import is_token_exhausted_error, is_it_related_by_keywords

logger = logging.getLogger(__name__)


def generate_ai_summary(content: str, title: str, max_retries: int = 2) -> str:
    """
    使用阿里云 DashScope HTTP API 生成招标公告摘要

    Args:
        content: 招标公告原文内容
        title: 招标公告标题
        max_retries: 最大重试次数（模型切换次数）

    Returns:
        str: 生成的摘要（20-60 字），失败返回空字符串

    功能特性:
        - 支持多模型自动切换（当 Token 不足时）
        - 使用 DashScope compatible-mode API
        - 自动降级处理
    """
    if not AI_SUMMARY_ENABLED:
        print("    [AI 摘要] 跳过：AI_SUMMARY_ENABLED={}".format(AI_SUMMARY_ENABLED))
        return ""

    if not content:
        print("    [AI 摘要] 跳过：内容为空")
        return ""

    content_stripped = content.strip()
    if len(content_stripped) < 10:
        print("    [AI 摘要] 跳过：内容太短 ({} 字)".format(len(content_stripped)))
        return ""

    prompt = f"""请为以下招标公告生成一个 20-60 字的精炼摘要，包含项目名称、预算金额（如有）、截止日期（如有）等关键信息：

标题：{title}

公告内容：
{content[:2000]}

请用一句话概括，20-60 字以内，不要多余说明。"""

    # 获取配置
    try:
        from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODELS
    except (ImportError, AttributeError):
        DASHSCOPE_API_KEY = None
        DASHSCOPE_BASE_URL = None
        MODELS = None

    if not DASHSCOPE_API_KEY:
        try:
            from config import ANTHROPIC_API_KEY
            DASHSCOPE_API_KEY = ANTHROPIC_API_KEY
        except:
            pass

    if not DASHSCOPE_API_KEY:
        print("    [AI 摘要] 未配置 API Key")
        return ""

    if not MODELS:
        MODELS = ["deepseek-chat", "deepseek-reasoner"]

    base_url = DASHSCOPE_BASE_URL or "https://api.deepseek.com/v1"
    api_url = base_url.rstrip('/') + '/chat/completions'

    for model_index, model in enumerate(MODELS):
        try:
            print(f"    [AI 摘要] 使用模型：{model} (尝试 {model_index + 1}/{len(MODELS)})")

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的招投标信息分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }

            headers = {
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            }

            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            resp_data = resp.json()

            # 检查是否有错误
            if resp_data.get("error"):
                error_msg = resp_data["error"].get("message", "未知错误")
                error_code = resp_data["error"].get("code", "")

                print(f"    [AI 摘要] 模型 {model} 错误：{error_msg}")

                # 使用公共函数判断是否是 Token 不足错误
                if is_token_exhausted_error(resp.status_code, error_msg):
                    print(f"    [AI 摘要] Token 不足，尝试下一个模型...")
                    continue
                else:
                    # 其他错误，直接返回
                    return ""

            # 成功响应
            if resp.status_code == 200 and resp_data.get("choices"):
                summary = resp_data["choices"][0]["message"]["content"].strip()
                if summary and len(summary) >= 10:
                    print(f"    [AI 摘要] {model} 生成成功：{len(summary)} 字")
                    return summary

            print(f"    [AI 摘要] {model} 返回内容为空")

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response else 500
            logger.warning(f"    [AI 摘要] 模型 {model} HTTP 错误 ({status_code}): {http_err}")
            continue

        except Exception as e:
            logger.warning(f"    [AI 摘要] 模型 {model} 异常：{e}")
            continue

    # 所有模型都尝试失败
    print("    [AI 摘要] 所有模型都失败，返回空")
    return ""


def fetch_detail_content(context, detail_url: str) -> str:
    """
    访问详情页并抓取正文内容（使用并发标签页模式）

    Args:
        context: Playwright 浏览器上下文对象
        detail_url: 详情页 URL

    Returns:
        str: 详情页纯文本内容

    优势:
        1. 稳定性：列表页的翻页位置不会因为页面跳转而重置
        2. 异步降级：新标签页加载即使崩了，也不会影响主程序的循环
        3. 兼容性：自动复用浏览器环境中的 Cookie

    多端适配:
        - 中石油：.content, .article-content
        - 中石化：.main-body (v3 平台)
        - 中海油：.content_body_box_body (多容器适配)
    """
    if not detail_url:
        return ""

    detail_page = None
    try:
        # 1. 开启独立新页面，保证列表页状态不丢失
        detail_page = context.new_page()

        # 2. 访问并等待 DOM 加载
        detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)  # 给动态数据留一点时间

        # 3. 稳健的样式提取（多端适配）
        content = detail_page.evaluate("""
            () => {
                // 多公司多容器选择器列表
                const sels = [
                    // 中海油专属选择器（优先）
                    '.content_body_box_body',
                    // 通用选择器
                    '.content', '.content_body', '.main-body',
                    '.article-content', '.detail-content', '.notice-content',
                    '.article-body', '.article', '.zwgk-content',
                    // PDF 阅读器降级
                    '.pdf-content', 'embed', 'object'
                ];
                for (const s of sels) {
                    const e = document.querySelector(s);
                    if (e && e.innerText.length > 100) return e.innerText;
                }
                // 降级：返回整个页面的文本
                return document.body.innerText;
            }
        """)

        return content.strip() if content else ""

    except Exception as e:
        print(f"   [详情页抓取] 失败：{e}")
        return ""
    finally:
        # 4. 处理完务必关闭，回收内存
        if detail_page:
            try:
                detail_page.close()
            except:
                pass


def fetch_cnpc_detail_by_click(page, item_id: str, list_url: str = None) -> str:
    """
    获取中石油详情页内容（通过点击列表项同页渲染方式）

    Args:
        page: 浏览器页面对象（保持在列表页状态）
        item_id: 文章 ID
        list_url: 列表页 URL，用于紧急恢复

    Returns:
        str: 详情页纯文本内容

    原理:
        1. 在列表页点击对应 ID 的列表项
        2. 页面通过 POST /cms/article/details 获取数据
        3. 详情内容动态渲染在同一页面的 .content 元素中

    注意:
        - 中石油是同页渲染，点击后 URL 不变
        - 不能使用 go_back()，会丢失页码状态
        - 必须点击页面上的返回按钮或重新渲染列表
    """
    if not item_id:
        return ""

    try:
        # 1. 查找并点击对应 ID 的列表项
        selector = f'[data-id="{item_id}"]'
        item = page.query_selector(selector)

        if not item:
            # 如果找不到带 data-id 的元素，点击第一个列表项
            item = page.query_selector('.box_data')
            if not item:
                print("   [中石油详情] 未找到列表项")
                return ""

        # 2. 滚动并点击
        item.scroll_into_view_if_needed()
        time.sleep(0.5)  # 等待页面响应
        item.click(timeout=5000)

        # 3. 等待详情内容加载（智能等待）
        try:
            page.wait_for_selector('.content', timeout=5000)
            print("   [等待] 详情内容已加载")
        except:
            print("   [等待] 超时，尝试提取")
        time.sleep(0.5)  # 等待内容渲染

        # 4. 提取 .content 元素文本
        content_elem = page.query_selector('.content')
        content = ""
        if content_elem:
            content = content_elem.inner_text()
            content = content.strip() if content else ""

        # 降级：尝试其他选择器
        if not content or len(content) < 50:
            for sel in ['.article-content', '.main-body', '.detail-content']:
                elem = page.query_selector(sel)
                if elem:
                    content = elem.inner_text()
                    content = content.strip() if content else ""
                    break

        # 5. 返回列表页状态
        time.sleep(0.5)  # 等待页面恢复

        # 检查是否还在列表页（使用 .box_data 选择器）
        is_list_visible = page.evaluate("""
            () => {
                const items = document.querySelectorAll('.box_data');
                return items.length > 0;
            }
        """)

        if is_list_visible:
            # 已经在列表页，无需返回
            print("   [返回] 已在列表页")
            return content if content else ""

        # 不在列表页，尝试点击返回按钮
        try:
            # 使用 JavaScript 查找并点击返回按钮
            back_clicked = page.evaluate("""
                () => {
                    // 查找包含"返回"文本的按钮
                    const buttons = Array.from(document.querySelectorAll('button, .el-button, [role="button"], a[role="button"]'));
                    for (const btn of buttons) {
                        const text = (btn.innerText || btn.textContent || '').toLowerCase();
                        if (text.includes('返回') || text.includes('back')) {
                            btn.click();
                            return 'text:' + text;
                        }
                    }
                    // 查找返回图标
                    const icons = document.querySelectorAll('.el-icon-arrow-left, .el-icon-back');
                    for (const icon of icons) {
                        const btn = icon.closest('button, .el-button, [role="button"], a');
                        if (btn) {
                            btn.click();
                            return 'icon:' + btn.tagName;
                        }
                    }
                    // 查找面包屑导航中的链接
                    const crumbs = document.querySelectorAll('.el-breadcrumb__item a');
                    if (crumbs.length > 1) {
                        crumbs[crumbs.length - 2].click(); // 点击上一个面包屑
                        return 'crumb:true';
                    }
                    return 'none';
                }
            """)

            print(f"   [返回] 点击类型：{back_clicked}")

            if back_clicked != 'none':
                time.sleep(2)

                # 等待列表页恢复
                for i in range(5):
                    is_list = page.evaluate("""
                        () => document.querySelectorAll('.box_data').length > 0
                    """)
                    if is_list:
                        print("   [返回] 已返回列表页")
                        break
                    time.sleep(0.5)
            else:
                # 没有找到返回按钮，尝试重新触发列表渲染
                print("   [返回] 未找到返回按钮，尝试重新搜索")
                try:
                    search_btn = page.locator('button:has-text("搜索")').first
                    if search_btn.is_visible(timeout=5000):
                        search_btn.click(timeout=5000)
                        time.sleep(2)
                        # 等待网络空闲和列表渲染
                        try:
                            page.wait_for_load_state('networkidle', timeout=10000)
                        except:
                            pass
                        time.sleep(1)
                        print("   [返回] 已重新点击搜索")
                except Exception as search_err:
                    print(f"   [返回] 重新搜索失败：{search_err}")

        except Exception as back_err:
            print(f"   [返回] 返回操作失败：{back_err}")

        # 最终检查：如果仍然不在列表页，强制刷新页面
        final_check = page.evaluate("""
            () => document.querySelectorAll('.box_data').length > 0
        """)
        if not final_check:
            print(f"   [返回] 未检测到列表，强制刷新页面...")
            try:
                page.reload(wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass
                time.sleep(1)
                print("   [返回] 已刷新页面")
            except Exception as e:
                print(f"   [返回] 刷新失败：{e}")

        return content if content else ""

    except Exception as e:
        print(f"   [中石油详情点击] 失败：{e}")
        # 尝试重新触发搜索恢复列表
        try:
            search_btn = page.locator('button:has-text("搜索")').first
            if search_btn.is_visible(timeout=5000):
                search_btn.click(timeout=5000)
                time.sleep(2)
        except:
            pass
        return ""


def fetch_cnpc_detail_via_api(page, item_id: str) -> dict:
    """
    获取中石油详情页内容（通过 API + RSA 解密方式）

    Args:
        page: 浏览器页面对象
        item_id: 文章 ID

    Returns:
        dict: {content: str, attachments: list}

    架构说明:
        1. API 端点：POST /cms/article/details
        2. 请求体：RSA 加密的文章 ID 字符串
        3. 响应：加密的 JSON 数据，需使用 decrypt_api_response_in_browser 解密
        4. 解密后结构：{code, message, data: {id, title, content, publishedTime, attachments}}
    """
    if not item_id:
        return {"content": "", "attachments": []}

    try:
        # 在浏览器中执行加密、API 请求、解密全流程
        # 临时设置超时为 60 秒（中石油 API 需要 RSA 加密/解密，可能较慢）
        # Playwright 默认超时是 30000 毫秒
        page.set_default_timeout(60000)
        try:
            result = page.evaluate(f"""
        (async () => {{
            try {{
                const articleId = '{item_id}';
                const key = localStorage.getItem('logo2');

                console.log('[DEBUG] articleId:', articleId);
                console.log('[DEBUG] key exists:', !!key);
                console.log('[DEBUG] key length:', key ? key.length : 0);

                if (!key) {{
                    return {{ error: '未找到私钥 (logo2)' }};
                }}

                // 使用 JSEncrypt 加密文章 ID
                const crypt = new JSEncrypt();
                crypt.setKey(key);
                const encryptedId = crypt.encryptLong(articleId);

                if (!encryptedId) {{
                    return {{ error: 'encryptLong 返回 null' }};
                }}

                // 发起 API 请求
                const response = await fetch('https://www.cnpcbidding.com/cms/article/details', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/plain, */*'
                    }},
                    body: JSON.stringify(encryptedId)
                }});

                if (!response.ok) {{
                    return {{ error: 'API 请求失败：' + response.status }};
                }}

                const responseBody = await response.text();
                console.log('[DEBUG] responseBody (前 100 字):', responseBody.substring(0, 100));

                // 解密响应
                const decryptCrypt = new JSEncrypt();
                decryptCrypt.setKey(key);
                const decrypted = decryptCrypt.decryptLong(responseBody);

                console.log('[DEBUG] decrypted exists:', !!decrypted);
                console.log('[DEBUG] decrypted length:', decrypted ? decrypted.length : 0);

                if (!decrypted) {{
                    return {{ error: 'decryptLong 返回 null，响应可能是加密的或格式错误' }};
                }}

                // 解码
                const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join(''));

                const data = JSON.parse(decoded);
                return {{
                    success: true,
                    content: data.data?.content || data.content || '',
                    attachments: data.data?.attachments || data.attachments || []
                }};
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }})()
        """)
        except Exception as eval_ex:
            # evaluate 执行异常，重新抛出由外层捕获
            raise eval_ex
        finally:
            # 恢复默认超时设置 (30000 毫秒)
            page.set_default_timeout(30000)

        if not result.get('success'):
            error_msg = result.get('error', '未知错误')
            print(f"    [详情 API] 失败：{error_msg}")
            return {"content": "", "attachments": []}

        content = result.get('content', '')
        attachments = result.get('attachments', [])

        return {"content": content, "attachments": attachments}

    except Exception as e:
        print(f"    [详情 API] 异常：{e}")
        return {"content": "", "attachments": []}


def generate_local_archive(company: str, title: str, content: str, url: str, publish_date: str) -> str:
    """
    生成本地 HTML 镜像存档文件

    Args:
        company: 公司名称（中石油/中石化/中海油）
        title: 招标公告标题
        content: 招标公告正文内容
        url: 招标公告原始 URL
        publish_date: 发布日期（YYYY-MM-DD 格式）

    Returns:
        str: 存档文件的绝对路径

    架构说明:
        1. 自动生成：在 fetch_detail_content 成功后立即生成
        2. 结构化存储：按公司、日期进行归档
        3. 跳转保障：用户查看数据时直接打开本地 HTML，100% 成功且不受网络/加密影响
    """
    try:
        # 1. 创建存档目录结构
        base_archive_dir = os.path.join(BASE_DIR, "data", "archives")
        company_dir = os.path.join(base_archive_dir, company)

        # 解析日期用于目录分类
        try:
            date_obj = datetime.strptime(publish_date, "%Y-%m-%d")
            date_dir = os.path.join(company_dir, date_obj.strftime("%Y%m"))
        except:
            date_dir = os.path.join(company_dir, "unknown")

        # 创建目录
        os.makedirs(date_dir, exist_ok=True)

        # 2. 生成安全的文件名
        safe_title = re.sub(r'[<>:"/\\|？*]', '_', title)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.html"
        filepath = os.path.join(date_dir, filename)

        # 3. 生成 HTML 内容（包含原始内容和样式）
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {company} - 本地存档</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 24px;
            color: #333;
            border-bottom: 2px solid #1890ff;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .meta span {{
            margin-right: 20px;
        }}
        .content {{
            color: #333;
            font-size: 16px;
            white-space: pre-wrap;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="meta">
            <span><strong>公司：</strong>{company}</span>
            <span><strong>发布日期：</strong>{publish_date}</span>
            <span><strong>存档时间：</strong>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
        <div class="content">
{content}
        </div>
        <div class="footer">
            <p>本地存档文件 - 原始 URL: {url}</p>
            <p>此文件由采集脚本自动生成，内容来源于网页抓取</p>
        </div>
    </div>
</body>
</html>"""

        # 4. 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"   [本地存档] 已生成：{filepath}")
        return filepath

    except Exception as e:
        print(f"   [本地存档] 生成失败：{e}")
        return ""


def is_it_related(title: str) -> bool:
    """
    判断单个标题是否是 IT 相关（严格模式）

    Args:
        title: 招标公告标题

    Returns:
        bool: 是否是 IT 相关
    """
    return is_it_related_batch([title]).get(0, False)


def is_it_related_batch(titles: list[str], batch_size: int = 20) -> dict[int, bool]:
    """
    批量判断多个标题是否是 IT 相关（支持自动分批处理）

    Args:
        titles: 标题列表
        batch_size: 每批最多判断多少条（默认 20 条，超过会自动分批）

    Returns:
        dict[int, bool]: {索引：是否 IT 相关} 字典，例如 {0: True, 1: False, 2: True}

    功能特性:
        - 支持多模型自动切换（当 Token 不足时）
        - AI 判断失败时降级为关键词匹配
        - 超过 batch_size 自动分批处理
        - 严格模式：不确定就判定为非 IT
    """
    from config import AI_IT_CLASSIFIER_ENABLED, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODELS

    if not titles:
        return {}

    if not AI_IT_CLASSIFIER_ENABLED:
        # 降级为关键词判断
        result = {}
        for i, title in enumerate(titles):
            result[i] = is_it_related_by_keywords(title, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS)
        return result

    # 如果标题数量超过 batch_size，分批处理
    if len(titles) > batch_size:
        print(f"    [AI 批量分类] 标题数量 ({len(titles)}) 超过 batch_size ({batch_size})，分批处理...")
        result = {}
        for i in range(0, len(titles), batch_size):
            batch_titles = titles[i:i+batch_size]
            print(f"    [AI 批量分类] 处理第 {i//batch_size + 1} 批 ({len(batch_titles)} 条)...")
            batch_result = _is_it_related_batch_single(batch_titles, batch_size)
            # 将批次结果的索引偏移到总列表中的位置
            for idx, is_it in batch_result.items():
                result[i + idx] = is_it
        return result

    # AI 批量判断（单批次）
    return _is_it_related_batch_single(titles, batch_size)


def _is_it_related_batch_single(titles: list[str], batch_size: int = 20) -> dict[int, bool]:
    """
    批量判断多个标题是否是 IT 相关（单批次处理，不超过 batch_size）

    Args:
        titles: 标题列表（不应超过 batch_size）
        batch_size: 每批最多判断多少条

    Returns:
        dict[int, bool]: {索引：是否 IT 相关} 字典
    """
    from config import AI_IT_CLASSIFIER_ENABLED, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODELS

    titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])

    prompt = f"""判断以下 {len(titles)} 个招标公告标题是否属于 IT/信息化项目。

标题列表：
{titles_text}

【判定为"是"】只要满足以下任一条件：
1. 明确提到"软件"、"信息系统"、"管理平台"、"平台开发"、"系统开发"
2. 数据中心、服务器、数据库、云计算相关
3. 网络安全、网络设备、信息安全、防钓鱼
4. IT 运维服务、软件运维
5. AI/人工智能相关：AI 平台、大模型、算力租赁、私有化部署、视频 AI
6. 物联网 (IoT)、RFID、传感器数据采集系统
7. 通信设备、网络设备采购（不含通信工程）
8. 信息化系统、数字化平台、管理信息系统

【判定为"否"】仅当明显是以下情况：
- 管道、阀门、泵、机械设备、电气设备、电缆（纯物理设备）
- 船舶、海洋工程、石油钻井平台设备
- 建筑工程、装修、物业、餐饮服务
- 化学品、材料、办公用品采购
- 车辆运输、物流服务

【注意】以下情况应判定为"是"：
- "智能" + 系统/平台（如"智能场站管理系统"）→ 是
- "监控" + 信息安全/网络安全 → 是
- AI+ 监控/视频分析 → 是
- 标题含"软件"、"信息系统"、"信息安全"、"AI"、"大模型"、"数据中心"、"服务器"、"数据库"、"网络" → 是

请按顺序回复，每条一行，格式：序号。是/否
例如：
1. 是
2. 否
3. 是
"""

    # 获取配置
    if not DASHSCOPE_API_KEY:
        try:
            from config import ANTHROPIC_API_KEY
            DASHSCOPE_API_KEY = ANTHROPIC_API_KEY
        except:
            pass

    if not DASHSCOPE_API_KEY:
        print("    [AI 批量分类] 未配置 API Key，降级为关键词判断")
        result = {}
        for i, title in enumerate(titles):
            result[i] = is_it_related_by_keywords(title, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS)
        return result

    if not MODELS:
        MODELS = ["deepseek-chat", "deepseek-reasoner"]

    base_url = DASHSCOPE_BASE_URL or "https://api.deepseek.com/v1"
    api_url = base_url.rstrip('/') + '/chat/completions'

    print(f"    [AI 批量分类] 正在判断 {len(titles)} 条标题...")

    # 遍历所有模型尝试
    for model_index, model in enumerate(MODELS):
        try:
            print(f"    [AI 批量分类] 使用模型：{model} (尝试 {model_index + 1}/{len(MODELS)})")

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200  # 增加 token 上限，支持更多条目的回复（每条约 10-15 token）
            }

            headers = {
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            }

            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            resp_data = resp.json()

            # 检查是否有错误
            if resp_data.get("error"):
                error_msg = resp_data["error"].get("message", "未知错误")
                print(f"    [AI 批量分类] 模型 {model} 错误：{error_msg}")

                # 使用公共函数判断是否是 Token 不足错误
                if is_token_exhausted_error(resp.status_code, error_msg):
                    print(f"    [AI 批量分类] Token 不足，尝试下一个模型...")
                    continue
                else:
                    # 其他错误，继续尝试下一个模型
                    continue

            # 成功响应
            if resp.status_code == 200 and resp_data.get("choices"):
                content = resp_data["choices"][0]["message"]["content"].strip()
                print(f"    [AI 批量分类] {model} AI 回复:\n{content}")

                # 解析回复
                result = {}
                content_lines = content.split("\n")
                print(f"    [AI 批量分类] AI 回复共 {len(content_lines)} 行")

                for line in content_lines:
                    line_orig = line
                    line = line.strip()
                    if not line:
                        continue
                    # 匹配格式："1. 是" 或 "1. 否" 或 "1.是" 或 "1、是"
                    match = re.match(r'^(\d+)\s*[:.．、]?\s*(是|否)\s*', line)
                    if match:
                        idx = int(match.group(1)) - 1
                        is_it = match.group(2) == '是'
                        result[idx] = is_it
                        print(f"    [AI 批量分类] 解析行：{line[:40]} -> 索引{idx}, 结果：{'IT' if is_it else '非 IT'}")
                    else:
                        # 尝试更宽松的匹配：只查找数字和"是/否"
                        num_match = re.search(r'(\d+)', line)
                        if num_match and ('是' in line or '否' in line):
                            idx = int(num_match.group(1)) - 1
                            is_it = '是' in line and '否' not in line
                            result[idx] = is_it
                            print(f"    [AI 批量分类] [宽松匹配] {line[:40]} -> 索引{idx}, 结果：{'IT' if is_it else '非 IT'}")
                        else:
                            # 尝试按顺序匹配：如果一行只有一个"否"字
                            if line.strip() in ['是', '否', '是  ', '否  ']:
                                idx = len(result)
                                is_it = '是' in line
                                result[idx] = is_it
                                print(f"    [AI 批量分类] [顺序匹配] {line[:40]} -> 索引{idx}, 结果：{'IT' if is_it else '非 IT'}")
                            else:
                                print(f"    [AI 批量分类] [无法解析] {line_orig[:50]}")

                # 检查是否有遗漏的索引
                if len(result) < len(titles):
                    print(f"    [AI 批量分类] 警告：AI 只回复了 {len(result)} 条")
                    for i in range(len(titles)):
                        if i not in result:
                            result[i] = is_it_related_by_keywords(titles[i], IT_KEYWORDS, IT_EXCLUDE_KEYWORDS)

                # 复核：对 AI 判定为"非 IT"但包含强 IT 关键词的项目进行纠正
                # 强 IT 关键词：明确属于 IT 领域的词，即使 AI 判定为"非 IT"也要纠正
                strong_it_keywords = ["信息安全", "网络安全", "软件", "信息系统", "数据库", "服务器", "AI", "人工智能", "大模型"]
                for i, title in enumerate(titles):
                    if i in result and result[i] == False:
                        # AI 判定为非 IT，检查是否包含强 IT 关键词
                        title_lower = title.lower()
                        has_strong_it = any(kw.lower() in title_lower for kw in strong_it_keywords)
                        if has_strong_it:
                            # 检查是否包含排除词（如"管道"、"电气"等）
                            has_exclude = any(kw.lower() in title_lower for kw in IT_EXCLUDE_KEYWORDS)
                            if not has_exclude:
                                result[i] = True
                                print(f"    [AI 批量分类] [关键词纠正] {title[:50]}... -> 非 IT 改为 IT")

                return result

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response else 500
            logger.warning(f"    [AI 批量分类] 模型 {model} HTTP 错误 ({status_code}): {http_err}")
            continue

        except Exception as e:
            logger.warning(f"    [AI 批量分类] 模型 {model} 异常：{e}")
            continue

    # 所有模型都失败，降级为关键词判断
    print("    [AI 批量分类] 所有模型都失败，降级为关键词判断")
    result = {}
    for i, title in enumerate(titles):
        result[i] = is_it_related_by_keywords(title, IT_KEYWORDS, IT_EXCLUDE_KEYWORDS)
    return result


def construct_cnooc_url(article_id: str, category: str = "alert") -> str:
    """
    构造中海油标准可分享路由 URL

    Args:
        article_id: 文章 ID（从 JSON 拦截或 DOM 提取）
        category: 类别，'alert' = 招标公告，'result' = 中标结果

    Returns:
        str: 完整的可分享 URL

    说明:
        根据文档 CNOOC_SHAREABLE_SCRAPER_DESIGN.md.resolved：
        - 必须包含 index=0&childrenActive=0 等状态参数
        - 使用 newsAlertDetails 路由（而非 newsDetail）
        - type=null 参数用于确保外部访问正常
    """
    base = "https://bid.cnooc.com.cn/home/#/newsAlertDetails"

    # 根据分类设置 childrenActive 参数
    # 4 = 招标公告，5 = 中标结果
    children_active = "4" if category == "alert" else "5"

    params = {
        "index": "0",
        "childrenActive": children_active,
        "id": article_id,
        "type": "null"
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{query}"


def is_date_too_old(publish_date: str) -> bool:
    """
    检查发布日期是否超过阈值（早于 DATE_START）

    Args:
        publish_date: 发布日期（支持多种格式）

    Returns:
        bool: 是否超过阈值（True 表示日期太旧）
    """
    if not publish_date:
        return False
    try:
        # 格式化日期为 YYYY-MM-DD 格式
        if len(publish_date) > 10:
            publish_date = publish_date[:10]

        # 规范化日期格式（处理 2024-1-5 这种情况）
        parts = publish_date.split('-')
        if len(parts) == 3:
            publish_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

        # 比较日期
        return publish_date < DATE_START
    except:
        return False


def decrypt_api_response_in_browser(page, body: str) -> dict:
    """
    在浏览器中解密 API 响应（中石油专用）

    Args:
        page: Playwright 页面对象
        body: API 响应体（加密的字符串或 JSON）

    Returns:
        dict: 解密后的数据，格式：{success: bool, data: dict, error?: str}
    """
    import json as json_lib

    # 如果响应是 JSON 字符串（带引号），先解析
    if body.startswith('"') and body.endswith('"'):
        try:
            body = json.loads(body)
        except:
            pass

    body_json = json_lib.dumps(body)

    result = page.evaluate(f"""
    (() => {{
        try {{
            const encryptedData = {body_json};
            const privateKey = localStorage.getItem('logo2');

            if (!privateKey) {{
                return {{ error: '未找到私钥 (logo2)' }};
            }}

            const crypt = new JSEncrypt();
            crypt.setPrivateKey(privateKey);

            const decrypted = crypt.decryptLong(encryptedData);
            if (!decrypted) {{
                return {{ error: 'decryptLong 返回 null' }};
            }}

            const decoded = decodeURIComponent(atob(decrypted).split('').map(c =>
                '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
            ).join(''));

            const data = JSON.parse(decoded);
            return {{ success: true, data: data }};
        }} catch (e) {{
            return {{ error: e.message }};
        }}
    }})()
    """)
    return result


def collect_cnpc(max_pages: int = 5000) -> list[dict]:
    """
    采集中石油数据 - 使用 API 拦截 + RSA 解密方式

    Args:
        max_pages: 最大翻页数（默认 5000）

    Returns:
        list[dict]: 采集到的招标公告记录列表

    功能特性:
        - 支持用户手动处理验证码
        - 自动翻页采集
        - API 响应加密/解密
        - IT 相关性自动判断

    工作流程:
        1. 启动浏览器并访问列表页
        2. 用户手动完成验证码（如有）
        3. 拦截 API 响应并使用 RSA 解密
        4. 批量判断 IT 相关性
        5. 获取详情页内容并生成 AI 摘要
        6. 返回结构化的记录列表
    """
    print("\n" + "=" * 80)
    print("开始采集 中石油 数据")
    print("=" * 80)

    # 打印配置
    print(f"日期范围：{DATE_START} 至 {DATE_END}")
    print(f"翻页策略：{FLIP_STRATEGY}")
    print(f"最大页数：{FETCH_PAGES if FETCH_PAGES else '无限制'}")
    print(f"IT 关键词过滤：{'开启' if IT_KEYWORDS else '关闭'}")

    base_url = "https://www.cnpcbidding.com"
    list_url = f"{base_url}/#/tenders"
    user_data_dir = os.path.join(BASE_DIR, "api_test", "browser_data_api")

    print(f"\n访问页面：{list_url}")

    playwright = None
    context = None

    import atexit
    def _cleanup_cnpc():
        try:
            if context:
                context.close()
        except:
            pass
        try:
            if playwright:
                playwright.stop()
        except:
            pass
    atexit.register(_cleanup_cnpc)

    try:
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(list_url, wait_until="domcontentloaded", timeout=60000)

        # 智能等待：等到列表元素出现或超时
        try:
            page.wait_for_selector('.box_data, button:has-text("搜索")', timeout=10000)
            print("  [等待] 列表元素已加载")
        except:
            print("  [等待] 超时，继续执行")
        time.sleep(1)  # 减少等待：5 秒 -> 1 秒

        # ===== 用户手动操作阶段 =====
        print("\n" + "=" * 60)
        print("请在浏览器中完成以下操作：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码，请手动完成验证码验证")
        print("\n等待 30 秒后自动开始采集数据...")
        print("=" * 60)
        time.sleep(30)

        time.sleep(1)  # 减少等待：2 秒 -> 1 秒

        all_records = []
        seen_keys = set()

        for page_num in range(max_pages):
            print(f"\n=== 第 {page_num + 1} 页 ===")

            if page_num > 0:
                # 翻页：使用 JavaScript 点击下一个页码数字
                flip_success = False
                flip_retry = 0

                while not flip_success and flip_retry < 3:
                    flip_retry += 1
                    if flip_retry > 1:
                        print(f"  [重试 {flip_retry}/3] 尝试翻页...")

                    try:
                        # 滚动到底部确保分页组件可见
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_selector('.el-pager', timeout=5000)  # 智能等待分页组件
                        page.wait_for_timeout(300)  # 减少等待：1000ms -> 300ms

                        # 检查当前页面状态 - 使用 .box_data 选择器
                        page_status = page.evaluate("""
                            () => {
                                const hasList = document.querySelectorAll('.box_data').length > 0;
                                const hasDetail = document.querySelector('.content') !== null;
                                const pagers = document.querySelectorAll('.el-pager');
                                const hasPager = pagers.length > 0;
                                return { hasList, hasDetail, hasPager };
                            }
                        """)

                        print(f"  [页面状态] 列表={page_status.get('hasList')} 详情={page_status.get('hasDetail')} 分页={page_status.get('hasPager')}")

                        # 如果在详情页，尝试返回
                        if page_status.get('hasDetail') and not page_status.get('hasList'):
                            print("  检测到详情页状态，尝试返回...")

                            # 先尝试点击搜索按钮刷新列表
                            try:
                                search_btn = page.locator('button:has-text("搜索")').first
                                if search_btn.is_visible(timeout=3000):
                                    search_btn.click(timeout=3000)
                                    time.sleep(1.5)  # 减少等待：3 秒 -> 1.5 秒
                                    print("  已点击搜索按钮刷新列表")

                                    # 检查是否返回列表
                                    check_after = page.evaluate("""
                                        () => document.querySelectorAll('.box_data').length > 0
                                    """)
                                    if check_after:
                                        print("  已返回列表页")
                                        # 刷新后重试翻页
                                        continue
                            except:
                                pass

                            # 搜索无效，使用 page.reload() 强制刷新
                            print("  搜索无效，强制刷新页面...")
                            page.reload(wait_until="domcontentloaded", timeout=30000)
                            time.sleep(1.5)  # 减少等待：3 秒 -> 1.5 秒
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                pass
                            time.sleep(1)  # 减少等待：2 秒 -> 1 秒
                            print("  已刷新页面")
                            continue

                        # 尝试点击返回按钮
                        back_clicked = page.evaluate("""
                            () => {
                                const buttons = document.querySelectorAll('button, .el-button');
                                for (const btn of buttons) {
                                    const text = (btn.innerText || '').toLowerCase();
                                    if (text.includes('返回') || text.includes('back')) {
                                        btn.click();
                                        return true;
                                    }
                                }
                                return false;
                            }
                        """)

                        if back_clicked:
                            time.sleep(2)
                            continue

                        # 检查分页组件
                        if not page_status.get('hasPager'):
                            print("  未找到分页组件，尝试刷新列表...")

                            # 方案 1：点击搜索按钮刷新
                            search_clicked = False
                            try:
                                search_btn = page.locator('button:has-text("搜索")').first
                                if search_btn.is_visible(timeout=3000):
                                    search_btn.click(timeout=3000)
                                    print("  已点击搜索，等待列表渲染...")
                                    time.sleep(3)
                                    try:
                                        page.wait_for_load_state('networkidle', timeout=10000)
                                    except:
                                        pass
                                    time.sleep(2)
                                    search_clicked = True
                            except Exception as e:
                                print(f"  点击搜索失败：{e}")

                            # 检查是否恢复
                            if search_clicked:
                                check_again = page.evaluate("""
                                    () => {
                                        const list = document.querySelectorAll('.box_data').length > 0;
                                        const pager = document.querySelectorAll('.el-pager').length > 0;
                                        return { list, pager };
                                    }
                                """)
                                print(f"  刷新后检查：列表={check_again.get('list')} 分页={check_again.get('pager')}")

                                if check_again.get('pager'):
                                    print("  分页组件已恢复，继续翻页")
                                    continue
                                elif check_again.get('list'):
                                    print("  列表已恢复，但分页组件仍缺失，尝试滚动触发...")
                                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                    time.sleep(2)
                                    continue
                                else:
                                    print("  列表仍未恢复，尝试额外等待...")
                                    time.sleep(5)
                                    continue
                            else:
                                print("  无法刷新，退出翻页")
                                break

                        # 使用 JavaScript 获取当前页码并点击下一页
                        result = page.evaluate("""
                            () => {
                                const pagers = document.querySelectorAll('.el-pager');
                                const targetPager = pagers[pagers.length - 1];
                                if (!targetPager) return { success: false, reason: 'no pager' };

                                // 首先获取当前激活的页码
                                const activeLi = targetPager.querySelector('li.number.active');
                                let currentPage = 1;
                                if (activeLi) {
                                    const activeText = activeLi.innerText.trim();
                                    currentPage = parseInt(activeText) || 1;
                                }

                                const targetPage = currentPage + 1;

                                // 尝试点击">"下一页按钮
                                const nextBtn = targetPager.querySelector('li.next');
                                if (nextBtn && !nextBtn.classList.contains('disabled')) {
                                    nextBtn.click();
                                    return { success: true, clicked: 'next', from: currentPage, to: targetPage };
                                }

                                // 点击当前页码 +1 的数字
                                const numberLis = targetPager.querySelectorAll('li.number');
                                for (const li of numberLis) {
                                    const text = li.innerText.trim();
                                    const pageNum = parseInt(text);
                                    if (pageNum === targetPage) {
                                        li.click();
                                        return { success: true, clicked: text, from: currentPage, to: targetPage };
                                    }
                                }

                                return { success: false, reason: 'no next page' };
                            }
                        """)

                        if result.get('success'):
                            from_page = result.get('from', '?')
                            to_page = result.get('to', '?')
                            clicked = result.get('clicked', '')
                            print(f"  已翻页：{from_page} -> {to_page} ({clicked})")

                            # 等待 API 响应或列表更新（智能等待）
                            try:
                                page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                page.wait_for_timeout(800)  # 减少等待：1500ms -> 800ms

                            # 翻页后短暂等待
                            time.sleep(0.3)  # 减少等待：0.5 秒 -> 0.3 秒

                            flip_success = True  # 翻页成功
                        else:
                            reason = result.get('reason', 'unknown')
                            print(f"  无法翻页：{reason}")
                            break  # 退出重试

                    except Exception as e:
                        print(f"  翻页异常：{e}")
                        break

                # 如果翻页失败，退出循环
                if not flip_success:
                    print("  翻页失败，停止采集")
                    break

            # 获取列表数据 - 点击搜索按钮并拦截 API 响应
            body = None
            print("  等待列表 API 响应...")
            try:
                with page.expect_response(
                    lambda r: '/cms/article/page' in r.url and r.status == 200,
                    timeout=30000
                ) as response_info:
                    search_btn = page.locator('button:has-text("搜索")').first
                    if search_btn.is_visible(timeout=10000):
                        search_btn.click(timeout=10000)
                        print("  已点击搜索按钮")
                    else:
                        print("  搜索按钮不可见，尝试等待...")
                        page.wait_for_timeout(2000)  # 减少等待：5000ms -> 2000ms

                response = response_info.value
                body = response.text()
                print(f"  [获取到列表 API] 长度={len(body)}")

            except Exception as e:
                print(f"  等待列表 API 失败：{e}")
                time.sleep(1)  # 减少等待：2 秒 -> 1 秒
                continue

            # 解密 API 响应
            print(f"  解密 API 响应...")
            result = decrypt_api_response_in_browser(page, body)
            if not result.get('success'):
                error_msg = result.get('error', '未知错误')
                print(f"  解密失败：{error_msg}")
                continue

            data = result['data']
            if data is None or not isinstance(data, dict):
                print(f"  错误：解密后数据格式异常")
                continue

            # 处理嵌套结构：{code, message, data} -> 真正的数据在 data 字段
            if 'data' in data and isinstance(data.get('data'), dict):
                data = data.get('data')

            records = data.get('records', data.get('data', {}).get('records', []))
            if not records and isinstance(data.get('data'), list):
                records = data['data']

            if not records:
                print(f"  未获取到记录")
                continue

            print(f"  获取到 {len(records)} 条记录")

            # 【优化】批量 IT 判断（一次请求判断 10 条，而不是逐条判断）
            print(f"  [AI 批量分类] 正在判断本页 {len(records)} 条记录...")
            titles_to_check = [r.get('title', '') for r in records]
            it_results = is_it_related_batch(titles_to_check)  # 返回 {索引：是否 IT}

            # 打印 AI 判断结果：选出 IT 相关的条目
            it_selected = [(idx, titles_to_check[idx][:60]) for idx, is_it in it_results.items() if is_it]
            if it_selected:
                print(f"  [AI 选中] 共 {len(it_selected)} 条 IT 相关：")
                for idx, title in it_selected:
                    print(f"    [{idx+1}] {title}...")
            else:
                print(f"  [AI 选中] 本页无 IT 相关记录")

            # 处理每条记录
            page_has_old_data = False
            for idx, item in enumerate(records):
                item_id = item.get('id')
                item_title = item.get('title', '')
                publish_date = item.get('publishedTime', '')

                if not item_title or len(item_title) < 5:
                    continue

                # 日期检查
                if FLIP_STRATEGY == "date" and publish_date:
                    if is_date_too_old(publish_date):
                        print(f"  [日期过滤] 发现旧数据：{publish_date}")
                        page_has_old_data = True
                        break

                # 去重检查
                key = f"{item_title}{publish_date}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                # IT 相关检查（使用批量判断结果）
                is_it = it_results.get(idx, False)

                # 构造记录
                record = {
                    "company": "中石油",
                    "title": item_title,
                    "category": "招标公告",
                    "publish_date": publish_date,
                    "url": f"{base_url}/#/tenders/detail?id={item_id}",
                    "content": "",
                    "summary": "",
                    "fetched_at": datetime.now().isoformat(),
                    "is_it_related": is_it,
                    "_item_id": item_id  # 用于后续详情采集
                }

                # 【核心功能】如果是 IT 相关，获取详情页内容并生成 AI 摘要
                if is_it:
                    print(f"  [IT] {item_title[:50]}... (获取详情页)")

                    # 构造详情页 URL
                    detail_url = f"{base_url}/#/tenders/detail?id={item_id}"
                    record["url"] = detail_url

                    # 获取详情页内容（使用点击列表项同页渲染方式）
                    # 注：中石油详情 API 返回"http 报文读取失败"，改用点击方式
                    detail_content = fetch_cnpc_detail_by_click(page, str(item_id), list_url)

                    if detail_content:
                        record["content"] = detail_content[:5000]

                        # 生成 AI 摘要
                        print(f"    [AI 摘要] 开始生成...")
                        ai_summary = generate_ai_summary(detail_content, item_title)
                        if ai_summary:
                            record["summary"] = ai_summary
                            print(f"    [AI 摘要] 成功：{ai_summary[:30]}...")
                        else:
                            record["summary"] = detail_content[:60]
                            print(f"    [AI 摘要] 失败，使用原文前 60 字")

                        print(f"    详情内容：{len(detail_content)} 字")
                    else:
                        record["summary"] = item_title[:60]
                        print(f"    详情页获取失败")
                else:
                    print(f"  [非 IT] {item_title[:50]}...")
                    record["summary"] = ""

                all_records.append(record)

            if page_has_old_data:
                print(f"已抓取到阈值日期 ({DATE_START}) 之前的数据，停止翻页")
                break

            # 检查是否还有更多页
            total = data.get('total', 0)
            current = data.get('current', 1)
            size = data.get('size', 10)
            total_pages = (total + size - 1) // size if size > 0 and total > 0 else 1

            # 使用 page_num+1 作为当前页码（更可靠）
            current_page_num = page_num + 1

            print(f"  [分页信息] total={total}, current={current}, size={size}, total_pages={total_pages}, 当前页={current_page_num}, max_pages={max_pages}")

            # 先检查 max_pages 限制（优先级最高）
            if current_page_num >= max_pages:
                print(f"  [停止条件] 已达到最大翻页限制 ({max_pages})")
                break
            # 再检查 total_pages 限制
            elif total == 0:
                print(f"  [停止条件] API 返回 total=0，停止采集")
                break
            elif current_page_num >= total_pages:
                print(f"  [停止条件] 已到达最后一页 (当前{current_page_num}/{total_pages})")
                break

        # 短暂等待（减少等待时间）
        time.sleep(0.1)  # 减少等待：0.3 秒 -> 0.1 秒

        print(f"\n中石油采集完成！共 {len(all_records)} 条")
        return all_records

    except Exception as e:
        logger.error(f"采集中石油数据时发生异常：{e}")
        raise
    finally:
        # 确保资源清理
        if context:
            try:
                context.close()
            except:
                pass
        if playwright:
            try:
                playwright.stop()
            except:
                pass


def collect_sinopec(max_pages: int = 5000) -> list[dict]:
    """
    采集中石化数据

    Args:
        max_pages: 最大翻页数（默认 5000）

    Returns:
        list[dict]: 采集到的招标公告记录列表

    功能特性:
        - 支持招标公告和中标结果两种类型
        - 自动识别并关闭弹窗
        - 日期阈值判断提前终止
        - IT 相关性自动判断
    """
    print("\n" + "=" * 80)
    print("开始采集 中石化 数据")
    print("=" * 80)

    # 打印日期范围配置
    print(f"日期范围：{DATE_START} 至 {DATE_END}")
    print(f"翻页策略：{FLIP_STRATEGY}")
    print(f"最大页数：{FETCH_PAGES if FETCH_PAGES else '无限制'}")

    # 使用 config.py 中的 URL
    base_url = "https://ebidding.sinopec.com"
    tender_url = "https://ebidding.sinopec.com/v3/portal/#/category/NOTICE/TENDER"
    result_url = "https://ebidding.sinopec.com/v3/portal/#/category/NOTICE/RESULT"
    user_data_dir = os.path.join(BASE_DIR, "api_test", "browser_data_sinopec")

    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="msedge",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )
    page = context.pages[0] if context.pages else context.new_page()

    import atexit
    def _cleanup_sinopec():
        try:
            if context:
                context.close()
        except:
            pass
        try:
            if playwright:
                playwright.stop()
        except:
            pass
    atexit.register(_cleanup_sinopec)

    all_records = []

    # 只采集招标公告，不采集中标公示
    category_name = "招标公告"
    url = tender_url
    selector = 'a[href*="/article/TENDER/"]'

    print(f"\n正在采集：{category_name}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)  # 从 5 秒减少到 3 秒

    # 关闭弹窗
    try:
        page.evaluate("""
            () => {
                document.querySelectorAll('.el-dialog, .modal, .ivu-modal, [class*="dialog"]').forEach(el => el.remove());
                document.querySelectorAll('.el-mask, .modal-mask, [class*="mask"]').forEach(m => m.remove());
            }
        """)
    except:
        pass

    time.sleep(1)  # 从 2 秒减少到 1 秒
    seen_keys = set()
    current_page = 1

    while current_page <= max_pages:
        print(f"\n  [{category_name}] 第 {current_page} 页...")

        # 标记当前页是否有旧数据
        page_has_old_data = False

        articles = page.evaluate(f"""
                () => {{
                    const items = [];
                    const links = document.querySelectorAll('{selector}');
                    links.forEach(link => {{
                        const text = link.textContent.trim();
                        if (text.length < 10) return;
                        let title = text;
                        if (title.startsWith('[')) {{
                            const idx = title.indexOf(']');
                            if (idx > 0) title = title.substring(idx + 1).trim();
                        }}
                        let date = '';
                        // 尝试多种日期格式
                        const patterns = [
                            /(\\d{{4}}-\\d{{1,2}}-\\d{{1,2}})/,    // YYYY-MM-DD 或 YYYY-M-D
                            /(\\d{{4}}\\/\\d{{1,2}}\\/\\d{{1,2}})/,  // YYYY/MM/DD
                            /(\\d{{4}}\\.\\d{{1,2}}\\.\\d{{1,2}})/,  // YYYY.MM.DD
                            /(\\d{{4}}年\\d{{1,2}}月\\d{{1,2}}日)/,  // YYYY 年 MM 月 DD 日
                        ];
                        for (const pattern of patterns) {{
                            const match = text.match(pattern);
                            if (match) {{
                                date = match[1].replace(/[年\\.\\/]/g, '-').replace('日', '');
                                break;
                            }}
                        }}

                        // 从 href 中提取 ID（如：/article/TENDER/12345）
                        let itemId = '';
                        const rawHref = link.href || '';
                        const idMatch = rawHref.match(/\\/article\\/(?:TENDER|RESULT)\\/([a-zA-Z0-9_-]+)/);
                        if (idMatch) {{
                            itemId = idMatch[1];
                        }}

                        // 构造完整的详情页 URL（使用 config 中的模板）
                        let detailUrl = '';
                        if (itemId) {{
                            detailUrl = 'https://ebidding.sinopec.com/v3/portal/#/article/TENDER/' + itemId;
                        }} else {{
                            detailUrl = rawHref;
                        }}

                        items.push({{
                            title: title,
                            publishDate: date,
                            url: detailUrl,
                            id: itemId  // 保留原始 ID 用于验证
                        }});
                    }});
                    return items;
                }}
            """)

        if articles:
            print(f"  获取到 {len(articles)} 条数据")

            # 【优化】批量 IT 判断（一次请求判断多条，而不是逐条判断）
            print(f"  [AI 批量分类] 正在判断本页 {len(articles)} 条记录...")
            titles_to_check = [a.get('title', '') for a in articles]
            it_results = is_it_related_batch(titles_to_check)  # 返回 {索引：是否 IT}

            for idx, article in enumerate(articles):
                # 调试：打印提取到的日期
                if FLIP_STRATEGY == "date":
                    if not article['publishDate']:
                        print(f"    [警告] 未提取到日期：{article['title'][:30]}...")
                    else:
                        print(f"    [日期] {article['publishDate']} - {article['title'][:30]}...")

                # 检查日期是否超过阈值
                if FLIP_STRATEGY == "date" and article['publishDate']:
                    if is_date_too_old(article['publishDate']):
                        print(f"    [日期过滤] 发现旧数据：{article['publishDate']} < {DATE_START}")
                        page_has_old_data = True
                        break

                key = f"{article['title']}{article['publishDate']}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                is_tender = any(x in article['title'] for x in ["招标", "采购", "询价", "谈判", "公告"])
                is_result = any(x in article['title'] for x in ["中标", "候选人", "结果公示", "成交"])

                if not is_tender:
                    continue

                # IT 相关检查（使用批量判断结果）
                is_it = it_results.get(idx, False)

                # 构造完整的详情页 URL（使用 config 中的模板）
                detail_url = ""
                if article.get('id'):
                    detail_url = DETAIL_URL_TEMPLATES["中石化"]["TENDER"].format(id=article['id'])
                elif article.get('url') and '/article/' in article['url']:
                    detail_url = article['url']

                # 初始化 record
                record = {
                    "company": "中石化",
                    "title": article['title'],
                    "category": category_name,
                    "publish_date": article['publishDate'],
                    "url": detail_url,
                    "content": "",
                    "summary": "",
                    "fetched_at": datetime.now().isoformat(),
                    "is_it_related": is_it  # 添加 IT 相关标记
                }

                # 如果是 IT 相关且有有效的详情页 URL，抓取正文并生成 AI 摘要
                has_valid_url = detail_url and article.get('id')
                if is_it and AI_SUMMARY_ENABLED and has_valid_url:
                    # 抓取详情页内容
                    detail_content = fetch_detail_content(context, detail_url)
                    if detail_content:
                        record["content"] = detail_content[:5000]

                        # 使用详情页内容生成 AI 摘要（20-60 字）
                        print(f"    [AI 摘要] 开始生成...")
                        ai_summary = generate_ai_summary(detail_content, article['title'])
                        if ai_summary:
                            record["summary"] = ai_summary
                            print(f"    [AI 摘要] 成功：{ai_summary[:30]}...")
                        else:
                            record["summary"] = detail_content[:60]
                            print(f"    [AI 摘要] 失败，使用原文前 60 字")
                    else:
                        record["summary"] = article['title'][:60]
                else:
                    if is_it:
                        print(f"    [IT] {article['title'][:50]}...")
                    record["summary"] = article['title'][:60] if is_it else ""

                all_records.append(record)

        print(f"  当前页：{len(articles)} 条")

        # 根据策略判断是否停止翻页
        if FLIP_STRATEGY == "date" and page_has_old_data:
            print(f"  已抓取到阈值日期 ({DATE_START}) 之前的数据，停止翻页")
            break

        # 翻页
        if current_page < max_pages:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)  # 从 2 秒减少到 1 秒

            next_clicked = False
            # 中石化使用 Element UI 分页组件，优先使用 .btn-next
            for sel in ['button.btn-next', 'button:has-text("下一页")', 'a:has-text("下一页")', 'li:has-text("下一页")']:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        # 检查是否被禁用
                        is_disabled = btn.get_attribute("disabled") is not None
                        if is_disabled:
                            print("  下一页按钮已禁用（已是最后一页）")
                            break
                        btn.click()
                        time.sleep(2)  # 从 3 秒减少到 2 秒
                        next_clicked = True
                        break
                except:
                    pass

            if not next_clicked:
                print("  已到达最后一页")
                break

        current_page += 1

    context.close()
    playwright.stop()
    print(f"\n中石化采集完成！共 {len(all_records)} 条")
    return all_records


def collect_cnooc(max_pages: int = 5000) -> list[dict]:
    """
    采集中海油数据

    Args:
        max_pages: 最大翻页数（默认 5000）

    Returns:
        list[dict]: 采集到的招标公告记录列表

    功能特性:
        - API 响应拦截 + DOM 提取双模式
        - SingletonLock 自动清理（防止浏览器多开锁定）
        - 可分享路由 URL 构造
        - IT 相关性自动判断
    """
    print("\n" + "=" * 80)
    print("开始采集 中海油 数据")
    print("=" * 80)

    # 打印日期范围配置
    print(f"日期范围：{DATE_START} 至 {DATE_END}")
    print(f"翻页策略：{FLIP_STRATEGY}")
    print(f"最大页数：{FETCH_PAGES if FETCH_PAGES else '无限制'}")

    user_data_dir = os.path.join(BASE_DIR, "api_test", "browser_data_cnooc")

    # 【核心功能】存储拦截到的文章数据
    cnooc_articles = []

    # 【核心功能】网络请求拦截器 - 拦截包含文章列表的 JSON 响应
    def handle_response(response):
        try:
            url = response.url
            # 中海油 API URL 包含 'announcement' 或 'page' 参数
            if 'cnooc.com.cn' in url and ('announcement' in url or ('page' in url and 'size=' in url)):
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        print(f"[API 拦截] 捕获到 JSON 响应：{url[:100]}")
                        # 中海油数据结构：{'result': {'data': [...], 'total': ..., 'pages': ...}}
                        result = data.get('result') or data
                        if isinstance(result, dict):
                            articles_list = result.get('data') or result.get('list') or []
                            row_index = 0
                            for item in articles_list:
                                if isinstance(item, dict):
                                    article_id = item.get('id') or item.get('articleId') or item.get('newsId')
                                    title = item.get('title') or item.get('newsTitle')
                                    # 中海油使用 createdTime 而不是 publishDate
                                    publish_date = item.get('createdTime') or item.get('publishDate') or item.get('createTime')

                                    if article_id and title:
                                        exists = any(a['id'] == article_id for a in cnooc_articles)
                                        if not exists:
                                            cnooc_articles.append({
                                                'id': article_id,
                                                'title': title,
                                                'publishDate': publish_date or '',
                                                'source': 'json_intercept',
                                                'row_index': row_index
                                            })
                                            print(f"[API 拦截] 新增：{title[:30]}...")
                                            row_index += 1
                            print(f"[API 拦截] 当前累计：{len(cnooc_articles)} 条")
                    except Exception as e:
                        print(f"[API 拦截] JSON 解析失败：{e}")
        except Exception as e:
            print(f"[API 拦截] 错误：{e}")

    # 【核心防御】清理 SingletonLock 文件以防止浏览器多开锁定
    def cleanup_singleton_lock(data_dir: str) -> None:
        """
        清理浏览器数据目录中的 SingletonLock 文件
        解决：Previous关闭不正常导致的浏览器无法启动问题
        """
        lock_file = os.path.join(data_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                print(f"   [Lock 清理] 已删除：{lock_file}")
            except PermissionError:
                print(f"   [Lock 清理] 文件被占用，跳过：{lock_file}")
            except Exception as e:
                print(f"   [Lock 清理] 失败：{e}")

    # 启动前清理 Lock
    cleanup_singleton_lock(user_data_dir)

    playwright = None
    context = None

    try:
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1920, "height": 1080},
        )
        # 设置响应拦截器
        context.on("response", handle_response)
    except Exception as e:
        # 【防御性设计】启动失败时尝试切换到临时目录
        print(f"   [浏览器启动] 失败：{e}")
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="playwright_")
        print(f"   [浏览器启动] 切换到临时目录：{temp_dir}")
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=temp_dir,
                channel="msedge",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1920, "height": 1080},
            )
            context.on("response", handle_response)
        except Exception as e2:
            print(f"   [浏览器启动] 临时目录也失败：{e2}")
            if playwright:
                playwright.stop()
            raise

    page = context.pages[0] if context.pages else context.new_page()

    # 注册退出清理（确保浏览器一定关闭）
    import atexit
    def _cleanup_cnooc():
        try:
            if context:
                context.close()
        except:
            pass
        try:
            if playwright:
                playwright.stop()
        except:
            pass
    atexit.register(_cleanup_cnooc)

    all_records = []

    # 采集中海油数据（只采集招标公告）
    category_name = "招标公告"
    print(f"\n正在采集：{category_name}")

    # 切换到对应分类
    base_url = "https://bid.cnooc.com.cn/home/#/newsAlertList?index=0&childrenActive=4&label=%E6%8B%9B%E6%A0%87%E9%87%87%E8%B4%AD"

    page.goto(base_url, wait_until="domcontentloaded", timeout=30000)

    # 等待页面数据加载（使用元素等待替代固定等待）
    print("   等待数据加载...")
    try:
        page.wait_for_selector('.table_page li, [class*="news-item"], .news-list li', timeout=10000)
        time.sleep(0.5)
    except:
        time.sleep(2)

    seen_keys = set()
    page_has_old_data = False
    current_page = 1

    api_processed_count = 0  # 已处理的 API 拦截数据条数

    # 【核心功能】循环翻页提取数据
    while True:
        print(f"\n  [招标公告] 第 {current_page} 页...")

        # 优先使用 API 拦截数据（有新数据就用）
        new_api_articles = cnooc_articles[api_processed_count:]
        if new_api_articles:
            print(f"  使用 API 拦截数据，新增 {len(new_api_articles)} 条（累计 {len(cnooc_articles)} 条）")
            articles = new_api_articles
            api_processed_count = len(cnooc_articles)
        else:
            # API 无新数据时，等待并尝试 DOM 提取
            try:
                page.wait_for_load_state('domcontentloaded', timeout=10000)
            except:
                pass
            time.sleep(2)

            # 再次检查是否有新的 API 数据到达
            new_api_articles = cnooc_articles[api_processed_count:]
            if new_api_articles:
                print(f"  使用 API 拦截数据（等待后），新增 {len(new_api_articles)} 条")
                articles = new_api_articles
                api_processed_count = len(cnooc_articles)
            else:
                print("  使用 DOM 提取当前页数据")
                articles = page.evaluate(r"""
() => {
    const items = [];
    // 增强选择器：尝试多种可能的列表项容器
    const selectors = [
        '.table_page li',           // 原有选择器
        '.table_page .item',        // 备用选择器
        '[class*="news-item"]',     // 可能的动态类名
        '[class*="list-item"]',     // 通用列表项
        '.news-list li',            // 备用列表
        '.page-content li',         // 降级选择器
    ];

    const allRows = [];
    selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            if (!allRows.includes(el)) allRows.push(el);
        });
    });

    console.log('找到列表项数量:', allRows.length);

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

            // 提取 ID（多种方案）
            let id = '';
            let href = '';
            const link = row.querySelector('a');

            // 获取 href
            if (link) {
                href = link.getAttribute('href') || '';
            }

            // 1. 从 data-id 属性获取
            id = row.getAttribute('data-id') ||
                row.getAttribute('data-item-id') ||
                row.getAttribute('data-project-id') ||
                (link ? (link.getAttribute('data-id') ||
                        link.getAttribute('data-item-id')) : '') ||
                '';

            // 2. 从 href 中提取 id 参数（新增：支持 bid.cnooc.com.cn/home/#/newsAlertDetails?id=xxx 格式）
            if (!id && link) {
                // 匹配 ?id=xxx 或 &id=xxx
                const idMatch = href.match(/[?&]id=([a-zA-Z0-9_-]+)/);
                if (idMatch) {
                    id = idMatch[1];
                    console.log('从 href 提取到 id:', id);
                }
            }

            // 3. 从 onclick 中提取
            if (!id) {
                const onclickAttr = row.getAttribute('onclick') ||
                                   (link ? link.getAttribute('onclick') : null);
                if (onclickAttr) {
                    const idMatch = onclickAttr.match(/id=['"]?([a-zA-Z0-9_-]+)['"]?/);
                    if (idMatch) {
                        id = idMatch[1];
                    }
                }
            }

            if (title && publishDate) {
                // 调试：输出 href 值
                console.log('行数据:', { title: title.substring(0, 30), href: href, id: id });

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
    console.log('提取到文章数量:', items.length);
    return items;
}
""")

        print(f"  获取到 {len(articles)} 条数据（DOM 提取）")

        if not articles:
            print("  没有获取到数据，停止翻页")
            break

        # 调试：打印前 5 条数据的日期
        for i, article in enumerate(articles[:5]):
            print(f"    [样本 {i+1}] 日期：{article.get('publishDate', '无')} - {article['title'][:40]}...")

        # 统计新数据和重复数据数量
        new_count = 0
        dup_count = 0
        page_has_old_data = False

        # 【优化】批量 IT 判断（一次请求判断多条，而不是逐条判断）
        print(f"  [AI 批量分类] 正在判断本页 {len(articles)} 条记录...")
        titles_to_check = [a.get('title', '') for a in articles]
        it_results = is_it_related_batch(titles_to_check)  # 返回 {索引：是否 IT}

        for idx, article in enumerate(articles):
            # 调试：打印提取到的日期
            if FLIP_STRATEGY == "date":
                if not article.get('publishDate'):
                    print(f"    [警告] 未提取到日期：{article.get('title', '')[:30]}...")
                else:
                    print(f"    [日期] {article['publishDate']} - {article['title'][:30]}...")

            # 检查日期是否超过阈值
            if FLIP_STRATEGY == "date" and article.get('publishDate'):
                if is_date_too_old(article['publishDate']):
                    print(f"    [日期过滤] 发现旧数据：{article['publishDate']} < {DATE_START}")
                    page_has_old_data = True
                    break

            key = f"{article['title']}{article.get('publishDate', '')}"
            if key in seen_keys:
                dup_count += 1
                continue
            seen_keys.add(key)
            new_count += 1

            # IT 相关检查（使用批量判断结果）
            title = article.get('title', '')
            is_it = it_results.get(idx, False)

            # 初始化 URL
            detail_url = ""

            # 【核心修改】IT 相关文章获取详情页 URL
            # 由于中海油网站使用 Vue.js 事件委托，自动化点击可能无效
            # 直接使用构造的 URL 作为主要方案
            if is_it:
                print(f"  [IT 相关] 处理：{title[:40]}...")

                # 优先使用 article_id 构造 URL（最可靠的方式）
                article_id = article.get('id', '')
                if article_id:
                    detail_url = construct_cnooc_url(article_id)
                    print(f"  [IT 相关] 使用构造 URL: {detail_url[:100]}...")
                else:
                    # 没有 id 时，尝试使用已有的 href
                    if article.get('href') and article.get('href').startswith('http'):
                        detail_url = article['href']
                        print(f"  [IT 相关] 使用已有 href: {detail_url[:100]}...")
                    else:
                        print(f"  [IT 相关] 无可用 URL，使用构造 URL（无 id）")
                        detail_url = ""

            # 如果没有获取到 URL，使用构造 URL 作为降级方案
            if not detail_url:
                article_id = article.get('id', '')
                if article_id:
                    detail_url = construct_cnooc_url(article_id)
                    print(f"  [IT 相关] 使用构造 URL: {detail_url[:100]}...")

            # 初始化 record
            record = {
                "company": "中海油",
                "title": title,
                "category": category_name,
                "publish_date": article.get('publishDate', ''),
                "url": detail_url,
                "content": "",
                "summary": "",
                "local_path": "",  # 本地 HTML 存档路径
                "fetched_at": datetime.now().isoformat(),
                "is_it_related": is_it  # 添加 IT 相关标记
            }

            # 【核心功能】如果是 IT 相关且有 URL，获取详情页内容并生成 AI 摘要
            if is_it and detail_url:
                print(f"    [IT 相关] 开始获取详情页内容...")

                # 获取详情页内容（使用并发标签页模式）
                detail_content = fetch_detail_content(context, detail_url)

                if detail_content:
                    record["content"] = detail_content[:5000]

                    # 生成 AI 摘要
                    print(f"    [AI 摘要] 开始生成...")
                    ai_summary = generate_ai_summary(detail_content, title)
                    if ai_summary:
                        record["summary"] = ai_summary
                        print(f"    [AI 摘要] 成功：{ai_summary[:30]}...")
                    else:
                        record["summary"] = detail_content[:60]
                        print(f"    [AI 摘要] 失败，使用原文前 60 字")

                    print(f"    详情内容：{len(detail_content)} 字")
                else:
                    record["summary"] = title[:60]
                    print(f"    详情页获取失败")
            else:
                if is_it:
                    print(f"  [IT] {title[:50]}...（无 URL）")
                record["summary"] = title[:60] if is_it else ""

            all_records.append(record)

        print(f"  当前页：{len(articles)} 条（新增：{new_count} 条，重复：{dup_count} 条）")

        # 根据策略判断是否停止翻页
        if FLIP_STRATEGY == "date" and page_has_old_data:
            print(f"  已抓取到阈值日期 ({DATE_START}) 之前的数据，停止翻页")
            break

        # 如果所有数据都是重复的，说明已到达最后一页
        if dup_count > 0 and new_count == 0:
            print(f"  当前页所有数据均为重复数据，已到达最后一页，停止翻页")
            break

        # 翻页 - 点击数字页码或 > 按钮
        next_clicked = False

        if current_page < max_pages:
            # 滚动到底部确保分页组件可见
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

            # 使用 JavaScript 点击下一个页码（最可靠的方式）
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
                        return {{ success: false, reason: 'page not found' }};
                    }}
                """)
                if result.get('success'):
                    next_clicked = True
                    print(f"  点击页码 {result.get('clicked')} 翻页")
            except:
                pass

            if not next_clicked:
                # 尝试点击 ">" 按钮
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
            time.sleep(2)  # 从 3 秒减少到 2 秒

        # 如果没有成功翻页，停止循环
        if not next_clicked:
            print("  已到达最后一页或达到最大页数限制")
            break

        current_page += 1

    # 正常清理资源
    try:
        if context:
            context.close()
    except Exception as e:
        print(f"   [资源清理] 警告：{e}")
    try:
        if playwright:
            playwright.stop()
    except Exception as e:
        print(f"   [Playwright清理] 警告：{e}")

    print(f"\n中海油采集完成！共 {len(all_records)} 条")
    return all_records


def main() -> None:
    """
    主函数 - 并行采集三家公司数据并处理结果

    工作流程:
        1. 使用 ThreadPoolExecutor 并行启动三家公司的采集任务
        2. 等待所有任务完成并合并结果
        3. 统计采集结果（按公司分类）
        4. 保存到 JSON 文件
        5. 存入 SQLite 数据库
        6. 导出 Excel 报表（仅 IT 相关数据）
        7. 生成 HTML 存档 ZIP（中石油详情）
        8. 发送电子邮件通知（带附件）

    输出:
        - JSON 文件：api_test/all_companies_result.json
        - SQLite 数据库：data/oil_tender.db
        - Excel 报表：data/exports/tender_report_YYYYMMDD.xlsx
        - HTML 存档 ZIP：output/tender_archive_YYYYMMDD_HHMMSS.zip
        - 邮件通知：发送至配置的收件人列表
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    start_time = time.time()
    start_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"开始时间：{start_datetime}")
    print("=" * 80)
    print("三家公司 API 统一采集脚本（并行模式）")
    print("=" * 80)

    all_records = []

    # 并行采集三家公司（每个线程独立启动浏览器）
    print("\n同时启动三家公司采集...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(collect_cnpc, FETCH_PAGES): "中石油",
            executor.submit(collect_sinopec, FETCH_PAGES): "中石化",
            executor.submit(collect_cnooc, FETCH_PAGES): "中海油",
        }
        for future in as_completed(futures):
            company = futures[future]
            try:
                records = future.result()
                all_records.extend(records)
                print(f"\n{company} 采集完成，获取 {len(records)} 条数据")
            except Exception as e:
                print(f"\n{company} 采集出错：{e}")

    # 结束统计
    end_time = time.time()
    elapsed = end_time - start_time
    end_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    print(f"\n" + "=" * 80)
    print(f"开始时间：{start_datetime}")
    print(f"结束时间：{end_datetime}")
    print(f"总耗时：{elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
    if all_records:
        avg_time = elapsed / len(all_records)
        print(f"平均速度：{avg_time:.2f} 秒/条")
    print(f"=" * 80)

    if all_records:
        # 统计
        from collections import Counter
        companies = Counter(r['company'] for r in all_records)
        print(f"\n按公司统计：{dict(companies)}")

        # 保存到文件
        output_file = os.path.join(BASE_DIR, "api_test", "all_companies_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到：{output_file}")

        # 保存到数据库
        sys.path.insert(0, BASE_DIR)
        try:
            from storage import Storage
            storage = Storage()
            new_count = storage.save_records(all_records)
            print(f"已保存 {new_count} 条新记录到数据库")

            # 导出 Excel（仅 IT 数据）
            excel_path = storage.export_to_excel(all_records)
            if excel_path:
                print(f"Excel 已导出：{excel_path}")

                # 生成 HTML 存档 ZIP（中石油详情）
                zip_path = ""
                try:
                    import generate_html_archive
                    zip_path = generate_html_archive.main()
                    print(f"HTML 存档 ZIP 已生成：{zip_path}")
                except Exception as zip_error:
                    print(f"HTML 存档 ZIP 生成失败：{zip_error}")
                    zip_path = ""

                # 发送邮件通知（使用采集到的 IT 记录，不依赖数据库）
                it_records = [r for r in all_records if r.get("is_it_related", False)]
                if it_records:
                    try:
                        from notifier import Notifier
                        notifier = Notifier()
                        # 直接使用采集到的 IT 记录发送邮件
                        notifier.send_daily_report(it_records, excel_path, zip_path)
                        print("邮件通知已发送")
                    except Exception as email_error:
                        print(f"邮件发送失败：{email_error}")
            else:
                print("Excel 导出失败（无 IT 数据）")
        except Exception as e:
            print(f"保存数据库失败：{e}")
    else:
        print("未获取到数据")


if __name__ == "__main__":
    main()
