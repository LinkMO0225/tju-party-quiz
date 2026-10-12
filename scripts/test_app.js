// 用 DOM stub 真实执行页面脚本，验证首页、卡片背诵、做题测验、错题强化
const fs = require('fs'), vm = require('vm'), path = require('path');
// 相对脚本位置定位产物，换机器/换目录名都能跑
const FILE = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(FILE, 'utf8');

const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
console.log('script 块数:', scripts.length, '(应为 4)');

let fail = 0;
const ok = (cond, label, extra) => {
  console.log((cond ? '  ✓ ' : '  ✗ ') + label + (extra !== undefined ? '  → ' + extra : ''));
  if (!cond) fail++;
};
const htmlesc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

function boot(preStore) {
  const store = Object.assign({}, preStore);
  const els = {};
  const mk = () => ({ innerHTML: '', textContent: '', style: {}, className: '',
    classList: { add() {}, remove() {} } });
  const document = {
    getElementById(id) { if (!els[id]) els[id] = mk(); return els[id]; },
    querySelector() { return mk(); },
    addEventListener() {},
  };
  const localStorage = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  };
  const ctx = { document, localStorage, console, Math, JSON, Date };
  vm.createContext(ctx);
  scripts.forEach(s => vm.runInContext(s, ctx));
  return { ctx, els, store };
}

/* 按「当前显示位置」作答：correct=true 选全部正确项，false 选全部错误项 */
function answer(ctx, BANK, correct) {
  const it = BANK[ctx.S.queue[ctx.S.pos]];
  const ds = [];
  for (let d = 0; d < 4; d++) {
    const isAns = it.a.indexOf('ABCD'[ctx.S.perm[d]]) >= 0;
    if (correct === isAns) ds.push(d);
  }
  ds.forEach(d => ctx.pick(d));
  ctx.submit();   // 单选（需确认）与多选都必须显式提交；已判分时 submit() 内部直接 return
}

const { ctx, els, store } = boot();
const BANK = ctx.BANK, CARDS = ctx.CARDS;

/* ---------------- 一、刷题题库 ---------------- */
console.log('\n=== 一、刷题题库（应已无填空题） ===');
ok(BANK.length === 579, '题库 579 道（旧 242 + 网上党课 337）', BANK.length);
ok(BANK.every(q => q.t !== 2), '题库里不存在填空题');
ok(BANK.filter(q => q.n === 1).length === 71, '第90期相关 71 道');
ok(BANK.filter(q => q.c === 2).length === 337, '网上党课 337 道');
ok(BANK.filter(q => q.c === 1).length === 171, '往期真题卷 171 道');
ok(BANK[242].c === 2 && BANK[241].c !== 2,
  '党课题目接在旧题库之后（前 242 道下标未位移，旧进度不串位）');
let bad = [];
BANK.forEach((q, i) => {
  if (!q.s || !q.a) bad.push([i, 'empty']);
  if (q.o.length !== 4 || q.o.some(x => !x)) bad.push([i, 'opts']);
  if (!/^[A-D]{1,4}$/.test(q.a)) bad.push([i, 'ansfmt']);
  if (q.t === 0 && q.a.length !== 1) bad.push([i, 'single-ans']);
  if (q.t === 1 && q.a.length < 2) bad.push([i, 'multi-ans']);
  // 选项内容重复会让乱序露馅；唯一豁免是平台原题就重复的题（数据里用 d=1 标记）
  if (new Set(q.o).size !== 4 && !q.d) bad.push([i, 'dup-opt']);
});
ok(bad.length === 0, '题干/选项/答案零异常（含选项不重复）', bad.slice(0, 5));
// 「统筹兼顾指（）」原留档里 A/C 选项文字相同，2026-10-10 已按平台最新题面修正
ok(BANK.filter(q => q.d === 1).length === 0,
  '选项重复题已消除（按平台最新题面修正后 0 道）', BANK.filter(q => q.d === 1).length);
const fixq = BANK.find(q => q.s.indexOf('统筹兼顾指') === 0);
ok(!!fixq, '题库中存在「统筹兼顾指（）」');
ok(fixq && new Set(fixq.o).size === 4, '该题四个选项已互不相同');
ok(fixq && fixq.o.indexOf('统筹国内发展与对外开放') >= 0, '该题已含「统筹国内发展与对外开放」');
ok(fixq && fixq.a === 'ABCD' && fixq.t === 1, '该题为多选且答案全选 ABCD');

