"""
AI Code Review 工具
使用阿里云百炼大模型自动审查代码质量
"""
import os
import sys
import requests
from pathlib import Path
from typing import Optional

# 配置
DEFAULT_MODEL = "deepseek-chat"
MODELS = ["deepseek-chat", "deepseek-reasoner"]

# Review 提示词模板
REVIEW_PROMPTS = {
    "general": """你是一个专业的代码审查专家。请对以下代码进行全面审查，关注：

1. **代码质量问题**
   - 代码结构是否清晰
   - 函数是否过长（建议不超过 50 行）
   - 变量命名是否规范
   - 是否有重复代码

2. **潜在 Bug**
   - 空指针/None 检查
   - 异常处理是否完善
   - 资源泄漏风险（文件、数据库连接等）
   - 并发问题

3. **安全性**
   - SQL 注入风险
   - 敏感信息泄露（密码、API Key 等）
   - 输入验证

4. **性能优化**
   - 低效的循环
   - 不必要的数据库查询
   - 可优化的算法

5. **可维护性**
   - 注释是否充分
   - 代码是否易于理解
   - 是否符合 Python 最佳实践

请按以下格式输出审查结果：

## 审查结果

### 🔴 严重问题
- [文件名：行号] 问题描述 + 修复建议

### 🟡 需要注意
- [文件名：行号] 问题描述 + 修复建议

### 🟢 改进建议
- [文件名：行号] 问题描述 + 优化建议

### ✅ 做得好的地方
- 列出代码中的优点

如果没有发现问题，请直接说明。""",

    "security": """你是一个安全专家。请审查以下代码的安全问题：

1. **注入攻击**
   - SQL 注入
   - 命令注入
   - XSS 攻击

2. **认证与授权**
   - 硬编码凭证
   - 弱密码
   - 权限校验缺失

3. **数据安全**
   - 敏感数据加密
   - 日志泄露
   - 不安全的随机数

4. **依赖安全**
   - 过时的库
   - 已知漏洞

请重点关注安全问题，按严重程度排序输出。""",

    "performance": """你是一个性能优化专家。请审查以下代码的性能问题：

1. **算法复杂度**
   - 低效的循环嵌套
   - 可优化的数据结构

2. **I/O 操作**
   - 频繁的磁盘/网络访问
   - 缺少缓存

3. **内存使用**
   - 内存泄漏
   - 不必要的对象创建

4. **数据库**
   - N+1 查询
   - 缺少索引
   - 事务使用

请给出具体的性能问题和优化建议。"""
}


class AIReviewer:
    """AI 代码审查器"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        初始化 AI Reviewer

        Args:
            api_key: 阿里云 DashScope API Key
            base_url: API 基础 URL
            model: 使用的模型名称
        """
        # 从 config 导入配置
        try:
            from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
            self.api_key = api_key or DASHSCOPE_API_KEY
            self.base_url = base_url or DASHSCOPE_BASE_URL
        except ImportError:
            self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
            self.base_url = base_url or "https://api.deepseek.com/v1"

        self.model = model or DEFAULT_MODEL
        self.api_url = self.base_url.rstrip('/') + '/chat/completions'

    def review_file(self, file_path: str, review_type: str = "general") -> str:
        """
        审查单个文件

        Args:
            file_path: 文件路径
            review_type: 审查类型 (general/security/performance)

        Returns:
            审查结果
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return f"[错误] 文件不存在：{file_path}"

        # 只处理代码文件
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
        if file_path.suffix not in code_extensions:
            return f"[警告] 跳过非代码文件：{file_path}"

        print(f"[*] 正在审查：{file_path}")

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 构建 prompt
        prompt = REVIEW_PROMPTS.get(review_type, REVIEW_PROMPTS["general"])
        full_prompt = f"""{prompt}

---
**待审查代码**：
文件：{file_path}

