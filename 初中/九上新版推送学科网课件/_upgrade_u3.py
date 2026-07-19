# -*- coding: utf-8 -*-
"""U3-8 / U3-9 升级改造：1)挑战四地图标注→因果链拼图 2)模块三教材栏目解答加内容 3)模块四课堂训练补为10选+2材+2问
按文件传参，执行单课。"""
import re, sys, shutil, os

PAGE_PAT = re.compile(r'<!--\s*(?:=*\s*)?PAGE\s*(\d+)\s*[:：]?\s*([^=<>]{2,80}?)\s*=?=*\s*-->', re.I)
TAG_PAT = re.compile(r'<div\b|</div>')
CSS_INSERT = """
.q-group-title { font-size: 15pt; font-weight: 700; color: var(--primary-dark);
  margin: 24px 0 12px; padding-left: 12px; border-left: 4px solid var(--primary); }
"""

# ===== 复用片段（来自已改好的第1课） =====
CAUSAL_JS = '''function causalPick(btn) {
  var chain = btn.closest('.causal-chain');
  if (!chain || chain.classList.contains('solved')) return;
  if (btn.classList.contains('picked')) return;
  if (!chain._picks) chain._picks = [];
  if (chain._picks.length >= 3) return;
  chain._picks.push(btn);
  var n = chain._picks.length;
  btn.classList.add('picked');
  btn.querySelector('.causal-seq').textContent = n;
  if (n === 3) {
    var ok = true;
    for (var i = 0; i < 3; i++) {
      if (parseInt(chain._picks[i].getAttribute('data-correct'), 10) !== i) { ok = false; break; }
    }
    var fb = chain.querySelector('.causal-feedback');
    if (ok) {
      chain.classList.add('solved');
      chain.querySelectorAll('.causal-piece').forEach(function(p){ p.classList.remove('picked'); p.classList.add('correct'); });
      if (fb) fb.textContent = '✅ 这条因果链顺序正确！';
      checkAllCausal();
    } else {
      chain.classList.add('wrong');
      if (fb) fb.textContent = '❌ 顺序不对，再想想因果逻辑～';
      setTimeout(function(){
        chain.classList.remove('wrong');
        chain._picks = [];
        chain.querySelectorAll('.causal-piece').forEach(function(p){
          p.classList.remove('picked');
          var s = p.querySelector('.causal-seq'); if (s) s.textContent = '';
        });
        if (fb) fb.textContent = '';
      }, 1000);
    }
  }
}

function checkAllCausal() {
  var chains = document.querySelectorAll('#causalZone .causal-chain');
  var all = true;
  chains.forEach(function(c){ if (!c.classList.contains('solved')) all = false; });
  if (all) {
    stageDone.causal = true;
    var el = document.getElementById('stageCausalDone');
    if (el) el.classList.add('show');
    updateStageProgress();
  }
}
'''

CAUSAL_CSS = """
.causal-zone{background:#f0edff;border-radius:10px;padding:14px;margin-bottom:8px;}
.causal-instruction{font-size:12pt;color:#5a4ac7;margin-bottom:12px;line-height:1.5;}
.causal-chain{background:#fff;border-radius:10px;padding:12px;margin:10px 0;box-shadow:0 1px 4px rgba(124,108,240,.15);}
.causal-chain-title{font-weight:700;color:#4a3aa8;margin-bottom:8px;font-size:13pt;}
.causal-pieces{display:flex;flex-wrap:wrap;gap:10px;}
.causal-piece{position:relative;display:flex;align-items:center;gap:6px;background:#fff;border:2px solid #c9bff0;border-radius:10px;padding:10px 14px;font-size:12pt;cursor:pointer;transition:.15s;font-family:inherit;color:#333;line-height:1.3;}
.causal-piece:hover{border-color:#7c6cf0;background:#f5f2ff;}
.causal-piece.picked{border-color:#7c6cf0;background:#ece7ff;}
.causal-piece.correct{border-color:#27ae60;background:#e8f8ef;color:#1e7e45;}
.causal-piece.wrong{border-color:#e74c3c;background:#fdecea;animation:shake .4s;}
.causal-seq{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:#7c6cf0;color:#fff;font-size:11pt;font-weight:700;flex:0 0 auto;}
.causal-piece.correct .causal-seq{background:#27ae60;}
.causal-feedback{margin-top:8px;font-size:12pt;font-weight:700;min-height:18px;}
.causal-chain.solved .causal-feedback{color:#27ae60;}
.causal-chain.wrong .causal-feedback{color:#e74c3c;}
"""


