# -*- coding: utf-8 -*-
"""
把页面 speak() 里的「固定时长兜底」换成「引擎还在说就继续等」的 watchdog。

背景（v6 暴露的 A 级问题）：
    setTimeout(finish, Math.min(2500 + text.length*260, 16000));
    中文 0.85 速率约 220ms/字 → 80 字需 17.6s，已超 16s 上限；
    长文本分片后总时长翻倍（156 字 ≈ 34s），第 16 秒 resolve → 下一步 speak()
    第一行 synth.cancel() → 第 2 片读 2 秒就被掐断。

新逻辑：3.5s 起轮询，只要「引擎在说」「有排队」「分片未播完」就继续等；
连续两次确认已停才 finish；120s 硬顶防卡死；哑引擎约 4.3s 快速放行。

用法：python patch_watchdog.py <根目录> [--apply]
"""
import os, re, sys

ROOT = sys.argv[1].rstrip("/\\")
APPLY = "--apply" in sys.argv

# 写法一：主流（95 页）
PAT = re.compile(
    r'setTimeout\(\s*finish\s*,\s*Math\.min\(\s*2500\s*\+\s*text\.length\s*\*\s*260\s*,\s*16000\s*\)\s*\)\s*;'
)
# 写法二：二年级最早 2 页（参数顺序相反、收尾函数叫 fin）
PAT2 = re.compile(
    r'setTimeout\(\s*fin\s*,\s*Math\.min\(\s*16000\s*,\s*2500\s*\+\s*text\.length\s*\*\s*260\s*\)\s*\)\s*;'
)

def build(fn):
    return (
        'var __t0=Date.now(),__m=0;'
        'function __wd(){if(done)return;'
        'if(Date.now()-__t0>120000){%s();return;}'                           # 硬顶防卡死
        'var __b=(synth&&(synth.speaking||synth.pending))||(window.__raBusy&&window.__raBusy());'
        'if(__b){__m=0;setTimeout(__wd,1500);return;}'                       # 引擎还在说 → 继续等
        'if(Date.now()-__t0<3500||++__m<2){setTimeout(__wd,800);return;}'    # 启动保护 + 双次确认
        '%s();}'
        'setTimeout(__wd,3500);' % (fn, fn)
    )

NEW, NEW2 = build('finish'), build('fin')

ok, miss, already = [], [], []
for dp, _, fs in os.walk(ROOT):
    for f in fs:
        if not f.endswith(".html"):
            continue
        p = os.path.join(dp, f)
        h = open(p, encoding="utf-8").read()
        if "synth.speak(u)" not in h and "synth.speak" not in h:
            continue
        if "__wd()" in h:
            already.append(p)
            continue
        n = len(PAT.findall(h)) + len(PAT2.findall(h))
        if n == 0:
            miss.append(p)
            continue
        ok.append((p, n))
        if APPLY:
            h2 = PAT.sub(NEW, h)
            h2 = PAT2.sub(NEW2, h2)
            open(p, "w", encoding="utf-8").write(h2)

print("待替换页 %d（共 %d 处），已替换过 %d，未匹配到该行 %d"
      % (len(ok), sum(n for _, n in ok), len(already), len(miss)))
for p in miss[:15]:
    print("  ✗ 未匹配:", os.path.relpath(p, ROOT))
if not APPLY:
    print("\n这是 dry-run；确认无误后加 --apply 真正写入。")
