# API 探测工具集

本文件夹包含对 https://www.cnpcbidding.com 网站的 API 探测和分析工具。

## 核心发现

### API 端点
- **URL**: `https://www.cnpcbidding.com/cms/article/page`
- **方法**: POST
- **请求头**: `Content-Type: application/json;charset=UTF-8`, `MACHINE_CODE: <timestamp>`

### 加密机制

网站使用 RSA 加密传输数据，关键信息：

1. **密钥存储**: localStorage
   - `logo1`: RSA 公钥
   - `logo2`: RSA 私钥

2. **密钥来源**: `/cms/css/bj.css` 文件中隐藏的 base64 编码数据

3. **加密流程**:
   ```
   JSON 数据 → Base64 编码 → RSA 公钥加密 (encryptLong) → 发送
   ```

4. **解密流程**:
   ```
   响应数据 → RSA 私钥解密 (decryptLong) → Base64 解码 → JSON 数据
   ```

5. **依赖库**: JSEncrypt / encryptlong

### 请求参数示例
```json
{
  "category": "ZBGG",    // 公告类型：ZBGG=招标公告，JSJG=中标结果
  "keyword": "",
  "page": 1,
  "pageSize": 20,
  "publishTime": "",
  "region": ""
}
```

## 文件说明

### 探测工具
| 文件 | 用途 |
|------|------|
| `find_api.py` | 拦截网络请求，定位 API 端点 |
| `analyze_api.py` | 分析 API 请求参数和响应格式 |
| `find_js.py` | 下载并分析网站 JS 文件 |
| `find_encrypt_func.js` | 查找加密函数定义 |
| `extract_request_utils.py` | 提取请求工具模块 |
| `extract_encrypt.py` | 提取加密相关代码 |

### 提取的代码
| 文件 | 说明 |
|------|------|
| `request_utils.js` | 提取的加密请求工具函数 |
| `request_module.js` | 请求模块完整代码 |
| `request_real.js` | 实际请求示例 |
| `js_files/` | 下载的原始 JS 文件 |

### 采集脚本
| 文件 | 说明 |
|------|------|
| `api_scraper.py` | 第一版 API 采集脚本 |
| `api_scraper_v2.py` ~ `v6.py` | 迭代版本 |
| `api_scraper_final.py` | 最终版 - 使用页面原生 API |
| `api_scraper_final_v2.py` | 实用版 - DOM 解析 + 浏览器处理验证码 |

## 使用方法

### 方案一：直接 API 调用（需要处理验证码）
```bash
python api_scraper_final.py
```

### 方案二：浏览器自动化（推荐）
```bash
python api_scraper_final_v2.py
```

## 注意事项

1. 验证码是主要障碍，需要使用真实浏览器会话处理
2. 密钥存储在 localStorage 中，首次运行需要从 CSS 文件获取
3. 建议使用 `api_scraper_final_v2.py`，它使用浏览器自动处理验证码和加密
4. 浏览器用户数据保存在 `browser_data_api/` 目录，可复用会话状态

## 相关 API

- 招标公告：`POST /cms/article/page` (category: "ZBGG")
- 中标结果：`POST /cms/article/page` (category: "JSJG")
- 候选人公示：`POST /cms/article/page` (category: "DBGS")