def causal_block(chains):
    """chains: [(title, [(label, correct_index), ...打乱显示顺序]), ...]"""
    parts = ['<div class="challenge-title">🎮 挑战四：将每条因果链的三块拼图按正确顺序排列（①→②→③）</div>',
             '<div class="causal-zone" id="causalZone">',
             '      <div class="causal-instruction">💡 点击下方拼图块，按因果关系排出正确顺序 ①→②→③。排对一条即点亮该链，全部排对即通关。</div>']
    for idx, (title, pieces) in enumerate(chains, 1):
        parts.append('      <div class="causal-chain" data-chain="%d">' % idx)
        parts.append('        <div class="causal-chain-title">因果链%d：%s</div>' % (idx, title))
        parts.append('        <div class="causal-pieces">')
        for (label, ci) in pieces:
            parts.append('          <button class="causal-piece" data-correct="%d" onclick="causalPick(this)"><b class="causal-seq"></b><span class="causal-label">%s</span></button>' % (ci, label))
        parts.append('        </div>')
        parts.append('        <div class="causal-feedback"></div>')
        parts.append('      </div>')
    parts.append('      </div>')
    parts.append('<div class="stage-done" id="stageCausalDone">🎉 第④关通过！</div>')
    return "\n".join(parts)


def choice_block(num, qtext, opts, correct, analysis):
    A, B, C, D = opts
    return (
        '<div class="exercise" id="q%d">\n'
        '    <div class="q-text"><strong>%d.</strong> %s</div>\n'
        '    <div class="options">\n'
        '      <label onclick="optClick(this,\'A\',\'q%d\',\'%s\')">A. %s</label>\n'
        '      <label onclick="optClick(this,\'B\',\'q%d\',\'%s\')">B. %s</label>\n'
        '      <label onclick="optClick(this,\'C\',\'q%d\',\'%s\')">C. %s</label>\n'
        '      <label onclick="optClick(this,\'D\',\'q%d\',\'%s\')">D. %s</label>\n'
        '    </div>\n'
        '    <div class="analysis" id="analysis-q%d">\n'
        '      <strong>📖 答案分析：</strong>\n'
        '      <p>正确答案：<span class="correct-answer">%s</span></p>\n'
        '      <p><strong>解析：</strong>%s</p>\n'
        '    </div>\n'
        '  </div>\n'
    ) % (num, num, qtext, num, A, A, num, B, B, num, C, C, num, D, D, num, correct, analysis)


def essay_block(num, qtext, answer):
    return (
        '<div class="exercise" id="sq%d">\n'
        '    <div class="q-text"><strong>简答题%d</strong> %s</div>\n'
        '    <div class="a" id="ans-p4-sq%d">\n'
        '      <p><strong>参考答案：</strong>%s</p>\n'
        '    </div>\n'
        '    <button class="ans-btn" onclick="toggleAnswer(\'ans-p4-sq%d\')">📝 查看答案</button>\n'
        '  </div>\n'
    ) % (num, num, qtext, num, answer, num)


def extract_exercises(block):
    opens = list(re.finditer(r'<div class="exercise" id="(\w+)">', block))
    res = []
    for m in opens:
        depth = 0
        for mm in TAG_PAT.finditer(block, m.start()):
            depth += 1 if mm.group(0).startswith('<div') else -1
            if depth == 0:
                res.append((m.group(1), block[m.start():mm.end()])); break
    return res


def type_of(eid):
    if eid.startswith("mq"): return "mq"
    if eid.startswith("sq"): return "sq"
    return "q"


def reorder_page4(t):
    pages = list(PAGE_PAT.finditer(t))
    p4 = None
    for i, p in enumerate(pages):
        if p.group(1) == "4":
            s = p.start(); e = pages[i + 1].start() if i + 1 < len(pages) else len(t)
            p4 = (s, e); break
    s, e = p4
    block = t[s:e]
    exs = extract_exercises(block)
    groups = {"q": [], "mq": [], "sq": []}
    for eid, html in exs:
        groups[type_of(eid)].append(html)
    first_start = block.find(exs[0][1])
    last_html = exs[-1][1]
    last_start = block.rfind(last_html)
    last_end = last_start + len(last_html)
    prefix = block[:first_start]
    suffix = block[last_end:]
    new_body = prefix
    for ty, head in (("q", '<div class="q-group-title">一、选择题</div>'),
                     ("mq", '<div class="q-group-title">二、材料题</div>'),
                     ("sq", '<div class="q-group-title">三、问答题</div>')):
        items = groups[ty]
        if not items: continue
        new_body += head + "\n" + "".join(items)
    new_body += suffix
    return t[:s] + new_body + t[e:]


