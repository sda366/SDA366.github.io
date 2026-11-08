/* ============================================================
   pinyin-read.js  v1（拼音字母→汉字读音 · 薄补丁）
   ------------------------------------------------------------
   背景（重要）：
   一年级语文上册的 48 个课件页都用【内联 speak()】朗读，并没有引入
   read-assist.js（全站公共朗读引擎），所以 read-assist.js 里的拼音修复
   对这些页根本没生效——拼音字母仍被中文 TTS 读成英语字母名
   （a→诶、b→比、sh→诗喝…）。

   本文件是最小补丁：只做一件事——给 SpeechSynthesis.prototype.speak 打补丁，
   在真正朗读前把 u.text 过一遍 pinyinRead（拼音字母→汉字读音），
   从而让所有内联 speak() 自动受益，无需改动 48 个页面的内部逻辑。

   原理同 read-assist.js 的 ⑥：
   ① ü 有时写作 v → ü；
   ② 带调元音【还原】成基础字母（ā→a、mā→ma、bá→ba，不是删掉！），
      同时兼容 NFD 组合声调符（U+0300–U+036F）；
   ③ 只把整段字母串正好等于某拼音键的片段替换成汉字读音
      （a→啊、sh→狮、zhi→知…）；整音节（ma、ba…）与英文单词
      （apple、shirt）整段不在表里 → 原样保留，中文 TTS 本就读对。

   门禁：仅当网址含「语文」或「拼音」时启用，避免误伤其他科目/英文。
   幂等：pinyinRead 对"已转换文本"再跑一次不会改变（如"啊"无字母），
        即便与 read-assist.js 同载也安全。
   ============================================================ */
(function () {
  if (window.__PINYIN_READ__) return;          // 防重复注入
  window.__PINYIN_READ__ = 1;
  if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') return;

  /* ---- 拼音字母 → 汉字读音 ---- */
  var PINYIN_MAP = {
    'a':'啊','o':'喔','e':'鹅','i':'衣','u':'乌','\u00fc':'迂',
    'b':'波','p':'坡','m':'摸','f':'佛','d':'得','t':'特','n':'讷','l':'勒',
    'ng':'嗯',   // 后鼻音 ng（独立出现时，如"后鼻音 ng"，读成"嗯"=ng 本音）
    'g':'哥','k':'科','h':'喝','j':'机','q':'七','x':'希',
    'r':'日','z':'资','c':'疵','s':'丝','y':'衣','w':'屋',
    'zh':'知','ch':'吃','sh':'狮',
    'er':'耳',
    'zhi':'知','chi':'吃','shi':'狮','ri':'日','zi':'资','ci':'疵','si':'丝',
    'yi':'衣','wu':'乌','yu':'迂','ye':'耶','yue':'约','yuan':'冤','yin':'因','yun':'晕','ying':'英'
  };
  /* ---- 声调符 → 基础字母：还原（不是删掉）---- */
  var TONE_MAP = {
    '\u0101':'a','\u00e1':'a','\u01ce':'a','\u00e0':'a',   // ā á ǎ à
    '\u0113':'e','\u00e9':'e','\u011b':'e','\u00e8':'e',   // ē é ě è
    '\u012b':'i','\u00ed':'i','\u01d0':'i','\u00ec':'i',   // ī í ǐ ì
    '\u014d':'o','\u00f3':'o','\u01d2':'o','\u00f2':'o',   // ō ó ǒ ò
    '\u016b':'u','\u00fa':'u','\u01d4':'u','\u00f9':'u',   // ū ú ǔ ù
    '\u01d6':'\u00fc','\u01d8':'\u00fc','\u01da':'\u00fc','\u01dc':'\u00fc' // ǖ ǘ ǚ ǜ
  };
  var TONE_RE = /[\u0101\u00e1\u01ce\u00e0\u0113\u00e9\u011b\u00e8\u012b\u00ed\u01d0\u00ec\u014d\u00f3\u01d2\u00f2\u016b\u00fa\u01d4\u00f9\u01d6\u01d8\u01da\u01dc]/g;
  var COMBINING_TONE = /[\u0300-\u036F]/g;                   // NFD 组合声调符
  var PINYIN_CHARS = /[a-zA-Z\u00fc]+/g;                    // 整段字母串（含 ü）

  function pinyinRead(t) {
    var s = String(t == null ? '' : t).replace(/v/gi, '\u00fc');   // ü 有时写作 v
    /* ②a 先处理 NFC 下的 precomposed 带调元音（ā→a） */
    s = s.replace(TONE_RE, function (c) {
      return Object.prototype.hasOwnProperty.call(TONE_MAP, c) ? TONE_MAP[c] : c;
    });
    /* ②b 再处理 NFD 分解形式：拆成基础+组合符 → 去掉组合声调符 → 重新组合 */
    try {
      s = s.normalize('NFD').replace(COMBINING_TONE, '').normalize('NFC');
    } catch (e) {}
    /* ③ 仅替换整段命中拼音表的字母串 */
    return s.replace(PINYIN_CHARS, function (seg) {
      return Object.prototype.hasOwnProperty.call(PINYIN_MAP, seg) ? PINYIN_MAP[seg] : seg;
    });
  }

  /* ---- 门禁：仅语文/拼音课件 ---- */
  function enabled() {
    var p = '';
    try { p = decodeURIComponent(location.href); } catch (e) {}
    return /语文|拼音/.test((location.pathname || '') + ' ' + p);
  }

  /* ---- 打补丁：朗读前改写文本 ---- */
  var orig = SpeechSynthesis.prototype.speak;
  if (orig && !orig.__pyPatched) {
    SpeechSynthesis.prototype.speak = function (u) {
      try {
        if (u && u.text != null && enabled()) {
          u.text = pinyinRead(String(u.text));
        }
      } catch (e) {}
      return orig.apply(this, arguments);
    };
    SpeechSynthesis.prototype.speak.__pyPatched = true;
  }
})();
