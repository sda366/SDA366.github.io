# -*- coding: utf-8 -*-
"""
add_sound_tip.py —— 小学有声图文页「手机没声音怎么办」提示条批量注入（幂等）

用法：
  python add_sound_tip.py <目录> <sound-check.html 的相对路径>

例：
  python add_sound_tip.py "E:/GitHub/SDA366.github.io/小学/二年级/数学/有声图文学习中心" "../../../../sound-check.html"
  python add_sound_tip.py "E:/WorkBuddy生成内容/其他/二年级语文上册-有声图文学习中心" "../sound-check.html"

规则：
  1. 只在每个页面 <div class="container"> 之后插入一块提示（页面最顶部，手机端可见）。
  2. 已含 id="sndTip" 的页面跳过（可重复运行）。
  3. 提示条带关闭按钮，关闭后写入 localStorage['sndTipClosed']=1，本站只提示一次。
  4. 宽屏（>=900px，一般即电脑）自动隐藏，只给手机/平板看。
  5. 保留原文件换行符（CRLF/LF 原样）。
"""
import os
import sys
import re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TIP_HTML = u'''<style>
#sndTip{{ margin:12px 0 2px; padding:10px 34px 10px 14px; background:#FFF8E1; border:1.5px dashed #F9A825;
  border-radius:12px; font-size:13.5px; line-height:1.9; color:#5D4037; position:relative; }}
#sndTip b{{ color:#E65100; }}
#sndTip .st-t{{ font-weight:bold; color:#E65100; }}
#sndTip .st-x{{ position:absolute; right:6px; top:4px; cursor:pointer; font-size:18px; color:#8D6E63; padding:2px 6px; }}
#sndTip a{{ color:#1565C0; font-weight:bold; }}
@media (min-width:900px){{ #sndTip{{ display:none; }} }}
</style>
<div id="sndTip">
  <span class="st-x" id="sndTipX" role="button" aria-label="关闭提示">&times;</span>
  <span class="st-t">\U0001F50A 手机听不到声音怎么办？</span><br>
  ① 先把手机<b>媒体音量调大</b>，确认没开静音、没连蓝牙耳机；在微信里打开的，点右上角「⋯ → 用浏览器打开」。<br>
  ② 还是没声音？到应用商店免费下载 <b>Microsoft Edge 浏览器</b>（它自带朗读发声），用它打开本页面就能出声。<br>
  ③ 换了 Edge 仍然没声音，说明这部手机的<b>硬件/系统不支持</b>网页朗读（多为老旧机型）；近几年买的新手机一般都能正常播放。
  <a href="{link}">→ 打开声音自检</a>
</div>
<script>
(function(){{
  try{{
    if(localStorage.getItem('sndTipClosed') === '1'){{
      var t0 = document.getElementById('sndTip'); if(t0) t0.style.display = 'none'; return;
    }}
    var x = document.getElementById('sndTipX');
    if(x) x.onclick = function(){{
      var t = document.getElementById('sndTip'); if(t) t.style.display = 'none';
      try{{ localStorage.setItem('sndTipClosed','1'); }}catch(e){{}}
    }};
  }}catch(e){{}}
}})();
</script>
'''


def inject(path, link):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        src = f.read()
    if 'id="sndTip"' in src:
        return 'skip'
    m = re.search(r'<div class="container">', src)
    if not m:
        return 'noanchor'
    block = TIP_HTML.format(link=link)
    # 沿用文件原有换行符（全站统一 CRLF，避免混入 LF）
    nl = '\r\n' if '\r\n' in src else '\n'
    if nl != '\n':
        block = block.replace('\n', nl)
    out = src[:m.end()] + nl + block + src[m.end():]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    return 'ok'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    root = sys.argv[1]
    link = sys.argv[2]
    stat = {'ok': 0, 'skip': 0, 'noanchor': 0}
    failed = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith('.html'):
                continue
            p = os.path.join(dirpath, fn)
            r = inject(p, link)
            stat[r] = stat.get(r, 0) + 1
            if r == 'noanchor':
                failed.append(p)
    print(u'注入完成：新增 %d 页，已存在跳过 %d 页，未找到锚点 %d 页' % (stat['ok'], stat['skip'], stat['noanchor']))
    if failed:
        print(u'未找到 <div class="container"> 的页面：')
        for p in failed:
            print('  ' + p)


if __name__ == '__main__':
    main()
