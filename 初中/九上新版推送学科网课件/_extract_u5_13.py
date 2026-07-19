# -*- coding: utf-8 -*-
"""提取 U5-13 课件全部文字内容（含折叠/隐藏部分）为纯文本，证明内容全面。V2：用 div 平衡块定位，避免嵌套截断。"""
import re, html, os

SRC = "九上-U5-第13课_西欧经济社会发展与文艺复兴运动.html"
OUT = "九上-U5-第13课_西欧经济社会发展与文艺复兴运动_内容全文.txt"
os.chdir("E:/WorkBuddy生成内容/下载")
t = open(SRC, encoding="utf-8").read()
JS = (re.search(r"<script>([\s\S]*?)</script>", t) or re.search(r"", "")).group(1)

TAG = re.compile(r"<div\b|</div>")
def block_at(s, start):
    """返回从位置 start 的 <div 开始到匹配闭合 </div> 的完整块（含标签）。"""
    depth = 0; i = start
    while i < len(s):
        m = TAG.search(s, i)
        if not m: break
        depth += 1 if m.group(0).startswith("<div") else -1
        if depth == 0:
            return s[start:m.end()]
        i = m.end()
    return s[start:]

def clean(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = s.replace("<br>", "\n").replace("<br/>", "\n")
    s = re.sub(r"</(p|li|div|h\d|tr)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()

def uls(seg):
    out = []
    for ul in re.findall(r"<ul>([\s\S]*?)</ul>", seg, re.S):
        for li in re.findall(r"<li>([\s\S]*?)</li>", ul, re.S):
            out.append("  • " + clean(li))
    return out

def seg_page(n):
    a = re.search(r"<!-- Page%d:" % n, t)
    b = re.search(r"<!-- Page%d:" % (n+1), t)
    return t[a.start(): (b.start() if b else len(t))]

def blocks(seg, cls):
    """返回 seg 中所有 class 含 cls 独立词元的 <div ...> 的完整平衡块。"""
    pat = re.compile(r'<div[^>]*class="(?:[^"]*\s)?%s(?:\s[^"]*)?"' % re.escape(cls))
    return [block_at(seg, m.start()) for m in pat.finditer(seg)]

L = []
def line(s=""): L.append(s)
def hr(): L.append("=" * 64)

# ---------- 封面 ----------
line("第13课《西欧经济和社会的发展》课件 · 全文内容提取")
line("（本课件为交互折叠式排版，以下为展开后的全部文字内容，用以证明资料内容全面）")
line()
line("【内容规模统计（展开后实际包含）】")
line("  · 学习目标：4 条（时空观念 / 史料实证 / 历史解释 / 家国情怀）")
line("  · 知识要点子目：3 个（农业 / 手工业 / 社会结构），各含知识卡 + 中考常考提示")
line("  · 闯关挑战：5 关（拖拽排序 / 填空填词 / 连线匹配 / 因果拼图 / 翻转卡）")
line("  · 核心概念翻转卡：18 张（农业6 + 手工业6 + 社会结构6）")
line("  · 重难点解析：4 个，每个含 基础理解 / 联系拓展 / 素养提升 3 层（共 12 张卡片）")
line("  · 教材栏目解答：7 个（相关史事×4 / 材料研读×2 / 知识拓展×1），各含正文 + 要点归纳")
line("  · 课堂训练：选择题 10 道 + 材料题 2 道（各 2 小问，共 4 问），均附答案与解析")
line("  · 知识结构图：4 个因果链节点 + 4 条规律")
line("  · 结束页核心要点回顾：6 张卡片")
line("  · 合计：7 个模块页、约 60+ 知识条目、14 道训练题（含详解）")
line()
p0 = seg_page(0)
line("【封面 / 学习目标】")
line("  单元：第五单元 · 走向近代")
line("  课题：第13课 · 西欧经济和社会的发展（统编版九年级上册 · 新版）")
for ti in re.findall(r'<div class="target-item"[^>]*>(.*?)</div>', p0, re.S):
    line("  □ " + clean(ti))
line()

# ---------- Page1 知识闯关 ----------
p1 = seg_page(1)
line("【模块一 · 知识要点 · 闯关解锁】（含3个子目知识卡 + 5关闯关 + 18张翻转卡）")
for tabid, label in [("tab1","子目一 · 新的生产和经营方式（农业）"),
                     ("tab2","子目一 · 新的生产和经营方式（手工业）"),
                     ("tab3","子目二 · 富裕农民和市民阶层")]:
    m = re.search(r'<div class="kp-card tab-panel[^"]*" id="%s">(.*)' % tabid, p1, re.S)
    seg = block_at(p1, m.start()) if m else ""
    line("  ── " + label + " ──")
    tl = re.search(r'<div class="timeline-bar">(.*?)</div>', seg, re.S)
    if tl: line("     脉络：" + clean(tl.group(1)))
    h3 = re.search(r"<h3>(.*?)</h3>", seg, re.S)
    if h3: line("     " + clean(h3.group(1)))
    for u in uls(seg): line(u)
    lb = re.search(r'<div class="link-bar">(.*?)</div>', seg, re.S)
    if lb: line("     " + clean(lb.group(1)))
line()

line("  ★ 挑战一（第①关）：请将西欧农业发展历程按时间先后顺序拖入槽位")
sorts = dict(re.findall(r'data-sortkey="(event\d+)"[^>]*id="item_\1">([^<]+)<', p1))
co = re.search(r"var correctOrder\s*=\s*\[([^\]]+)\]", JS)
if co:
    for i, k in enumerate(re.findall(r"'([^']+)'", co.group(1)), 1):
        line("     第%d步：%s" % (i, sorts.get(k, k)))
line()

line("  ★ 挑战二（第②关）：填写手工工场发展的关键信息")
for row in re.findall(r'<div class="fill-blank-row">([\s\S]*?)</div>', p1):
    q = clean(re.sub(r"<input[^>]*>", "（    ）", row))
    ans = re.search(r'data-answer="([^"]+)"', row)
    line("     " + q + ("  → 答案：%s" % ans.group(1) if ans else ""))
line()

line("  ★ 挑战三（第③关）：将农村社会变化与对应内容配对")
lefts = dict(re.findall(r'data-match="([a-c])"[^>]*onclick="selectMatch\(this\)">([^<]+)<', p1))
rights = dict(re.findall(r'data-match="([a-c])"[^>]*onclick="pairMatch\(this\)">([^<]+)<', p1))
for k in sorted(set(lefts) & set(rights)):
    line("     %s  ↔  %s" % (lefts[k], rights[k]))
line()

line("  ★ 挑战四（第④关）：将每条因果链的三块拼图按正确顺序排列（①→②→③）")
pd = re.search(r"var puzzleData\s*=\s*(\[.*?\]);", JS, re.S)
if pd:
    for ci, (title, pstr) in enumerate(re.findall(r"title:'([^']+)',badge:'[^']+',pieces:\[(.*?)\]", pd.group(1), re.S), 1):
        line("     " + title)
        for j, (txt, _) in enumerate(sorted(re.findall(r"text:'([^']+)',order:(\d+)", pstr), key=lambda x: int(x[1])), 1):
            line("       %d. %s" % (j, txt))
line()

line("  ★ 挑战五（第⑤关）：核心概念翻转卡（共18张，点击翻面）")
# 记录每个 group-label 位置与每个 flash-card 块，按就近归组
labels = [(m.start(), clean(m.group(1))) for m in re.finditer(r'<div class="flash-group-label">([\s\S]*?)</div>', p1)]
cards = [(m.start(), block_at(p1, m.start())) for m in re.finditer(r'<div class="flash-card"', p1)]
cur = "（未分组）"
for pos, blk in cards:
    while labels and pos > labels[0][0]:
        cur = labels.pop(0)[1]
    line("     ▣ %s" % cur)
    fr = re.search(r'<div class="flash-front">([\s\S]*?)</div>', blk, re.S)
    bk = re.search(r'<div class="flash-back">([\s\S]*?)</div>', blk, re.S)
    line("        · %s  →  %s" % (clean(fr.group(1)) if fr else "", clean(bk.group(1)) if bk else ""))
line()

# ---------- Page2 重难点 ----------
p2 = seg_page(2)
line("【模块二 · 重难点解析】（4个重难点，每个含 基础理解 / 联系拓展 / 素养提升 三层）")
for ag in blocks(p2, "acc-group"):
    hd = re.search(r"<h3>(.*?)</h3>", ag, re.S)
    if hd: line("  ▶ " + clean(hd.group(1)))
    for dc in blocks(ag, "deep-card"):
        ch = re.search(r'<div class="deep-card-hd">([\s\S]*?)</div>', dc, re.S)
        if ch: line("     ◇ " + clean(ch.group(1)))
        for u in uls(dc): line(u)
        for p in re.findall(r"<p>([\s\S]*?)</p>", dc, re.S):
            ct = clean(p)
            if ct: line("        " + ct)
line()

# ---------- Page3 教材栏目解答 ----------
p3 = seg_page(3)
line("【模块三 · 教材栏目解答】（7个栏目，含正文 + 要点归纳/解析）")
for cb in blocks(p3, "col-box"):
    cat = re.search(r'data-cat="([^"]+)"', cb)
    hdr = re.search(r'col-header[^>]*>\s*<span>([\s\S]*?)</span>', cb, re.S)
    line("  ▣ [%s] %s" % (cat.group(1) if cat else "", clean(hdr.group(1)) if hdr else ""))
    for p in re.findall(r"<p>([\s\S]*?)</p>", cb, re.S):
        ct = clean(p)
        if ct: line("     正文：" + ct)
    for ans in re.findall(r'<div class="a"[^>]*>([\s\S]*?)</div>', cb, re.S):
        ct = clean(ans)
        if ct: line("     " + ct)
line()

# ---------- Page4 课堂训练 ----------
p4 = seg_page(4)
line("【模块四 · 课堂训练】（选择题10道 + 材料题2道，含答案与解析）")
for ex in blocks(p4, "exercise"):
    eid = re.search(r'id="(\w+)"', ex)
    if not eid: continue
    eid = eid.group(1)
    if eid.startswith("q"):
        qt = re.search(r'<div class="q-text"><strong>\d+\.</strong>\s*([\s\S]*?)</div>', ex, re.S)
        line("  %s. %s" % (eid[1:], clean(qt.group(1)) if qt else ""))
        for lab in re.findall(r"<label[^>]*>([^<]+)</label>", ex):
            line("     " + clean(lab))
        an = re.search(r'<div class="analysis"[^>]*>([\s\S]*?)</div>', ex, re.S)
        if an: line("     【答案】" + clean(an.group(1)))
    else:
        qt = re.search(r'<div class="q-text"><strong>([\s\S]*?)</strong>([\s\S]*?)</div>', ex, re.S)
        line("  〔%s〕" % (clean(qt.group(1)+qt.group(2)) if qt else eid))
        sm = re.search(r'<div class="source-material">([\s\S]*?)</div>', ex, re.S)
        if sm:
            for p in re.findall(r"<p>([\s\S]*?)</p>", sm.group(1), re.S):
                line("     材料：" + clean(p))
        for num, qst, ans in re.findall(r'<div class="q-text"[^>]*>\s*（(\d+)）([\s\S]*?)</div>\s*<div class="a"[^>]*>([\s\S]*?)</div>', ex, re.S):
            line("     问（%s）：%s" % (num, clean(qst)))
            line("     答：%s" % clean(ans))
line()

# ---------- Page5 知识结构图 ----------
p5 = seg_page(5)
line("【模块五 · 知识结构图】（因果链 4 节点 + 4 条规律）")
for node in blocks(p5, "kg-node"):
    title = re.search(r"<strong>([\s\S]*?)</strong>", node, re.S)
    sub = re.search(r"<p>([\s\S]*?)</p>", node, re.S)
    det = re.search(r'<div class="kg-detail"><p>([\s\S]*?)</p>', node, re.S)
    line("  ▸ " + (clean(title.group(1)) if title else "") + (" — " + clean(sub.group(1)) if sub else ""))
    if det: line("     解析：" + clean(det.group(1)))
for rule in blocks(p5, "kg-rule"):
    line("  · " + clean(rule))
line()

# ---------- Page6 结束页 ----------
p6 = seg_page(6)
line("【结束页 · 核心要点回顾】（6 张卡片）")
for card in blocks(p6, "recap-card"):
    h = re.search(r"<h3>([\s\S]*?)</h3>", card, re.S)
    if h: line("  ▣ " + clean(h.group(1)))
    for u in uls(card): line(u)
line()
line("（全文完）")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("已写出:", OUT, "字符数:", len("\n".join(L)))
