"""
阿里云百炼多模型切换模块
当某个模型的 Token 不足时，自动切换到下一个模型
"""
import logging

logger = logging.getLogger(__name__)


class ModelSwitcher:
    """
    模型切换器 - 阿里云百炼专用
    支持多个模型轮询，当 Token 不足时自动切换
    """

    # DeepSeek 模型列表（按优先级排序）
    DEFAULT_MODELS = [
        "deepseek-chat",       # DeepSeek V3 (首选)
        "deepseek-reasoner",   # DeepSeek R1 (推理)
    ]

    def __init__(self, models: list[str] = None, api_key: str = None, base_url: str = None):
        """
        初始化模型切换器

        Args:
            models: 模型列表（按优先级排序）
            api_key: API Key
            base_url: 基础 URL
        """
        self.models = models if models else self.DEFAULT_MODELS.copy()
        self.api_key = api_key
        self.base_url = base_url.rstrip('/') if base_url else "https://api.deepseek.com/v1"

        # 当前模型索引
        self.current_index = 0

        # 模型失败记录
        self.failure_count = {}
        for model in self.models:
            self.failure_count[model] = 0

    def get_current_model(self) -> str:
        """获取当前模型名称"""
        if not self.models:
            raise RuntimeError("没有可用的模型")
        return self.models[self.current_index]

    def switch_to_next(self) -> bool:
        """
        切换到下一个模型
        返回是否成功切换
        """
        if len(self.models) <= 1:
            logger.warning("只有一个模型，无法切换")
            return False

        # 记录当前模型失败
        current_model = self.get_current_model()
        self.failure_count[current_model] = self.failure_count.get(current_model, 0) + 1
        logger.warning(f"模型 {current_model} Token 不足，切换到下一个... (失败次数：{self.failure_count[current_model]})")

        # 切换到下一个
        self.current_index = (self.current_index + 1) % len(self.models)

        logger.info(f"已切换到模型：{self.get_current_model()}")
        return True

    def reset(self):
        """重置为第一个模型"""
        self.current_index = 0
        logger.info("模型已重置为：{}", self.get_current_model())

    def is_token_error(self, status_code: int, error_message: str = "") -> bool:
        """
        判断是否是 Token 不足的错误

        常见错误：
        - No free action words left today (免费额度用完)
        - Insufficient balance (余额不足)
        - Quota exceeded (额度超出)
        - Token exhausted (Token 耗尽)
        """
        # 状态码检查
        if status_code in [402, 429, 503]:
            return True

        # 错误消息关键词
        token_error_keywords = [
            'no free action',
            'insufficient balance',
            'quota exceeded',
            'token',
            '额度',
            '余额',
            '耗尽',
            '不足',
            'exhausted',
            'limit',
        ]

        error_lower = error_message.lower()
        for keyword in token_error_keywords:
            if keyword.lower() in error_lower:
                return True

        return False

    def record_success(self):
        """记录成功调用"""
        current_model = self.get_current_model()
        self.failure_count[current_model] = 0


# ===== 全局单例 =====
_default_switcher = None


def init_model_switcher(models: list[str] = None, api_key: str = None, base_url: str = None):
    """初始化全局模型切换器"""
    global _default_switcher
    _default_switcher = ModelSwitcher(models, api_key, base_url)
    return _default_switcher


def get_current_model() -> str:
    """获取当前模型名称"""
    if _default_switcher is None:
        return "deepseek-chat"
    return _default_switcher.get_current_model()


def switch_to_next_model() -> bool:
    """切换到下一个模型"""
    if _default_switcher is None:
        return False
    return _default_switcher.switch_to_next()


def is_token_error(status_code: int, error_message: str = "") -> bool:
    """判断是否是 Token 错误"""
    if _default_switcher is None:
        # 简单判断
        if status_code in [402, 429, 503]:
            return True
        token_keywords = ['token', 'quota', 'balance', '额度', '余额']
        return any(kw in error_message.lower() for kw in token_keywords)
    return _default_switcher.is_token_error(status_code, error_message)
