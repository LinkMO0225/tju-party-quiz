# -*- coding: utf-8 -*-
"""v6.0 题库重构：90 期 + 91 期合并（互斥分类，非标签制）。

分类规则（c 字段）：
  0 = 91期相关   本期册子收录的全部 57 道（45 道库内已有 + 12 道新增）
  1 = 往年真题   原 90 期未被本期继承的 + 原往年真题里未被本期收录的
  2 = 网上党课   原党课里未被本期收录的

铁律：数组顺序只允许「末尾追加」，已有题的下标一律不动，否则用户进度串位。
"""
import json, os, re, unicodedata, difflib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(BASE, *p)

merged = json.load(open(J('pdf90', 'merged_bank.json'), encoding='utf-8'))
party = json.load(open(J('pdf90', 'party_bank.json'), encoding='utf-8'))
raw = json.load(open(J('pdf91', 'bank91_raw.json'), encoding='utf-8'))

TYPE = {'single': 0, 'multi': 1}

# 90 期来源的短标签（保持 v5 写法，页面在非本期题上会显示「出处」）
GROUP = {
    '第90期·题型专练':       '第90期专练',
    '第90期·真题选讲例题':   '第90期例题',
    '第90期·87期真题':       '87期真题',
    '第90期·87期真题·附加': '87期附加',
    '25261版·题型专练':      '题型专练',
    '25261版·真题选讲':      '真题选讲',
    '25261版·82期':          '82期真题',
    '25261版·83期':          '83期真题',
    '25261版·模拟卷':        '模拟卷',
}


def norm(s):
    """比对用归一化：全半角、标点、空白、空括号全部抹平。"""
    s = unicodedata.normalize('NFKC', s or '')
    for a, b in [('（', '('), ('）', ')'), ('，', ','), ('。', '.'), ('；', ';'),
                 ('：', ':'), ('“', '"'), ('”', '"')]:
        s = s.replace(a, b)
    s = re.sub(r'[\s\u3000_＿]+', '', s)
    return re.sub(r'[（(]\s*[）)]', '', s)


def opt_sig(q):
    return tuple(sorted(norm(v) for v in q.get('options', {}).values() if v))