/* ---------------- 一之二、范围筛选（新增网上党课） ---------------- */
console.log('\n=== 一之二、范围筛选 ===');
const sc2 = ctx.scopeCount();
ok(sc2.all === 579 && sc2.n90 === 71 && sc2.vol === 171 && sc2.party === 337,
  'scopeCount 三类来源分类正确', sc2);
ctx.setting.scope = 'party';
ok(ctx.buildQueue().length === 337, '范围=网上党课 → 337 题', ctx.buildQueue().length);
ok(ctx.buildQueue().every(i => BANK[i].c === 2), '筛选结果全部是党课题');
ctx.setting.scope = 'n90';
ok(ctx.buildQueue().length === 71, '范围=第90期相关 → 71 题', ctx.buildQueue().length);
ctx.setting.scope = 'vol';
ok(ctx.buildQueue().length === 171, '范围=往期真题卷 → 171 题', ctx.buildQueue().length);
ctx.setting.scope = 'all';
ok(ctx.buildQueue().length === 579, '范围=全部 → 579 题', ctx.buildQueue().length);

/* ---------------- 二、卡片数据 ---------------- */
console.log('\n=== 二、卡片数据 ===');
ok(CARDS.length === 87, '卡片总数 87', CARDS.length);
ok(CARDS.filter(c => c.n).length === 28, '第90期卡片 28');
let mism = [];
CARDS.forEach((c, i) => {
  const k = (c.s.match(/_{3,}/g) || []).length;
  if (k !== c.h.length || !c.a || !c.s) mism.push(i);
});
ok(mism.length === 0, '空位数 == 答案数（零失配）');
ok(CARDS.every(c => c.h.every(x => x && x.trim())), '所有答案片段非空');

/* ---------------- 三、首页 ---------------- */
console.log('\n=== 三、首页 ===');
ctx.home();
ok(els['app'].innerHTML.includes('卡片背诵') && els['app'].innerHTML.includes('做题测验'), '两个入口都在');
ok(els['app'].innerHTML.includes('单选 438') && els['app'].innerHTML.includes('多选 141'), '题数正确');
ctx.examHome();
ok(els['app'].innerHTML.includes('网上党课 337'), '测验首页出现「网上党课」范围筛选');
ok(els['app'].innerHTML.includes('第90期相关 71') && els['app'].innerHTML.includes('往期真题卷 171'),
  '其他范围筛选数字正确');
ok(els['app'].innerHTML.includes('含网上党课 337 道'), '测验首页副标题提到党课题量');

/* ---------------- 四、选项打乱（本次迭代重点 1） ---------------- */
console.log('\n=== 四、选项打乱 ===');
const iS = BANK.findIndex(q => q.t === 0);
const iM = BANK.findIndex(q => q.t === 1);
ctx.S.mode = 'exam'; ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
const itS = BANK[iS];
const seenPerm = new Set();
for (let i = 0; i < 60; i++) { ctx.render(); seenPerm.add(ctx.S.perm.join('')); }
ok(seenPerm.size >= 8, '同一道题反复进入，选项顺序会变（不是固定的）', seenPerm.size + ' 种排列');
ok([...seenPerm].every(p => [...p].sort().join('') === '0123'), '每种排列都是 0-3 的合法全排列');

ctx.render();
const shown = [...els['opts'].innerHTML.matchAll(/<span>([^<]*)<\/span>/g)].map(m => m[1]);
ok(shown.length === 4, '渲染出 4 个选项', shown.length);
ok(shown.join('|') === [0, 1, 2, 3].map(d => htmlesc(itS.o[ctx.S.perm[d]])).join('|'),
  '选项文本严格按 perm 顺序渲染');

const da = ctx.dispAns(itS);
ok(da.length === itS.a.length && da.split('').every(c => 'ABCD'.includes(c)),
  'dispAns 返回等长 A-D 字母', da + '（原答案 ' + itS.a + '）');
ok(da.split('').every(ch => itS.a.indexOf('ABCD'[ctx.S.perm['ABCD'.indexOf(ch)]]) >= 0),
  'dispAns 指向的显示位置确实都是正确项');

let judgeOk = 0;
for (let i = 0; i < 30; i++) {
  ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
  answer(ctx, BANK, true);
  if (ctx.prog[iS].ok === true) judgeOk++;
}
ok(judgeOk === 30, '打乱后按显示位置选正确答案，30/30 判对', judgeOk);
ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
answer(ctx, BANK, false);
ok(ctx.prog[iS].ok === false, '打乱后选错误项 → 判错');
ok(els['jd'].innerHTML.includes('正确答案：<b>' + ctx.dispAns(BANK[iS]) + '</b>'),
  '判分框「正确答案」用的是打乱后的字母，不是原始字母');

