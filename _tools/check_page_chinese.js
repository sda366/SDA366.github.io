/**
 * 小学语文带读页校验 check_page.js  v0.2（chinese-primary-courseware）
 *
 * 用法：
 *   node assets/check_page.js <html文件路径> [段落数] [会认] [会写] [题数] [句数] [听写词] [近义词组]
 * 例：
 *   node assets/check_page.js 第1课-小蝌蚪找妈妈-有声图文.html 6 16 8 8 14 10 4
 *
 * v0.2 相对 v0.1 的新增项（对应「试验版二版」四项升级）：
 *   14 句级点读：.sent 数量 = stepsRead 条数；.para .no 存在（点序号读整段）
 *   15 跟读模式：followWait + 跟读开关按钮
 *   16 听写：dictWords 条数 = 词语卡 .wc 数量；每个词有示范句 data-say
 *   17 近义词辨析：.near 数量 = 期望；每组含 相同 / 不一样 / 造句
 *   18 开放题：运用层与拓展层的题里出现「答案不唯一」
 *   19 分角色：.role 有 data-role 与 data-lines
 *   20 朗读要求卡：req 卡存在且有 data-say
 * 沿用数学技能：参数化校验 + 逐项 PASS/FAIL + 末尾汇总，任一项 FAIL 即退出码 1。
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const file = process.argv[2];
const EXP = {
  para: +(process.argv[3] || 6),
  zin:  +(process.argv[4] || 16),
  ziw:  +(process.argv[5] || 8),
  qa:   +(process.argv[6] || 8),
  sent: +(process.argv[7] || 0),
  dict: +(process.argv[8] || 10),
  near: +(process.argv[9] || 4)
};
if (!file) { console.error('用法: node check_page.js <html> [段落] [会认] [会写] [题数] [句数] [听写词] [近义词组]'); process.exit(1); }

const html = fs.readFileSync(file, 'utf8');
const dir = path.dirname(path.resolve(file));
let pass = 0, fail = 0;
function chk(name, ok, extra) {
  if (ok) { pass++; console.log('  PASS  ' + name + (extra ? '  → ' + extra : '')); }
  else    { fail++; console.log('  FAIL  ' + name + (extra ? '  → ' + extra : '')); }
}
const count = (re) => (html.match(re) || []).length;

console.log('\n校验：' + path.basename(file));
console.log('期望：段落 ' + EXP.para + ' / 会认 ' + EXP.zin + ' / 会写 ' + EXP.ziw + ' / 题 ' + EXP.qa +
            ' / 句 ' + (EXP.sent || '自动') + ' / 听写词 ' + EXP.dict + ' / 近义词 ' + EXP.near + '\n');

/* 1. 朗读兜底注入位置：必须在 <body> 开标签后 */
const bodyM = html.match(/<body[^>]*>/i);
const afterBody = bodyM ? html.slice(bodyM.index + bodyM[0].length, bodyM.index + bodyM[0].length + 200) : '';
chk('1  read-assist.js 注入在 <body> 开头', !!bodyM && afterBody.includes('read-assist.js'));

