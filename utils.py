"""
公共工具函数模块
"""
from typing import Optional


# Token 错误判断的关键词列表
TOKEN_ERROR_KEYWORDS = [
    'no free action', 'insufficient', 'quota', 'token expired',
    'token 不足', 'token 耗尽', '额度', '余额', '耗尽', 'exhausted',
    'rate limit', 'too many requests'
]

# Token 不足时的 HTTP 状态码
TOKEN_ERROR_STATUS_CODES = [402, 429, 503]


def is_token_exhausted_error(status_code: int, error_message: str = "") -> bool:
    """
    判断是否是 Token 不足/配额耗尽的错误

    Args:
        status_code: HTTP 响应状态码
        error_message: 错误消息文本

    Returns:
        bool: 是否是 Token 不足错误

    Examples:
        >>> is_token_exhausted_error(429, "")
        True
        >>> is_token_exhausted_error(200, "quota exceeded")
        True
        >>> is_token_exhausted_error(500, "internal error")
        False
    """
    # 检查状态码
    if status_code in TOKEN_ERROR_STATUS_CODES:
        return True

    # 检查错误消息中是否包含 Token 相关关键词
    if error_message:
        error_lower = error_message.lower()
        for keyword in TOKEN_ERROR_KEYWORDS:
            if keyword.lower() in error_lower:
                return True

    return False


def is_it_related_by_keywords(title: str, it_keywords: list, it_exclude_keywords: list) -> bool:
    """
    使用关键词判断标题是否是 IT 相关

    判断逻辑:
    1. 标题必须包含至少一个 IT 关键词
    2. 如果同时包含 IT 关键词和排除关键词，则判断为"非 IT 相关"
       （排除关键词的优先级更高，用于过滤掉名称中带有 IT 但实际是非 IT 的项目）

    Args:
        title: 标题文本
        it_keywords: IT 关键词列表
        it_exclude_keywords: 排除关键词列表

    Returns:
        bool: 是否是 IT 相关

    Examples:
        >>> is_it_related_by_keywords("软件开发项目", ["软件"], ["管道"])
        True
        >>> is_it_related_by_keywords("软件采购管道检测", ["软件"], ["管道"])
        False
        >>> is_it_related_by_keywords("电气设备采购", ["软件"], ["电气"])
        False
    """
    if not title:
        return False

    title_lower = title.lower()

    # 检查是否包含 IT 关键词
    has_it_keyword = any(kw.lower() in title_lower for kw in it_keywords)
    if not has_it_keyword:
        return False

    # 如果包含 IT 关键词，再检查是否包含排除关键词
    # 如果同时包含，则排除（排除关键词优先级更高）
    has_exclude_keyword = any(kw.lower() in title_lower for kw in it_exclude_keywords)
    if has_exclude_keyword:
        return False

    return True


def safe_get_dict_value(data: dict, key: str, default=None, max_depth: int = 3):
    """
    安全地从嵌套字典中获取值

    Args:
        data: 字典对象
        key: 键名（支持点号分隔的嵌套键，如 'data.content'）
        default: 默认值
        max_depth: 最大嵌套深度

    Returns:
        获取到的值或默认值

    Examples:
        >>> safe_get_dict_value({'a': {'b': 1}}, 'a.b')
        1
        >>> safe_get_dict_value({'a': None}, 'a.b', 'default')
        'default'
    """
    if not isinstance(data, dict):
        return default

    keys = key.split('.') if '.' in key else [key]
    current = data

    for i, k in enumerate(keys):
        if i >= max_depth:
            break
        if not isinstance(current, dict) or k not in current:
            return default
        current = current[k]

    return current if current is not None else default
