# AI Code Review 使用指南

## 概述

使用阿里云百炼大模型自动审查代码质量，发现潜在问题并给出改进建议。

## 快速开始

### 方式一：命令行使用

```bash
# 审查单个文件
cd E:\nandaoshuo\oil_tender
python ai_review.py collect_all_companies_API_NEW.py

# 审查整个目录
python ai_review.py .

# 安全专项审查
python ai_review.py . -t security

# 性能专项审查
python ai_review.py . -t performance

# 限制审查文件数量
python ai_review.py . --max-files 5

# 保存结果到文件
python ai_review.py . -o review_result.txt
```

### 方式二：在代码中调用

```python
from ai_review import AIReviewer

# 创建 Reviewer
reviewer = AIReviewer()

# 审查单个文件
result = reviewer.review_file("collect_all_companies_API_NEW.py")
print(result)

# 审查目录
result = reviewer.review_directory(".", max_files=3)
print(result)

# 审查代码片段
code = """
def login(user, pwd):
    sql = f"SELECT * FROM users WHERE name='{user}' AND password='{pwd}'"
    return db.execute(sql)
"""
result = reviewer.review_code_snippet(code, review_type="security")
print(result)
```

### 方式三：让 Claude Code 直接 Review

在当前对话中直接说：
- "Review 这个文件"
- "检查这部分的代码质量问题"
- "帮我看看有没有安全隐患"

---

## 审查类型

| 类型 | 参数 | 关注点 |
|------|------|--------|
| **综合审查** | `general` (默认) | 代码质量、潜在 Bug、安全性、性能、可维护性 |
| **安全审查** | `security` | SQL 注入、XSS、认证授权、敏感数据 |
| **性能审查** | `performance` | 算法复杂度、I/O 优化、内存使用、数据库查询 |

---

## 配置说明

### API Key 配置

在 `config.py` 中已有配置时会自动使用：

```python
# config.py
DASHSCOPE_API_KEY = "sk-xxxxxxxxx"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

或者设置环境变量：

```bash
set DASHSCOPE_API_KEY=sk-xxxxxxxxx
```

### 模型配置

默认按顺序尝试以下模型（Token 不足时自动切换）：

```python
MODELS = ["qwen-plus", "qwen-max", "qwen-turbo"]
```

---

## 命令行参数

```
usage: ai_review.py [-h] [-t {general,security,performance}] [-o OUTPUT]
                    [-m MAX_FILES] [-e EXTENSIONS [EXTENSIONS ...]]
                    path

AI Code Review 工具

positional arguments:
  path                  要审查的文件或目录路径

optional arguments:
  -h, --help            显示帮助信息
  -t, --type            审查类型 (general/security/performance)
  -o, --output          输出文件路径
  -m, --max-files       最多审查的文件数量
  -e, --extensions      要审查的文件扩展名列表
```

---

## 输出示例

```
============================================================
AI Code Review 工具
============================================================
审查路径：.
审查类型：general

📁 准备审查 3 个文件...
📄 正在审查：E:\nandaoshuo\oil_tender\collect_all_companies_API_NEW.py
  🤖 使用模型：qwen-plus (尝试 1/3)
  ✅ qwen-plus 完成审查

============================================================
审查结果
============================================================

## 审查结果

### 🔴 严重问题
- [collect_all_companies_API_NEW.py:1234] SQL 注入风险：使用 f-string 拼接 SQL 语句...

### 🟡 需要注意
- [collect_all_companies_API_NEW.py:567] 未处理异常情况...

### 🟢 改进建议
- [collect_all_companies_API_NEW.py:890] 函数过长，建议拆分...

### ✅ 做得好的地方
- 代码结构清晰，注释充分
- 使用了类型提示
```

---

## 最佳实践

### 1. 分模块审查
```bash
# 分别审查不同模块
python ai_review.py api_test/ -m 3
python ai_review.py . -e .py --max-files 5
```

### 2. 专项审查
```bash
# 发布前安全审查
python ai_review.py . -t security -o security_review.txt

# 性能优化前审查
python ai_review.py . -t performance
```

### 3. 集成到 CI/CD
```bash
# 在提交前运行（如果发现问题则失败）
python ai_review.py . -o review.md
# 然后检查结果中是否有🔴严重问题
```

---

## 常见问题

### Q: 审查速度慢怎么办？
A: 使用 `-m` 参数限制文件数量，或使用更快的模型：
```python
DEFAULT_MODEL = "qwen-turbo"  # 最快
```

### Q: 如何自定义审查重点？
A: 修改 `REVIEW_PROMPTS` 字典，添加自定义审查维度。

### Q: 支持哪些编程语言？
A: 理论上支持所有主流语言，修改 `extensions` 参数即可：
```bash
python ai_review.py . -e .py .js .ts
```

### Q: 如何忽略某些文件？
A: 修改代码中的 `exclude_dirs` 集合，或在使用时指定具体文件。

---

## 集成建议

### Git Hook（提交前审查）
在 `.git/hooks/pre-commit` 中：
```bash
#!/bin/bash
python ai_review.py $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') -t security
```

### VS Code 集成
在 `settings.json` 中添加：
```json
{
    "python.terminal.executeInFileDir": true
}
```
然后右键文件选择在终端中运行 `ai_review.py`。

---

## 文件清单

- `ai_review.py` - AI Review 主程序
- `AI_REVIEW_README.md` - 使用说明（本文件）
- `config.py` - 配置文件（API Key、模型等）
