/* ============================================================
   小学朗读兜底  read-assist.js  v4（静默版 · 无声才提示）
   ------------------------------------------------------------
   设计原则（2026-10-27 定）：
   1. 浏览器支持朗读 且 系统有中文语音 → 【完全静默】
      不建任何 DOM、不显示任何图标，课件自带按钮直接发声。
   2. 只有真正"发不出声"时才弹一次引导：
      A. 浏览器不支持朗读（微信/QQ 内置）  → 引导换 Edge/Chrome
      B. 浏览器支持，但系统没有语音引擎   → 一键打开系统朗读设置
      C. 有引擎但没有中文语音            → 引导下载中文语音包
   3. 顺带做"语音预热"：国产 ROM（MIUI/HyperOS）上
      getVoices() 首次返回空数组，页面同步调用会选不到中文语音。
      本脚本提前轮询触发 voiceschanged，提高首次点击的成功率。

   用法：页面 <body> 开标签后、页面自身脚本之前加
   <script src="相对路径/js/read-assist.js"></script>
   ============================================================ */
(function () {
  if (window.__READ_ASSIST__) return;      // 防止重复注入
  window.__READ_ASSIST__ = 1;

  var realTTS = ('speechSynthesis' in window) && (typeof SpeechSynthesisUtterance !== 'undefined');
  var synth = realTTS ? window.speechSynthesis : null;

  /* 本脚本所在目录，供「设置教程 / 声音自检」跳转（层级无关） */
  var SCRIPT_DIR = '';
  try { SCRIPT_DIR = String(document.currentScript.src).replace(/[^/]*$/, ''); } catch (e) {}
  function page(name) { return SCRIPT_DIR ? (SCRIPT_DIR + '../' + name) : ''; }

  /* ============================================================
     引导层：只在"确定发不出声"时出现
     ============================================================ */
  var guideLast = 0;
  function showGuide(kind) {
    var now = Date.now();
    if (now - guideLast < 30000) return;   // 30 秒内只弹一次
    guideLast = now;
    if (document.getElementById('ra-guide')) return;

    // 安卓可用 intent 直接唤起系统「文字转语音」设置页
    var isAndroid = /Android/i.test(navigator.userAgent);
    var ttsIntent = 'intent:#Intent;action=com.android.settings.TTS_SETTINGS;end';

    var title, body, btns = '';
    if (kind === 'nobrowser') {
      title = '📢 这个浏览器发不出声音';
      body  = '当前浏览器缺少网页朗读功能（微信、QQ 内置浏览器都没有）。<br>' +
              '请复制网址，用 <b>Edge</b> 或 <b>Chrome</b> 打开本页，点「① 解析教材图片」即可听讲解。';
    } else if (kind === 'no-voice') {
      title = '🔇 手机还没有可用的朗读语音';
      body  = '浏览器没问题，但系统里<b>没有装语音引擎</b>，所以发不出声。<br>' +
              '请打开系统「文字转语音」，把首选引擎设为 <b>小爱同学语音引擎</b>（或讯飞语音引擎），' +
              '并确认已下载「中文（普通话）」语音数据。';
      btns  = (isAndroid ? '<a class="ra-ga" href="' + ttsIntent + '">⚙ 打开系统朗读设置</a>' : '');
    } else {
      title = '🔈 缺少中文语音包';
      body  = '系统有语音引擎，但<b>没有中文语音</b>。<br>' +
              '请在系统「文字转语音」里把语言选为 <b>中文（普通话）</b>，并下载语音数据。';
      btns  = (isAndroid ? '<a class="ra-ga" href="' + ttsIntent + '">⚙ 打开系统朗读设置</a>' : '');
    }

    var g = document.createElement('div');
    g.id = 'ra-guide';
    g.innerHTML = [
      '<div class="ra-gcard">',
        '<div class="ra-gt">' + title + '</div>',
        '<p class="ra-gp">' + body + '</p>',
        '<p class="ra-gsm">设置顶部的搜索框搜「<b>文字转语音</b>」也能直接找到。</p>',
        '<div class="ra-gbtns">',
          btns,
          (page('voice-setup.html') ? '<a class="ra-ga ra-ga2" href="' + page('voice-setup.html') + '">📖 看图设置</a>' : ''),
          '<button class="ra-gb" id="ra-gok">知道了</button>',
        '</div>',
      '</div>'
    ].join('');
    document.body.appendChild(g);
    var ok = g.querySelector('#ra-gok');
    if (ok) ok.onclick = function () { g.remove(); };
    g.addEventListener('click', function (e) { if (e.target === g) g.remove(); });
  }

  /* ============================================================
     情况 A：浏览器不支持朗读 → 装垫片，接住课件按钮
     ============================================================ */
  if (!realTTS) {
    if (window.__RA_SHIM__) return;
    window.__RA_SHIM__ = 1;
    function ShimUtterance(text) { this.text = text || ''; }
    window.SpeechSynthesisUtterance = ShimUtterance;
    window.speechSynthesis = {
      speaking: false, paused: false, pending: false,
      onvoiceschanged: null,
      getVoices: function () { return []; },
      cancel: function () {}, pause: function () {}, resume: function () {},
      addEventListener: function () {}, removeEventListener: function () {},
      dispatchEvent: function () { return true; },
      speak: function (u) {
        showGuide('nobrowser');            // ← 课件按钮在这里被接住
        setTimeout(function () {
          if (u && typeof u.onend === 'function') { try { u.onend(); } catch (e) {} }
        }, 60);
      }
    };
  }

  /* ============================================================
     情况 B/C：浏览器支持，但系统语音没准备好
     —— 先静默预热；用户点击后若确认"没在发声"才提示
     ============================================================ */
  if (realTTS) {
    var voices = [];
    function loadVoices() {
      try {
        var v = synth.getVoices();
        if (v && v.length) voices = v;
      } catch (e) {}
    }
    loadVoices();
    try {
      if ('onvoiceschanged' in synth) synth.onvoiceschanged = loadVoices;
      synth.addEventListener && synth.addEventListener('voiceschanged', loadVoices);
    } catch (e) {}
    /* 轮询预热：国产 ROM 常迟迟不触发 voiceschanged */
    var tries = 0;
    var timer = setInterval(function () {
      loadVoices();
      if ((voices.length && tries > 4) || ++tries > 20) clearInterval(timer);
    }, 100);

    function hasZh() {
      for (var i = 0; i < voices.length; i++) {
        if (/^zh|^cmn/i.test(voices[i].lang || '')) return true;
      }
      return false;
    }

    /* 用户点击课件按钮后，等一会儿确认到底有没有发声 */
    document.addEventListener('click', function () {
      if (Date.now() - guideLast < 30000) return;
      setTimeout(function () {
        try {
          loadVoices();
          if (synth.speaking || synth.pending) return;   // 正在读 → 正常，不打扰
          if (voices.length && hasZh()) return;          // 有中文语音 → 正常
          showGuide(voices.length ? 'no-zh' : 'no-voice');
        } catch (e) {}
      }, 900);
    }, true);
  }

  /* 引导层样式（只在需要提示时才插入，平时页面零新增） */
  var st = document.createElement('style');
  st.textContent = [
    '#ra-guide{position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(10,30,45,.55);',
      'z-index:2147483100;display:flex;align-items:center;justify-content:center;padding:20px;}',
    '#ra-guide .ra-gcard{background:#fff;border-radius:16px;max-width:360px;width:100%;padding:20px;',
      'box-shadow:0 12px 40px rgba(0,0,0,.3);color:#24485c;',
      'font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}',
    '#ra-guide .ra-gt{font-size:17px;font-weight:700;margin-bottom:10px;}',
    '#ra-guide .ra-gp{font-size:14px;line-height:1.85;margin:6px 0;}',
    '#ra-guide .ra-gsm{font-size:12.5px;line-height:1.7;color:#7d97a5;margin:8px 0 0;}',
    '#ra-guide .ra-gbtns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;}',
    '#ra-guide .ra-ga,#ra-guide .ra-gb{flex:1;min-width:110px;text-align:center;padding:11px 12px;',
      'border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;text-decoration:none;}',
    '#ra-guide .ra-ga{background:#2E6E8E;color:#fff;}',
    '#ra-guide .ra-ga2{background:#e6f2f7;color:#2E6E8E;border:1.5px solid #9dc4d4;}',
    '#ra-guide .ra-gb{background:#f4f9fb;color:#24485c;border:1.5px solid #c9dbe3;}'
  ].join('');
  document.head.appendChild(st);
})();
