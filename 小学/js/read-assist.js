/* ============================================================
   小学朗读小助手  read-assist.js
   ------------------------------------------------------------
   1. 默认关闭，点开才出声 —— 这个「点击」同时满足 iPhone
      必须由用户手势才允许朗读的限制。
   2. 打开后「选中文字就朗读」，划一句听一句。
   3. 开关 / 语速 / 划词开关记在本机，下次自动沿用。
   4. 【联动课件】本脚本注入在页面自身脚本之前：若浏览器不支持
      网页朗读（微信内置浏览器、旧内核等），会放一个「垫片」，
      课件自带朗读按钮被点击时自动弹出引导层，不再无声装读。
   5. 纯浏览器自带语音，不用联网、不用后端、不用装插件。

   用法：页面 <body> 开标签后、页面自身脚本之前加
   <script src="相对路径/js/read-assist.js"></script>
   ============================================================ */
(function () {
  if (window.__READ_ASSIST__) return;      // 防止重复注入
  window.__READ_ASSIST__ = 1;

  /* 记录本脚本所在目录，供「声音自检」跳转用（层级无关） */
  var SCRIPT_DIR = '';
  try { SCRIPT_DIR = String(document.currentScript.src).replace(/[^/]*$/, ''); } catch (e) {}

  var KEY_ON = 'ra_on', KEY_RATE = 'ra_rate', KEY_SEL = 'ra_sel';
  var on     = localStorage.getItem(KEY_ON) === '1';
  var rate   = parseFloat(localStorage.getItem(KEY_RATE) || '0.85');
  if (isNaN(rate) || rate < 0.6 || rate > 1.2) rate = 0.85;
  var selOn  = localStorage.getItem(KEY_SEL) !== '0';
  var lastErr = '';

  /* 真实能力检测（必须在垫片之前求值） */
  var realTTS = ('speechSynthesis' in window) && (typeof SpeechSynthesisUtterance !== 'undefined');

  /* ============================================================
     垫片：浏览器不支持朗读时，接住课件自带的朗读调用
     —— 点课件按钮 → 不再无声装读，而是弹出引导层
     ============================================================ */
  var guideLast = 0;
  function showGuide() {
    var now = Date.now();
    if (now - guideLast < 30000) return;   // 30 秒内只弹一次
    guideLast = now;
    if (document.getElementById('ra-guide')) return;
    var g = document.createElement('div');
    g.id = 'ra-guide';
    var link = SCRIPT_DIR ? (SCRIPT_DIR + '../sound-check.html') : '';
    g.innerHTML = [
      '<div class="ra-gcard">',
        '<div class="ra-gt">📢 这个浏览器不能朗读</div>',
        '<p class="ra-gp">当前浏览器缺少网页语音功能（微信内置浏览器、部分手机自带浏览器都这样）。</p>',
        '<p class="ra-gp">请用 <b>Chrome</b> 或 <b>Edge</b> 打开本页；也可以先打开声音自检，按提示检查手机语音设置。</p>',
        '<div class="ra-gbtns">',
          (link ? '<a class="ra-ga" href="' + link + '">🔍 打开声音自检</a>' : ''),
          '<button class="ra-gb" id="ra-gok">继续浏览</button>',
        '</div>',
      '</div>'
    ].join('');
    document.body.appendChild(g);
    g.querySelector('#ra-gok').onclick = function () { g.remove(); };
    g.addEventListener('click', function (e) { if (e.target === g) g.remove(); });
  }

  function installShim() {
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
        setTimeout(function () {
          if (u && typeof u.onend === 'function') { try { u.onend(); } catch (e) {} }
        }, 60);
      }
    };
  }
  if (!realTTS) installShim();

  /* ---------------- 样式（内联，不额外引 CSS） ---------------- */
  var css = [
    '#ra-box{position:fixed;right:18px;bottom:18px;z-index:2147483000;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}',
    '#ra-ball{width:54px;height:54px;border-radius:50%;border:none;cursor:pointer;',
      'background:linear-gradient(135deg,#2E6E8E,#4A9CC4);color:#fff;font-size:24px;',
      'box-shadow:0 4px 14px rgba(46,110,142,.35);transition:transform .18s;}',
    '#ra-ball:hover{transform:scale(1.08);}',
    '#ra-ball.on{background:linear-gradient(135deg,#1E8E6E,#43B581);}',
    '#ra-panel{display:none;width:260px;max-width:82vw;margin-bottom:10px;padding:14px 15px 12px;',
      'background:#fff;border-radius:14px;box-shadow:0 8px 28px rgba(0,0,0,.18);color:#24485c;}',
    '#ra-panel.show{display:block;}',
    '.ra-hd{display:flex;align-items:center;justify-content:space-between;font-weight:700;font-size:15px;margin-bottom:10px;}',
    '#ra-x{cursor:pointer;font-size:20px;line-height:1;color:#8aa5b3;padding:0 2px;}',
    '#ra-toggle{width:100%;padding:11px;border:none;border-radius:10px;cursor:pointer;',
      'font-size:15px;font-weight:700;background:#2E6E8E;color:#fff;}',
    '#ra-toggle.on{background:#1E8E6E;}',
    '.ra-row{display:flex;align-items:center;gap:8px;font-size:13.5px;margin:11px 0;}',
    '#ra-rate{flex:1;}',
    '#ra-rate-v{width:34px;text-align:right;color:#5b7c8d;}',
    '#ra-stop,#ra-test{width:100%;padding:9px;margin-top:6px;border:1.5px solid #c9dbe3;background:#f4f9fb;',
      'border-radius:10px;cursor:pointer;font-size:14px;color:#24485c;}',
    '.ra-tip{margin:10px 0 0;font-size:12px;line-height:1.7;color:#7d97a5;}',
    '#ra-state{margin-top:10px;padding:8px 10px;border-radius:8px;background:#f4f9fb;',
      'font-size:12px;line-height:1.6;color:#5b7c8d;word-break:break-all;white-space:pre-line;}',
    '#ra-state.warn{background:#fff5e6;color:#a35a00;}',
    '#ra-state.err{background:#fdeaea;color:#b32d2d;}',
    '#ra-guide{position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(10,30,45,.55);',
      'z-index:2147483100;display:flex;align-items:center;justify-content:center;padding:20px;}',
    '#ra-guide .ra-gcard{background:#fff;border-radius:16px;max-width:340px;width:100%;padding:20px;',
      'box-shadow:0 12px 40px rgba(0,0,0,.3);color:#24485c;font-family:inherit;}',
    '#ra-guide .ra-gt{font-size:17px;font-weight:700;margin-bottom:10px;}',
    '#ra-guide .ra-gp{font-size:14px;line-height:1.8;margin:6px 0;}',
    '#ra-guide .ra-gbtns{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;}',
    '#ra-guide .ra-ga,#ra-guide .ra-gb{flex:1;min-width:120px;text-align:center;padding:10px 12px;',
      'border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;text-decoration:none;}',
    '#ra-guide .ra-ga{background:#2E6E8E;color:#fff;}',
    '#ra-guide .ra-gb{background:#f4f9fb;color:#24485c;border:1.5px solid #c9dbe3;}'
  ].join('');

  /* ---------------- 建 DOM ---------------- */
  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  var box = document.createElement('div');
  box.id = 'ra-box';
  box.innerHTML = [
    '<div id="ra-panel">',
      '<div class="ra-hd"><span>🔊 朗读小助手</span><span id="ra-x">×</span></div>',
      '<button id="ra-toggle">开启朗读</button>',
      '<div class="ra-row"><span>语速</span><input type="range" id="ra-rate" min="0.6" max="1.2" step="0.05" value="', rate, '"><span id="ra-rate-v">', rate.toFixed(2), '</span></div>',
      '<div class="ra-row"><input type="checkbox" id="ra-sel"', (selOn ? ' checked' : ''), '><label for="ra-sel">选中文字就朗读</label></div>',
      '<button id="ra-stop">⏹ 停止</button>',
      '<button id="ra-test">🔍 声音自检</button>',
      '<div id="ra-state">未开启</div>',
      '<p class="ra-tip">用鼠标或手指选中一句话即可朗读。<br>iPhone 请关闭侧边静音拨杆。</p>',
    '</div>',
    '<button id="ra-ball" title="朗读小助手">🔊</button>'
  ].join('');
  document.body.appendChild(box);

  /* 页面元素就绪后再定位置：有控制条就上移让位 */
  function placeBox() {
    var b = document.querySelector('.ctrl-bar');
    box.style.bottom = (b ? 108 : 18) + 'px';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', placeBox);
  else placeBox();

  var panel   = box.querySelector('#ra-panel');
  var ball    = box.querySelector('#ra-ball');
  var toggle  = box.querySelector('#ra-toggle');
  var slider  = box.querySelector('#ra-rate');
  var rateV   = box.querySelector('#ra-rate-v');
  var selBox  = box.querySelector('#ra-sel');
  var stopBt  = box.querySelector('#ra-stop');
  var testBt  = box.querySelector('#ra-test');
  var stateEl = box.querySelector('#ra-state');

  /* ---------------- 状态显示 ---------------- */
  function showState() {
    var s, cls = '';
    if (!realTTS) {
      s = '❌ 此浏览器不支持朗读，请换 Chrome 或 Edge 打开。\n点课件朗读按钮也会弹出这个提醒。'; cls = 'err';
    } else if (lastErr) {
      s = '❌ 朗读失败：' + lastErr; cls = 'err';
    } else if (speaking) {
      s = '🔊 正在朗读…';
    } else if (!on) {
      s = '未开启（点上方按钮开启）';
    } else if (!hasZh) {
      s = '⚠️ 没检测到中文语音包，会没声音。\n请到手机「设置 → 系统 → 语言和输入法 → 文字转语音」安装中文语音，或换 Chrome。';
      cls = 'warn';
    } else {
      s = '✅ 就绪 · 语音：' + (voice ? voice.name : '系统默认');
    }
    stateEl.className = cls;
    stateEl.textContent = s;
  }

  /* ---------------- 语音 ---------------- */
  var voice = null, hasZh = false, speaking = false;
  var queue = [], keepAlive = null;

  function pickVoice() {
    var vs = speechSynthesis.getVoices() || [];
    if (!vs.length) return null;
    var zh = vs.filter(function (v) { return /zh|cmn|chinese|中文/i.test(v.lang + ' ' + v.name); });
    hasZh = zh.length > 0;
    if (!hasZh) return null;               // 没有中文语音就交给系统默认，别硬点英文引擎
    var nice = zh.filter(function (v) { return /xiaoxiao|tingting|ting-ting|yaoyao|huihui|小燕|小爱/i.test(v.name); });
    return (nice[0] || zh[0]);
  }
  if (realTTS) {
    voice = pickVoice();
    speechSynthesis.onvoiceschanged = function () { voice = pickVoice(); showState(); };
  }

  // 长文本按标点切片，避免 Chrome 读到一半自动停
  function splitText(t) {
    var parts = [], cur = '';
    t.replace(/\s+/g, ' ').split('').forEach(function (ch) {
      cur += ch;
      if (cur.length >= 100 && /[。！？；，、,.!?;]/.test(ch)) { parts.push(cur); cur = ''; }
    });
    if (cur.trim()) parts.push(cur);
    return parts;
  }

  // 安卓（小米/MIUI）已知问题：朗读十几秒后会被系统掐断，定时 resume 可续命
  function startKeep() {
    stopKeep();
    keepAlive = setInterval(function () {
      if (speechSynthesis.speaking) speechSynthesis.resume();
    }, 8000);
  }
  function stopKeep() {
    if (keepAlive) { clearInterval(keepAlive); keepAlive = null; }
  }

  function playNext() {
    if (!queue.length) { speaking = false; stopKeep(); showState(); return; }
    var u = new SpeechSynthesisUtterance(queue.shift());
    u.lang = 'zh-CN'; u.rate = rate; u.pitch = 1;
    if (voice) u.voice = voice;
    u.onstart = function () { speaking = true; showState(); };
    u.onend = playNext;
    u.onerror = function (e) {
      queue = []; speaking = false; stopKeep();
      lastErr = (e && e.error) ? e.error : '未知错误';
      showState();
    };
    speechSynthesis.speak(u);
  }

  function speak(text) {
    if (!realTTS) { showGuide(); return; }
    text = (text || '').trim();
    if (!text) return;
    lastErr = '';
    try { speechSynthesis.cancel(); } catch (e) {}
    // 安卓上 cancel 后立刻 speak 常常失败，隔一拍再读；同时先 resume 唤醒引擎
    setTimeout(function () {
      try { if (speechSynthesis.paused) speechSynthesis.resume(); } catch (e) {}
      queue = splitText(text);
      startKeep();
      playNext();
    }, 100);
  }

  /* ---------------- 界面状态 ---------------- */
  function render() {
    toggle.textContent = on ? '✅ 朗读已开启（点击关闭）' : '开启朗读';
    toggle.className = on ? 'on' : '';
    ball.className = on ? 'on' : '';
    ball.textContent = on ? '🔊' : '🔇';
    selBox.disabled = !on;
    showState();
  }
  render();

  ball.onclick = function () { panel.classList.toggle('show'); };
  box.querySelector('#ra-x').onclick = function () { panel.classList.remove('show'); };

  toggle.onclick = function () {
    on = !on;
    localStorage.setItem(KEY_ON, on ? '1' : '0');
    render();
    if (on) speak('朗读已开启，选中文字就能听');  // 这一下同时解锁 iPhone 语音
    else { queue = []; speaking = false; stopKeep(); try { speechSynthesis.cancel(); } catch (e) {} showState(); }
  };

  slider.oninput = function () {
    rate = parseFloat(slider.value);
    rateV.textContent = rate.toFixed(2);
    localStorage.setItem(KEY_RATE, String(rate));
  };

  selBox.onchange = function () {
    selOn = selBox.checked;
    localStorage.setItem(KEY_SEL, selOn ? '1' : '0');
  };

  stopBt.onclick = function () {
    queue = [];
    speaking = false;
    stopKeep();
    try { speechSynthesis.cancel(); } catch (e) {}
    showState();
  };

  // 声音自检：读一句测试音，并把引擎/错误直接显示在面板上
  testBt.onclick = function () {
    if (!realTTS) { showGuide(); return; }
    pickVoice();
    lastErr = '';
    stateEl.className = '';
    stateEl.textContent = '⏳ 正在测试…请听是否有声音';
    var vs = (speechSynthesis.getVoices() || []).length;
    speak('你好，我是朗读小助手');
    setTimeout(function () {
      if (lastErr) { showState(); return; }
      stateEl.className = hasZh ? '' : 'warn';
      stateEl.textContent = hasZh
        ? ('✅ 测试已发出 · 语音：' + (voice ? voice.name : '系统默认'))
        : ('⚠️ 本机共 ' + vs + ' 个语音，没有中文语音包。\n请到「设置 → 系统 → 语言和输入法 → 文字转语音」安装中文语音，或换 Chrome 打开。');
    }, 2500);
  };

  /* ---------------- 划词即读 ---------------- */
  var timer = null;
  function onSelect() {
    if (!on || !selOn) return;
    clearTimeout(timer);
    timer = setTimeout(function () {
      var t = (window.getSelection() || '').toString();
      if (t && t.trim().length > 0) speak(t);
    }, 350);
  }
  document.addEventListener('mouseup', onSelect);
  document.addEventListener('touchend', onSelect);
  document.addEventListener('keyup', function (e) {
    if (e.shiftKey) onSelect();     // 键盘 Shift 选词也能读
  });
})();
