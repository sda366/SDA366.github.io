/* 通用有声图文页校验脚本
   用法: node check_page.js <html路径> [热区数] [steps1思考数] [sayable数] [点读表条数]
   说明: 4 个数量参数为**可选**——不传时该项标记 SKIP 并回显实际值，
         不会拿 undefined 去比较产生假阳性 FAIL（2026-11-01 修）。
         传入时严格比对。 */
const fs = require("fs");
const [, , f, hotN, thinkN, sayN, clickN] = process.argv;
if (!f || !fs.existsSync(f)) {
  console.log("❌ 文件不存在或未提供路径: " + (f || "(空)"));
  console.log("用法: node check_page.js <html路径> [热区数] [思考数] [sayable数] [点读表条数]");
  console.log("提示: 路径含中文/空格时要用英文双引号包起来");
  process.exit(1);
}
const html = fs.readFileSync(f, "utf8");
// 取**最长**的内联 <script> 块：页面顶部「手机没声音提示条」自带一个小 <script>，
// 只取第一个会拿到它，导致后面所有检查基于错误的脚本（2026-11-01 踩到）。
const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
const m = [null, blocks.length ? blocks.reduce((a, b) => (b.length > a.length ? b : a)) : ""];
let pass = 0, fail = 0, skip = 0;
function ck(name, ok, extra) {
  if (ok) { pass++; console.log("PASS", name, extra || ""); }
  else { fail++; console.log("FAIL", name, extra || ""); }
}
/* 期望值为空 → 跳过（SKIP），只回显实际值，绝不算失败 */
function ckN(name, want, got, extra) {
  if (want === undefined || want === "" || isNaN(+want)) {
    skip++; console.log("SKIP", name, "实际" + got + "（未给期望值，未校验）");
    return;
  }
  ck(name + "=" + want, got === +want, extra || ("实际" + got));
}
// 1. 脚本语法
try { new Function(m[1]); ck("JS语法", true); }
catch (e) { ck("JS语法", false, e.message); }
// 2. steps2 不引用图片/热区
const s2 = m[1].match(/var steps2=\[([\s\S]*?)\];/)[1];
ck("steps2无imgWrap", !s2.includes("imgWrap"));
ck("steps2无hot引用", !/hot[A-Z]\w*/.test(s2));
// 3. 热区与 steps1 引用一致性
const hotIds = [...html.matchAll(/id="(hot\w+)"/g)].map(x => x[1]);
const s1 = m[1].match(/var steps1=\[([\s\S]*?)\];/)[1];
const s1refs = [...new Set([...s1.matchAll(/region:'(hot\w+)'/g)].map(x => x[1]))];
const missing = s1refs.filter(r => !hotIds.includes(r));
ck("steps1引用的热区都存在", missing.length === 0, missing.join(",") || "");
ckN("热区数量", hotN, hotIds.length, "共" + hotIds.length + "个");
// 4. steps1 think 数
const tk = (s1.match(/think:true/g) || []).length;
ckN("steps1思考数", thinkN, tk, "实际" + tk);
// 5. qa 数量与分层
const qas = [...html.matchAll(/id="(q\d)"[^>]*data-ans[\s\S]{0,900}?lv-pill (lv-\w)/g)];
ck("qa共6题且带data-ans", qas.length === 6, "实际" + qas.length);
const lvCount = {}; qas.forEach(x => lvCount[x[2]] = (lvCount[x[2]] || 0) + 1);
ck("认知2强化3拓展1", lvCount["lv-r"] === 2 && lvCount["lv-q"] === 3 && lvCount["lv-t"] === 1, JSON.stringify(lvCount));
// 6. sayable 数量与 data-say
const sayAll = (html.match(/class="sayable"/g) || []).length;
const sayOk = (html.match(/class="sayable" id="t\d+" data-say=/g) || []).length;
if (sayN === undefined || sayN === "" || isNaN(+sayN)) {
  ck("sayable都有data-say", sayAll === sayOk && sayAll > 0, "共" + sayAll + "/带say " + sayOk);
} else {
  ck("sayable=" + sayN + "且都有data-say", sayAll === +sayN && sayOk === +sayN, "共" + sayAll + "/带say " + sayOk);
}
// 7. 热区点读表条数
const hotClicks = m[1].match(/\[\['hot[\s\S]*?\]\s*\]\.forEach/);
const clicks = hotClicks ? (hotClicks[0].match(/\['hot/g) || []).length : 0;
ckN("热区点读表", clickN, clicks, "实际" + clicks + "条");
// 8. 无小鼠标残留
ck("无小鼠标/光标残留", !html.includes("cursor-move") && !html.includes("小鼠标") && !/mouse/.test(m[1]));
// 9. 图片路径存在
const img = (html.match(/src="(images\/[^"]+)"/) || [])[1];
const imgPath = f.replace(/\/[^/]+$/, "/") + img;
ck("图片文件存在", fs.existsSync(imgPath), img);
// 10. steps2 引用的 qN 都存在
const q2ids = [...new Set([...s2.matchAll(/qa:'(q\d)'/g)].map(x => x[1]))];
const q2miss = q2ids.filter(q => !html.includes(`id="${q}"`));
ck("steps2引用的题都存在", q2miss.length === 0, q2miss.join(",") || "");

/* ---- 以下 3 项是 2026-11-01 全站 586 题补分析时踩出的坑，固化进校验 ---- */

// 11. 每道分层题的解析区必须有「怎么想的」思路块（全站红线）
const ansBodies = [...html.matchAll(/<div class="qa-a"><div class="qa-a-inner">([\s\S]*?)<\/div><\/div>/g)]
  .map(x => x[1]);
const noThink = [];
ansBodies.forEach((b, i) => { if (!/sol sol3/.test(b)) noThink.push("第" + (i + 1) + "题"); });
ck("每题解析区都有「怎么想的」块",
   ansBodies.length > 0 && noThink.length === 0,
   "共" + ansBodies.length + "题" + (noThink.length ? "，缺" + noThink.join("/") : ""));

// 12. data-ans 属性无破损（被英文直引号提前截断会使结构崩坏）
const loose = [...html.matchAll(/<div class="qa" id="(q\d+)" data-ans=/g)].map(x => x[1]);
const strict = [...html.matchAll(/<div class="qa" id="(q\d+)" data-ans="[^"]*">/g)].map(x => x[1]);
const broken = loose.filter(q => !strict.includes(q));
ck("data-ans属性无破损", broken.length === 0, broken.length ? "破损:" + broken.join(",") : "共" + loose.length + "题");

// 13. read-assist.js 必须注入在 <body> 开标签后（早于页面脚本，否则垫片接不住）
const bodyM = html.match(/<body[^>]*>/);
const injected = /read-assist\.js/.test(html);
const atHead = bodyM && /read-assist\.js/.test(html.slice(bodyM.index, bodyM.index + 200));
ck("read-assist注入位置", !injected || atHead, injected ? (atHead ? "在body开头" : "位置靠后，垫片会失效") : "未注入");

// 14. 单题点击链路（askQA）：abort 置真后必须复位（2026-11-01 用户实测缺陷）
//     不复位 → speak().then() 里的 if(abort) return 全部命中 → 没想一想/不展开/不读答案
const askM = m[1].match(/function askQA\([\s\S]*?\n\}/);
if (!askM) { skip++; console.log("SKIP 单题点击链路（该页无 askQA，非分层提问页型）"); }
else {
  const ab = askM[0];
  ck("askQA 中 abort 已复位", /abort\s*=\s*false/.test(ab),
     /abort\s*=\s*false/.test(ab) ? "" : "缺 abort=false：单题点击会静默中断");
  ck("askQA 含「想一想」与朗读答案", /think\(/.test(ab) && /data-ans/.test(ab));
}
// 15. speak 不能在 cancel 后立刻调用（Chrome/安卓 WebView 会静默吞掉，表现为点了不出声）
const spM = m[1].match(/function speak\([\s\S]*?\n\}/);
if (!spM) { skip++; console.log("SKIP speak 延迟（未找到 speak 函数）"); }
else ck("speak 有 cancel→延迟保护", /RA-SPEAK-DELAY/.test(spM[0]) || /setTimeout\([\s\S]{0,60}synth\.speak\(u\)/.test(spM[0]),
        /RA-SPEAK-DELAY/.test(spM[0]) ? "" : "cancel 后立刻 speak，可能被浏览器静默吞掉");

console.log("\n==>", pass + " 通过, " + fail + " 失败, " + skip + " 跳过");
if (skip) console.log("（SKIP 项未给期望值，不影响结论；传齐 4 个数量参数可全量校验）");
process.exit(fail ? 1 : 0);
