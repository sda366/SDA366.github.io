/* ============================================================
   小学朗读兜底  read-assist.js  v6（静默版 · 系统性防御）
   ------------------------------------------------------------
   设计原则（2026-10-27 定）：
   1. 浏览器支持朗读 且 系统有中文语音 → 【完全静默】
      不建任何 DOM、不显示任何图标，课件自带按钮直接发声。
   2. 只有真正"发不出声"时才弹一次引导：
      A. 浏览器不支持朗读（微信/QQ 内置）  → 引导换 Edge/Chrome
      B. 浏览器支持，但系统没有语音引擎   → 一键打开系统朗读设置
      C. 有引擎但没有中文语音            → 引导下载中文语音包
      D. 哑引擎：引擎在跑但声道没声音     → 唤醒音频通道 + 声音自检

   v6 相对 v5 新增的「移动端四道防线」（2026-10-27）：
   ① 文本安全清洗  —— iOS Safari 已知 Bug：朗读文本以 < 开头、以 > 结尾
      且含中文时，speechSynthesis 会彻底卡死（必须重启 Safari 才恢复）。
      在 utterance 进入引擎前统一把尖括号转为全角 ＜＞，从源头规避。
   ② 长文本分片    —— 单次 speak() 超过 80 字时按句末/逗号标点切成多片，
      排队依次朗读；页面的 onend 仍只在【最后一片】结束时回调，
      所以「读一句 → 停一下 → 下一句」的教学节奏完全不变。
   ③ 智能滚动      —— 劫持 scrollIntoView：目标已完整可见就不滚；
      两次滚动间隔不足 800ms 直接跳过；热区获得高亮时只在它【看不见】
      时才补一次滚动。避免手机上页面反复跳动、看不清当前高亮。
   ④ 字幕条避让    —— 动态测量控制栏实际高度，把 #cap 抬高到控制栏之上，
      解决手机上按钮换行导致字幕压住按钮、点不到的问题。

   全局开关（页面里 window.__RA_XXX__ = 1 可临时关掉某一项）：
      __RA_NOSPLIT__   关闭长文本分片
      __RA_NOSCROLL__  关闭智能滚动（恢复浏览器原生行为）
      __RA_NOCAPFIX__  关闭字幕避让

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
     ① 文本安全清洗（防 iOS Safari 静默失败 Bug）
     ------------------------------------------------------------
     注意：不能整体 trim 掉 \u3000（全角空格）——解锁用的静音发声
     就发这一个字符，trim 掉就变成空串，解锁会失效。
     ============================================================ */
  function sanitize(t) {
    var s = (t === null || t === undefined) ? '' : String(t);
    if (!s) return s;
    s = s.replace(/<\/?[A-Za-z][A-Za-z0-9-]*(\s[^<>]*)?\/?>/g, ' ');  // 只剥真 HTML 标签
    s = s.replace(/&lt;/gi, '\uFF1C').replace(/&gt;/gi, '\uFF1E');
    s = s.replace(/</g, '\uFF1C').replace(/>/g, '\uFF1E');     // 尖括号 → 全角
    s = s.replace(/&nbsp;/gi, ' ').replace(/\u00A0/g, ' ');
    s = s.replace(/[ \t\r\n]{2,}/g, ' ');                      // 压缩空白（不动 \u3000）
    return s;
  }

  /* ============================================================
     ② 长文本按标点分片（单片不超过 SPLIT_AT 字）
     ============================================================ */
  var SPLIT_AT = 80;
  function splitText(t) {
    var s = String(t || '');
    if (s.length <= SPLIT_AT) return [s];
    var out = [], start = 0, i, cut, end;
    var half = Math.floor(SPLIT_AT * 0.5);
    while (start < s.length) {
      end = Math.min(start + SPLIT_AT, s.length);
      if (end >= s.length) { out.push(s.slice(start)); break; }
      cut = -1;
      for (i = end; i > start + half; i--) {                   // 优先句末标点
        if (/[\u3002\uff01\uff1f!?\uff1b;\n]/.test(s.charAt(i - 1))) { cut = i; break; }
      }
      if (cut < 0) {                                           // 其次逗号、顿号
        for (i = end; i > start + half; i--) {
          if (/[\uff0c,\u3001]/.test(s.charAt(i - 1))) { cut = i; break; }
        }
      }
      if (cut < 0) cut = end;                                  // 实在没有就硬切
      out.push(s.slice(start, cut));
      start = cut;
    }
    var res = [];
    for (i = 0; i < out.length; i++) { if (out[i] && out[i].replace(/\s/g, '')) res.push(out[i]); }
    return res.length ? res : [s];
  }

  /* ============================================================
     ③ 智能滚动：节流 + 已可见就不滚 + 热区高亮时按需补滚
     ============================================================ */
  var origSIV = null;
  try { origSIV = Element.prototype.scrollIntoView; } catch (e) {}
  var lastScroll = 0;

  function doScroll(el) {
    lastScroll = Date.now();
    try {
      if (origSIV) origSIV.call(el, { behavior: 'smooth', block: 'center' });
      else el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (e) { try { el.scrollIntoView(); } catch (e2) {} }
  }
  function ensureVisible(el, force) {
    if (!el || window.__RA_NOSCROLL__) return;
    var now = Date.now();
    if (!force && now - lastScroll < 800) return;              // 节流：800ms 内只滚一次
    var r;
    try { r = el.getBoundingClientRect(); } catch (e) { return; }
    if (!r || (!r.height && !r.top)) return;
    var vh = window.innerHeight || document.documentElement.clientHeight || 0;
    var topPad = 70, botPad = 130;                             // 上留页头、下留控制栏+字幕
    if (r.height >= vh - topPad - botPad) {
      /* 元素比可视区还高（竖版教材整幅图）：只要求它的头部落在视口内 */
      if (r.top < topPad || r.top > vh * 0.45) doScroll(el);
      return;
    }
    if (r.top >= topPad && r.bottom <= vh - botPad) return;    // 已完整可见 → 不滚
    doScroll(el);
  }
  if (origSIV && !Element.prototype.scrollIntoView.__raPatched) {
    Element.prototype.scrollIntoView = function () {
      if (window.__RA_NOSCROLL__) return origSIV.apply(this, arguments);
      ensureVisible(this);
      return undefined;
    };
    Element.prototype.scrollIntoView.__raPatched = true;
  }
  /* 热区拿到高亮（.hl）时，若它在屏幕外才补一次滚动；
     这样 playStep1 换热区时页面不会跟着乱跳，但又不会"读到看不见的地方"。 */
  function watchHotspots() {
    if (!window.MutationObserver) return;
    var mo = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var el = muts[i].target;
        try { if (el && el.classList && el.classList.contains('hl')) ensureVisible(el); } catch (e) {}
      }
    });
    function bind() {
      var hs = document.querySelectorAll('.hotspot');
      for (var i = 0; i < hs.length; i++) {
        mo.observe(hs[i], { attributes: true, attributeFilter: ['class'] });
      }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
    else bind();
  }

  /* ============================================================
     ④ 字幕条避让控制栏（动态测量，按钮换行也不会压住）
     ============================================================ */
  function fixCaption() {
    if (window.__RA_NOCAPFIX__) return;
    var cap = document.getElementById('cap');
    var bar = document.querySelector('.ctrl-bar');
    if (!cap || !bar) return;
    var h = 0;
    try { h = Math.ceil(bar.getBoundingClientRect().height); } catch (e) {}
    if (!h) return;
    var b = h + 14;
    if (b > 64) cap.style.bottom = b + 'px';                   // 只在控制栏确实更高时才抬
  }
  function scheduleCapFix() {
    fixCaption();
    setTimeout(fixCaption, 400);
    setTimeout(fixCaption, 1500);
    window.addEventListener('resize', fixCaption);
    window.addEventListener('orientationchange', function () { setTimeout(fixCaption, 500); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scheduleCapFix);
  else scheduleCapFix();

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
    var chk = page('sound-check.html');

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
    } else if (kind === 'mute') {
      title = '🔈 语音引擎是"哑"的';
      body  = '手机其实认得字，但<b>声音没出来</b>（常见于声道被占用或蓝牙没连上）。<br>' +
              '请先<b>随便放一段音乐或视频</b>把声音通道"唤醒"，再回来点「① 解析教材图片」；<br>' +
              '顺便确认：手机没静音、没连着蓝牙耳机。';
      btns  = (chk ? '<a class="ra-ga" href="' + chk + '">🔍 声音自检</a>' : '') +
              (isAndroid ? '<a class="ra-ga ra-ga2" href="' + ttsIntent + '">⚙ 朗读设置</a>' : '');
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
    function ShimUtterance(text) { this.text = sanitize(text || ''); }
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
     情况 B/C/D：浏览器支持，但系统语音没准备好 / 引擎是哑的
     —— 先静默预热；用户点击后若确认"没在发声"才提示
     ============================================================ */
  if (realTTS) {
    /* ---------- 语音列表：异步就绪 + 轮询兜底 + 挑出中文语音 ---------- */
    var voices = [], zhVoice = null;

    function pickZh(v) {
      var zh = [], i, s;
      for (i = 0; i < v.length; i++) {
        s = v[i] || {};
        if (/^zh|^cmn/i.test(s.lang || '') || /Chinese|中文|普通话/i.test(s.name || '')) zh.push(s);
      }
      if (!zh.length) return null;
      for (i = 0; i < zh.length; i++) {
        if (/xiaoxiao|tingting|ting-ting|yaoyao|huihui/i.test(zh[i].name || '')) return zh[i];
      }
      return zh[0];
    }
    function loadVoices() {
      try {
        var v = synth.getVoices();
        if (v && v.length) { voices = v; if (!zhVoice) zhVoice = pickZh(v); }
      } catch (e) {}
    }
    loadVoices();
    try {
      if ('onvoiceschanged' in synth) synth.onvoiceschanged = loadVoices;
      if (synth.addEventListener) synth.addEventListener('voiceschanged', loadVoices);
    } catch (e) {}
    var tries = 0;
    var timer = setInterval(function () {
      loadVoices();
      if ((voices.length && tries > 4) || ++tries > 40) clearInterval(timer);
    }, 100);

    /* ---------- 发声埋点：给"哑引擎"检测提供证据 ---------- */
    var stat = { last: 0, started: false, startedAt: 0 };

    /* ---------- 修复②：补齐 voice + 文本清洗 + 长文本分片 ----------
       页面 speak() 同步取 getVoices()（移动端首返 []），且只设 lang='zh-CN'
       不指定 voice —— Safari 17+ / 部分安卓对未指定 voice 的中文会静默失败。
       这里在引擎层兜住：补 voice、清洗危险字符、超长文本切片排队。 */
    try {
      var origSpeak = SpeechSynthesis.prototype.speak;
      if (origSpeak && !origSpeak.__raPatched) {
        SpeechSynthesis.prototype.speak = function (u) {
          try {
            if (u) {
              if (!u.lang) u.lang = 'zh-CN';
              if (zhVoice && (!u.voice || !/^zh|^cmn/i.test(u.voice.lang || ''))) u.voice = zhVoice;
              u.text = sanitize(u.text);
              stat.last = Date.now(); stat.started = false;
              var oStart = u.onstart;
              u.onstart = function () {
                stat.started = true; stat.startedAt = Date.now();
                if (typeof oStart === 'function') { try { oStart.apply(u, arguments); } catch (e) {} }
              };
              if (!window.__RA_NOSPLIT__ && u.text && u.text.length > SPLIT_AT) {
                return speakChunks(this, u);
              }
            }
          } catch (e) {}
          return origSpeak.apply(this, arguments);
        };
        SpeechSynthesis.prototype.speak.__raPatched = true;
      }
    } catch (e) {}

    /* 分片朗读：把原 utterance 的第一片交给它自己，
       后续片用同参数的新 utterance 接上；页面绑定的 onend
       只在最后一片结束时触发一次 —— 教学节奏不变。 */
    function speakChunks(self, u) {
      var parts = splitText(u.text), i = 0;
      var origEnd = u.onend, origErr = u.onerror;
      function finish() { if (typeof origEnd === 'function') { try { origEnd.call(u, {}); } catch (e) {} } }
      function fail() { if (typeof origErr === 'function') { try { origErr.call(u, {}); } catch (e) {} } }
      function next() {
        if (i >= parts.length) { finish(); return; }
        var t = parts[i++];
        if (i === 1) {
          u.text = t;
          u.onend = function () { setTimeout(next, 30); };
          u.onerror = fail;
          origSpeak.call(self, u);
        } else {
          var n = new SpeechSynthesisUtterance(t);
          n.lang = u.lang; n.voice = u.voice; n.rate = u.rate;
          n.pitch = u.pitch; n.volume = u.volume;
          n.onstart = u.onstart;
          n.onend = function () { setTimeout(next, 30); };
          n.onerror = fail;
          origSpeak.call(self, n);
        }
      }
      next();
      return undefined;
    }

    /* ---------- 修复①：在手势同步路径里先"解锁" ----------
       页面 playStep1/playStep2 在首次 speak() 前有 await wait(600/500)，
       发声已脱离 click 的同步上下文，移动端会静默拒绝。
       这里用 capture 阶段（最先执行、仍在同步手势中）跑一次静音发声完成授权，
       之后页面自己的 speak 即使晚几百毫秒也能正常出声。 */
    var unlocked = false, lastUnlock = 0;
    function unlockOnce() {
      if (unlocked) return;
      var now = Date.now();
      if (now - lastUnlock < 3000) return;   // 语音还没就绪时，每 3 秒重试一次
      lastUnlock = now;
      try {
        var u = new SpeechSynthesisUtterance('\u3000');  // 全角空格，极短
        u.volume = 0; u.lang = 'zh-CN';
        if (zhVoice) u.voice = zhVoice;
        synth.speak(u);
        if ((synth.getVoices() || []).length) unlocked = true;
      } catch (e) {}
    }
    document.addEventListener('click', unlockOnce, true);
    document.addEventListener('touchend', unlockOnce, true);

    function hasZh() {
      for (var i = 0; i < voices.length; i++) {
        if (/^zh|^cmn/i.test(voices[i].lang || '')) return true;
      }
      return false;
    }

    /* ---------- 哑引擎检测：点了按钮、引擎也"在跑"，但就是没声 ---------- */
    function diagnose() {
      try {
        loadVoices();
        if (synth.paused) {                       // 被系统挂起：先试着恢复
          try { synth.resume(); } catch (e) {}
          setTimeout(function () { if (synth.paused) showGuide('mute'); }, 400);
          return;
        }
        if (synth.speaking || synth.pending) return;             // 正在读 → 正常，不打扰
        if (stat.last && Date.now() - stat.last < 6000 && !stat.started) {
          /* 确实发起过发声，但引擎从没 onstart → 典型的哑引擎/声道被占 */
          showGuide(voices.length && hasZh() ? 'mute' : (voices.length ? 'no-zh' : 'no-voice'));
          return;
        }
        if (voices.length && hasZh()) return;                    // 有中文语音 → 静默
        showGuide(voices.length ? 'no-zh' : 'no-voice');
      } catch (e) {}
    }

    /* 用户点击课件按钮后，等一会儿确认到底有没有发声（900ms 初判 + 2.4s 复查） */
    document.addEventListener('click', function () {
      if (Date.now() - guideLast < 30000) return;
      setTimeout(diagnose, 900);
      setTimeout(diagnose, 2400);
    }, true);

    watchHotspots();
  }

  /* 引导层样式 + 移动端高亮/字幕兜底（只在需要提示时才建 DOM；CSS 常驻但极轻） */
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
    '#ra-guide .ra-gb{background:#f4f9fb;color:#24485c;border:1.5px solid #c9dbe3;}',

    /* ---- 热区高亮：改用 outline + box-shadow，避免 border 变动引发重排（低端机更顺）---- */
    '.hotspot.hl{border-color:transparent !important;',
      'outline:3px solid var(--hl,#ffb300);outline-offset:1px;',
      'animation:raFlash .9s ease-in-out infinite !important;}',
    '@keyframes raFlash{',
      '0%,100%{outline-color:var(--hl,#ffb300);box-shadow:0 0 0 3px rgba(255,179,0,.16);}',
      '50%{outline-color:var(--hl2,#ff7043);box-shadow:0 0 0 8px rgba(255,112,67,.20);}}',

    /* ---- 字幕条：手机上控制栏按钮会换行，静态兜底抬高（JS 还会按实测再调）---- */
    '@media (max-width:600px){ #cap{bottom:110px;} }'
  ].join('');
  document.head.appendChild(st);
})();