/* ---------------- 四之二、选项乱序开关 ---------------- */
console.log('\n=== 四之二、选项乱序开关 ===');
ctx.examHome();
ok(els['app'].innerHTML.includes('选项乱序：开'), '首页有「选项乱序」开关，默认开');
ok(els['app'].innerHTML.includes('题目随机：'), '首页有「题目随机」开关');
ok(els['app'].innerHTML.includes('关掉后，选项固定按 A B C D 原顺序显示'), '开关下方有说明');

ctx.S.mode = 'exam';
ctx.setting.shuffleOpt = 0;
let allFixed = true;
for (let i = 0; i < 25; i++) {
  ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
  if (ctx.S.perm.join('') !== '0123') allFixed = false;
}
ok(allFixed, '关掉后 25 次渲染，选项顺序恒为 0123');
ctx.render();
const shown2 = [...els['opts'].innerHTML.matchAll(/<span>([^<]*)<\/span>/g)].map(m => m[1]);
ok(shown2.join('|') === [0, 1, 2, 3].map(d => htmlesc(itS.o[d])).join('|'),
  '关掉后选项严格按原始 A/B/C/D 顺序显示');
ok(ctx.dispAns(itS) === itS.a, '关掉后 dispAns 就等于原始答案字母', ctx.dispAns(itS));
ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
answer(ctx, BANK, true);
ok(ctx.prog[iS].ok === true, '关掉乱序后判分依然正确（原下标即显示下标）');
ctx.S.queue = [iM]; ctx.S.pos = 0; ctx.render();
answer(ctx, BANK, true);
ok(ctx.prog[iM].ok === true, '关掉乱序后多选判分也正确');

ctx.togF('shuffleOpt');
ok(+ctx.setting.shuffleOpt === 1, '再点一下开关 → 重新打开');
ok(JSON.parse(store['tju_exam_setting_v1'] || '{}').shuffleOpt === 1, '开关状态已写入 localStorage');
ctx.togF('shuffleOpt');
ok(+ctx.setting.shuffleOpt === 0 && els['app'].innerHTML.includes('选项乱序：关'),
  '再点一下 → 关闭，且首页按钮文字同步变化');
ctx.togF('shuffleOpt');

// 新用户默认值
const b4 = boot();
ok(+b4.ctx.setting.shuffleOpt === 1, '没有历史设置时，默认开启选项乱序');
b4.ctx.S.mode = 'exam'; b4.ctx.S.queue = [0]; b4.ctx.S.pos = 0;
const varied2 = new Set();
for (let i = 0; i < 30; i++) { b4.ctx.S.queue = [0]; b4.ctx.S.pos = 0; b4.ctx.render(); varied2.add(b4.ctx.S.perm.join('')); }
ok(varied2.size >= 5, '默认状态确实在乱序', varied2.size + ' 种排列');

// 错题强化模式也遵守该开关
const eb7 = boot({ tju_exam_setting_v1: JSON.stringify({ shuffleOpt: 0 }) });
eb7.ctx.prog = {}; eb7.ctx.prog[9] = { p: 'A', ok: false, seen: 1 };
eb7.ctx.rStart();
ok(eb7.ctx.S.mode === 'reinforce' && eb7.ctx.S.perm.join('') === '0123',
  '错题强化模式同样遵守「选项乱序」开关');
const eb8 = boot();
eb8.ctx.prog = {}; eb8.ctx.prog[9] = { p: 'A', ok: false, seen: 1 };
let v3 = new Set();
eb8.ctx.rStart();
for (let i = 0; i < 20; i++) { eb8.ctx.render(); v3.add(eb8.ctx.S.perm.join('')); }
ok(v3.size >= 4, '默认（开）时强化模式也在乱序', v3.size + ' 种');

/* ---------------- 五、卡片背诵（可撤回重背） ---------------- */
console.log('\n=== 五、卡片背诵 ===');
ctx.reciteStart(0);
ok(ctx.R.queue.length === 28, '默认（第90期）28 张');
ctx.rsetF('scope', 'all'); ctx.reciteStart(0);
ok(ctx.R.queue.length === 87, '全部 87 张');

