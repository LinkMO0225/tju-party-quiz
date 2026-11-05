// Regression checks for the defects found during the local assessment.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const LS = 'tju_exam_progress_v3', LSR = 'tju_recite_v2';
let passed = 0;

function boot(store = {}) {
  const els = {}, listeners = {};
  const mk = () => ({ innerHTML: '', textContent: '', hidden: true, className: '', attributes: {},
    setAttribute(k, v) { this.attributes[k] = String(v); }, focus() {} });
  const document = {
    getElementById(id) {
      if (id === 'rcard' && !(els.app && els.app.innerHTML.includes('id="rcard"'))) return null;
      return els[id] || (els[id] = mk());
    }, querySelector: () => mk(), addEventListener() {}
  };
  const localStorage = { getItem: k => Object.hasOwn(store, k) ? store[k] : null,
    setItem: (k, v) => { store[k] = String(v); } };
  const ctx = { document, localStorage, console, Math, JSON, Date,
    window: { addEventListener: (type, fn) => { listeners[type] = fn; } } };
  vm.createContext(ctx);
  scripts.forEach(s => vm.runInContext(s, ctx));
  return { ctx, els, store, listeners };
}
function answer(ctx, idx, correct = true) {
  ctx.S.queue = [idx]; ctx.S.pos = 0; ctx.render();
  if (correct) {
    ctx.S.perm.forEach((v, d) => { if (ctx.BANK[idx].a.includes('ABCD'[v])) ctx.pick(d); });
    ctx.submit();
  } else ctx.skip();
}
function test(name, fn) { fn(); passed++; console.log('PASS', name); }

