#!/usr/bin/env python3
"""
测试标题提取功能
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test import extract_title_from_description, read_json_file, extract_items_data

def test_title_extraction():
    """测试标题提取功能"""
    print("=== 测试标题提取功能 ===\n")

    # 测试用例
    test_cases = [
        "【0714-17】結束的那一刻池畏倆人都已經氣喘吁吁💙幕後花絮 逆愛 Revenged Love  #逆愛 #柴雞蛋 #吳所畏",
        "【0714-16】池聘：就親了是嗎？導演：不不不，假親假親！🤣💙幕後花絮 逆愛 Revenged Love  #逆愛 #柴雞蛋",
        "【0714-18】池聘偷瞄大畏被大畏公開處刑，只好裝模作樣看手機🤣💙幕後花絮 逆愛 Revenged Love  #逆愛",
        "普通標題沒有【】格式 #标签1 #标签2",
        "沒有任何特殊格式的描述文本"
    ]

    for i, description in enumerate(test_cases, 1):
        title = extract_title_from_description(description)
        print(f"测试案例 {i}:")
        print(f"  原始描述: {description}")
        print(f"  提取标题: {title}")
        print()

def test_with_example_json():
    """使用example.json测试完整功能"""
    print("=== 使用example.json测试完整功能 ===\n")

    # 读取example.json
    json_data = read_json_file('example.json')
    if not json_data:
        print("无法读取example.json文件")
        return

    # 提取数据
    extracted_items = extract_items_data(json_data)

    if extracted_items:
        print(f"成功提取了 {len(extracted_items)} 条记录\n")

        # 显示前5条记录的标题提取结果
        print("前5条记录的标题提取结果:")
        for i, item in enumerate(extracted_items[:5], 1):
            print(f"\n记录 {i}:")
            print(f"  ID: {item['id']}")
            print(f"  提取的标题: {item['title']}")
            print(f"  原始描述: {item['description'][:100]}...")
            print("-" * 50)
    else:
        print("没有提取到任何数据")

if __name__ == "__main__":
    test_title_extraction()
    test_with_example_json()