def page_region(t, num):
    pages = list(PAGE_PAT.finditer(t))
    for i, p in enumerate(pages):
        if p.group(1) == num:
            s = p.start(); e = pages[i + 1].start() if i + 1 < len(pages) else len(t)
            return t[s:e], s, e
    return None, None, None


# ======================= 单课内容定义 =======================
def lesson_content(fname):
    if "第8课" in fname:
        # 挑战四：西欧城市与大学 因果链
        chains = [
            ("城市兴起与市民阶层", [
                ("手工业、商业发展，城市重新兴起", 1),
                ("农业技术进步，剩余产品增多", 0),
                ("市民阶层形成，城市争取自治", 2),
            ]),
            ("早期大学的产生", [
                ("大学兴起（巴黎、牛津、博洛尼亚）", 2),
                ("城市经济繁荣，世俗文化需求增长", 0),
                ("教会学校不足，学者聚集自由讲学", 1),
            ]),
            ("大学自治与影响", [
                ("大学获得自治权与教学自主权", 1),
                ("学术自由，欧洲文化教育发展", 2),
                ("国王或教皇颁发特许状", 0),
            ]),
        ]
        # 新选择题 q6-q10
        new_choices = [
            (6, "西欧城市重新兴起的主要经济原因是（  ）",
             ["农业发展，剩余产品增多", "教会鼓励经商", "阿拉伯人入侵", "罗马帝国复兴"], "A",
             "从10世纪起，西欧农业技术提高，剩余产品增多，手工业和商业发展，促使旧城复苏、新城产生。"),
            (7, "西欧中世纪城市的基本居民不包括（  ）",
             ["手工业者", "商人", "银行家", "封建领主"], "D",
             "城市基本居民是手工业者、商人和银行家（早期资产阶级）；封建领主是封建主，不住在城市、不属市民阶层。"),
            (8, "城市居民争取自治的常用手段是（  ）",
             ["金钱赎买和武力斗争", "宗教改革", "对外殖民扩张", "发动农民起义"], "A",
             "市民常通过金钱赎买自治权，赎买不成则举行武装起义（如琅城起义）来争取自由与自治。"),
            (9, "欧洲早期大学普遍兴起于（  ）",
             ["8世纪", "10世纪", "12世纪", "15世纪"], "C",
             "11—12世纪，随着城市繁荣，巴黎大学、牛津大学、博洛尼亚大学等早期大学相继兴起。"),
            (10, "大学获得自治地位的主要标志是（  ）",
             ["国王或教皇颁发特许状", "城市商业繁荣", "学者人数众多", "教会允许传教"], "A",
             "国王或教皇颁发特许状，承认大学自治权和教学自主权，是大学获得自治地位的主要标志。"),
        ]
        # 新问答题 sq1-sq2
        new_essays = [
            (1, "简述西欧城市兴起的历史意义。",
             "①经济上：城市是手工业、商业中心，促进商品经济发展；②政治上：市民阶层壮大，城市自治削弱了封建割据；③文化上：推动大学产生，为近代文明奠基。"),
            (2, "简述西欧早期大学兴起的背景。",
             "①城市繁荣使对世俗文化、专业知识的需求增长；②教会学校不能满足需要，学者在城市自由讲学；③国王和教皇为争取支持，颁发特许状，大学获得自治权。巴黎大学、牛津大学、博洛尼亚大学是代表。"),
        ]
        # 模块三新增 3 个栏目（凑足标题所说的“7大栏目”）
        mod3_add = [
            '''  <div class="col-box" data-cat="相关史事">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📖 相关史事：城市中的行会（基尔特）</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>中世纪城市里，手工业者和商人分别组成行会（基尔特）。行会制定规章，规定生产规模、产品质量、劳动时间、学徒期限等，维护同行利益，也限制了自由竞争。如伦敦马刺业基尔特规定学徒须学满七年，禁止夜间工作、宗教节日停业。行会既是经济组织，也承担互助、宗教、治安等城市自治职能。</p>
      <div class="a" id="ans-p3-guild">
        <strong>📝 要点归纳：</strong><br>
        • <strong>性质：</strong>手工业者、商人同业团体<br>
        • <strong>职能：</strong>规范生产、维护权益、限制竞争<br>
        • <strong>自治：</strong>参与城市管理与互助<br>
        • <strong>学徒制：</strong>一般不少于七年
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-guild')">📝 查看要点归纳</button>
    </div>
  </div>''',
            '''  <div class="col-box" data-cat="知识拓展">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📚 知识拓展：“城市的空气使人自由”</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>西欧中世纪流行一句谚语：“城市的空气使人自由”（Stadtluft macht frei）。按照惯例，农奴逃到城市并居住满一年零一天，即可获得自由人身份，领主不得再追捕。许多农奴因此涌入城市，城市成为摆脱封建人身依附的避难所，也为城市发展提供了自由劳动力。这反映了城市与封建庄园在人身关系上的对立。</p>
      <div class="a" id="ans-p3-air">
        <strong>📝 要点归纳：</strong><br>
        • <strong>含义：</strong>农奴居城满一年零一日即获自由<br>
        • <strong>作用：</strong>吸引逃亡农奴，提供自由劳动力<br>
        • <strong>本质：</strong>城市与庄园人身依附关系的对立
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-air')">📝 查看要点归纳</button>
    </div>
  </div>''',
            '''  <div class="col-box" data-cat="课后活动">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📝 课后活动：比较巴黎大学与博洛尼亚大学的管理模式</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>早期大学的管理模式有所不同。意大利北部的博洛尼亚大学以学生社团（同乡会）为基础建立，学生掌握管理权，负责任免教师、监督教学；巴黎大学则以教师行会为核心，教师主导学校事务。两者都通过国王或教皇颁发的特许状获得自治权与教学自主权。</p>
      <div class="a" id="ans-p3-cmp">
        <strong>📝 参考答案：</strong><br>
        • <strong>博洛尼亚大学：</strong>学生主导，学生行会掌握管理权<br>
        • <strong>巴黎大学：</strong>教师主导，教师行会管理学院<br>
        • <strong>共同点：</strong>均凭特许状获得自治与教学自主
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-cmp')">📝 查看答案</button>
    </div>
  </div>''',
        ]
        return chains, new_choices, new_essays, mod3_add
    else:  # 第9课 拜占庭帝国
        chains = [
            ("拜占庭帝国的延续", [
                ("拜占庭（东罗马）帝国延续", 1),
                ("罗马帝国分裂，西罗马灭亡", 0),
                ("保存古典文化，沟通东西文明", 2),
            ]),
            ("《查士丁尼法典》的编撰", [
                ("罗马法体系完备，影响后世", 2),
                ("查士丁尼即位，立志复兴罗马", 0),
                ("编撰《查士丁尼法典》等", 1),
            ]),
            ("拜占庭帝国的灭亡", [
                ("15世纪奥斯曼土耳其兴起扩张", 0),
                ("拜占庭军事、经济衰落", 1),
                ("1453年君士坦丁堡陷落，帝国灭亡", 2),
            ]),
        ]
        new_choices = [
            (6, "拜占庭帝国是指（  ）",
             ["西罗马帝国", "东罗马帝国", "亚历山大帝国", "阿拉伯帝国"], "B",
             "拜占庭帝国即东罗马帝国，定都君士坦丁堡（原名拜占庭），在西罗马灭亡后延续千年。"),
            (7, "《查士丁尼法典》编撰于（  ）",
             ["公元前5世纪", "2世纪", "6世纪", "9世纪"], "C",
             "查士丁尼在位时（6世纪）组织编撰《查士丁尼法典》，后与其三部法律合称《罗马民法大全》。"),
            (8, "《罗马民法大全》不包括（  ）",
             ["《查士丁尼法典》", "《法学汇纂》", "《法理概要》", "《十二铜表法》"], "D",
             "《罗马民法大全》含《查士丁尼法典》《法学汇纂》《法理概要》《新法典》；《十二铜表法》是古罗马共和国早期法律。"),
            (9, "拜占庭帝国灭亡于（  ）",
             ["1258年", "1453年", "1500年", "1606年"], "B",
             "1453年，奥斯曼土耳其攻陷君士坦丁堡，拜占庭帝国灭亡。"),
            (10, "拜占庭文化对后世的重要贡献是（  ）",
             ["保存并传播古希腊罗马文化", "创立伊斯兰教", "发明活字印刷", "开辟新航路"], "A",
             "拜占庭帝国保存了大量古希腊罗马文化，并对东欧、俄罗斯及文艺复兴产生重要影响。"),
        ]
        new_essays = [
            (1, "简述《罗马民法大全》的历史地位。",
             "它是古罗马法律体系的系统总结，标志着罗马法体系完备；巩固了君主专制，维护了奴隶主利益；对后世欧美国家的立法和司法产生了深远影响。"),
            (2, "简述拜占庭帝国灭亡的原因。",
             "①外部：奥斯曼土耳其兴起并不断扩张；②内部：军事力量削弱、经济衰落、领土不断缩小；③1453年君士坦丁堡陷落，帝国终结。其文化遗产由意大利等西欧地区继承，助推文艺复兴。"),
        ]
        mod3_add = [
            '''  <div class="col-box" data-cat="相关史事">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📖 相关史事：圣索菲亚大教堂</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>查士丁尼时期兴建的圣索菲亚大教堂，是拜占庭建筑艺术的杰作。它气势宏伟，以巨大的穹顶著称，内部装饰着精美的镶嵌画，集中体现了拜占庭帝国强盛时期的国力与东西方文化交融的特色。1453年君士坦丁堡陷落后，教堂被改为清真寺。</p>
      <div class="a" id="ans-p3-hagia">
        <strong>📝 要点归纳：</strong><br>
        • <strong>时期：</strong>查士丁尼统治时期兴建<br>
        • <strong>特色：</strong>巨大穹顶、镶嵌画、东西交融<br>
        • <strong>命运：</strong>1453年后改为清真寺
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-hagia')">📝 查看要点归纳</button>
    </div>
  </div>''',
            '''  <div class="col-box" data-cat="知识拓展">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📚 知识拓展：拜占庭文化对东欧与文艺复兴的影响</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>拜占庭帝国保存了大量古希腊罗马的文化典籍，其宗教、艺术、法律深刻影响了东欧斯拉夫世界（如俄罗斯）。帝国灭亡前后，许多学者携带古希腊文献流亡意大利，为文艺复兴提供了重要的古典文化养料。拜占庭因此是沟通古代希腊罗马文明与近代欧洲文明的桥梁。</p>
      <div class="a" id="ans-p3-infl">
        <strong>📝 要点归纳：</strong><br>
        • <strong>保存：</strong>古希腊罗马典籍与文化<br>
        • <strong>东传：</strong>影响东欧斯拉夫世界<br>
        • <strong>西渐：</strong>学者携文献赴意大利，助推文艺复兴<br>
        • <strong>定位：</strong>古代与近代文明的桥梁
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-infl')">📝 查看要点归纳</button>
    </div>
  </div>''',
            '''  <div class="col-box" data-cat="课后活动">
    <div class="col-header" onclick="toggleColBox(this)">
      <span>📝 课后活动：拜占庭帝国为何能延续千年？</span>
      <span class="col-toggle">▼</span>
    </div>
    <div class="col-body">
      <p>西罗马帝国在5世纪灭亡，而拜占庭帝国却延续到15世纪。其原因包括：地处欧亚交界，商业繁荣、经济相对稳固；君权与教会结合，统治较稳固；查士丁尼等君主武力扩张、编撰法典，一度重振国势；地理位置有利于吸收东西方文明成果。</p>
      <div class="a" id="ans-p3-last">
        <strong>📝 参考答案：</strong><br>
        • <strong>经济：</strong>商业枢纽，财政较充实<br>
        • <strong>政治：</strong>中央集权，政教结合<br>
        • <strong>军事法律：</strong>查士丁尼法典与扩张<br>
        • <strong>地理：</strong>扼守东西通道，兼收文明成果
      </div>
      <button class="ans-btn" onclick="toggleAnswer('ans-p3-last')">📝 查看答案</button>
    </div>
  </div>''',
        ]
        return chains, new_choices, new_essays, mod3_add


