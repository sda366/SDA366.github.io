/**
 * sim_askqa.js —— 仿真验证「单独点击某一题」的完整链路
 *
 * 用最小 DOM / TTS 替身跑页面脚本里的 askQA(id)，断言四件事：
 *   1. 有朗读题目（有声音）
 *   2. 出现「想一想」倒计时
 *   3. 解析被展开（classList 含 open）
 *   4. 朗读了 data-ans（思路 + 答案 + 检查）
 *
 * 用法：node sim_askqa.js <html> [题号 id，默认 q1]
 */
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const file = process.argv[2];
const qid = process.argv[3] || 'q1';
if (!file) { console.error('用法: node sim_askqa.js <html> [qid]'); process.exit(1); }

const html = fs.readFileSync(file, 'utf8');
// 取页面内联脚本（不含 <script src=...>）
const scripts = [];
const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
let m;
while ((m = re.exec(html)) !== null) scripts.push(m[1]);
const code = scripts.join('\n');

// ---------------- DOM / TTS 替身 ----------------
const spoken = [];
const pills = [];
const els = new Map();

function makeEl(id) {
  const cls = new Set();
  const el = {
    id: id, _cls: cls, style: {}, innerHTML: '', value: '', disabled: false,
    textContent: '',
    classList: {
      contains: c => cls.has(c),
      add: c => cls.add(c),
      remove: c => cls.delete(c),
      toggle: c => (cls.has(c) ? cls.delete(c) : cls.add(c))
    },
    getAttribute(a) {
      if (a === 'data-ans') return '【怎么想的】先算一共几个，再想每份几个。答案是六个。检查一遍：六乘一等于六，对。';
      if (a === 'data-secs') return '1';
      if (a === 'data-say') return '这是点读文本';
      return '';
    },
    setAttribute() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {},
    scrollIntoView() {}, appendChild() {}, focus() {}, click() {},
    querySelector(sel) {
      const sub = makeEl(id + sel);
      if (sel.indexOf('q-text') >= 0) sub.textContent = '第一题，认知：图上哪种气球最多？';
      if (sel.indexOf('think-pill') >= 0) {
        Object.defineProperty(sub, 'textContent', {
          set(v) { pills.push(v); }, get() { return pills[pills.length - 1] || ''; }
        });
      }
      return sub;
    },
    querySelectorAll() { return []; }
  };
  return el;
}
function byId(id) {
  if (!els.has(id)) els.set(id, makeEl(id));
  return els.get(id);
}

const synth = {
  speaking: false, pending: false, paused: false,
  getVoices: () => [],
  cancel() {},
  resume() {},
  speak(u) {
    spoken.push(String(u.text));
    setTimeout(() => { if (u.onend) u.onend(); }, 10);
  }
};

const sandbox = {
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  requestAnimationFrame: cb => setTimeout(cb, 0),
  speechSynthesis: synth,
  SpeechSynthesisUtterance: function (t) { this.text = t; },
  localStorage: { getItem: () => null, setItem() {} },
  document: {
    getElementById: byId,
    querySelector: sel => makeEl(sel),
    querySelectorAll: () => [],
    createElement: () => makeEl('new'),
    addEventListener() {},
    body: makeEl('body')
  },
  navigator: { userAgent: 'node-sim' },
  location: { href: 'file:///' + path.basename(file) }
};
sandbox.window = sandbox;
sandbox.window.__raBusy = () => false;
vm.createContext(sandbox);

// ---------------- 执行 ----------------
(async () => {
  try {
    vm.runInContext(code, sandbox, { filename: path.basename(file) });
  } catch (e) {
    console.log('❌ 页面脚本执行失败：' + e.message);
    process.exit(1);
  }
  if (typeof sandbox.askQA !== 'function') {
    console.log('SKIP 该页没有 askQA（非分层提问页型）');
    process.exit(0);
  }
  const t0 = Date.now();
  await sandbox.askQA(qid);
  await new Promise(r => setTimeout(r, 300));
  const qa = byId(qid);

  const saidQ = spoken.some(t => t.indexOf('第一题') >= 0 || t.indexOf('气球') >= 0);
  const thought = pills.some(t => t.indexOf('想一想') >= 0);
  const opened = qa.classList.contains('open');
  const saidAns = spoken.some(t => t.indexOf('怎么想的') >= 0);

  const ok = saidQ && thought && opened && saidAns;
  console.log((ok ? '✅ PASS ' : '❌ FAIL ') + path.basename(file) + '  ' + qid +
    '  （用时 ' + (Date.now() - t0) + 'ms）');
  console.log('   读题: ' + saidQ + ' | 想一想: ' + thought + ' | 展开: ' + opened + ' | 读答案: ' + saidAns);
  console.log('   朗读序列: ' + JSON.stringify(spoken));
  process.exit(ok ? 0 : 1);
})();
