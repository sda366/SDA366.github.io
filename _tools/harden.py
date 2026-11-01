# -*- coding: utf-8 -*-
"""
一键加固 + 体检（小学有声图文课件站点：数学 / 语文通用）
==========================================================
把过去散落的手工修补动作固化成一条流水线，做到「改完必跑、跑完必过」。

用法:
    python harden.py <站点根目录> [选项]

选项:
    --check            只体检不改文件（默认会写）
    --link <路径>      提示条指向的声音自检页相对路径
                       默认 ../../../../sound-check.html（数学站）
                       语文站本地用 ../sound-check.html
    --skip-inject      跳过第 1~4 步修补，只做换行符与体检
    --sim [N]          逐页跑 sim_askqa.js 真点一次单题（N=页数上限，默认全跑）
                       这是唯一能真正验证「点单题有没有声音」的手段，建议至少抽样
    --self-test        不传根目录：检查**技能自身**模板/脚本是否已加固

流水线（默认全跑，全部幂等，可重复执行）:
    1. add_read_assist.py   —— read-assist.js 注入/迁移到 <body> 开标签后
    2. add_sound_tip.py     —— 顶部「手机没声音怎么办」提示条（可关闭、记住、宽屏隐藏）
    3. fix_askqa.py         —— 单题点击链路：abort 复位 + cancel 后延迟发声
    4. patch_watchdog.py    —— 超时兜底改轮询，避免长文本被硬截断
    5. 换行符统一为 CRLF    —— 全站既有约定，混用会让后续批量脚本出错
    6. verify_all.py        —— 全站体检（注入/思路块/语法/图片/导航/单题链路…）

退出码: 0 = 全过；1 = 有 FAIL 或有步骤异常
"""
import os
import re
import sys
import subprocess
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
NODE_CANDIDATES = [
    r"C:\Users\hxszs\.workbuddy\binaries\node\versions\20.18.0\node.exe",
    "node",
]