const ci = ctx.R.queue.find(i => CARDS[i].h.length >= 3);
ctx.R.queue = [ci, CARDS.findIndex((c, i) => i !== ci)]; ctx.R.pos = 0; ctx.reciteRender();
ok(els['cbody'].innerHTML.includes('class="blank"'), '初始为空格占位');
ctx.R.lock = 0; ctx.cardTap();
ok(ctx.R.revealed === true, '点一下 → 翻开答案');
ok(els['chint'].textContent.includes('收起'), '提示语提示可收起');
ctx.R.lock = 0; ctx.cardTap();
ok(ctx.R.revealed === false, '再点一下 → 收起答案（可重背）');
ok(els['cbody'].innerHTML.includes('class="blank"') && !els['cbody'].innerHTML.includes('class="fill"'),
  '收起后回到空格占位');
ok(!CARDS[ci].h.some(h => els['cbody'].innerHTML.includes(htmlesc(h))), '收起后答案文字已从页面移除');
ctx.R.lock = 0; ctx.cardTap();
ok(ctx.R.revealed === true, '第三次点击 → 再次翻开（反复重背）');
const rv = ctx.R.revealed; ctx.R.lock = Date.now() + 900; ctx.cardTap();
ok(ctx.R.revealed === rv, '250ms 内连点不重复翻转（防手抖）');
ctx.R.lock = 0;
const p0 = ctx.R.pos; ctx.cardNext();
ok(ctx.R.pos === p0 + 1, '「下一张」按钮翻页');
ok(ctx.R.revealed === false, '新卡片默认收起');
ctx.cardPrev(); ok(ctx.R.pos === p0, '「上一张」可回退');
ctx.rprog.m = {};
ctx.reciteStart(1);
ok(els['app'].innerHTML.includes('没有卡片'), '无标记时给出空态');

/* ---------------- 六、单选 / 多选 区分 ---------------- */
console.log('\n=== 六、单选 / 多选 区分 ===');
ctx.examHome();
ok(els['app'].innerHTML.includes('第90期相关'), '测验首页筛选器仍在');
ok(!els['app'].innerHTML.includes('>填空<'), '题型筛选没有「填空」');
ok(els['app'].innerHTML.includes('填空题已移到「卡片背诵」'), '页面注明填空已移走');

ctx.S.mode = 'exam'; ctx.S.queue = [iM]; ctx.S.pos = 0; ctx.render();
ok(els['app'].innerHTML.includes('ttag t1') && els['app'].innerHTML.includes('>多选题<'), '多选徽标');
ok(els['opts'].innerHTML.includes('mnotice') && els['opts'].innerHTML.includes('不止一个'), '多选提示条');
ok(els['opts'].innerHTML.indexOf('mnotice') < els['opts'].innerHTML.indexOf('opt'), '提示条在选项之前');
ok(els['foot'].innerHTML.includes('请先勾选答案'), '未勾选时提示先勾选');
ctx.pick(0);
ok(els['foot'].innerHTML.includes('已选 1 项'), '勾选后显示已选数量');
ctx.S.queue = [iM]; ctx.S.pos = 0; ctx.render();
answer(ctx, BANK, true);
ok(ctx.prog[iM].ok === true, '多选全选对 → 判对');
ok(els['jd'].innerHTML.includes('多选，共'), '判分框注明多选项数');
ctx.S.queue = [iM]; ctx.S.pos = 0; ctx.render();
answer(ctx, BANK, false);
ok(ctx.prog[iM].ok === false, '多选漏选/错选 → 判错');

ctx.S.queue = [iS]; ctx.S.pos = 0; ctx.render();
ok(els['app'].innerHTML.includes('ttag t0') && els['app'].innerHTML.includes('>单选题<'), '单选徽标');
ok(!els['opts'].innerHTML.includes('mnotice'), '单选题无多选提示条');
ok(els['foot'].innerHTML.includes('不会，看答案'), '单选按钮文案');

/* ---------------- 七、错题强化 · 无限刷（本次迭代重点 2） ---------------- */
console.log('\n=== 七、错题强化 ===');
const eb = boot();
eb.ctx.prog = {};
[10, 20, 30, 40].forEach(i => { eb.ctx.prog[i] = { p: 'A', ok: false, seen: 1 }; });
ok(eb.ctx.wrongCount() === 4, 'wrongCount 数出 4 道错题', eb.ctx.wrongCount());
eb.ctx.examHome();
ok(eb.els['app'].innerHTML.includes('错题强化 · 无限刷（当前范围 4 道错题）'), '测验首页出现强化入口');
ok(!eb.els['app'].innerHTML.includes('disabled'), '有错题时强化按钮可点（未禁用）');
eb.ctx.rStart();
ok(eb.ctx.S.mode === 'reinforce', '进入强化模式');
ok(eb.ctx.R2.pool.length === 4, '错题池 4 道', eb.ctx.R2.pool.length);
ok(eb.ctx.S.fromPool === true, '第一题直接上强化题');
ok(eb.els['app'].innerHTML.includes('rnotice') && eb.els['app'].innerHTML.includes('强化题'), '强化题显示蓝色标识');

