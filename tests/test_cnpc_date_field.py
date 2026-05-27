"""
中石油日期字段测试脚本
用于检测 API 返回的数据结构中日期字段的实际名称
"""
import json
import time
from playwright.sync_api import sync_playwright


def test_cnpc_records_structure():
    """
    测试中石油 API 返回的 records 数据结构
    输出字段名称，特别是日期字段
    """
    print("=" * 80)
    print("中石油 API 数据结构测试")
    print("=" * 80)

    base_url = "https://www.cnpcbidding.com"
    list_url = f"{base_url}/#/tenders"
    user_data_dir = r"E:\nandaoshuo\oil_tender\api_test\browser_data_api"

    print(f"\n访问页面：{list_url}")

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

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(list_url, wait_until="domcontentloaded", timeout=60000)

        # 等待列表元素出现
        try:
            page.wait_for_selector('.box_data, button:has-text("搜索")', timeout=10000)
            print("[等待] 列表元素已加载")
        except:
            print("[等待] 超时，继续执行")

        time.sleep(1)

        # ===== 用户手动操作阶段 =====
        print("\n" + "=" * 60)
        print("请在浏览器中完成以下操作：")
        print("  1. 点击【搜索】按钮")
        print("  2. 如有验证码，请手动完成验证码验证")
        print("\n完成后按【回车键】继续...")
        print("=" * 60)

        try:
            input()
        except:
            print("未检测到输入，等待 30 秒后继续...")
            time.sleep(30)

        time.sleep(1)

        # 拦截 API 响应
        print("\n等待列表 API 响应...")
        body = None

        try:
            with page.expect_response(
                lambda r: '/cms/article/page' in r.url and r.status == 200,
                timeout=30000
            ) as response_info:
                search_btn = page.locator('button:has-text("搜索")').first
                if search_btn.is_visible(timeout=10000):
                    search_btn.click(timeout=10000)
                    print("已点击搜索按钮")
                else:
                    print("搜索按钮不可见，尝试等待...")
                    page.wait_for_timeout(2000)

            response = response_info.value
            body = response.text()
            print(f"[获取到列表 API] 长度={len(body)}")

        except Exception as e:
            print(f"等待列表 API 失败：{e}")
            return

        # 解密 API 响应
        print("\n解密 API 响应...")
        result = decrypt_api_response_in_browser(page, body)

        if not result.get('success'):
            error_msg = result.get('error', '未知错误')
            print(f"解密失败：{error_msg}")
            return

        data = result['data']
        print(f"\n解密后的数据结构:")
        print(f"  顶层键：{list(data.keys()) if isinstance(data, dict) else '非字典类型'}")

        # 处理嵌套结构
        if 'data' in data and isinstance(data.get('data'), dict):
            print(f"  data.data 的键：{list(data['data'].keys())}")
            data = data.get('data')

        records = data.get('records', data.get('data', {}).get('records', []))
        if not records and isinstance(data.get('data'), list):
            records = data['data']

        if not records:
            print("未获取到 records")
            return

        print(f"\n获取到 {len(records)} 条记录")
        print("\n=== 第一条记录的完整结构 ===")
        print(json.dumps(records[0], indent=2, ensure_ascii=False))

        print("\n=== 第一条记录的所有键 ===")
        first_record_keys = list(records[0].keys())
        for i, key in enumerate(first_record_keys, 1):
            value = records[0].get(key)
            value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"  {i}. {key}: {value_str}")

        # 检查可能的日期字段
        print("\n=== 检查可能的日期字段 ===")
        date_field_candidates = [
            'publishedTime', 'publishTime', 'publishDate',
            'createdTime', 'createTime', 'createDate',
            'updatedTime', 'updateTime', 'updateDate',
            'date', 'time', 'publishtime', 'publishtime'
        ]

        for field in date_field_candidates:
            value = records[0].get(field)
            if value:
                print(f"  [找到] {field}: {value}")
            else:
                print(f"  [空值] {field}")

    except Exception as e:
        print(f"\n异常：{e}")
        import traceback
        traceback.print_exc()

    finally:
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

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


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
            body = json_lib.loads(body)
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


if __name__ == "__main__":
    test_cnpc_records_structure()
