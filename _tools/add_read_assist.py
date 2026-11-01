# -*- coding: utf-8 -*-
"""
小学朗读小助手 · 批量注入脚本（v2：注入到 <body> 开头）

为什么要在 <body> 开头：
    课件页面自身脚本在顶层就取 window.speechSynthesis，
    助手必须先于它执行，才能在不支持的浏览器里「接管」
    课件朗读按钮（弹出引导层，而不是无声装读）。

用法：
    python add_read_assist.py <根目录> [js 相对根目录的路径]

行为：
1. 扫描 <根目录> 下所有 *.html；
2. 先删除旧位置（</body> 前）的注入标签（自动迁移旧版页面）；
3. 在 <body ...> 开标签后插入 <script src="...">（按层级算相对路径）；
4. 已在新位置的自动跳过。
"""
import os
import re
import sys

if len(sys.argv) < 2:
    print("用法: python add_read_assist.py <根目录> [js相对路径]")
    sys.exit(1)

ROOT = sys.argv[1].rstrip("/\\")
JS = sys.argv[2] if len(sys.argv) > 2 else "js/read-assist.js"
JS = JS.replace("\\", "/").lstrip("/")

FLAG = JS.split("/")[-1]          # 用文件名判断是否已注入
# 排除名单：诊断页必须保持「真实环境」，垫片会干扰它的检测
EXCLUDE = ("sound-check.html", "voice-setup.html")   # 诊断/说明页须保持真实环境
added, skipped, failed = [], [], []

BODY_OPEN = re.compile(r'<body[^>]*>', re.I)
OLD_TAIL  = re.compile(r'\s*<script src="[^"]*' + re.escape(FLAG) + r'"></script>(?=\s*</body>)')

for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.lower().endswith(".html"):
            continue
        if f in EXCLUDE:
            continue
        path = os.path.join(dirpath, f)
        try:
            html = open(path, encoding="utf-8").read()
        except Exception as e:
            failed.append((path, str(e)))
            continue

        has_flag = FLAG in html
        if has_flag and BODY_OPEN.search(html) is None:
            failed.append((path, "未找到 <body> 开标签"))
            continue

        if has_flag:
            # 已注入：若在旧位置（</body> 前），先摘除以便迁移到新位置
            html2 = OLD_TAIL.sub("", html)
            if html2 == html:
                # 标签不在旧位置 → 已在新位置，跳过
                skipped.append(path)
                continue
            html = html2
            action = "迁移"
        else:
            action = "新增"

        # 按层级算相对路径
        rel_dir = os.path.relpath(dirpath, ROOT)
        depth = 0 if rel_dir == "." else len(rel_dir.replace("\\", "/").split("/"))
        src = ("../" * depth) + JS

        tag = '\n<script src="%s"></script>' % src
        m = BODY_OPEN.search(html)
        html = html[: m.end()] + tag + html[m.end():]

        open(path, "w", encoding="utf-8").write(html)
        (added if action == "新增" else skipped).append(path) if False else None
        if action == "迁移":
            added.append(path + "  [迁移]")
        else:
            added.append(path)

print("注入完成：新增/迁移 %d 个，已是新位置跳过 %d 个，失败 %d 个" % (len(added), len(skipped), len(failed)))
for p in failed[:10]:
    print("  ✗ 失败:", p[0], "->", p[1])
if added:
    print("  示例:", os.path.relpath(added[0].split("  [")[0], ROOT))
print("提示：改动后抽验 1~2 页，确认页面原有功能不受影响。")
