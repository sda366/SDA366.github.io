import re, glob, os

os.chdir("E:/WorkBuddy生成内容/九上新版推送学科网课件")

CANON = "基于新版教材 · 交互式学习课件"   # 目标统一句（保留中间点 ·）

files = sorted(glob.glob("九上-U*.html"))
print("待处理课件数:", len(files))

report = []
changed = 0

for f in files:
    t = open(f, encoding="utf-8").read()
    fm = re.search(r'<footer>.*?</footer>', t, re.S)
    if not fm:
        report.append((f, "无<footer>", "跳过"))
        continue
    footer = fm.group(0)
    ps = list(re.finditer(r'<p>(.*?)</p>', footer, re.S))
    if not ps:
        report.append((f, "footer无<p>", "跳过"))
        continue
    last = ps[-1]
    old_text = last.group(1).strip()
    had_2024 = "2024修订版" in footer
    if old_text == CANON and not had_2024:
        report.append((f, old_text, "已一致·未改"))
        continue
    new_footer = footer[:last.start()] + "<p>" + CANON + "</p>" + footer[last.end():]
    t2 = t[:fm.start()] + new_footer + t[fm.end():]
    open(f, "w", encoding="utf-8").write(t2)
    changed += 1
    tag = " [原含2024修订版]" if had_2024 else ""
    report.append((f, old_text + "  ->  " + CANON + tag, "已替换"))

print("=" * 70)
for f, info, st in report:
    print("  %-10s | %s" % (st, f))
    print("            %s" % info)
print("=" * 70)
print("实际替换文件数:", changed, "/", len(files))

# 复检：替换后 footer 内是否仍残留 2024修订版
leftover = []
for f in files:
    t = open(f, encoding="utf-8").read()
    fm = re.search(r'<footer>.*?</footer>', t, re.S)
    if fm and "2024修订版" in fm.group(0):
        leftover.append(f)
print("替换后 footer 仍含'2024修订版'的文件:", leftover or "无 ✅")

# 报告：footer 之外（如封面 hero-sub）是否仍含 2024修订版，供您决定是否另处理
cover_2024 = []
for f in files:
    t = open(f, encoding="utf-8").read()
    body = re.sub(r'<footer>.*?</footer>', '', t, flags=re.S)
    if "2024修订版" in body:
        cover_2024.append(f)
print("封面/正文(footer外)仍含'2024修订版'的文件:", cover_2024 or "无 ✅")
