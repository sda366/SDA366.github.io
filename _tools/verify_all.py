# -*- coding: utf-8 -*-
"""
全站一键体检（小学数学课件站点）
================================
把每次批量改动后手工拼的一串检查命令固化成一个脚本。

用法:
    python verify_all.py <站点根目录> [--fix-crlf] [--verbose]

体检项（全部为只读检查，除非显式加 --fix-crlf）:
  1. read-assist.js 注入位置是否在 <body> 开标签后（早于页面脚本，否则垫片接不住）
  2. 每道分层题的解析区是否都有「怎么想的」思路块（sol sol3；--no-think 可关闭）
  3. data-ans 属性是否被英文直引号提前截断（结构破损信号）
  4. 页面内联 <script> 语法（调用 node --check）
  5. 教材图 src 指向的文件是否真实存在
  6. 换行符是否统一为 CRLF（混用会让 diff 变大、后续批量脚本出错）
  7. 导航页 index.html 是否收录了所有课件页
  8. 多音字风险词提示（只提示，需人工判断读音）
  9. 单题点击链路 askQA：abort 打断后必须复位，且含「想一想」+ 朗读答案
 10. speak() 是否有 cancel→延迟发声保护（否则点了不出声）
 11. speak() 是否有 watchdog 轮询兜底（否则长文本被硬超时截断）

退出码: 0 = 全过；1 = 有 FAIL
"""
import os
import re
import sys
import subprocess
import argparse
from collections import Counter

# node 路径（用于语法检查；找不到就跳过该项）
NODE_CANDIDATES = [
    r"C:\Users\hxszs\.workbuddy\binaries\node\versions\20.18.0\node.exe",
    "node",
]

# 多音字风险词：出现时需要人工确认读音（引擎层词典已覆盖大部分，这里做兜底提示）
POLY_WORDS = ["一行", "每行", "测量", "量一量", "数一数", "数不清", "得数",
              "部分", "相差", "重阳", "不重", "空格", "颠倒", "对应", "成长"]