/* 2~3. 课文段落 */
const paras = html.match(/<div class="para"[^>]*id="[^"]+"[^>]*>/g) || [];
chk('2  课文段落卡数量 = ' + EXP.para, paras.length === EXP.para, '实际 ' + paras.length);
const sayableParas = (html.match(/<div class="para"[^>]*data-say="/g) || []).length;
chk('3  每张段落卡都有 data-say（读整段）', sayableParas === paras.length, sayableParas + '/' + paras.length);

/* 4~6. 生字卡 */
function sliceBlock(startId, endId, tailMark) {
  const i = html.indexOf('id="' + startId + '"');
  if (i < 0) return '';
  let j = endId ? html.indexOf('id="' + endId + '"', i) : -1;
  if (!(j > i) && tailMark) j = html.indexOf(tailMark, i);
  return html.slice(i, j > i ? j : undefined);
}
const zinBlock = sliceBlock('zinGrid', 'ziwGrid', '</div>');
const ziwBlock = sliceBlock('ziwGrid', 'w1', '</div>');
const ziAll = html.match(/<div class="zi(?: write)?"[^>]*data-say="/g) || [];
const ziAllAny = html.match(/<div class="zi(?: write)?"/g) || [];
chk('4  会认字卡数量 = ' + EXP.zin, (zinBlock.match(/<div class="zi"/g) || []).length === EXP.zin,
  '实际 ' + (zinBlock.match(/<div class="zi"/g) || []).length);
chk('5  会写字卡数量 = ' + EXP.ziw, (ziwBlock.match(/<div class="zi write"/g) || []).length === EXP.ziw,
  '实际 ' + (ziwBlock.match(/<div class="zi write"/g) || []).length);
chk('6  每张生字卡都有 data-say', ziAll.length === ziAllAny.length, ziAll.length + '/' + ziAllAny.length);
chk('6b 会写字卡含书写提示（wtip）', (ziwBlock.match(/class="wtip"/g) || []).length === EXP.ziw,
  '实际 ' + (ziwBlock.match(/class="wtip"/g) || []).length);

/* 7. 分层题与层级 */
const qaCount = (html.match(/<div class="qa" id="q\d+"/g) || []).length;
const lvR = (html.match(/lv-pill lv-r/g) || []).length;
const lvQ = (html.match(/lv-pill lv-q/g) || []).length;
const lvY = (html.match(/lv-pill lv-y/g) || []).length;
const lvT = (html.match(/lv-pill lv-t/g) || []).length;
chk('7  分层题数 = ' + EXP.qa, qaCount === EXP.qa, '实际 ' + qaCount);
chk('7b 四层齐全（认知/理解/运用/拓展）', lvR > 0 && lvQ > 0 && lvY > 0 && lvT > 0,
  lvR + ':' + lvQ + ':' + lvY + ':' + lvT);
const ansCount = (html.match(/<div class="qa" id="q\d+" data-ans="[^"]{10,}"/g) || []).length;
chk('7c 每题都有可读的 data-ans', ansCount === qaCount, ansCount + '/' + qaCount);

/* 8. 序列与页面元素一致 */
const stepsRead = (html.match(/\{id:'s\d+', say:/g) || []).length;
const stepsQa = (html.match(/\{id:'q\d+', say:/g) || []).length;
if (EXP.sent) chk('8a stepsRead 条数 = 句数', stepsRead === EXP.sent, stepsRead + '/' + EXP.sent);
else chk('8a stepsRead 条数 > 段落数（已拆到句）', stepsRead > paras.length, stepsRead + ' 句 / ' + paras.length + ' 段');
chk('8b stepsQa 条数 = 题数', stepsQa === qaCount, stepsQa + '/' + qaCount);
const wordIdsAll = [...html.matchAll(/\{id:'([^']+)', say:/g)].map(m => m[1]).filter(x => /^(w|zin|ziw|n|a)/.test(x));
const missing = wordIdsAll.filter(id => !html.includes('id="' + id + '"'));
chk('8c steps 引用的 id 都存在于页面', missing.length === 0, missing.length ? '缺失 ' + missing.join(',') : wordIdsAll.join(','));
chk('8d lead 段指向字卡容器（用 querySelectorAll 取卡）', html.includes("querySelectorAll('.zi')"));

/* 9. 图片 src 与实际文件一致 */
const srcs = [...html.matchAll(/<img src="([^"]+)"/g)].map(m => m[1]);
const badImg = srcs.filter(s => !fs.existsSync(path.join(dir, s)));
chk('9  图片 src 与文件一致（共 ' + srcs.length + ' 张）', badImg.length === 0,
  badImg.length ? '缺失 ' + badImg.join(', ') : srcs.map(s => s.split('/').pop()).join(' / '));

/* 10. 控制条 */
['btnStep1', 'btnStep2', 'btnStep3', 'btnStep4', 'btnStep5', 'btnStop'].forEach((b, i) => {
  chk('10.' + (i + 1) + ' 控制条按钮 ' + b, html.includes('id="' + b + '"'));
});

/* 11. 朗读兜底 */
chk('11a speak() 含 watchdog（__wd）', html.includes('function __wd()'));
chk('11b 未残留旧固定兜底 Math.min(2500+text.length*260,16000)',
  !html.includes('Math.min(2500+text.length*260, 16000)') && !html.includes('Math.min(2500+text.length*260,16000)'));
chk('11c 有文本安全清洗 __safeText', html.includes('__safeText'));
chk('11d wait() 可被「停止」打断（检查 abort）', /function wait\(ms,[\s\S]{0,200}abort/.test(html));

/* 12. 语文特有 */
const rubyCount = (html.match(/<ruby>/g) || []).length;
chk('12a 课文含 ruby 注音（' + rubyCount + ' 处）', rubyCount > 0);
chk('12b 注音开关（no-py）存在', html.includes('no-py') && html.includes('btnPy'));
const pinyinInSay = /data-say="[^"]*[a-z]{1,6}[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]/.test(html);
chk('12c 朗读文本里没有拼音字母（TTS 会读成英文字母）', !pinyinInSay);
chk('12d 版权与出处说明（教材图片）', html.includes('版权归人民教育出版社所有'));
chk('12e 部首笔画/书写提示已标注「供参考」', html.includes('供参考'));

/* 13. 页面脚本语法 */
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
const tmp = path.join(require('os').tmpdir(), '_chk_cn_' + Date.now() + '.js');
fs.writeFileSync(tmp, scripts, 'utf8');
let synOk = true, synMsg = '';
try { execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' }); }
catch (e) { synOk = false; synMsg = String(e.stderr || e.message).split('\n').slice(0, 3).join(' '); }
try { fs.unlinkSync(tmp); } catch (e) {}
chk('13 页面脚本语法（node --check）', synOk, synMsg);

/* 14. 句级点读（二版核心） */
const sentCount = (html.match(/<span class="sent"/g) || []).length;
const sentWithSay = (html.match(/<span class="sent" data-say="/g) || []).length;
chk('14a 课文已拆到句（.sent ' + sentCount + ' 个）', sentCount > paras.length, sentCount + ' 句 / ' + paras.length + ' 段');
chk('14b 每句都有 data-say', sentWithSay === sentCount, sentWithSay + '/' + sentCount);
chk('14c 句 id 由 stepsRead 顺序分配（脚本中 s1…sN）', /sents\[i\]\.id\s*=\s*stepsRead\[i\]\.id/.test(html));
chk('14d 段前序号可点（读整段）', (html.match(/class="no"/g) || []).length >= paras.length);
const tipCount = (html.match(/data-tip="/g) || []).length;
chk('14e 关键句带朗读提示（' + tipCount + ' 处）', tipCount >= 4);

/* 15. 跟读模式 */
chk('15a 跟读等待函数 followWait', html.includes('function followWait'));
chk('15b 跟读开关按钮 btnFollow', html.includes('id="btnFollow"') && html.includes('var follow='));
chk('15c 跟读时间按句长计算（3~8 秒）', /Math\.min\(8,\s*Math\.max\(3/.test(html));

/* 16. 听写（二版新增） */
const dictArr = html.match(/var dictWords=\[([\s\S]*?)\];/);
const dictItems = dictArr ? (dictArr[1].match(/\{w:'/g) || []).length : 0;
const wcCards = (html.match(/<div class="wc" id="wc\d+"/g) || []).length;
const wcSay = (html.match(/class="w-say" data-say="/g) || []).length;
chk('16a 听写词表条数 = ' + EXP.dict, dictItems === EXP.dict, '实际 ' + dictItems);
chk('16b 词语卡数量 = 听写词数', wcCards === EXP.dict, wcCards + '/' + EXP.dict);
chk('16c 每张词语卡都有示范句', wcSay === wcCards, wcSay + '/' + wcCards);
chk('16d 听写读两遍后再给答案（流程含 6000ms 书写等待）', /wait\(6000/.test(html) && /dictSkip/.test(html));
chk('16e 听写三个按钮（开始/再读/看答案）', ['btnDictStart', 'btnDictAgain', 'btnDictShow'].every(b => html.includes('id="' + b + '"')));

/* 17. 近义词辨析 */
const nearCount = (html.match(/<div class="near" id="n\d+"/g) || []).length;
const nearSame = (html.match(/class="n-same"/g) || []).length;
const nearDiff = (html.match(/class="n-diff"/g) || []).length;
const nearEg = (html.match(/class="n-eg"/g) || []).length;
chk('17a 近义词组数 = ' + EXP.near, nearCount === EXP.near, '实际 ' + nearCount);
chk('17b 每组都有 相同点 / 不一样 / 造句', nearSame === nearCount && nearDiff === nearCount && nearEg === nearCount,
  nearSame + '/' + nearDiff + '/' + nearEg);

/* 18. 开放题标注 */
const openBlocks = [...html.matchAll(/<div class="qa"[\s\S]*?<\/div>\s*<\/div>/g)].map(m => m[0]);
const yOrT = openBlocks.filter(b => /lv-pill lv-(y|t)/.test(b));
const openMarked = yOrT.filter(b => b.includes('答案不唯一')).length;
chk('18 运用/拓展题标注「答案不唯一」（' + openMarked + '/' + yOrT.length + '）', yOrT.length > 0 && openMarked >= Math.ceil(yOrT.length / 2));

/* 19. 分角色朗读 */
const roles = (html.match(/<div class="role" id="r\d+"/g) || []).length;
const roleLines = (html.match(/data-lines="/g) || []).length;
chk('19a 角色卡数量（' + roles + ' 个）', roles >= 4);
chk('19b 每个角色都有台词 data-lines', roleLines === roles, roleLines + '/' + roles);

/* 20. 朗读要求卡 */
chk('20 朗读要求卡（req1）存在且可读', /id="req1"[^>]*data-say="[^"]{20,}"/.test(html) || /data-say="[^"]{20,}"[^>]*id="req1"/.test(html));

/* 21. 单题点击链路（askQA）：abort 打断后必须复位
      2026-11-01 数学侧实测缺陷（点单题没想一想/不展开/不出声），语文是同源代码 */
const askBlk = (html.match(/function askQA\([\s\S]*?\n\}/) || [''])[0];
if (!askBlk) { console.log('SKIP 21 单题点击链路（该页无 askQA）'); }
else {
  chk('21a askQA 中 abort 已复位（否则单题点击静默中断）', /abort\s*=\s*false/.test(askBlk));
  chk('21b askQA 含「想一想」与朗读答案', /think\(/.test(askBlk) && /data-ans/.test(askBlk));
  chk('21c speak 有 cancel→延迟保护（否则点了不出声）',
      /RA-SPEAK-DELAY/.test(html) || /setTimeout\([\s\S]{0,60}synth\.speak\(u\)/.test(html));
}

console.log('\n结果：' + pass + ' 项通过 / ' + fail + ' 项失败  →  ' + (fail === 0 ? '全部通过 ✅' : '存在 FAIL，请修正 ❌') + '\n');
process.exit(fail === 0 ? 0 : 1);
