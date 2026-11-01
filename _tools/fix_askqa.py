# -*- coding: utf-8 -*-
"""
fix_askqa.py —— 修「单独点击某一题：没想一想 / 没分析 / 没声音 / 不展开」

根因（两处）：
  1. askQA() 开头把 abort 置真去打断旧流程，却**从未复位**。后续 speak().then(...) 里
     的 `if(abort) return;` 会全部命中 → 想一想、展开解析、朗读答案整条链被掐断。
     整体播放正常，是因为 playStep2() 开头有 `abort=false`。
  2. speak() 里 `synth.cancel()` 之后**紧跟着** `synth.speak(u)`，Chrome / 安卓 WebView
     上常被静默吞掉（cancel 尚未生效），表现为"点了不出声"。整体播放因为中间有
     wait(500) 所以正常。

修法：
  A. askQA 改为 async：打断 → 等 150ms → **abort 复位 false** → 读题 → 想一想
     → 展开解析 → 朗读答案 → 收尾；再点已展开的题卡则收起并停读。
     （顺带补齐早期 3 页"单题只展开、不朗读答案"的缺口，符合题目答案都要配音的约定）
  B. speak() 内 `synth.speak(u);` 改为延迟 150ms 再调用，避开 cancel 竞态。

幂等：靠注释标记 RA-ASKQA-FIXED / RA-SPEAK-DELAY，可重复运行。保留原换行符（CRLF）。
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = sys.argv[1] if len(sys.argv) > 1 else \
    'E:/GitHub/SDA366.github.io/小学/二年级/数学/有声图文学习中心'

NEW_ASKQA = u'''async function askQA(id){
  var qa=document.getElementById(id);
  if(!qa) return;
  if(qa.classList.contains('open')){
    abort=true; if(synth) synth.cancel(); unhl(); try{ cap.style.display='none'; }catch(e){}
    closeAnswer(qa); return;
  }
  abort=true; if(synth) synth.cancel();
  await wait(150);
  abort=false;
  focusEl(qa);
  var qtext=qa.querySelector('.q-text').textContent;
  await speak(qtext);
  if(abort) return;
  closeAnswer(qa);
  await think(qa);
  if(abort) return;
  openAnswer(qa);
  await wait(300);
  if(abort) return;
  await speak(qa.getAttribute('data-ans')||'');
  if(abort) return;
  unhl(); try{ cap.style.display='none'; }catch(e){}
}'''


def find_block(s, marker):
    """从 marker 起，找到函数体配平的花括号，返回 (start, end)"""
    i = s.find(marker)
    if i < 0:
        return None
    j = s.find('{', i)
    if j < 0:
        return None
    depth = 0
    k = j
    while k < len(s):
        if s[k] == '{':
            depth += 1
        elif s[k] == '}':
            depth -= 1
            if depth == 0:
                return (i, k + 1)
        k += 1
    return None


def fix_file(path):
    s = io.open(path, encoding='utf-8', newline='').read()
    changed = False

    # ---- A. 换掉 askQA ----
    if 'function askQA' in s and 'RA-ASKQA-FIXED' not in s:
        rng = find_block(s, 'function askQA')
        if rng:
            nl = u'\r\n' if u'\r\n' in s else u'\n'
            new = NEW_ASKQA if nl == u'\n' else NEW_ASKQA.replace(u'\n', u'\r\n')
            new = new.replace(u'async function askQA(id){',
                              u'async function askQA(id){  /* RA-ASKQA-FIXED：abort 打断后必须复位 */', 1)
            s = s[:rng[0]] + new + s[rng[1]:]
            changed = True

    # ---- B. speak 延迟 150ms ----
    if 'synth.speak(u);' in s and 'RA-SPEAK-DELAY' not in s:
        nl = u'\r\n' if u'\r\n' in s else u'\n'
        rep = (u'setTimeout(function(){ try{ synth.speak(u); }catch(e){} },150);'
               u'  /* RA-SPEAK-DELAY：cancel 后立刻 speak 会被浏览器静默吞掉 */')
        s = s.replace(u'synth.speak(u);', rep)
        changed = True

    if changed:
        io.open(path, 'w', encoding='utf-8', newline='').write(s)
    return changed


def main():
    n = 0
    total = 0
    for dp, dn, fns in os.walk(ROOT):
        for fn in fns:
            if not fn.endswith('.html') or fn == 'index.html':
                continue
            p = os.path.join(dp, fn)
            total += 1
            if fix_file(p):
                n += 1
    print(u'扫描 %d 页，修复 %d 页' % (total, n))


if __name__ == '__main__':
    main()
