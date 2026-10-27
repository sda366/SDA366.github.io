/* ============================================================
   小学朗读兜底  read-assist.js  v3（静默版）
   ------------------------------------------------------------
   设计原则（2026-10-27 定）：
   1. 浏览器【支持】网页朗读（Edge / Chrome / Safari / 电脑端…）
      → 本脚本什么都不做：不显示任何图标、不占任何屏幕空间，
        课件自带的「① 解析教材图片 / ② 分层提问练习 / 停止」
        直接用浏览器自身语音，完全由原页面接管。
   2. 浏览器【不支持】朗读（微信/QQ 内置、旧内核…）
      → 安装垫片接住课件的朗读调用，学生点课件按钮时
        弹出引导层：告知原因 + 引导换浏览器 + 声音自检入口。
        （不再出现"字幕在动却没声音"的迷惑状态）

   用法：页面 <body> 开标签后、页面自身脚本之前加
   <script src="相对路径/js/read-assist.js"></script>
   ============================================================ */
(function () {
  if (window.__READ_ASSIST__) return;      // 防止重复注入
  window.__READ_ASSIST__ = 1;

  /* 真实能力检测：支持就立刻退出，页面零打扰 */
  var realTTS = ('speechSynthesis' in window) && (typeof SpeechSynthesisUtterance !== 'undefined');
  if (realTTS) return;

  /* 记录本脚本所在目录，供「声音自检」跳转用（层级无关） */
  var SCRIPT_DIR = '';
  try { SCRIPT_DIR = String(document.currentScript.src).replace(/[^/]*$/, ''); } catch (e) {}

  /* ============================================================
     引导层：只在"没有声音"时出现，可点空白处或按钮关闭
     ============================================================ */
  var guideLast = 0;
  function showGuide() {
    var now = Date.now();
    if (now - guideLast < 30000) return;   // 30 秒内只弹一次，不反复打扰
    guideLast = now;
    if (document.getElementById('ra-guide')) return;
    var g = document.createElement('div');
    g.id = 'ra-guide';
    var link = SCRIPT_DIR ? (SCRIPT_DIR + '../sound-check.html') : '';
    g.innerHTML = [
      '<div class="ra-gcard">',
        '<div class="ra-gt">📢 这个浏览器发不出声音</div>',
        '<p class="ra-gp">当前浏览器缺少网页朗读功能（微信、QQ 内置浏览器都没有）。</p>',
        '<p class="ra-gp">请复制网址，用 <b>Edge</b> 或 <b>Chrome</b> 浏览器打开本页，点「① 解析教材图片」即可听讲解。</p>',
        '<div class="ra-gbtns">',
          (link ? '<a class="ra-ga" href="' + link + '">🔍 打开声音自检</a>' : ''),
          '<button class="ra-gb" id="ra-gok">知道了</button>',
        '</div>',
      '</div>'
    ].join('');
    document.body.appendChild(g);
    g.querySelector('#ra-gok').onclick = function () { g.remove(); };
    g.addEventListener('click', function (e) { if (e.target === g) g.remove(); });
  }

  /* ============================================================
     垫片：接住课件的朗读调用（页面顶层取 window.speechSynthesis
     时本脚本已在位），点课件按钮 → 弹引导层，页面流程照常走完
     ============================================================ */
  if (window.__RA_SHIM__) return;
  window.__RA_SHIM__ = 1;
  function ShimUtterance(text) { this.text = text || ''; }
  window.SpeechSynthesisUtterance = ShimUtterance;
  window.speechSynthesis = {
    speaking: false, paused: false, pending: false,
    onvoiceschanged: null,
    getVoices: function () { return []; },
    cancel: function () {},
    pause: function () {},
    resume: function () {},
    addEventListener: function () {},
    removeEventListener: function () {},
    dispatchEvent: function () { return true; },
    speak: function (u) {
      showGuide();                       // ← 课件按钮在这里被接住
      setTimeout(function () {           // 快速回调，页面步骤不被卡住
        if (u && typeof u.onend === 'function') { try { u.onend(); } catch (e) {} }
      }, 60);
    }
  };

  /* 引导层样式（仅在不支持的浏览器里才会用到） */
  var st = document.createElement('style');
  st.textContent = [
    '#ra-guide{position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(10,30,45,.55);',
      'z-index:2147483100;display:flex;align-items:center;justify-content:center;padding:20px;}',
    '#ra-guide .ra-gcard{background:#fff;border-radius:16px;max-width:340px;width:100%;padding:20px;',
      'box-shadow:0 12px 40px rgba(0,0,0,.3);color:#24485c;',
      'font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}',
    '#ra-guide .ra-gt{font-size:17px;font-weight:700;margin-bottom:10px;}',
    '#ra-guide .ra-gp{font-size:14px;line-height:1.8;margin:6px 0;}',
    '#ra-guide .ra-gbtns{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;}',
    '#ra-guide .ra-ga,#ra-guide .ra-gb{flex:1;min-width:120px;text-align:center;padding:10px 12px;',
      'border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;text-decoration:none;}',
    '#ra-guide .ra-ga{background:#2E6E8E;color:#fff;}',
    '#ra-guide .ra-gb{background:#f4f9fb;color:#24485c;border:1.5px solid #c9dbe3;}'
  ].join('');
  document.head.appendChild(st);
})();
