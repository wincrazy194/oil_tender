#!/usr/bin/env python
"""
测试邮件中 URL 的格式 - 验证中海油/中石化链接是否正常
"""

import sys
import re
sys.path.insert(0, '..')

from notifier import Notifier

# 模拟测试数据
test_records = [
    {
        "company": "中石化",
        "title": "测试标题 1-软件开发项目",
        "category": "招标公告",
        "publish_date": "2026-03-24",
        "url": "https://ebidding.sinopec.com/v3/portal/#/article/TENDER/7b16ef06-87e6-4dcd-82c4-941338d81bf2",
        "content": "",
        "summary": "测试摘要",
        "is_it_related": True,
    },
    {
        "company": "中海油",
        "title": "测试标题 2-网络安全设备采购",
        "category": "招标公告",
        "publish_date": "2026-03-24",
        "url": "https://bid.cnooc.com.cn/home/#/newsAlertDetails?index=0&childrenActive=4&id=584497&type=null",
        "content": "",
        "summary": "测试摘要",
        "is_it_related": True,
    },
    {
        "company": "中石油",
        "title": "测试标题 3-信息系统运维",
        "category": "招标公告",
        "publish_date": "2026-03-24",
        "url": "https://www.cnpcbidding.com/#/tenders/detail?id=12345",
        "content": "",
        "summary": "测试摘要",
        "is_it_related": True,
    },
]

notifier = Notifier()
html = notifier._build_section("IT 业务", test_records)

print("=" * 80)
print("URL 验证结果")
print("=" * 80)

# 检查 URL 是否正确包含 #
href_pattern = r'href="([^"]+)"'
matches = re.findall(href_pattern, html)

all_passed = True
for i, url in enumerate(matches):
    record = test_records[i] if i < len(test_records) else None
    expected_url = record["url"] if record else None

    print(f"\n记录 {i+1} ({record['company']}):")
    print(f"  原始 URL: {expected_url}")
    print(f"  邮件 URL: {url}")

    # 检查 # 是否被编码
    if '%23' in url:
        print(f"  [FAIL] # 被编码成了 %23")
        all_passed = False
    elif '#' in url and '#' in expected_url:
        print(f"  [PASS] # 保留完好")
    elif '#' not in expected_url:
        print(f"  [PASS] URL 不含 #")
    else:
        print(f"  [WARN] URL 格式异常")
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("所有 URL 测试通过!")
else:
    print("部分 URL 测试失败!")
print("=" * 80)