// 隔离干扰：把错题从「普通题循环」里剔除，保证后面 3 个普通位不会撞上错题，
// 于是"池子减少量"只由强化位决定，断言才稳定。
// （普通位撞上错题也会出池的真实行为，由后面的 eb7 单独覆盖。）
eb.ctx.R2.norm = eb.ctx.R2.norm.filter(i => eb.ctx.R2.pool.indexOf(i) < 0);
eb.ctx.R2.np = 0;

const seq = [];
for (let i = 0; i < 5; i++) {
  seq.push(eb.ctx.S.fromPool);
  answer(eb.ctx, eb.ctx.BANK, true);
  if (eb.ctx.S.mode !== 'reinforce') break;
  eb.ctx.next();
}
ok(seq.join(',') === 'true,false,false,false,true',
  '节奏：强化 → 3 道正常 → 强化 → …', seq.map(x => x ? '强' : '常').join(' '));
ok(eb.ctx.R2.pool.length === 2, '答对 2 道强化题后池子从 4 减到 2', eb.ctx.R2.pool.length);
ok(eb.els['app'].innerHTML.includes('第 ' + (eb.ctx.S.pos + 1) + ' 题'),
  '强化模式顶栏显示「第 N 题」而非 x/y', '第 ' + (eb.ctx.S.pos + 1) + ' 题');
ok(eb.els['app'].innerHTML.includes('width:50%'), '进度条按攻克比例走（2/4=50%）');

// 强化题答错 → 留在池里
const eb2 = boot();
eb2.ctx.prog = {}; [7, 8].forEach(i => { eb2.ctx.prog[i] = { p: 'A', ok: false, seen: 1 }; });
eb2.ctx.rStart();
const firstP = eb2.ctx.S.queue[eb2.ctx.S.pos];
answer(eb2.ctx, eb2.ctx.BANK, false);
ok(eb2.ctx.R2.pool.indexOf(firstP) >= 0, '强化题答错 → 仍在错题池');
ok(eb2.ctx.R2.mastered === 0, 'mastered 不增加');
ok(eb2.els['jd'].innerHTML.includes('稍后会再来'), '判分框说明会再来');
ok(eb2.ctx.prog[firstP].ok === false, '错题记录仍是错');

// 普通题答错 → 进池
const eb3 = boot();
eb3.ctx.prog = {}; eb3.ctx.prog[100] = { p: 'A', ok: false, seen: 1 };
eb3.ctx.rStart();
const nidx = eb3.ctx.R2.base.find(i => !eb3.ctx.prog[i]);
const before = eb3.ctx.R2.pool.length;
eb3.ctx.S.mode = 'reinforce'; eb3.ctx.S.fromPool = false;
eb3.ctx.S.queue = [nidx]; eb3.ctx.S.pos = 0; eb3.ctx.render();
answer(eb3.ctx, eb3.ctx.BANK, false);
ok(eb3.ctx.R2.pool.length === before + 1, '普通题答错 → 自动加入错题池');
ok(eb3.els['jd'].innerHTML.includes('已加入错题池'), '判分框提示已进池');

// 全部答对 → 通关
const eb4 = boot();
eb4.ctx.prog = {}; [5, 6].forEach(i => { eb4.ctx.prog[i] = { p: 'A', ok: false, seen: 1 }; });
eb4.ctx.rStart();
let guard = 0;
while (eb4.ctx.S.mode === 'reinforce' && guard++ < 300) {
  answer(eb4.ctx, eb4.ctx.BANK, true);
  if (eb4.ctx.S.mode !== 'reinforce') break;
  eb4.ctx.next();
}
ok(eb4.ctx.R2.pool.length === 0, '错题全部答对后池子清空');
ok(eb4.els['app'].innerHTML.includes('错题全清了'), '出现通关页');
ok(eb4.ctx.R2.mastered === 2, '共攻克 2 道', eb4.ctx.R2.mastered);
ok(guard < 300, '有限步内收敛（不会无限循环）', guard + ' 步');

