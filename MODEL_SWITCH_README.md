# 阿里云百炼多模型切换说明

## 概述

当使用的阿里云百炼模型 Token 不足时，系统会自动按顺序切换到下一个模型，确保 AI 服务持续运行。

## 配置方法

### 在 `config.py` 中配置模型列表

```python
# 多模型配置（按优先级排序）
MODELS = [
    "qwen-plus",        # 首选：Qwen Plus (性价比高)
    "qwen-max",         # 备选 1: Qwen Max (最强)
    "qwen-turbo",       # 备选 2: Qwen Turbo (最快)
]
```

## 工作原理

### 自动切换流程

1. **首选模型**: `qwen-plus`
2. **Token 不足时**: 自动切换到 `qwen-max`
3. **仍然不足**: 切换到 `qwen-turbo`
4. **全部失败**: 降级为关键词匹配

### 识别的错误类型

系统会自动识别以下 Token 不足错误并触发切换：

- **HTTP 402**: Payment Required (余额不足)
- **HTTP 429**: Too Many Requests (速率限制)
- **HTTP 503**: Service Unlimited (服务不可用)
- **错误消息包含**: `no free action`, `insufficient`, `quota`, `token`, `额度`, `余额` 等

## 日志输出示例

```
[AI 摘要] 使用模型：qwen-plus (尝试 1/3)
[AI 摘要] 模型 qwen-plus 错误：No free action words left today
[AI 摘要] Token 不足，尝试下一个模型...
[AI 摘要] 使用模型：qwen-max (尝试 2/3)
[AI 摘要] qwen-max 生成成功：45 字
```

## 可用模型

阿里云百炼常用模型：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| qwen-plus | 性价比高 | 常规任务（推荐首选） |
| qwen-max | 最强能力 | 复杂任务 |
| qwen-turbo | 速度最快 | 快速响应 |
| qwen-long | 长文本 | 超长文档处理 |

## 自定义模型顺序

根据你的需求调整模型优先级：

```python
# 示例 1：优先使用最强模型
MODELS = ["qwen-max", "qwen-plus", "qwen-turbo"]

# 示例 2：优先使用最快模型
MODELS = ["qwen-turbo", "qwen-plus", "qwen-max"]

# 示例 3：只使用一个模型
MODELS = ["qwen-plus"]
```

## 集成位置

已集成到以下函数：

1. **`generate_ai_summary()`**: 生成招标公告摘要
2. **`is_it_related_batch()`**: 批量 IT 分类判断

## 注意事项

1. **单个 API Key**: 只需要一个 API Key，无需配置多个
2. **自动降级**: 所有模型都失败时，会自动降级为关键词匹配
3. **无需额外代码**: 配置 `MODELS` 后自动生效