test('F1: resume respects scope, type, state and random order', () => {
  const { ctx } = boot(); answer(ctx, 0);
  Object.assign(ctx.setting, { scope: 'party', type: '1', state: 'todo', shuffle: 1 });
  ctx.resume();
  const expect = ctx.BANK.filter(q => q.c === 2 && q.t === 1).length;
  assert.equal(ctx.S.queue.length, expect);
  assert.ok(ctx.S.queue.every(i => ctx.BANK[i].c === 2 && ctx.BANK[i].t === 1 && !ctx.prog[i]));
  const wrong = ctx.S.queue[0]; answer(ctx, wrong, false);
  ctx.setting.state = 'wrong'; ctx.resume(); assert.equal(ctx.S.queue.join(','), String(wrong));
});
test('F2: resume and render handle empty queues', () => {
  const { ctx, els } = boot();
  ctx.BANK.forEach((q, i) => { ctx.prog[i] = { p: q.a, ok: true, seen: 1 }; });
  ctx.setting.state = 'todo'; ctx.resume();
  assert.equal(ctx.S.queue.length, 0); assert.ok(els.app.innerHTML.includes('没有题目'));
  ctx.setting.scope = 'unknown'; ctx.setting.state = 'all'; ctx.resume();
  assert.ok(els.app.innerHTML.includes('没有题目'));
});
test('F3: simultaneous distinct answers survive a stale whole-object snapshot', () => {
  const store = {}, a = boot(store), b = boot(store);
  const set = a.ctx.localStorage.setItem;
  let intercepted = false;
  a.ctx.localStorage.setItem = (key, value) => {
    if (key === LS && !intercepted) { intercepted = true; answer(b.ctx, 1); }
    set(key, value);
  };
  answer(a.ctx, 0);
  assert.ok(!JSON.parse(store[LS])[1], 'fixture forces a stale aggregate write');
  const restored = boot(store).ctx.prog;
  assert.equal(restored[0].ok, true); assert.equal(restored[1].ok, true);
});
test('F3: old tabs cannot restore an older answer to the same question', () => {
  const store = {}, a = boot(store), b = boot(store);
  answer(a.ctx, 0); answer(b.ctx, 0, false); answer(a.ctx, 1);
  assert.equal(boot(store).ctx.prog[0].ok, false);
});
test('F3: independent card marks and explicit unmark survive stale tabs', () => {
  const store = {}, a = boot(store), b = boot(store);
  a.ctx.reciteStart(0); a.ctx.toggleMark();
  b.ctx.reciteStart(0); b.ctx.cardNext(); b.ctx.toggleMark();
  const first = a.ctx.R.queue[0], second = b.ctx.R.queue[1];
  a.ctx.toggleMark(); b.ctx.R.lock = 0; b.ctx.cardTap();
  const restored = boot(store).ctx.rprog;
  assert.equal(restored.m[first], undefined); assert.equal(restored.m[second], 1);
  assert.equal(restored.s[second], 1);
});
test('F3: storage events synchronize records without changing current answer selection', () => {
  const store = {}, a = boot(store), b = boot(store);
  b.ctx.S.queue = [2]; b.ctx.S.pos = 0; b.ctx.render(); b.ctx.pick(0);
  answer(a.ctx, 0);
  b.listeners.storage({ key: LS + '.0' });
  assert.equal(b.ctx.prog[0].ok, true); assert.equal(b.ctx.S.picked.join(','), '0');
});
for (const fixture of [null, [], 'bad', 42, true, { 0: null }, { 0: {} },
  { 0: { p: 'AA', ok: false, seen: 1 } }, { 0: { p: 'X', ok: true, seen: 1 } },
  { 0: { p: 'A', ok: 'true', seen: 1 } }, { 591: { p: 'A', ok: true, seen: 1 } }]) {
  test('F4: malformed progress ' + JSON.stringify(fixture), () => {
    const store = { [LS]: JSON.stringify(fixture) }, { ctx, els } = boot(store);
    ctx.examHome(); ctx.start(); ctx.reciteStart(0);
    assert.equal(ctx.stats().done, 0); assert.ok(els.app.innerHTML.includes('rcard'));
    assert.equal(store[LS], JSON.stringify(fixture));
    assert.equal(els.storageStatus.hidden, false);
  });
}
test('F4: retain valid rows and preserve the raw invalid data before saving', () => {
  const raw = JSON.stringify({ 0: null, 1: { p: 'C', ok: true, seen: 1 } });
  const { ctx, store } = boot({ [LS]: raw });
  assert.equal(ctx.prog[1].ok, true); answer(ctx, 2);
  const backup = Object.keys(store).find(k => k.startsWith(LS + '_recovery_'));
  assert.equal(store[backup], raw); assert.equal(JSON.parse(store[LS])[1].ok, true);
});
test('F4: malformed card maps and settings recover to usable defaults', () => {
  const { ctx } = boot({ [LSR]: '{"m":"invalid","s":[1]}', tju_exam_setting_v1: '{"scope":"unknown","type":2}', tju_recite_setting_v1: '[]' });
  ctx.start(); assert.equal(ctx.S.queue.length, 586);
  assert.equal(ctx.setting.type, 'all'); ctx.reciteStart(0); assert.equal(ctx.R.queue.length, 22);
  assert.equal(ctx.rStats().marked, 0);
});
test('F4: unknown inherited names and object-valued settings cannot crash boot', () => {
  for (const raw of ['{"__proto__":{}}', '{"constructor":"x"}', '{"scope":{"toString":"x"}}', '{"shuffle":{}}']) {
    const { ctx } = boot({ tju_exam_setting_v1: raw, tju_recite_setting_v1: raw });
    ctx.start(); assert.equal(ctx.S.queue.length, 586);
    ctx.reciteStart(0); assert.equal(ctx.R.queue.length, 22);
  }
});
test('Long reinforcement sessions bound history while preserving question numbers', () => {
  const { ctx, els } = boot(); ctx.prog[0] = { p: '', ok: false, seen: 1 }; ctx.rStart();
  for (let i = 0; i < 120; i++) { ctx.skip(); ctx.next(); }
  assert.equal(ctx.S.queue.length, 100); assert.equal(ctx.R2.offset, 21);
  assert.ok(els.app.innerHTML.includes('第 121 题'));
  ctx.prev(); assert.ok(els.app.innerHTML.includes('第 120 题'));
});
test('F5: denied writes show a warning, retain pending answers, and retry successfully', () => {
  const { ctx, els, store } = boot(), set = ctx.localStorage.setItem;
  ctx.localStorage.setItem = () => { throw Error('QuotaExceededError'); };
  answer(ctx, 0); answer(ctx, 1);
  assert.equal(els.storageStatus.hidden, false); assert.ok(els.storageStatus.innerHTML.includes('本地保存失败'));
  assert.ok(ctx.ld()[0] && ctx.ld()[1]);
  ctx.localStorage.setItem = set; ctx.retrySaves();
  assert.equal(Object.keys(ctx.pendingWrites).length, 0); assert.equal(els.storageStatus.hidden, true);
  const restored = boot(store).ctx.prog; assert.ok(restored[0] && restored[1]);
});
test('F5: retry failed marks, unmarks and settings', () => {
  const { ctx, store } = boot(), set = ctx.localStorage.setItem;
  ctx.reciteStart(0); ctx.toggleMark(); const idx = ctx.R.queue[0];
  ctx.localStorage.setItem = () => { throw Error('QuotaExceededError'); };
  ctx.toggleMark(); ctx.R.lock = 0; ctx.cardTap(); ctx.togF('shuffleOpt');
  ctx.localStorage.setItem = set; ctx.retrySaves();
  const restored = boot(store).ctx;
  assert.equal(restored.rprog.m[idx], undefined); assert.equal(restored.rprog.s[idx], 1);
  assert.equal(restored.setting.shuffleOpt, 0);
});
test('F5: pending retry does not lose progress written by another tab', () => {
  const store = {}, a = boot(store), b = boot(store), set = a.ctx.localStorage.setItem;
  a.ctx.localStorage.setItem = () => { throw Error('QuotaExceededError'); };
  answer(a.ctx, 0); answer(b.ctx, 1);
  a.ctx.localStorage.setItem = set; a.ctx.retrySaves();
  assert.ok(boot(store).ctx.prog[0] && boot(store).ctx.prog[1]);
});
test('F5: denied reads with allowed writes cannot overwrite unread legacy progress', () => {
  const { ctx, store } = boot(), get = ctx.localStorage.getItem;
  const original = JSON.stringify({ 0: { p: 'A', ok: true, seen: 1 }, 1: { p: 'C', ok: true, seen: 1 } });
  const originalCards = '{"m":{"0":1,"1":1},"s":{}}';
  store[LS] = original; store[LSR] = originalCards;
  ctx.localStorage.getItem = () => { throw Error('SecurityError'); };
  answer(ctx, 2); ctx.R.queue = [2]; ctx.R.pos = 0; ctx.reciteRender(); ctx.toggleMark();
  assert.equal(store[LS], original); assert.equal(store[LSR], originalCards);
  ctx.localStorage.getItem = get; ctx.retrySaves();
  const restored = boot(store).ctx;
  assert.ok(restored.prog[0] && restored.prog[1] && restored.prog[2]);
  assert.equal(Object.keys(restored.rprog.m).length, 3);
});
test('F6: native filter controls expose pressed state and cards expose expansion', () => {
  const { ctx, els } = boot(); ctx.examHome();
  assert.equal((els.app.innerHTML.match(/<button type="button" class="chip/g) || []).length, 13);
  ctx.reciteStart(0); assert.ok(els.app.innerHTML.includes('role="button" tabindex="0"'));
  ctx.cardTap(); assert.equal(els.rcard.attributes['aria-expanded'], 'true');
});
test('F7: mastered question feedback describes removal from the wrong pool', () => {
  const { ctx, els } = boot(); ctx.prog[0] = { p: '', ok: false, seen: 1 }; ctx.rStart();
  ctx.S.perm.forEach((v, d) => { if (ctx.BANK[0].a.includes('ABCD'[v])) ctx.pick(d); }); ctx.submit();
  assert.ok(els.jd.innerHTML.includes('已移出错题池')); assert.ok(!els.jd.innerHTML.includes('不会再出现'));
});
test('F8: reviewing a mastered question cannot push it back into the pool', () => {
  const { ctx } = boot(); ctx.prog[0] = { p: '', ok: false, seen: 1 }; ctx.rStart();
  ctx.S.perm.forEach((v, d) => { if (ctx.BANK[0].a.includes('ABCD'[v])) ctx.pick(d); });
  ctx.submit();
  assert.equal(ctx.R2.pool.length, 0); assert.equal(ctx.R2.mastered, 1); assert.equal(ctx.R2.total, 1);
  ctx.S.queue = [0]; ctx.S.pos = 0; ctx.render(); ctx.skip();
  assert.equal(ctx.R2.pool.length, 0, 'pool must stay empty after a review re-answer');
  assert.equal(ctx.R2.mastered, 1, 'mastered must not double-count');
  assert.equal(ctx.R2.total, 1, 'total must not double-count');
});
test('F9: reinforcement next() advances through history instead of jumping', () => {
  const { ctx } = boot(); ctx.prog[0] = { p: '', ok: false, seen: 1 }; ctx.rStart();
  for (let i = 0; i < 5; i++) { ctx.skip(); ctx.next(); }
  const len = ctx.S.queue.length; assert.equal(len, 6);
  ctx.prev(); ctx.prev(); assert.equal(ctx.S.pos, len - 3);
  ctx.next();
  assert.equal(ctx.S.pos, len - 2, 'next() must step forward through history');
  assert.equal(ctx.S.queue.length, len, 'no new question while history remains');
});
test('F10: reinforcement normal questions come only from attempted questions', () => {
  const { ctx } = boot();
  ctx.prog[0] = { p: '', ok: false, seen: 1 };
  ctx.prog[1] = { p: 'A', ok: true, seen: 1 };
  ctx.rStart();
  assert.equal(ctx.R2.base.slice().sort((a, b) => a - b).join(','), '0,1');
  assert.ok(ctx.R2.base.every(i => ctx.prog[i]), 'base must exclude untouched questions');
});
test('F11: reinforcement intro shows the warning copy and density chips', () => {
  const { ctx, els } = boot();
  ctx.prog[0] = { p: '', ok: false, seen: 1 };
  ctx.rIntro();
  assert.ok(els.app.innerHTML.includes('欢迎进入强化模式'));
  assert.ok(els.app.innerHTML.includes('不会结束'));
  assert.ok(els.app.innerHTML.includes('每 3 题'));
  assert.ok(els.app.innerHTML.includes('开始强化'));
});
test('F12: reinforcement density setting controls the gap', () => {
  const { ctx } = boot();
  ctx.prog[0] = { p: '', ok: false, seen: 1 };
  ctx.setGap(5);
  assert.equal(+ctx.setting.gap, 5);
  ctx.rStart();
  assert.equal(ctx.R2.gap, 5);
  assert.equal(ctx.S.fromPool, true, 'first question is a reinforcement one');
});
test('F13: reinforcement session persists and resumes', () => {
  const store = { [LS]: JSON.stringify({
    0: { p: '', ok: false, seen: 1 }, 1: { p: '', ok: false, seen: 1 }, 2: { p: 'A', ok: true, seen: 1 } }) };
  const a = boot(store);
  a.ctx.rStart();
  const saved = a.ctx.ldr2();
  assert.ok(saved && saved.pool.length === 2, 'session persisted with 2 wrong questions');
  const b = boot(store);
  b.ctx.rResume();
  assert.equal(b.ctx.S.mode, 'reinforce');
  assert.equal(b.ctx.R2.pool.length, 2);
  assert.equal(b.ctx.R2.mastered, 0);
});
test('F14: clearing the pool removes the saved session', () => {
  const store = { [LS]: JSON.stringify({ 0: { p: '', ok: false, seen: 1 } }) };
  const a = boot(store);
  a.ctx.rStart();
  assert.ok(a.ctx.ldr2(), 'session saved on start');
  a.ctx.S.perm.forEach((v, d) => { if (a.ctx.BANK[0].a.includes('ABCD'[v])) a.ctx.pick(d); });
  a.ctx.submit();
  assert.equal(a.ctx.R2.pool.length, 0);
  assert.equal(a.ctx.ldr2(), null, 'empty pool must clear the saved session');
});
test('F15: three scopes are mutually exclusive and exhaustive (no double counting)', () => {
  const { ctx } = boot();
  const B = ctx.BANK;
  assert.equal(B.filter(q => !q.h).length, 586);
  const vis = B.filter(q => !q.h);
  const c0 = vis.filter(q => q.c === 0).length, c1 = vis.filter(q => q.c === 1).length,
        c2 = vis.filter(q => q.c === 2).length;
  assert.equal(c0 + c1 + c2, vis.length, 'scopes must add up to all visible questions');
  assert.equal(c0, 57, '91期相关');
  assert.equal(c1, 207, '往年真题');
  assert.equal(c2, 322, '网上党课');
  // B 方案的承诺：「全部」视图里不该出现同一道题两次
  const keys = vis.map(q => q.s.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, ''));
  assert.equal(new Set(keys).size, keys.length, 'duplicate stems in the visible bank');
  // 互斥分类的前提：同一道题只存一条可见记录。这里校验本次合并的承诺——
  // 「91期相关」不得与其它两类有任何交叉（重复题已在构建阶段合并隐藏）
  const norm = s => s.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, '');
  const others = new Set(B.filter(q => q.c !== 0 && !q.h).map(q => norm(q.s)));
  const cross = B.filter(q => q.c === 0 && !q.h && others.has(norm(q.s)));
  assert.equal(cross.length, 0, '91期相关与其它分类交叉: ' + cross.slice(0, 3).map(q => q.s));
});
test('F16: 91st-edition revisions overwrite the old wording', () => {
  const { ctx } = boot();
  const q = ctx.BANK.find(x => x.s.includes('发展党员工作坚持马克思列宁主义'));
  assert.ok(q, 'revised question must exist');
  assert.ok(q.s.includes('基本方略'), 'must use the new wording');
  assert.ok(!q.s.includes('基本纲领'), 'old wording must be gone');
  assert.equal(q.c, 0);
  assert.equal(q.n, 1);
});
test('F17: new questions are appended at the tail, leaving old indices intact', () => {
  const { ctx } = boot();
  const B = ctx.BANK;
  const tail = B.slice(579);
  assert.equal(tail.length, 12, '12 new questions appended');
  assert.ok(tail.every(q => q.c === 0 && q.n === 1), 'tail is all 91st-edition questions');
  assert.ok(tail.every(q => q.s && q.o.length === 4 && q.o.every(x => x)), 'tail rows are complete');
  // 前 579 道仍然按 c 分类（没有越界、没有空洞）
  assert.ok(B.slice(0, 579).every(q => q.c === 0 || q.c === 1 || q.c === 2));
});
test('F18: 入场动画只在换题时播，重绘不重播', () => {
  const { ctx, els } = boot();
  ctx.S.queue = [0, 1]; ctx.S.pos = 0; ctx.render();
  assert.equal(els.opts.className, 'anim', '换题应播放入场');
  ctx.pick(0);                       // 选中会重建 #opts
  assert.equal(els.opts.className, '', '选中重绘不得重播');
  ctx.submit();                      // 判分会再重建一次
  assert.equal(els.opts.className, '', '判分重绘不得重播');
  ctx.S.pos = 1; ctx.render();
  assert.equal(els.opts.className, 'anim', '下一题重新播');
});
test('F19: 真模糊只出现在两条固定底栏上', () => {
  const css = html.match(/<style>([\s\S]*?)<\/style>/)[1].replace(/\/\*[\s\S]*?\*\//g, '');
  const sel = css.split('}').filter(r => {
    const head = r.split('{')[0].trim();
    return !head.startsWith('@supports') && /backdrop-filter:\s*blur/.test(r);
  }).map(r => r.split('{')[0].trim()).sort();
  assert.deepEqual(sel, ['.cfoot', '.foot'], '模糊层扩到列表项会让低端机滚动掉帧');
});
console.log(`全部 ${passed} 项回归检查通过`);