// 没有错题：入口常驻可见但置灰（可发现性优先，别再让用户找不到）
const eb5 = boot();
eb5.ctx.prog = {};
eb5.ctx.examHome();
const h5html = eb5.els['app'].innerHTML;
ok(h5html.includes('错题强化 · 无限刷'), '没错题时强化入口仍然常驻显示');
ok(h5html.includes('当前没有错题'), '没错题时按钮文案给出引导');
ok(h5html.includes('disabled'), '没错题时按钮置灰不可点');
eb5.ctx.rStart();
ok(eb5.els['app'].innerHTML.includes('还没有错题'), '没错题时给出空态而非白屏');

// 中途退出
const eb6 = boot();
eb6.ctx.prog = {}; [3, 4].forEach(i => { eb6.ctx.prog[i] = { p: 'A', ok: false, seen: 1 }; });
eb6.ctx.rStart();
eb6.ctx.exitReinforce();
ok(eb6.els['app'].innerHTML.includes('错题池还剩 2 道'), '退出页显示剩余错题');
ok(eb6.ctx.S.mode === 'exam', '退出后模式复位');

// 错题夹在「普通位」被抽到并答对 → 同样出池（真实行为，有意保留）
const ebp = boot();
ebp.ctx.prog = {}; [11, 12].forEach(i => { ebp.ctx.prog[i] = { p: 'A', ok: false, seen: 1 }; });
ebp.ctx.rStart();
const pit = ebp.ctx.R2.pool[0];
ebp.ctx.S.mode = 'reinforce'; ebp.ctx.S.fromPool = false;
ebp.ctx.S.queue = [pit]; ebp.ctx.S.pos = 0; ebp.ctx.render();
answer(ebp.ctx, ebp.ctx.BANK, true);
ok(ebp.ctx.R2.pool.indexOf(pit) < 0, '错题夹在普通位被答对 → 同样移出错题池');
ok(ebp.els['jd'].innerHTML.includes('已攻克'), '判分框提示已攻克');

/* ---------------- 八、旧版本残留兜底 ---------------- */
console.log('\n=== 八、旧 localStorage 兼容 ===');
const b2 = boot({ tju_exam_setting_v1: JSON.stringify({ type: '2', scope: 'all' }) });
ok(b2.ctx.setting.type === 'all', '旧的「填空」筛选(type=2)自动重置');
b2.ctx.setting.shuffle = 0;
ok(b2.ctx.buildQueue().length === 579, '重置后队列不为空', b2.ctx.buildQueue().length);
const b3 = boot({ tju_recite_v1: '{坏数据' });
ok(b3.ctx.rprog && b3.ctx.rprog.m && b3.ctx.rprog.s, '背诵进度损坏时回落为空');
b3.ctx.reciteStart(0);
ok(b3.ctx.R.queue.length === 28, '损坏数据下仍能开始背诵');

/* ---------------- 九、持久化 ---------------- */
console.log('\n=== 九、持久化 ===');
console.log('  localStorage 键:', Object.keys(store).sort().join(', '));
['tju_recite_v1', 'tju_recite_setting_v1', 'tju_exam_progress_v3'].forEach(k =>
  ok(Object.keys(store).includes(k), k + ' 已落盘'));

/* ---------------- 十、本次迭代修复（Q1 提示字母 / Q2 多选跳过 / Q3 单选确认） ---------------- */
console.log('\n=== 十、本次修复 ===');
const OFF = { scope: 'all', type: 'all', state: 'all', shuffle: 0, shuffleOpt: 0, confirmSingle: 0 };
const bootOff = () => boot({ tju_exam_setting_v1: JSON.stringify(OFF) });

