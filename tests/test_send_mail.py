#!/usr/bin/env python
"""
发送测试邮件 - 包含中石化和中海油的 IT 相关记录
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifier import Notifier
from config import EMAIL_RECEIVERS

# 模拟测试数据（使用数据库中的真实 URL 格式）
test_records = [
    {
        "company": "中石化",
        "title": "胜利油田分公司信息化建设软件系统升级项目招标公告",
        "category": "招标公告",
        "publish_date": "2026-03-24",
        "url": "https://ebidding.sinopec.com/v3/portal/#/article/TENDER/7b16ef06-87e6-4dcd-82c4-941338d81bf2",
        "content": "本项目为胜利油田分公司信息化建设软件系统升级项目，主要包括...",
        "summary": "胜利油田信息化建设软件升级，包含服务器、数据库升级等",
        "is_it_related": True,
    },
    {
        "company": "中石化",
        "title": "燕山石化公司网络安全设备采购项目招标公告",
        "category": "招标公告",
        "publish_date": "2026-03-23",
        "url": "https://ebidding.sinopec.com/v3/portal/#/article/TENDER/abc12345-6789-4def-ghij-klmnopqrstuv",
        "content": "燕山石化公司拟采购网络安全设备一批，包括防火墙、入侵检测系统等...",
        "summary": "网络安全设备采购，包含防火墙、IDS 等安全设备",
        "is_it_related": True,
    },
    {
        "company": "中海油",
        "title": "中国海油信息化平台建设项目大模型应用开发招标公告",
        "category": "招标公告",
        "publish_date": "2026-03-24",
        "url": "https://bid.cnooc.com.cn/home/#/newsAlertDetails?index=0&childrenActive=4&id=584497&type=null",
        "content": "中国海洋石油集团有限公司信息化平台建设项目，包含大模型私有化部署...",
        "summary": "大模型应用开发，包含 AI 平台建设和私有化部署",
        "is_it_related": True,
    },
    {
        "company": "中海油",
        "title": "中海石油数据中心服务器存储设备采购项目",
        "category": "招标公告",
        "publish_date": "2026-03-23",
        "url": "https://bid.cnooc.com.cn/home/#/newsAlertDetails?index=0&childrenActive=4&id=584486&type=null",
        "content": "中海石油数据中心拟采购服务器及存储设备一批...",
        "summary": "数据中心服务器和存储设备采购",
        "is_it_related": True,
    },
    {
        "company": "中海油",
        "title": "海洋石油勘探开发信息系统运维服务项目",
        "category": "招标公告",
        "publish_date": "2026-03-22",
        "url": "https://bid.cnooc.com.cn/home/#/newsAlertDetails?index=0&childrenActive=4&id=584461&type=null",
        "content": "海洋石油勘探开发信息系统运维服务，包括日常运维、故障处理等...",
        "summary": "信息系统运维服务，包含日常运维和故障处理",
        "is_it_related": True,
    },
]

print("=" * 80)
print("测试邮件发送 - 中石化/中海油")
print("=" * 80)
print(f"\n收件人：{EMAIL_RECEIVERS}")
print(f"记录数量：{len(test_records)}")
print(f"公司分布:")
for r in test_records:
    print(f"  - {r['company']}: {r['title'][:40]}...")

# 发送邮件
notifier = Notifier()
notifier.send_daily_report(test_records)

print("\n" + "=" * 80)
print("发送完成!")
print("=" * 80)