def clean_text(s):
    """清掉 PDF 提取在汉字与数字/字母之间插入的空格：'2026 年 3 月' → '2026年3月'。"""
    s = s or ''
    s = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[0-9A-Za-z])', '', s)
    s = re.sub(r'(?<=[0-9A-Za-z])\s+(?=[\u4e00-\u9fa5])', '', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()


# ---------- 1. 现有题库（保持原顺序） ----------
bank = []
for q in merged:
    if q['kind'] == 'fill':          # 填空只走卡片，不进刷题
        continue
    bank.append({
        's': q['stem'], 'o': [q['options'].get(k, '') for k in 'ABCD'],
        'a': q['answer'], 't': TYPE[q['kind']], 'g': GROUP[q['src']],
        'n': 1 if q['src'].startswith('第90期') else 0,
        'c': 0 if q['src'].startswith('第90期') else 1,
    })
n_old = len(bank)

for q in party:
    bank.append({
        's': q['stem'], 'o': [q['options'].get(k, '') for k in 'ABCD'],
        'a': q['answer'], 't': TYPE[q['kind']], 'g': q['src'], 'n': 0, 'c': 2,
        'd': q.get('dup', 0),
    })
n_total_old = len(bank)          # 579

# ---------- 1.5 修补 83 期真题第 33 题：选项被吞进题干 ----------
OPT_RE = re.compile(r'[（(]\s*[）)]\s*A(.+?)B\s*(.+?)C\s*(.+?)D\s*(.+)$')
patched = 0
for e in bank:
    if sum(1 for x in e['o'] if x) >= 2:
        continue
    m = OPT_RE.search(e['s'])
    if m:
        e['s'] = e['s'][:m.start()].rstrip() + '（ ）'
        e['o'] = [m.group(1).strip(), m.group(2).strip(),
                  m.group(3).strip(), m.group(4).strip()]
        patched += 1
print('修补选项被吞进题干的题: %d' % patched)

# ---------- 2. 匹配 91 期 57 道选择题 ----------
stem_idx, opt_idx = {}, {}
for i, e in enumerate(bank):
    stem_idx.setdefault(norm(e['s']), []).append(i)
    o = opt_sig({'options': dict(zip('ABCD', e['o']))})
    if o:
        opt_idx.setdefault(o, []).append(i)


def match(q):
    s = norm(q['stem'])
    if s in stem_idx:
        return stem_idx[s][0]
    o = opt_sig(q)
    if o and o in opt_idx:
        best, bi = 0, -1
        for i in opt_idx[o]:
            r = difflib.SequenceMatcher(None, s, norm(bank[i]['s'])).ratio()
            if r > best:
                best, bi = r, i
        if best >= 0.60:
            return bi
    best, bi = 0, -1
    for i, e in enumerate(bank):
        if abs(len(norm(e['s'])) - len(s)) > max(16, len(s) * 0.35):
            continue
        r = difflib.SequenceMatcher(None, s, norm(e['s'])).ratio()
        if r > best:
            best, bi = r, i
    return bi if best >= 0.90 else -1


q57 = [('专练', x) for x in raw['practice'] if x['kind'] != 'fill'] + \
      [('选讲', x) for x in raw['trial'] if x['kind'] != 'fill']

hit, new = [], []
for tag, q in q57:
    i = match(q)
    if i < 0:
        new.append((tag, q))
    else:
        hit.append((tag, q, i))

assert len(hit) + len(new) == 57, '91 期选择题应为 57 道'
assert len({i for _, _, i in hit}) == len(hit), '一道库内题被多道 91 题命中，匹配有误'

# ---------- 3. 命中题：原地用 91 期版本覆盖（按最新期修订） ----------
for tag, q, i in hit:
    bank[i]['s'] = clean_text(q['stem'])
    bank[i]['o'] = [clean_text(q['options'].get(k, '')) for k in 'ABCD']
    bank[i]['a'] = q['answer']
    bank[i]['t'] = TYPE[q['kind']]
    bank[i]['g'] = '91期·题型专练' if tag == '专练' else '91期·真题选讲'
    bank[i]['n'] = 1
    bank[i]['c'] = 0

# ---------- 4. 新题：追加末尾 ----------
for tag, q in new:
    bank.append({
        's': clean_text(q['stem']),
        'o': [clean_text(q['options'].get(k, '')) for k in 'ABCD'],
        'a': q['answer'], 't': TYPE[q['kind']],
        'g': '91期·题型专练' if tag == '专练' else '91期·真题选讲',
        'n': 1, 'c': 0,
    })

# ---------- 5. 其余题重排分类 ----------
# 原 90 期（c=0）里没被本期继承的 → 往年真题；本期收录的已在第 3 步置为 c=0
# n=1 只留给本期收录的题（n 控制页面上是否显示「出处」）
hitset = {i for _, _, i in hit}
for i, e in enumerate(bank):
    if i < n_total_old and i not in hitset:
        e['n'] = 0
        if e['c'] == 0:
            e['c'] = 1

# ---------- 6. 跨分类去重 ----------
# 旧题库里本来就有 4 组「往年真题 / 网上党课」同题双份。B 方案要求三类互斥、
# 「全部」视图零重复，所以这里按来源权威性保留一条：91期 > 往年真题 > 网上党课。
# 被合并的题标 h=1（隐藏），该条记录仍留在数组里——绝不删元素，否则下标漂移、进度串位。
PRIORITY = {0: 0, 1: 1, 2: 2}


def dedup_key(s):
    """去重用：只留汉字、字母、数字。标点、空格、下划线、引号全忽略——
    同一道题在不同来源里常常只差一个句号或全半角引号。"""
    s = unicodedata.normalize('NFKC', s or '')
    return re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s)