def upgrade(fname):
    t = open(fname, encoding="utf-8").read()
    chains, new_choices, new_essays, mod3_add = lesson_content(fname)

    # ---------- 1) 挑战四 地图→因果链 ----------
    # HTML 替换：从 挑战四标题(地图) 到 stageMapDone 横幅
    m = re.search(r'<div class="challenge-title">🎮 挑战四：点击地图标注[\s\S]*?<div class="stage-done" id="stageMapDone">🎉 第④关通过！</div>', t)
    if not m:
        raise RuntimeError("未找到挑战四地图块: " + fname)
    t = t[:m.start()] + causal_block(chains) + t[m.end():]
    # CSS 注入
    if ".causal-zone" not in t:
        si = t.find("</style>")
        t = t[:si] + CAUSAL_CSS + t[si:]
    if ".q-group-title" not in t:
        si = t.find("</style>")
        t = t[:si] + CSS_INSERT + t[si:]
    # JS 替换
    t = t.replace("map:false", "causal:false")
    t = t.replace("'map'", "'causal'")
    t = t.replace("stageDone.map", "stageDone.causal")
    t = t.replace("stageMapDone", "stageCausalDone")
    # initMapMarkers 函数/IIFE → causalPick + checkAllCausal
    idx = t.find("function initMapMarkers")
    if idx < 0:
        raise RuntimeError("未找到 initMapMarkers: " + fname)
    p = idx
    while p > 0 and t[p - 1] == '(':  # 包含前导 '(' (IIFE)
        p -= 1
    j = t.find("{", idx)
    depth = 0; end = j
    for k in range(j, len(t)):
        if t[k] == "{": depth += 1
        elif t[k] == "}":
            depth -= 1
            if depth == 0: end = k + 1; break
    # 消费函数后的 )(); （IIFE 形式：函数 } 之后紧跟 )();，可能含空白）
    k2 = end
    while k2 < len(t) and t[k2] in " \n\t\r":
        k2 += 1
    if k2 < len(t) and t[k2] == '}':   # 越过函数自身的闭合 }
        k2 += 1
        while k2 < len(t) and t[k2] in " \n\t\r":
            k2 += 1
    end2 = k2 + 4 if t[k2:k2 + 4] == ")();" else end
    t = t[:p] + CAUSAL_JS + t[end2:]

    # ---------- 2) 模块三 加内容 ----------
    m3, s3, e3 = page_region(t, "3")
    if not m3:
        raise RuntimeError("未找到 PAGE3: " + fname)
    # 在 page3 内最后一个 col-box 之后、page3 结束 </div> 之前插入
    # 找 page3 内最后一个 col-box 的结束位置
    boxes = list(re.finditer(r'<div class="col-box"', m3))
    last_box_start = boxes[-1].start()
    depth = 0; be = None
    for mm in TAG_PAT.finditer(m3, last_box_start):
        depth += 1 if mm.group(0).startswith("<div") else -1
        if depth == 0: be = mm.end(); break
    inserted = "\n".join(mod3_add) + "\n"
    new_m3 = m3[:be] + inserted + m3[be:]
    t = t[:s3] + new_m3 + t[e3:]

    # ---------- 3) 模块四 补题 + 重排 ----------
    m4, s4, e4 = page_region(t, "4")
    if not m4:
        raise RuntimeError("未找到 PAGE4: " + fname)
    # 现有练习
    exs = extract_exercises(m4)
    last_html = exs[-1][1]
    last_start = m4.rfind(last_html)
    last_end = last_start + len(last_html)
    new_blocks = "".join(choice_block(*c) for c in new_choices)
    new_blocks += "".join(essay_block(*es) for es in new_essays)
    new_m4 = m4[:last_end] + new_blocks + m4[last_end:]
    t = t[:s4] + new_m4 + t[e4:]
    # correctAnswers 追加 q6-q10（兼容 '...};' 与 '...},mcDone=...' 两种写法）
    mm = re.search(r'var correctAnswers\s*=\s*\{', t)
    if mm:
        start = mm.end()                      # '{' 之后
        end = t.find("}", start)              # 匹配的右大括号（本对象无嵌套）
        body = t[start:end].rstrip().rstrip(",")
        add = ""
        for c in new_choices:
            add += ", q%d:'%s'" % (c[0], c[3])  # 元组 (num,qtext,opts,correct,analysis) -> 索引3=correct
        new_body = body + add
        t = t[:start] + new_body + t[end:]
    # 重排 page4 按题型
    t = reorder_page4(t)
    open(fname, "w", encoding="utf-8").write(t)


if __name__ == "__main__":
    os.chdir("E:/WorkBuddy生成内容/下载")
    target = sys.argv[1] if len(sys.argv) > 1 else "九上-U3-第8课_西欧的城市和大学.html"
    shutil.copy2(target, "_backup_u3_" + os.path.basename(target))
    upgrade(target)
    print("已升级:", target)