```{file_path.suffix.lstrip('.')}
{content}
```"""

        return self._call_ai(full_prompt)

    def review_directory(self, dir_path: str, review_type: str = "general",
                         extensions: list = None, max_files: int = None) -> str:
        """
        审查整个目录

        Args:
            dir_path: 目录路径
            review_type: 审查类型
            extensions: 要审查的文件扩展名列表
            max_files: 最多审查的文件数量

        Returns:
            审查结果汇总
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return f"[错误] 目录不存在：{dir_path}"

        if extensions is None:
            extensions = ['.py']

        # 收集文件
        files = []
        for ext in extensions:
            files.extend(dir_path.rglob(f"*{ext}"))

        # 排除常见非业务目录
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'build', 'dist'}
        files = [f for f in files if not any(exclude in str(f) for exclude in exclude_dirs)]

        if max_files:
            files = files[:max_files]

        print(f"[*] 准备审查 {len(files)} 个文件...")

        if not files:
            return "[警告] 没有找到可审查的文件"

        # 合并文件内容
        combined_content = ""
        file_list = []
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                combined_content += f"\n\n{'='*60}\n"
                combined_content += f"文件：{file.relative_to(dir_path) if file.is_relative_to(dir_path) else file}\n"
                combined_content += f"{'='*60}\n\n"
                combined_content += content
                file_list.append(str(file))
            except Exception as e:
                print(f"[警告] 读取失败 {file}: {e}")

        # 构建 prompt
        prompt = REVIEW_PROMPTS.get(review_type, REVIEW_PROMPTS["general"])
        full_prompt = f"""{prompt}

---
**待审查文件列表**：
{'\n'.join(map(str, file_list))}

**代码内容**：
{combined_content}"""

        return self._call_ai(full_prompt)

    def review_code_snippet(self, code: str, review_type: str = "general") -> str:
        """
        审查代码片段

        Args:
            code: 代码片段
            review_type: 审查类型

        Returns:
            审查结果
        """
        prompt = REVIEW_PROMPTS.get(review_type, REVIEW_PROMPTS["general"])
        full_prompt = f"""{prompt}

---
**待审查代码**：
```python
{code}
```"""

        return self._call_ai(full_prompt)

    def _call_ai(self, prompt: str, max_retries: int = len(MODELS)) -> str:
        """
        调用 AI 模型

        Args:
            prompt: 提示词
            max_retries: 最大重试次数（模型切换）

        Returns:
            AI 响应
        """
        if not self.api_key:
            return "[错误] 未配置 API Key\n请设置 DASHSCOPE_API_KEY 环境变量或在 config.py 中配置"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 遍历模型尝试
        for i, model in enumerate(MODELS):
            try:
                print(f"  [AI] 使用模型：{model} (尝试 {i+1}/{len(MODELS)})")

                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的代码审查专家，擅长发现代码问题并给出建设性的改进建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.3  # 较低温度，更严谨
                }

                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
                resp_data = resp.json()

                # 检查错误
                if resp_data.get("error"):
                    error_msg = resp_data["error"].get("message", "未知错误")
                    print(f"  [警告] 模型 {model} 错误：{error_msg}")

                    # 判断是否是 Token 不足
                    is_token_err = resp.status_code in [402, 429, 503] or \
                                   any(kw in error_msg.lower() for kw in ['token', 'quota', 'balance', '额度', '余额'])

                    if is_token_err:
                        print(f"  [提示] Token 不足，尝试下一个模型...")
                        continue
                    else:
                        return f"[错误] API 错误：{error_msg}"

                # 成功响应
                if resp.status_code == 200 and resp_data.get("choices"):
                    content = resp_data["choices"][0]["message"]["content"].strip()
                    print(f"  [完成] {model} 完成审查")
                    return content

            except requests.exceptions.Timeout:
                print(f"  [超时] 模型 {model} 请求超时")
                continue
            except Exception as e:
                print(f"  [异常] 模型 {model} 异常：{e}")
                continue

        return "[错误] 所有模型都调用失败，请检查网络连接或 API Key 配置"


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Code Review 工具")
    parser.add_argument("path", help="要审查的文件或目录路径")
    parser.add_argument("-t", "--type", choices=["general", "security", "performance"],
                        default="general", help="审查类型")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-m", "--max-files", type=int, help="最多审查的文件数量")
    parser.add_argument("-e", "--extensions", nargs="+", default=[".py"],
                        help="要审查的文件扩展名")

    args = parser.parse_args()

    # 创建 Reviewer
    reviewer = AIReviewer()

    # 执行审查
    print("=" * 60)
    print("AI Code Review 工具")
    print("=" * 60)
    print(f"审查路径：{args.path}")
    print(f"审查类型：{args.type}")
    print()

    path = Path(args.path)
    if path.is_file():
        result = reviewer.review_file(str(path), args.type)
    elif path.is_dir():
        result = reviewer.review_directory(str(path), args.type,
                                           args.extensions, args.max_files)
    else:
        result = f"[错误] 路径不存在：{args.path}"

    # 输出结果
    print("\n" + "=" * 60)
    print("审查结果")
    print("=" * 60)

    # 使用 UTF-8 编码输出，避免 Windows 命令行编码问题
    try:
        print(result)
    except UnicodeEncodeError:
        # 如果包含 emoji，尝试用 replace 忽略无法编码的字符
        print(result.encode('gbk', 'replace').decode('gbk'))

    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"\n[*] 结果已保存到：{args.output}")


if __name__ == "__main__":
    main()