groups = {}
for i, e in enumerate(bank):
    groups.setdefault(dedup_key(e['s']), []).append(i)
hidden = []
for k, idxs in groups.items():
    if len(idxs) < 2:
        continue
    idxs.sort(key=lambda i: (PRIORITY[bank[i]['c']], i))
    for i in idxs[1:]:
        bank[i]['h'] = 1
        hidden.append(i)

# ---------- 7. 卡片：只保留 91 期专练的 22 张填空 ----------
NOTE_RE = re.compile(r'[（(]([^）)]*(?:不可换序|一字不差|可换序|按对上几个空|原文)[^）)]*)[）)]')


def take_note(ans):
    notes = NOTE_RE.findall(ans)
    return NOTE_RE.sub('', ans).strip(), (notes[0] if notes else '')


def split_by(ans, n):
    for seps in (['、'], ['，'], ['；'], ['、', '，'], ['、', '；'], ['、', '，', '；'],
                 ['，', '、'], [',', ';'], ['，', ',']):
        tmp = ans
        for s in seps:
            tmp = tmp.replace(s, '\x00')
        parts = [p.strip() for p in tmp.split('\x00') if p.strip()]
        if len(parts) == n:
            return parts
    return None


cards, failed = [], []
for q in [x for x in raw['practice'] if x['kind'] == 'fill']:
    stem = re.sub(r'_{2,}', '___________', clean_text(q['stem']))
    holes = stem.count('___________')
    ans, note = take_note(q['answer'])
    parts = split_by(ans, holes) if holes else None
    if parts is None and holes:
        rough = [p.strip() for p in re.split(r'[、，,；;]', ans) if p.strip()]
        if len(rough) > holes:
            parts = rough[:holes - 1] + ['，'.join(rough[holes - 1:])]
        elif len(rough) == 1:
            parts = rough
    if parts is None or len(parts) != holes:
        failed.append((q['no'], stem[:36], holes, ans[:34]))
        parts = ([ans] + [''] * (holes - 1)) if holes else [ans]
    cards.append({'s': stem, 'h': parts, 'a': ans, 'note': note,
                  'g': '91期·题型专练', 'n': 1})

# ---------- 输出 ----------
os.makedirs(J('data'), exist_ok=True)
json.dump(bank, open(J('data', 'bank.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
json.dump(cards, open(J('data', 'cards.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)

c = {0: 0, 1: 0, 2: 0}
vis = {0: 0, 1: 0, 2: 0}
for e in bank:
    c[e['c']] += 1
    if not e.get('h'):
        vis[e['c']] += 1

print('原题库 %d 道 → 新题库 %d 条记录（追加 %d）' % (n_total_old, len(bank), len(bank) - n_total_old))
print('  91期相关 c=0  %3d   其中：库内已有 %d / 新增 %d' % (c[0], len(hit), len(new)))
print('  往年真题 c=1  %3d' % c[1])
print('  网上党课 c=2  %3d' % c[2])
print('  合计          %3d' % sum(c.values()))
print()
print('跨分类去重：隐藏 %d 条重复记录（下标 %s）' % (len(hidden), sorted(hidden)))
print('  「全部」实际可见 %d 道 = 91期 %d + 往年真题 %d + 党课 %d' % (
    sum(vis.values()), vis[0], vis[1], vis[2]))
print()
print('91 期命中题的原归属：')
from collections import Counter
src = Counter('90期' if bank[i]['c'] == 0 or True else '' for _, _, i in hit)
print('  （覆盖后已统一为 c=0，原归属见下）')
print('  单选 %d / 多选 %d' % (sum(1 for e in bank if e['t'] == 0),
                              sum(1 for e in bank if e['t'] == 1)))
print()
print('卡片 %d 张（单选空数分布 %s）' % (
    len(cards), dict(Counter(len(x['h']) for x in cards))))
if failed:
    print('!! 切分异常 %d 条' % len(failed))
    for f in failed:
        print('   ', f)
else:
    print('   全部切分正常')