// Q1：选项乱序后，判分框「你选的是」必须用屏幕字母（与「正确答案」同源）
const mi = BANK.findIndex(q => q.s.indexOf('孟良崮') >= 0);
ok(mi >= 0, 'Q1 定位到孟良崮那道题（真实案例）', mi);
{
  const q1 = bootOff();
  q1.ctx.S.mode = 'exam'; q1.ctx.S.queue = [mi]; q1.ctx.S.pos = 0; q1.ctx.render();
  q1.ctx.S.perm = [1, 0, 3, 2]; q1.ctx.paint();      // 复刻截图：屏幕 A陈毅 B刘伯承 C粟裕 D彭德怀
  q1.ctx.pick(0); q1.ctx.submit();                   // 只点屏幕上的陈毅（漏选粟裕）→ 判错
  const jd = q1.els['jd'].innerHTML;
  ok(q1.ctx.prog[mi].ok === false, 'Q1 漏选 → 判错');
  ok(q1.ctx.prog[mi].p === 'B', 'Q1 存档仍用原始字母 B', q1.ctx.prog[mi].p);
  ok(jd.includes('你选的是 A'), 'Q1「你选的是」= 屏幕字母 A（而非原始字母 B）');
  ok(jd.includes('正确答案：<b>AC'), 'Q1「正确答案」= 屏幕字母 AC');
}
{
  const q1b = bootOff();
  q1b.ctx.S.mode = 'exam'; q1b.ctx.S.queue = [mi]; q1b.ctx.S.pos = 0; q1b.ctx.render();
  q1b.ctx.S.perm = [1, 0, 3, 2]; q1b.ctx.paint();
  q1b.ctx.pick(1); q1b.ctx.pick(3); q1b.ctx.submit(); // 点屏幕上的刘伯承、彭德怀
  const jd = q1b.els['jd'].innerHTML;
  ok(q1b.ctx.prog[mi].ok === false, 'Q1 屏幕选错 → 判错');
  ok(jd.includes('你选的是 BD'), 'Q1 选错时「你选的是」= 屏幕字母 BD');
  ok(jd.includes('正确答案：<b>AC'), 'Q1 正确项仍显示屏幕字母 AC');
}
{
  const q1c = bootOff();
  q1c.ctx.S.mode = 'exam'; q1c.ctx.S.queue = [iS]; q1c.ctx.S.pos = 0; q1c.ctx.render();
  q1c.ctx.S.perm = [2, 3, 0, 1]; q1c.ctx.paint();    // 非恒等，两套字母才会分叉
  let dWrong = -1;
  for (let d = 0; d < 4; d++) if (BANK[iS].a.indexOf('ABCD'[q1c.ctx.S.perm[d]]) < 0) { dWrong = d; break; }
  q1c.ctx.pick(dWrong);                              // 选一个错的屏幕位置
  ok(q1c.els['jd'].innerHTML.includes('你选的是 ' + 'ABCD'[dWrong]),
    'Q1 单选题提示字母 = 屏幕字母 ' + 'ABCD'[dWrong]);
}

// Q2：多选题补「不会，看答案」
{
  const q2 = boot();
  q2.ctx.S.mode = 'exam'; q2.ctx.S.queue = [iM]; q2.ctx.S.pos = 0; q2.ctx.render();
  ok(q2.els['foot'].innerHTML.includes('不会，看答案'), 'Q2 多选题底部出现「不会，看答案」');
  q2.ctx.skip();
  ok(q2.ctx.S.done === true && q2.ctx.prog[iM].ok === false, 'Q2 多选跳过 → 判未作答');
  ok(q2.els['jd'].innerHTML.includes('（未作答）'), 'Q2 判分框标注未作答');
}

// Q3：单选「确认提交」+ 首页开关
{
  const q3 = boot();                                   // 默认 confirmSingle=1
  ok(+q3.ctx.setting.confirmSingle === 1, 'Q3 开关默认开启');
  q3.ctx.examHome();
  ok(q3.els['app'].innerHTML.includes('单选需确认'), 'Q3 首页出现开关 chip');
  q3.ctx.S.mode = 'exam'; q3.ctx.S.queue = [iS]; q3.ctx.S.pos = 0; q3.ctx.render();
  ok(q3.els['foot'].innerHTML.includes('请先选择答案'), 'Q3 未选时提示先选择');
  q3.ctx.pick(0);
  ok(q3.ctx.S.done === false, 'Q3 点选后不判分（等确认）');
  ok(q3.els['foot'].innerHTML.includes('确认提交'), 'Q3 出现「确认提交」按钮');
  q3.ctx.pick(1);
  ok(q3.ctx.S.picked.length === 1 && q3.ctx.S.picked[0] === 1, 'Q3 可反悔改选');
  q3.ctx.submit();
  ok(q3.ctx.S.done === true, 'Q3 点提交后才判分');
}
{
  const q3b = bootOff();
  q3b.ctx.S.mode = 'exam'; q3b.ctx.S.queue = [iS]; q3b.ctx.S.pos = 0; q3b.ctx.render();
  ok(q3b.els['foot'].innerHTML.includes('不会，看答案') && !q3b.els['foot'].innerHTML.includes('确认提交'),
    'Q3 关闭时仍是单按钮「不会，看答案」');
  q3b.ctx.pick(0);
  ok(q3b.ctx.S.done === true, 'Q3 开关关闭 → 单选点即判');
}