def find_node():
    for p in NODE_CANDIDATES:
        try:
            r = subprocess.run([p, "-v"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None


def strip_comments(h):
    """把 HTML 注释抹成等长空格（保持索引不变），避免注释里的 <div> 干扰标签配平"""
    out = list(h)
    for m in re.finditer(r"<!--[\s\S]*?-->", h):
        for i in range(m.start(), m.end()):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def find_qa_blocks(h):
    """返回 [(start, end, qid, ans)] —— 按 <div class="qa" ...> 起，做 div 配平找到结束"""
    hc = strip_comments(h)
    out = []
    for m in re.finditer(r'<div class="qa" id="(q\d+)" data-ans="([^"]*)"', hc):
        start, qid, ans = m.start(), m.group(1), m.group(2)
        depth, i = 0, start
        while i < len(hc):
            no = hc.find("<div", i)
            nc = hc.find("</div>", i)
            if nc < 0:
                break
            if no >= 0 and no < nc:
                depth += 1
                i = no + 4
            else:
                depth -= 1
                i = nc + 6
                if depth == 0:
                    out.append((start, i, qid, ans))
                    break
    return out


def list_pages(root):
    pages = []
    for dp, dn, fs in os.walk(root):
        dn[:] = [d for d in dn if d not in ("images", "js", "audio", "__pycache__", ".git")]
        for f in sorted(fs):
            if f.endswith(".html") and f != "index.html":
                pages.append(os.path.join(dp, f))
    return sorted(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="站点根目录（含各单元子目录与 index.html）")
    ap.add_argument("--fix-crlf", action="store_true", help="把非 CRLF 的文件统一转成 CRLF")
    ap.add_argument("--verbose", "-v", action="store_true", help="逐页打印通过信息")
    ap.add_argument("--no-think", action="store_true",
                    help="跳过第 2 项「思路块」检查（语文课文页无 sol sol3 结构时用）")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    pages = list_pages(root)
    node = find_node()
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_verify_tmp.js")

    print("=" * 64)
    print("全站体检：%s" % root)
    print("课件页数：%d    （node: %s）" % (len(pages), node or "未找到，跳过语法检查"))
    print("=" * 64)

    problems = []          # (级别, 文件, 说明)
    stat = Counter()

    for p in pages:
        rel = os.path.relpath(p, root).replace("\\", "/")
        raw = open(p, "rb").read()
        h = raw.decode("utf-8", errors="replace")
        stat["pages"] += 1

        # 1. 注入位置
        if "read-assist.js" in h:
            bm = re.search(r"<body[^>]*>", h)
            ok_pos = bool(bm) and "read-assist.js" in h[bm.end():bm.end() + 200]
            if not ok_pos:
                problems.append(("FAIL", rel, "read-assist.js 不在 <body> 开头，垫片会失效"))
            else:
                stat["inject_ok"] += 1

        # 2. 思路块
        blocks = find_qa_blocks(h)
        stat["questions"] += len(blocks)
        if a.no_think:
            stat["think_skip"] += 1
        else:
            for s, e, qid, ans in blocks:
                if "sol sol3" in h[s:e]:
                    stat["think_ok"] += 1
                else:
                    problems.append(("FAIL", rel, "%s 解析区缺「怎么想的」块" % qid))

        # 3. data-ans 破损
        loose = [x.group(1) for x in re.finditer(r'<div class="qa" id="(q\d+)" data-ans=', h)]
        strict = [x.group(1) for x in re.finditer(r'<div class="qa" id="(q\d+)" data-ans="[^"]*">', h)]
        broken = [q for q in loose if q not in strict]
        if broken:
            problems.append(("FAIL", rel, "data-ans 属性破损（直引号截断）: %s" % ",".join(broken)))

        # 4. 脚本语法
        if node:
            js = "\n;\n".join(re.findall(r"<script>([\s\S]*?)</script>", h))
            if js.strip():
                open(tmp, "w", encoding="utf-8").write(js)
                try:
                    r = subprocess.run([node, "--check", tmp], capture_output=True, text=True, timeout=30)
                    if r.returncode != 0:
                        problems.append(("FAIL", rel, "JS 语法错误: %s" % r.stderr.strip().splitlines()[0][:90]))
                    else:
                        stat["js_ok"] += 1
                except Exception as e:
                    problems.append(("WARN", rel, "语法检查异常: %s" % e))

        # 5. 图片存在
        for im in re.findall(r'src="(images/[^"]+)"', h):
            fp = os.path.join(os.path.dirname(p), im.replace("/", os.sep))
            if not os.path.exists(fp):
                problems.append(("FAIL", rel, "图片缺失: %s" % im))

        # 6. 换行符
        crlf = raw.count(b"\r\n")
        lf = raw.count(b"\n")
        if lf and crlf != lf:
            if a.fix_crlf:
                new = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                open(p, "wb").write(new)
                problems.append(("FIXED", rel, "换行符已统一为 CRLF"))
            else:
                problems.append(("WARN", rel, "换行符不统一（CRLF %d / LF %d），加 --fix-crlf 可修" % (crlf, lf)))

        # 8. 多音字提示
        plain = re.sub(r"<[^>]+>", "", h)
        hits = [w for w in POLY_WORDS if w in plain]
        if hits:
            stat["poly_pages"] += 1
            stat["poly_hits"] += len(hits)

        # 9. 单题点击链路（askQA）：abort 打断后必须复位，否则整条链静默中断
        ask = re.search(r"function askQA\([\s\S]*?\n\}", h)
        if ask:
            blk = ask.group(0)
            stat["askqa_pages"] += 1
            if re.search(r"abort\s*=\s*false", blk):
                stat["askqa_ok"] += 1
            else:
                problems.append(("FAIL", rel, "askQA 未复位 abort → 单题点击没声音/不展开"))
            if not ("think(" in blk and "data-ans" in blk):
                problems.append(("FAIL", rel, "askQA 缺「想一想」或朗读答案"))
        else:
            stat["askqa_none"] += 1

        # 10. speak 延迟保护：cancel() 后紧接 speak() 会被浏览器静默吞掉
        if "function speak(" in h:
            if "RA-SPEAK-DELAY" in h or re.search(r"setTimeout\([\s\S]{0,80}synth\.speak\(u\)", h):
                stat["delay_ok"] += 1
            else:
                problems.append(("FAIL", rel, "speak() 缺 cancel→延迟发声保护（点了不出声）"))

        # 11. watchdog：等待式 speak（返回 Promise / 有 finish 兜底）不能被固定超时硬截断；
        #     纯朗读型页（点了就读、不等回调）无需 watchdog，记入 wd_na
        if "function speak(" in h:
            waits = re.search(r"setTimeout\(\s*(finish|fin)\s*,", h) or "return new Promise" in h
            if not waits:
                stat["wd_na"] += 1
            elif "function __wd()" in h:
                stat["wd_ok"] += 1
            else:
                problems.append(("FAIL", rel, "等待式 speak() 缺 watchdog 轮询兜底（长文本会被截断）"))

    # 7. 导航收录
    idx = os.path.join(root, "index.html")
    if os.path.exists(idx):
        ih = open(idx, encoding="utf-8").read()
        miss = []
        for p in pages:
            rel = os.path.relpath(p, root).replace("\\", "/")
            if rel not in ih:
                miss.append(rel)
        if miss:
            problems.append(("WARN", "index.html", "导航未收录 %d 页" % len(miss)))
            for x in miss[:10]:
                problems.append(("WARN", "index.html", "  未收录: %s" % x))
        else:
            stat["nav_ok"] = 1
    else:
        problems.append(("WARN", "index.html", "站点根目录无导航页"))

    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except Exception:
            pass

    # ---------- 汇总 ----------
    print()
    print("—— 汇总 ——")
    print("  课件页        %d" % stat["pages"])
    if a.no_think:
        print("  分层题        %d 题（已跳过思路块检查 --no-think）" % stat["questions"])
    else:
        print("  分层题        %d 题，其中带思路块 %d 题" % (stat["questions"], stat["think_ok"]))
    print("  注入位置正确  %d 页" % stat["inject_ok"])
    print("  脚本语法通过  %d 页" % stat["js_ok"])
    print("  单题链路      %d 页有 askQA，其中复位正确 %d 页（无 askQA 的旧式页 %d）"
          % (stat["askqa_pages"], stat["askqa_ok"], stat["askqa_none"]))
    print("  延迟发声保护  %d 页    watchdog 兜底 %d 页（纯朗读型不适用 %d 页）"
          % (stat["delay_ok"], stat["wd_ok"], stat["wd_na"]))
    print("  导航收录      完整" if stat.get("nav_ok") else "  导航收录      有缺失")
    if stat["poly_hits"]:
        print("  多音字提示    %d 页命中 %d 个风险词（引擎词典已覆盖，仅提示人工抽查）"
              % (stat["poly_pages"], stat["poly_hits"]))

    fails = [x for x in problems if x[0] == "FAIL"]
    warns = [x for x in problems if x[0] == "WARN"]
    fixed = [x for x in problems if x[0] == "FIXED"]

    print()
    if fails:
        print("❌ FAIL %d 项：" % len(fails))
        for lv, f, msg in fails[:30]:
            print("   [%s] %s" % (f, msg))
        if len(fails) > 30:
            print("   …… 另有 %d 项" % (len(fails) - 30))
    else:
        print("✅ 无 FAIL")

    if warns:
        print()
        print("⚠️  WARN %d 项：" % len(warns))
        for lv, f, msg in warns[:15]:
            print("   [%s] %s" % (f, msg))
    if fixed:
        print()
        print("🔧 已修复 %d 项（换行符）" % len(fixed))

    print()
    print("=" * 64)
    print("结论：" + ("全部通过 ✅" if not fails else "存在 %d 项 FAIL，需修复 ❌" % len(fails)))
    print("=" * 64)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
