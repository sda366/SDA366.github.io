#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 E:\\WorkBuddy生成内容\\ 目录下的所有22课课件HTML文件添加导航链接。
每个文件自动提取主题色，插入导航CSS和导航HTML块。
将结果输出到 E:\\WorkBuddy生成内容\\nav_output\\ 目录。
"""

import re
import os

WORK_DIR = r"E:\WorkBuddy生成内容"

LESSON_NAMES = {
    1: "古代埃及", 2: "古代两河流域", 3: "古代印度",
    4: "希腊城邦和亚历山大帝国", 5: "罗马城邦和罗马帝国", 6: "希腊罗马古典文化",
    7: "基督教的兴起和法兰克王国", 8: "西欧庄园", 9: "中世纪城市和大学的兴起",
    10: "拜占庭帝国和查士丁尼法典", 11: "古代日本", 12: "阿拉伯帝国",
    13: "西欧经济和社会的发展", 14: "文艺复兴运动", 15: "探寻新航路",
    16: "早期殖民掠夺", 17: "君主立宪制的英国", 18: "美国的独立",
    19: "法国大革命和拿破仑帝国", 20: "第一次工业革命",
    21: "马克思主义的诞生和国际共产主义运动的兴起", 22: "活动课唱响国际歌"
}

PREV_NEXT = {
    1: (None, 2), 2: (1, 3), 3: (2, 4), 4: (3, 5), 5: (4, 6),
    6: (5, 7), 7: (6, 8), 8: (7, 9), 9: (8, 10), 10: (9, 11),
    11: (10, 12), 12: (11, 13), 13: (12, 14), 14: (13, 15),
    15: (14, 16), 16: (15, 17), 17: (16, 18), 18: (17, 19),
    19: (18, 20), 20: (19, 21), 21: (20, 22), 22: (21, None)
}

THEME_COLORS = {
    1: "#0f3460", 2: "#6B4423", 3: "#FF6600", 4: "#2a5298",
    5: "#8B0000", 6: "#663399", 7: "#2E7D32", 8: "#8B7355",
    9: "#4A5568", 10: "#1a1a3e", 11: "#DC143C", 12: "#B8860B",
    13: "#2C5F2D", 14: "#B8860B", 15: "#1565C0", 16: "#8B0000",
    17: "#4A2C8A", 18: "#D32F2F", 19: "#002654", 20: "#8B7355",
    21: "#CC0000", 22: "#CC0000"
}


def get_filename(lesson_num):
    name = LESSON_NAMES[lesson_num]
    return f"九年级历史上_第{lesson_num}课_{name}.html"


def extract_theme_color(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return None
    m = re.search(r'border-bottom\s*:\s*3px\s+solid\s+(#[0-9A-Fa-f]{3,8})', content)
    return m.group(1) if m else None


def find_container_end(content):
    if 'class="lesson-nav"' in content:
        return None
    body_end = content.rfind("</body>")
    if body_end == -1:
        return None
    before_body = content[:body_end]
    last_div = before_body.rstrip().rfind("</div>")
    return last_div if last_div >= 0 else None


def generate_nav_css(theme_color):
    hex_color = theme_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    lines = []
    lines.append("")
    lines.append("        /* 导航链接 */")
    lines.append("        .lesson-nav {")
    lines.append("            display: flex; justify-content: space-between; align-items: center;")
    lines.append(f"            padding: 20px 30px; background: #f8f9fa; border-top: 3px solid {theme_color};")
    lines.append("            flex-wrap: wrap; gap: 10px;")
    lines.append("        }")
    lines.append("        .lesson-nav a {")
    lines.append("            text-decoration: none; font-size: 14pt; font-weight: bold;")
    lines.append("            padding: 10px 20px; border-radius: 25px; transition: all 0.3s;")
    lines.append("        }")
    lines.append("        .lesson-nav .prev-link {")
    lines.append(f"            background: #fff; color: {theme_color}; border: 2px solid {theme_color};")
    lines.append("        }")
    lines.append("        .lesson-nav .prev-link:hover { background:#FFF0F0; transform:translateX(-3px); }")
    lines.append("        .lesson-nav .next-link {")
    lines.append(f"            background: linear-gradient(135deg,{theme_color} 0%,{theme_color}dd 100%); color:#fff;")
    lines.append("        }")
    lines.append(f"        .lesson-nav .next-link:hover {{ transform:translateX(3px); box-shadow:0 5px 15px rgba({r},{g},{b},0.4); }}")
    lines.append("        .lesson-nav .home-link {")
    lines.append("            background: #e9ecef; color: #333; border: 2px solid #adb5bd;")
    lines.append("        }")
    lines.append("        .lesson-nav .home-link:hover { background:#dee2e6; }")
    lines.append("")
    lines.append("        @media print { body{background:#fff;padding:0} .container{box-shadow:none} .lesson-nav{display:none} }")
    return "\n".join(lines)


def generate_nav_html(lesson_num):
    prev_lesson, next_lesson = PREV_NEXT[lesson_num]
    
    if prev_lesson is None:
        prev_html = '<a href="javascript:void(0)" class="prev-link" style="opacity:0.5;cursor:default;">本课为第一课</a>'
    else:
        prev_file = get_filename(prev_lesson)
        prev_name = LESSON_NAMES[prev_lesson]
        prev_html = f'<a href="{prev_file}" class="prev-link">← 第{prev_lesson}课：{prev_name}</a>'
    
    if next_lesson is None:
        next_html = '<a href="javascript:void(0)" class="next-link" style="opacity:0.5;cursor:default;">本课为最后一课</a>'
    else:
        next_file = get_filename(next_lesson)
        next_name = LESSON_NAMES[next_lesson]
        next_html = f'<a href="{next_file}" class="next-link">第{next_lesson}课：{next_name} →</a>'
    
    home_html = '<a href="index.html" class="home-link">🏠 返回导航页</a>'
    
    lines = []
    lines.append("")
    lines.append("        <!-- 课程导航 -->")
    lines.append('        <div class="lesson-nav">')
    lines.append(f"            {prev_html}")
    lines.append(f"            {home_html}")
    lines.append(f"            {next_html}")
    lines.append("        </div>")
    return "\n".join(lines)


def process_file(lesson_num):
    filename = get_filename(lesson_num)
    filepath = os.path.join(WORK_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"[{lesson_num}] 文件不存在: {filename}")
        return None
    
    print(f"[{lesson_num}] 处理: {filename}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    extracted_color = extract_theme_color(filepath)
    theme_color = extracted_color if extracted_color else THEME_COLORS.get(lesson_num, "#333")
    if extracted_color:
        print(f"  主题色: {extracted_color}")
    else:
        print(f"  默认色: {theme_color}")
    
    if 'class="lesson-nav"' in content:
        print(f"  已有导航，跳过")
        return None
    
    nav_css = generate_nav_css(theme_color)
    style_end = content.rfind("</style>")
    if style_end == -1:
        print(f"  [错误] 找不到 </style>")
        return None
    
    content = content[:style_end] + nav_css + "\n" + content[style_end:]
    
    container_end = find_container_end(content)
    if container_end is None:
        print(f"  [错误] 找不到容器结束位置")
        return None
    
    nav_html = generate_nav_html(lesson_num)
    content = content[:container_end] + nav_html + "\n    " + content[container_end:]
    
    print(f"  ✓ 修改完成")
    return content


def main():
    print("=" * 60)
    print("为九年级历史上册课件添加导航链接")
    print("=" * 60)
    
    results = {}
    
    for lesson_num in range(1, 23):
        result = process_file(lesson_num)
        if result is not None:
            results[lesson_num] = result
    
    print(f"\n修改了 {len(results)} 个文件")
    
    # 输出每个修改文件的文件名和内容，供 Write 工具使用
    for lesson_num, content in sorted(results.items()):
        filename = get_filename(lesson_num)
        filepath = os.path.join(WORK_DIR, filename)
        print(f"\n=== FILE:{filepath} ===")
        # Print first 10 lines and last 10 lines for verification
        lines = content.split('\n')
        print(f"总行数: {len(lines)}")
        # Check nav CSS and HTML presence
        has_nav_css = 'lesson-nav' in content and 'class="lesson-nav"' in content
        print(f"导航已添加: {has_nav_css}")


if __name__ == "__main__":
    main()