/* ---------------- 十一、底部按钮位置（主按钮在右，拇指不用挪） ---------------- */
console.log('\n=== 十一、按钮位置 ===');
{
  const qp = boot();
  qp.ctx.S.mode = 'exam'; qp.ctx.S.queue = [iS]; qp.ctx.S.pos = 0; qp.ctx.render();
  qp.ctx.pick(0);
  const fh = qp.els['foot'].innerHTML;
  ok(fh.indexOf('不会，看答案') < fh.indexOf('确认提交'), '单选：「不会，看答案」在左、「确认提交」在右');
  qp.ctx.submit();
  const fh2 = qp.els['foot'].innerHTML;
  ok(fh2.indexOf('上一题') < fh2.indexOf('下一题'), '判分后「下一题」仍在右（与提交同侧）');
}
{
  const qm = boot();
  qm.ctx.S.mode = 'exam'; qm.ctx.S.queue = [iM]; qm.ctx.S.pos = 0; qm.ctx.render();
  const fh = qm.els['foot'].innerHTML;
  ok(fh.indexOf('不会，看答案') < fh.indexOf('请先勾选答案'), '多选：「不会，看答案」在左、提交在右');
}

/* ---------------- 十二、关于本网站 / 更新日志 ---------------- */
console.log('\n=== 十二、关于 / 更新日志 ===');
{
  const ab = boot();
  const hh = ab.els['app'].innerHTML;
  ok(hh.includes('关于本网站'), '首页出现「关于本网站」入口');
  ok(/v\d+\.\d+(?:fixed)?/.test(hh), '首页入口带版本号',
    (hh.match(/v\d+\.\d+(?:fixed)?/) || [''])[0]);
  ok(!/__VER__|__LOG__|__CARDS__/.test(hh), '首页无未替换占位符');

  ab.ctx.about();
  const ah = ab.els['app'].innerHTML;
  ['这是什么', '数据来源及说明', '使用须知', '鸣谢'].forEach(s =>
    ok(ah.includes(s), '关于页含小节「' + s + '」'));
  ok(ah.includes('Link_MO'), '鸣谢署名 Link_MO');
  ok(ah.includes('doki') && ah.includes('宝宝巴豆') && ah.includes('爱读报的坚果'),
    '鸣谢含三位测试者');
  ok(ah.includes('Wilson') && ah.includes('DeepSeek V4.1 Flash'), '鸣谢含协作方 Wilson 与底层模型');
  ok(ah.includes('24软工｜Hilbert') && ah.includes('代码贡献'), '鸣谢含代码贡献者 24软工｜Hilbert');
  ok(!/「林克」|「都大」|「🫘」|「果子哥」/.test(ah), '鸣谢已去掉全部「称号」括号');
  ok(ah.includes('579') && ah.includes('87'), '数据来源写明题库与卡片规模');
  ok(ah.includes('不是官方答案'), '写明「不是官方答案」的免责说明');
  ok(!/__VER__|__LOG__/.test(ah), '关于页无未替换占位符');
  ok(/v\d+\.\d+(?:fixed)?/.test(ah), '关于页底部版本号已替换为真实值',
    (ah.match(/v\d+\.\d+(?:fixed)?/) || [''])[0]);
}
{
  const lg = boot();
  lg.ctx.vlog();
  const lh = lg.els['app'].innerHTML;
  ok(lh.includes('更新日志') && lh.includes('←'), '日志页有标题与返回按钮');
  const logMd = fs.readFileSync(path.join(__dirname, '..', 'output', '更新日志.md'), 'utf8');
  const expectedHeadings = [...logMd.matchAll(/^## (.+)$/gm)].map(m => m[1].trim());
  const renderedHeadings = [...lh.matchAll(/<h3>(.*?)<\/h3>/g)].map(m => m[1]);
  ok(JSON.stringify(renderedHeadings) === JSON.stringify(expectedHeadings), '日志版本与源文件一致且顺序正确',
    renderedHeadings.length);
  ok(lh.includes(expectedHeadings[0]) && lh.includes(expectedHeadings[expectedHeadings.length - 1]), '日志首尾版本都在');
  ok(lh.includes('<table>'), '日志里的 markdown 表格已转成 HTML 表格');
  ok(!/\*\*/.test(lh), '日志无残留 markdown 粗体记号');
  ok(!/\|\s*-{3,}/.test(lh), '日志无残留 markdown 表格分隔行');
  ok(!lh.includes('题库来源') && !lh.includes('访问地址'),
    '日志已掐掉尾部的来源/地址块（避免自指链接）');
}

console.log('\n' + (fail === 0 ? '全部检查通过 ✓' : '有 ' + fail + ' 项未通过 ✗'));
process.exit(fail === 0 ? 0 : 1);