def find_node():
    for p in NODE_CANDIDATES:
        try:
            r = subprocess.run([p, "-v"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None


def run(cmd, tag):
    """跑一步子脚本，返回 (是否成功, 输出尾部)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        ok = (r.returncode == 0)
        tail = "\n".join([x for x in out.strip().splitlines() if x.strip()][-4:])
        print("-" * 60)
        print("[%s] %s  (%s)" % (tag, "OK" if ok else "退出码 %d" % r.returncode, os.path.basename(cmd[1])))
        if tail:
            print("    " + tail.replace("\n", "\n    "))
        return ok, out
    except Exception as e:
        print("-" * 60)
        print("[%s] 异常: %s" % (tag, e))
        return False, str(e)


def norm_crlf(root, write=True):
    """全站换行符统一为 CRLF（既有约定）。write=False 时只报数量"""
    changed = 0
    bad = []
    for dp, dn, fs in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fs:
            if not f.endswith(".html"):
                continue
            p = os.path.join(dp, f)
            raw = open(p, "rb").read()
            crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
            if not lf or crlf == lf:
                continue
            bad.append(os.path.relpath(p, root).replace("\\", "/"))
            if write:
                open(p, "wb").write(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
                changed += 1
    print("-" * 60)
    if bad:
        print("[5/6] 换行符：%d 个文件不统一%s" % (len(bad), "，已统一为 CRLF" if write else "（--check 未修改）"))
        for x in bad[:5]:
            print("    " + x)
    else:
        print("[5/6] 换行符：全站已统一 CRLF ✅")
    return len(bad) == 0


def self_test():
    """检查技能自身：模板是否已内置全部加固项、脚本是否齐全"""
    print("=" * 64)
    print("技能自检：%s" % HERE)
    print("=" * 64)
    need_scripts = ["read-assist.js", "check_page.js", "verify_all.py", "fix_askqa.py",
                    "sim_askqa.js", "add_sound_tip.py", "add_read_assist.py",
                    "patch_watchdog.py"]
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print("  ✅ %s" % name)
        else:
            fail += 1
            print("  ❌ %s %s" % (name, extra))

    for s in need_scripts:
        chk("脚本存在 %s" % s, os.path.exists(os.path.join(HERE, s)))

    tpls = [f for f in os.listdir(HERE) if f.startswith("page-template") and f.endswith(".html")]
    chk("至少一个页面模板", len(tpls) > 0, "(找到 %d)" % len(tpls))
    for t in tpls:
        h = open(os.path.join(HERE, t), encoding="utf-8", errors="replace").read()
        bm = re.search(r"<body[^>]*>", h)
        # 模板里若引用了引擎，必须紧跟 <body>；没引用则说明靠脚本注入（次优，给出提示）
        if "read-assist.js" in h and re.search(r'<script[^>]+src="[^"]*read-assist\.js"', h):
            chk("%s 引擎引用在 <body> 后" % t,
                bool(bm) and "read-assist.js" in h[bm.end():bm.end() + 300])
        else:
            print("  ⚠️  %s 未内置引擎引用（依赖 add_read_assist.py 事后注入）" % t)
        ask = (re.search(r"function askQA\([\s\S]*?\n\}", h) or [""])[0]
        if ask:
            chk("%s askQA 已复位 abort" % t, "abort=false" in ask.replace(" ", ""))
            chk("%s askQA 含想一想+读答案" % t, "think(" in ask and "data-ans" in ask)
        chk("%s speak 有延迟保护" % t, "RA-SPEAK-DELAY" in h)
        # watchdog 只对「等待式 speak」必需（纯朗读型点了就读，不需要）
        waits = re.search(r"setTimeout\(\s*(finish|fin)\s*,", h) or "return new Promise" in h
        if waits:
            chk("%s 有 watchdog 兜底" % t, "function __wd()" in h)
        chk("%s 有声音提示条" % t, 'id="sndTip"' in h or 'id="sndTipNav"' in h)

    ra = os.path.join(HERE, "read-assist.js")
    if os.path.exists(ra):
        r = open(ra, encoding="utf-8", errors="replace").read()
        code = re.sub(r"/\*[\s\S]*?\*/", "", re.sub(r"//[^\n]*", "", r))  # 剥注释再查，别被说明文字误报
        chk("read-assist 含分片总线 __raBusy", "__raBusy" in code)
        chk("read-assist 含多音字词典", "polyphone" in code)
        chk("read-assist 禁用后行断言 (?<=)（旧 Safari 会整脚本报错）",
            "(?<=" not in code and "(?<!" not in code)
    print()
    print("自检结果：%d 通过 / %d 失败 → %s" % (ok, fail, "技能已加固 ✅" if fail == 0 else "技能有缺口 ❌"))
    return 1 if fail else 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("root", nargs="?", help="站点根目录")
    ap.add_argument("--check", action="store_true", help="只体检不写文件")
    ap.add_argument("--link", default="../../../../sound-check.html")
    ap.add_argument("--skip-inject", action="store_true")
    ap.add_argument("--sim", nargs="?", const="all", default=None)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test or not a.root:
        sys.exit(self_test())

    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print("目录不存在：%s" % root)
        sys.exit(1)

    write = not a.check
    print("=" * 64)
    print("一键加固：%s" % root)
    print("模式：%s" % ("只体检（--check）" if not write else "写入修补 + 体检"))
    print("=" * 64)

    results = []

    if not a.skip_inject and write:
        # 0. 引擎缺失时先补一份
        js_dst = os.path.join(root, "js", "read-assist.js")
        if not os.path.exists(js_dst):
            src = os.path.join(HERE, "read-assist.js")
            if os.path.exists(src):
                os.makedirs(os.path.dirname(js_dst), exist_ok=True)
                open(js_dst, "wb").write(open(src, "rb").read())
                print("[0/6] 站点缺 js/read-assist.js，已从技能复制一份")
        results.append(run([PY, os.path.join(HERE, "add_read_assist.py"), root], "1/6"))
        results.append(run([PY, os.path.join(HERE, "add_sound_tip.py"), root, a.link], "2/6"))
        results.append(run([PY, os.path.join(HERE, "fix_askqa.py"), root], "3/6"))
        results.append(run([PY, os.path.join(HERE, "patch_watchdog.py"), root, "--apply"], "4/6"))
    else:
        print("[1~4/6] 跳过修补（--check 或 --skip-inject）")

    norm_crlf(root, write=write)

    ok_v, out_v = run([PY, os.path.join(HERE, "verify_all.py"), root], "6/6")
    results.append((ok_v, out_v))

    # 可选：逐页真跑一次单题点击
    sim_bad = []
    if a.sim:
        node = find_node()
        if not node:
            print("[sim] 未找到 node，跳过")
        else:
            pages = []
            for dp, dn, fs in os.walk(root):
                dn[:] = [d for d in dn if d not in ("images", "js", "audio", "__pycache__", ".git")]
                for f in sorted(fs):
                    if f.endswith(".html") and f != "index.html":
                        pages.append(os.path.join(dp, f))
            pages.sort()
            if a.sim != "all":
                pages = pages[:int(a.sim)]
            n_ok = 0
            for p in pages:
                r = subprocess.run([node, os.path.join(HERE, "sim_askqa.js"), p, "q1"],
                                   capture_output=True, text=True, timeout=120,
                                   encoding="utf-8", errors="replace")
                first = (r.stdout or "").strip().splitlines()[:1]
                if first and "PASS" in first[0]:
                    n_ok += 1
                elif first and "SKIP" in first[0]:
                    pass
                else:
                    sim_bad.append(os.path.relpath(p, root).replace("\\", "/"))
            print("-" * 60)
            print("[sim] 单题点击仿真：%d 页 PASS，%d 页异常" % (n_ok, len(sim_bad)))
            for x in sim_bad[:10]:
                print("    异常: " + x)

    failed_steps = [i for i, (o, _) in enumerate(results, 1) if not o]
    bad = bool(failed_steps) or bool(sim_bad)
    print()
    print("=" * 64)
    if bad:
        print("结论：存在问题 ❌（体检或某步骤未通过，见上方输出）")
    else:
        print("结论：全部通过 ✅")
    print("=" * 64)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
