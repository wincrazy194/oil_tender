#!/usr/bin/env python
"""
测试 AI 批量分类功能 - 验证超过 batch_size 时的处理能力
"""

from collect_all_companies_API_NEW import is_it_related_batch

# 模拟真实场景：25 条招标公告标题
test_titles = [
    "中国石油天然气股份有限公司软件开发项目招标公告",
    "管道设备采购项目招标公告",
    "信息系统运维服务招标公告",
    "阀门采购项目招标公告",
    "网络安全设备采购招标公告",
    "建筑工程招标公告",
    "数据库升级改造项目招标公告",
    "物业服务招标公告",
    "AI 视频分析系统招标公告",
    "车辆租赁服务招标公告",
    "云计算平台建设项目招标公告",
    "化学品采购招标公告",
    "服务器采购招标公告",
    "装修工程招标公告",
    "大模型应用开发招标公告",
    "办公用品采购招标公告",
    "RFID 传感器系统招标公告",
    "餐饮服务招标公告",
    "管理平台开发招标公告",
    "船舶租赁招标公告",
    "数字化系统建设招标公告",
    "电缆采购招标公告",
    "软件运维服务招标公告",
    "石油钻井平台设备招标公告",
    "管理信息系统招标公告",
]

print("=" * 80)
print("AI 批量分类测试 - 25 条标题")
print("=" * 80)
print(f"\n测试标题数量：{len(test_titles)}")
print(f"batch_size 设置：10（默认）\n")

# 执行批量分类
result = is_it_related_batch(test_titles, batch_size=10)

print("\n" + "=" * 80)
print("测试结果统计")
print("=" * 80)
print(f"返回结果数量：{len(result)}")
print(f"IT 相关数量：{sum(1 for v in result.values() if v)}")
print(f"非 IT 数量：{sum(1 for v in result.values() if not v)}")

print("\n" + "=" * 80)
print("IT 相关标题详情")
print("=" * 80)
for idx, is_it in result.items():
    if is_it:
        print(f"  [{idx+1}] {test_titles[idx]}")

print("\n" + "=" * 80)
print("验证结果")
print("=" * 80)
if len(result) == len(test_titles):
    print("- OK 所有标题都已处理")
else:
    print(f"- ERROR 有 {len(test_titles) - len(result)} 条标题未处理")

# 验证预期应该被识别为 IT 的标题
expected_it_indices = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
expected_it_count = len(expected_it_indices)
actual_it_count = sum(1 for v in result.values() if v)

print(f"- 预期 IT 相关约 {expected_it_count} 条，实际识别 {actual_it_count} 条")
