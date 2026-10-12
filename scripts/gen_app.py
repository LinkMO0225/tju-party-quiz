# -*- coding: utf-8 -*-
"""生成手机端复习程序（单文件 HTML，数据内嵌）。
两种模式：卡片背诵（填空，一张一题，点开看答案） + 做题测验（单选/多选/填空判对错）。"""
import json, re, os

# 基准目录 = 本脚本所在目录的父目录。写成相对，换机器、换目录名都能跑
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
merged = json.load(open(os.path.join(BASE, 'pdf90', 'merged_bank.json'), encoding='utf-8'))
cards = json.load(open(os.path.join(BASE, 'pdf90', 'fill_cards.json'), encoding='utf-8'))
party = json.load(open(os.path.join(BASE, 'pdf90', 'party_bank.json'), encoding='utf-8'))

# ---------- 修复 83 期第 33 题（选项被吞进题干） ----------
fixed = 0
for q in merged:
    if q['kind'] != 'fill' and not q['options']:
        s = q['stem']
        m = re.search(r'[（(]\s*[）)]\s*A(.+?)B\s*(.+?)C\s*(.+?)D\s*(.+)$', s)
        if m:
            q['stem'] = s[:m.start()].rstrip() + '（ ）'
            q['options'] = {k: v.strip() for k, v in
                            zip('ABCD', [m.group(1), m.group(2), m.group(3), m.group(4)])}
            fixed += 1
print('修复选项缺失题: %d' % fixed)

GROUP = {
    '第90期·题型专练':   ('第90期专练', 1),
    '第90期·真题选讲例题': ('第90期例题', 1),
    '第90期·87期真题':   ('87期真题', 1),
    '第90期·87期真题·附加': ('87期附加', 1),
    '25261版·题型专练':  ('题型专练', 0),
    '25261版·真题选讲':  ('真题选讲', 0),
    '25261版·82期':     ('82期真题', 0),
    '25261版·83期':     ('83期真题', 0),
    '25261版·模拟卷':    ('模拟卷', 0),
}
TYPE = {'single': 0, 'multi': 1}

# c: 题目来源分类 0=第90期相关 / 1=往期真题卷 / 2=网上党课
bank = []
for q in merged:
    # 填空题已由「卡片背诵」承担，刷题模式里不再出现，避免两套题互相干扰
    if q['kind'] == 'fill':
        continue
    g, is90 = GROUP[q['src']]
    bank.append({'s': q['stem'], 'o': [q['options'].get(k, '') for k in 'ABCD'],
                 'a': q['answer'], 't': TYPE[q['kind']], 'g': g, 'n': is90,
                 'c': 0 if is90 else 1})

# 网上党课（第1~20讲）追加在末尾：前 242 道下标保持不变，已有刷题进度不会串位
for q in party:
    bank.append({'s': q['stem'], 'o': [q['options'].get(k, '') for k in 'ABCD'],
                 'a': q['answer'], 't': TYPE[q['kind']], 'g': q['src'], 'n': 0, 'c': 2,
                 'd': q.get('dup', 0)})   # d=1 表示平台原题选项文字有重复

DATA = json.dumps(bank, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
CDATA = json.dumps(cards, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
print('刷题题库: %d 道（已剔除全部填空）' % len(bank))
print('  单选 %d / 多选 %d' % (
    sum(1 for q in bank if q['t'] == 0), sum(1 for q in bank if q['t'] == 1)))
print('  来源：第90期相关 %d / 往期真题卷 %d / 网上党课 %d' % (
    sum(1 for q in bank if q['c'] == 0), sum(1 for q in bank if q['c'] == 1),
    sum(1 for q in bank if q['c'] == 2)))
print('卡片: %d 张（第90期 %d）' % (len(cards), sum(1 for c in cards if c['n'])))

# ---------- 更新日志：读 output/更新日志.md，转成 HTML 嵌进「关于」页 ----------
# .md 是唯一数据源，网页版不另写一份，避免两边说的不一样
log_md = open(os.path.join(BASE, 'output', '更新日志.md'), encoding='utf-8').read()
log_body = log_md[log_md.index('## '):log_md.rindex('\n---')]   # 掐掉尾部的来源/地址块
VER = re.search(r'^## (\S+)', log_body, re.M).group(1)


def _in(s):
    """行内标记：HTML 转义 + 粗体 + 行内代码"""
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', s)


def _cells(row):
    row = row.strip()
    if row.startswith('|'):
        row = row[1:]
    if row.endswith('|'):
        row = row[:-1]
    return [c.strip() for c in row.split('|')]


def md2html(text):
    """只支持日志里用到的那几种标记：##/### 标题、表格、- 列表、**粗体**、`代码`"""
    out, lines, i = [], text.split('\n'), 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s == '---':        # 版本之间靠 h3 的上边框分隔，不再输出 <hr>
            i += 1
            continue
        for n, tag in ((4, 'h5'), (3, 'h4'), (2, 'h3'), (1, 'h3')):
            if s.startswith('#' * n + ' '):
                out.append('<%s>%s</%s>' % (tag, _in(s[n + 1:]), tag))
                break
        else:
            if s.startswith('|'):
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    rows.append(lines[i])
                    i += 1
                head = _cells(rows[0])
                body = [_cells(r) for r in rows[1:]
                        if not re.match(r'^[\s\-:|]+$', r)]
                t = '<table><tr>' + ''.join('<th>%s</th>' % _in(x) for x in head) + '</tr>'
                for b in body:
                    t += '<tr>' + ''.join('<td>%s</td>' % _in(x) for x in b) + '</tr>'
                out.append(t + '</table>')
                continue
            if s.startswith('- '):
                items = []
                while i < len(lines) and lines[i].strip().startswith('- '):
                    items.append(lines[i].strip()[2:])
                    i += 1
                out.append('<ul>' + ''.join('<li>%s</li>' % _in(x) for x in items) + '</ul>')
                continue
            out.append('<p>%s</p>' % _in(s))
        i += 1
    return '\n'.join(out)


LOG_HTML = md2html(log_body)
LOGDATA = json.dumps(LOG_HTML, ensure_ascii=False)
print('更新日志: v%s（%d 个版本，%d KB）' % (
    VER, log_body.count('\n## ') + 1, len(LOG_HTML.encode('utf-8')) // 1024))

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1a5fb4">
<title>入党申请人复习</title>
<style>
:root{--blue:#1a5fb4;--blue-d:#134a8e;--bg:#f2f4f7;--card:#fff;--tx:#1c1f23;--tx2:#5f6b7a;
--line:#e3e7ed;--ok:#1e7d34;--okbg:#e8f5ea;--no:#c62828;--nobg:#fdeaea;--r:14px}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;height:100%}
body{background:var(--bg);color:var(--tx);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
padding-bottom:env(safe-area-inset-bottom)}
.wrap{max-width:560px;margin:0 auto;padding:16px 14px 120px}
h1{font-size:22px;margin:6px 0 4px}
.sub{color:var(--tx2);font-size:13px;margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:16px;margin-bottom:14px}
.stat{display:flex;gap:10px;margin-bottom:14px}
.stat div{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.stat b{display:block;font-size:20px;line-height:1.3}
.stat span{font-size:12px;color:var(--tx2)}
.fgroup{margin-bottom:12px}
.fgroup .lb{font-size:13px;color:var(--tx2);margin-bottom:7px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 14px;font:inherit;font-size:14px;color:var(--tx);cursor:pointer}
.chip.on{background:var(--blue);border-color:var(--blue);color:#fff}
button:focus-visible,[role="button"]:focus-visible{outline:3px solid var(--blue);outline-offset:3px}
.storage-status{max-width:532px;margin:12px auto 0;padding:10px 14px;border:1px solid #f0d9a8;
border-radius:10px;background:#fff6e8;color:#8a5a00;font-size:13px}
.storage-status p{margin:0 0 6px}
.storage-status button{font:inherit;color:var(--blue);background:#fff;border:1px solid var(--blue);border-radius:6px;padding:4px 10px}
.btn{display:block;width:100%;border:0;border-radius:12px;background:var(--blue);color:#fff;
font-size:17px;font-weight:600;padding:15px;cursor:pointer;font-family:inherit}
.btn.ghost{background:#fff;color:var(--blue);border:1.5px solid var(--blue)}
.btn:active{opacity:.85}
/* 首页入口 */
.entry{display:flex;align-items:center;gap:13px;width:100%;text-align:left;background:#fff;
border:1px solid var(--line);border-radius:16px;padding:17px 16px;margin-bottom:12px;cursor:pointer;
font-family:inherit;color:var(--tx)}
.entry .ic{flex:0 0 44px;height:44px;border-radius:12px;background:#e8effa;display:flex;
align-items:center;justify-content:center;font-size:21px}
.entry .tx{flex:1;min-width:0}
.entry b{display:block;font-size:17px;line-height:1.4}
.entry em{display:block;font-size:12.5px;color:var(--tx2);font-style:normal;margin-top:2px}
.entry .go{color:#b9c2ce;font-size:20px;line-height:1}
.entry.pri{background:linear-gradient(135deg,#1a5fb4,#2f7fd8);border-color:#1a5fb4;color:#fff;
box-shadow:0 4px 14px rgba(26,95,180,.22)}
.entry.pri .ic{background:rgba(255,255,255,.22);color:#fff}
.entry.pri em{color:rgba(255,255,255,.88)}
.entry.pri .go{color:rgba(255,255,255,.8)}
.entry:active{opacity:.9}
/* 答题页 */
.top{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.back{border:0;background:none;font-size:22px;line-height:1;padding:4px 6px;cursor:pointer;color:var(--tx2)}
.prog{font-size:14px;color:var(--tx2);font-variant-numeric:tabular-nums}
.tag{margin-left:auto;font-size:12px;color:var(--blue);background:#e8effa;border-radius:999px;padding:3px 10px;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:40%}
/* 题型徽标：单选蓝、多选橙，一眼分得开 */
.ttag{flex:0 0 auto;font-size:12px;font-weight:700;border-radius:6px;padding:3px 8px;white-space:nowrap}
.ttag.t0{background:#e8effa;color:#1a5fb4}
.ttag.t1{background:#ffe9c9;color:#a15600;border:1px solid #f0cf94}
/* 多选题提示条 */
.mnotice{background:#fff6e8;border:1px solid #f0d9a8;color:#8a5a00;border-radius:10px;
padding:9px 12px;font-size:13.5px;line-height:1.6;margin-bottom:12px}
.mnotice b{color:#a15600}
/* 错题强化提示条 */
.rnotice{background:#eef4fd;border:1px solid #bcd4f0;color:#14477a;border-radius:10px;
padding:9px 12px;font-size:13.5px;line-height:1.6;margin-bottom:12px}
.rnotice b{color:#0f3f6e}
.btn.warn{background:#e8890c}
/* 禁用态：错题强化在没有错题时常驻显示但不给点，用浅灰底让人一眼看出「暂时用不上」 */
.btn:disabled{background:#e5e9ef;color:#8d97a4;cursor:default}
.bar{height:4px;background:var(--line);border-radius:2px;overflow:hidden;margin-bottom:16px}
.bar i{display:block;height:100%;background:var(--blue);width:0;transition:width .25s}
.stem{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
padding:16px;font-size:17px;line-height:1.8;margin-bottom:14px;white-space:pre-wrap;word-break:break-word}
.stem.fillans{background:var(--okbg);border-color:#bfe0c6;color:#14471f}
.opt{display:flex;gap:10px;width:100%;text-align:left;background:var(--card);border:1.5px solid var(--line);
border-radius:12px;padding:13px 14px;margin-bottom:10px;font-size:16px;line-height:1.6;cursor:pointer;
font-family:inherit;color:var(--tx);align-items:flex-start}
.opt .k{flex:0 0 24px;height:24px;border-radius:50%;border:1.5px solid var(--line);
display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--tx2)}
.opt.sel{border-color:var(--blue);background:#eef4fd}
.opt.sel .k{background:var(--blue);border-color:var(--blue);color:#fff}
.opt.ok{border-color:var(--ok);background:var(--okbg)}
.opt.ok .k{background:var(--ok);border-color:var(--ok);color:#fff}
.opt.no{border-color:var(--no);background:var(--nobg)}
.opt.no .k{background:var(--no);border-color:var(--no);color:#fff}
.judge{border-radius:12px;padding:12px 14px;font-size:15px;margin:4px 0 10px;line-height:1.7}
.judge.ok{background:var(--okbg);color:#14471f}
.judge.no{background:var(--nobg);color:#7a1616}
.judge b{font-size:16px}
.foot{position:fixed;left:0;right:0;bottom:0;background:rgba(242,244,247,.96);
backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:12px 14px calc(12px + env(safe-area-inset-bottom))}
.foot .in{max-width:560px;margin:0 auto;display:flex;gap:10px}
.foot .btn{flex:1}
.hint{text-align:center;color:var(--tx2);font-size:12.5px;margin-top:10px}
.empty{text-align:center;color:var(--tx2);padding:40px 0}
/* 卡片模式 */
.rcard{background:var(--card);border:1px solid var(--line);border-radius:18px;
padding:22px 18px;min-height:46vh;font-size:19px;line-height:2.05;
white-space:pre-wrap;word-break:break-word;cursor:pointer;
display:flex;align-items:center;justify-content:center;
transition:box-shadow .18s,border-color .18s}
.rcard:active{border-color:#c7d6ea;box-shadow:0 2px 12px rgba(26,95,180,.09)}
.rcard .inner{width:100%}
.blank{display:inline-block;min-width:74px;border-bottom:2px solid #c3cede;margin:0 3px;
vertical-align:-2px}
.fill{display:inline-block;color:#0f7a2e;font-weight:700;background:#eaf7ee;
border-bottom:2px solid #0f7a2e;border-radius:5px;padding:0 5px;margin:0 2px;
animation:pop .2s ease-out}
@keyframes pop{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.rnote{display:block;width:fit-content;margin-top:14px;font-size:12.5px;line-height:1.6;
color:#8a5a00;background:#fff6e0;border:1px solid #f0dca8;border-radius:8px;
padding:4px 10px;font-weight:400;animation:pop .2s ease-out}
.gline{margin-top:10px;font-size:12px;color:var(--tx2);font-weight:400}
.cfoot{position:fixed;left:0;right:0;bottom:0;background:rgba(242,244,247,.96);
backdrop-filter:blur(8px);border-top:1px solid var(--line);
padding:10px 14px calc(10px + env(safe-area-inset-bottom))}
.cfoot .in{max-width:560px;margin:0 auto;display:flex;gap:9px;align-items:stretch}
.cfoot button{flex:1;border:1px solid var(--line);background:#fff;border-radius:12px;
padding:13px 0;font-size:15px;font-family:inherit;color:var(--tx);cursor:pointer}
.cfoot button.main{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.cfoot button.mk{flex:0 0 58px;font-size:22px;line-height:1;color:#c3cede}
.cfoot button.mk.on{color:#f0a800;border-color:#f0d48a;background:#fffaef}
.cfoot button:active{opacity:.82}
/* 关于 / 更新日志 */
.card h3{font-size:16px;margin:0 0 10px}
.abtlink{display:block;width:100%;text-align:center;margin-top:22px;font:inherit;font-size:12.5px;
color:var(--tx2);cursor:pointer;background:none;border:0}
.abtlink b{color:var(--blue)}
.doc h3{font-size:16px;margin:24px 0 8px;padding-top:18px;border-top:1px solid var(--line)}
.doc h3:first-child{margin-top:0;padding-top:0;border-top:0}
.doc h4{font-size:14.5px;margin:16px 0 6px;color:var(--blue)}
.doc p{font-size:14.5px;line-height:1.75;margin:0 0 10px}
.doc ul{margin:0 0 10px;padding-left:20px;font-size:14.5px;line-height:1.75}
.doc li{margin-bottom:5px}
.doc hr{border:0;border-top:1px solid var(--line);margin:18px 0}
.doc table{width:100%;border-collapse:collapse;margin:6px 0 14px;font-size:13px}
.doc th,.doc td{border:1px solid var(--line);padding:6px 8px;text-align:left;line-height:1.5}
.doc th{background:#f6f8fb;color:var(--tx2);font-weight:600}
.doc code{background:#f0f3f7;border-radius:4px;padding:1px 5px;font-size:12.5px}
.ver{display:block;width:100%;text-align:center;margin-top:14px;padding:12px;font-size:13px;
color:var(--tx2);background:none;border:0;font-family:inherit;cursor:pointer}
.ver b{color:var(--blue)}
.cred{padding:0;margin:6px 0 10px;list-style:none}
.cred li{padding:9px 0;border-bottom:1px dashed var(--line);font-size:14.5px;line-height:1.6}
.cred li:last-child{border-bottom:0}
.gnote{color:var(--tx2);font-size:13px;line-height:1.7;background:#f7f9fc;
border-radius:10px;padding:10px 12px;margin:2px 0 0}
</style>
</head>
<body>
<div id="storageStatus" class="storage-status" role="status" aria-live="polite" hidden></div>
<div id="app"></div>
<script>var BANK=__BANK__;</script>
<script>var CARDS=__CARDS__;</script>
<script>var LOG=__LOG__;</script>
<script>
var T={0:'单选',1:'多选'};
// 进度键名带版本号。v1 的题库含 87 道填空，2.0 剔除后下标整体前移，
// 老记录已经对不上题（错题会串位），所以直接换键名重来，不做半吊子迁移。
// 卡片模式(R/LSR)按卡片下标存，卡片没变过，进度不受影响。
var LS='tju_exam_progress_v3', LSS='tju_exam_setting_v1';
var LSR='tju_recite_v1', LSRS='tju_recite_setting_v1';
var pendingWrites={}, damagedStore={}, storeRaw={}, storeReadFailed=false, storeInvalid=false;
function storeStatus(){
  var el=document.getElementById('storageStatus'), messages=[];
  if(storeReadFailed) messages.push('无法读取本地进度，请允许浏览器保存本地数据后重试。');
  if(Object.keys(pendingWrites).length) messages.push('本地保存失败，部分进度或设置尚未保存。重试成功前请勿关闭或刷新页面。');
  if(storeInvalid) messages.push('检测到异常的本地记录，已保留原始数据并忽略无效条目。');
  el.hidden=!messages.length;
  el.innerHTML=messages.map(function(s){return '<p>'+s+'</p>'}).join('')+
    (storeReadFailed||Object.keys(pendingWrites).length?'<button type="button" onclick="retrySaves()">重试保存</button>':'');
}
function badStore(key){
  if(storeRaw[key]!=null){damagedStore[key]=storeRaw[key];storeInvalid=true;storeStatus()}
}
function readStore(key){
  var raw;
  try{raw=Object.prototype.hasOwnProperty.call(pendingWrites,key)?pendingWrites[key]:localStorage.getItem(key)}
  catch(e){storeReadFailed=true;storeStatus();return null}
  storeRaw[key]=raw;
  if(raw===null) return null;
  try{return JSON.parse(raw)}catch(e){badStore(key);return null}
}
function writeStore(key,value){
  var raw=JSON.stringify(value);pendingWrites[key]=raw;
  try{
    if(Object.prototype.hasOwnProperty.call(damagedStore,key)){
      var backup=key+'_recovery_'+Date.now();
      while(localStorage.getItem(backup)!==null) backup+='x';
      localStorage.setItem(backup,damagedStore[key]);delete damagedStore[key];
    }
    localStorage.setItem(key,raw);delete pendingWrites[key];storeStatus();return true;
  }catch(e){storeStatus();return false}
}
function isObject(o){return o!==null&&typeof o==='object'&&!Array.isArray(o)}
function validIndex(k,n){return /^(0|[1-9][0-9]*)$/.test(k)&&+k<n}
function validProgress(p){
  return isObject(p)&&typeof p.p==='string'&&/^[A-D]*$/.test(p.p)&&p.p.length<=4&&
    p.p.split('').every(function(c,i){return p.p.indexOf(c)===i})&&typeof p.ok==='boolean'&&p.seen===1;
}
function cleanExam(o,key){
  var out={};
  if(!isObject(o)){badStore(key);return out}
  Object.keys(o).forEach(function(k){
    if(validIndex(k,BANK.length)&&validProgress(o[k])) out[k]={p:o[k].p,ok:o[k].ok,seen:1};
    else badStore(key);
  });return out;
}
function cleanFlags(o,key){
  var out={};
  if(!isObject(o)){badStore(key);return out}
  Object.keys(o).forEach(function(k){
    if(validIndex(k,CARDS.length)&&(o[k]===0||o[k]===1||typeof o[k]==='boolean')){if(o[k])out[k]=1}
    else badStore(key);
  });return out;
}
function cleanCards(o,key){
  if(!isObject(o)){badStore(key);return {m:{},s:{}}}
  return {m:cleanFlags(o.m,key),s:cleanFlags(o.s,key)};
}
// 单题/单卡片字段是权威记录；原整对象键继续保留，兼容已有进度。
// 不同标签页写不同键，不会因整份快照的读写竞争丢失其他题目。
function ld(){
  var out=cleanExam(readStore(LS),LS);
  for(var i=0;i<BANK.length;i++){
    var key=LS+'.'+i,p=readStore(key);
    if(p===null){if(storeRaw[key]!=null)badStore(key);continue}
    if(validProgress(p)) out[i]=p;else badStore(key);
  }return out;
}
function sv(o,idx){
  if(idx===undefined)return writeStore(LS,o);
  writeStore(LS+'.'+idx,o[idx]);
  var latest=cleanExam(readStore(LS),LS);
  if(storeReadFailed){storeStatus();return false} // 无法读取时不能覆盖尚未读到的旧快照。
  latest[idx]=o[idx];
  prog=Object.assign({},o,latest);return writeStore(LS,prog);
}
function ldr(){
  var out=cleanCards(readStore(LSR),LSR);
  ['m','s'].forEach(function(section){
    for(var i=0;i<CARDS.length;i++){
      var key=LSR+'.'+section+'.'+i,v=readStore(key);
      if(v===null){if(storeRaw[key]!=null)badStore(key);continue}
      if(v===1||v===true) out[section][i]=1;
      else if(v===0||v===false) delete out[section][i];else badStore(key);
    }
  });return out;
}
function svr(o,section,idx){
  if(idx===undefined)return writeStore(LSR,o);
  var value=o[section][idx]?1:0;writeStore(LSR+'.'+section+'.'+idx,value);
  var latest=cleanCards(readStore(LSR),LSR);
  if(storeReadFailed){storeStatus();return false}
  rprog={m:Object.assign({},o.m,latest.m),s:Object.assign({},o.s,latest.s)};
  if(value)rprog[section][idx]=1;else delete rprog[section][idx];
  return writeStore(LSR,rprog);
}
function cleanSettings(o,key,recite){
  var out={}, allowed=recite?{scope:['n90','all'],shuffle:[0,1],onlyMark:[0,1]}:
    {scope:['all','n90','vol','party'],type:['all','0','1','2'],state:['all','todo','wrong'],shuffle:[0,1],shuffleOpt:[0,1],confirmSingle:[0,1]};
  if(!isObject(o)){badStore(key);return out}
  Object.keys(o).forEach(function(k){
    if(Object.prototype.hasOwnProperty.call(allowed,k)&&(typeof o[k]==='string'||typeof o[k]==='number')&&
       allowed[k].some(function(v){return String(v)===String(o[k])}))out[k]=typeof allowed[k][0]==='number'?+o[k]:String(o[k]);else badStore(key);
  });return out;
}
function lds(){return cleanSettings(readStore(LSS),LSS,false)}
function svs(o){return writeStore(LSS,o)}
function ldrs(){return cleanSettings(readStore(LSRS),LSRS,true)}
function svrs(o){return writeStore(LSRS,o)}
function retrySaves(){
  try{localStorage.getItem(LS);storeReadFailed=false}catch(e){storeReadFailed=true}
  Object.keys(pendingWrites).filter(function(k){return k!==LS&&k!==LSR}).forEach(function(k){writeStore(k,JSON.parse(pendingWrites[k]))});
  var latest=ld(),cards=ldr();
  if(!storeReadFailed){
    prog=Object.assign({},prog,latest);rprog=cards;
    if(pendingWrites[LS])writeStore(LS,prog);
    if(pendingWrites[LSR])writeStore(LSR,rprog);
  }
  storeStatus();
}
var app=document.getElementById('app');
function esc(s){return String(s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
/* 选项打乱：返回 0..n-1 的随机排列（Fisher-Yates） */
function shuffled(n){var a=[];for(var i=0;i<n;i++)a.push(i);
 for(var j=a.length-1;j>0;j--){var k=Math.floor(Math.random()*(j+1));var t=a[j];a[j]=a[k];a[k]=t}return a}
function shuffArr(src){var a=src.slice();
 for(var j=a.length-1;j>0;j--){var k=Math.floor(Math.random()*(j+1));var t=a[j];a[j]=a[k];a[k]=t}return a}

/* ==================== 首页 ==================== */
function home(){
  var st=rStats(), sc=rScopeCount();
  var n1=BANK.filter(function(x){return x.t===0}).length;
  var n2=BANK.filter(function(x){return x.t===1}).length;
  app.innerHTML='<div class="wrap"><h1>入党申请人复习</h1>'+
   '<p class="sub">结业考试备考 · 两种模式，按需切</p>'+
   '<button class="entry pri" onclick="reciteHome()">'+
     '<span class="ic">🗂</span><span class="tx"><b>卡片背诵</b>'+
     '<em>填空 '+sc.all+' 张 · 第90期 '+sc.n90+' 张 · 一张一屏</em></span><span class="go">›</span></button>'+
   '<button class="entry" onclick="examHome()">'+
     '<span class="ic">✍️</span><span class="tx"><b>做题测验</b>'+
     '<em>单选 '+n1+' · 多选 '+n2+' · 判对错</em></span><span class="go">›</span></button>'+
   '<p class="hint">背诵进度：已背 '+st.seen+' / '+sc.all+'　标记 '+st.marked+'</p>'+
   '<button type="button" class="abtlink" onclick="about()">关于本网站 · <b>v__VER__</b></button></div>';
}

/* ==================== 关于本网站 / 更新日志 ==================== */
function about(){
  app.innerHTML='<div class="wrap"><div class="top"><button class="back" onclick="home()">←</button>'+
   '<div class="prog">关于本网站</div></div>'+

   '<div class="card"><h3>这是什么</h3>'+
   '<p>天津大学入党申请人培训结业考试的复习工具。题库整理自公开复习资料，'+
   '做成一个单页网页：不用登录、不连服务器，打开就能用。</p>'+
   '<p>两种模式——<b>卡片背诵</b>（填空题，一张一屏，点开看答案）、'+
   '<b>做题测验</b>（单选 / 多选，判对错，错题可无限强化）。</p></div>'+

   '<div class="card"><h3>数据来源及说明</h3>'+
   '<ul>'+
   '<li>选择题 <b>579 道</b>，来自三处：《复习指导与专题训练》第九十期版、'+
   '25261 学期版真题卷、学生党建平台网上党课第 1–20 讲。</li>'+
   '<li>填空卡片 <b>87 张</b>；另有简答、辨析、论述、材料分析共 <b>57 道</b>的背诵手册。</li>'+
   '<li>答案做过逐题交叉校验（用选项文本反查，不沿用平台下标）。</li>'+
   '</ul>'+
   '<p class="gnote">以上均为公开复习资料的个人整理，<b>不是官方答案</b>。'+
   '如与官方题库有出入，以官方为准。</p></div>'+

   '<div class="card"><h3>使用须知</h3>'+
   '<ul>'+
   '<li>进度存在<b>浏览器本地</b>：换设备、换浏览器、用无痕窗口都不同步，清缓存会清空。</li>'+
   '<li>「选项乱序」默认开着，同一道题每次进来字母都不一样——'+
   '<b>别按 A/B/C/D 背，按选项内容记</b>。</li>'+
   '<li>平台上题目顺序和选项顺序对不同账号是随机的，这里看到的顺序未必等于考试时的顺序。</li>'+
   '</ul></div>'+

   '<div class="card"><h3>鸣谢</h3>'+
   '<p>作者　<b>26材料｜Link_MO</b></p>'+
   '<p>协作　<b>Wilson</b>（AI 助手 · DeepSeek V4.1 Flash）</p>'+
   '<p>代码贡献　<b>24软工｜Hilbert🐊</b></p>'+
   '<p style="margin-bottom:4px">参与测试</p>'+
   '<ul class="cred">'+
   '<li>26社科｜doki</li>'+
   '<li>26电气｜宝宝巴豆</li>'+
   '<li>26脑机｜爱读报的坚果</li>'+
   '</ul>'+
   '<p style="margin-bottom:0">以及 26 天大 JiaYuan 群参与测试的所有群友。</p></div>'+

   '<button class="ver" onclick="vlog()">版本 <b>v__VER__</b>　查看更新日志 →</button>'+
   '</div>';
}

function vlog(){
  app.innerHTML='<div class="wrap"><div class="top"><button class="back" onclick="about()">←</button>'+
   '<div class="prog">更新日志</div></div>'+
   '<div class="doc">'+LOG+'</div>'+
   '<button class="btn ghost" style="margin-top:18px" onclick="about()">返回</button></div>';
}

/* ==================== 卡片背诵 ==================== */
var rprog=ldr();
var rset=Object.assign({scope:'n90',shuffle:0,onlyMark:0},ldrs());
var R={queue:[],pos:0,revealed:false,lock:0};

function rStats(){
  var seen=0,marked=0,k;
  for(k in rprog.s){if(rprog.s[k])seen++}
  for(k in rprog.m){if(rprog.m[k])marked++}
  return {total:CARDS.length,seen:seen,marked:marked};
}
function rScopeCount(){
  var n90=0;
  for(var i=0;i<CARDS.length;i++) if(CARDS[i].n) n90++;
  return {n90:n90,all:CARDS.length};
}
function rQueue(){
  var q=[];
  for(var i=0;i<CARDS.length;i++){
    var c=CARDS[i];
    if(rset.scope==='n90'&&!c.n) continue;
    if(+rset.onlyMark&&!rprog.m[i]) continue;
    q.push(i);
  }
  if(+rset.shuffle){for(var j=q.length-1;j>0;j--){var k=Math.floor(Math.random()*(j+1));var t=q[j];q[j]=q[k];q[k]=t}}
  return q;
}
function rchip(k,v,label){
  return '<button type="button" class="chip'+(String(rset[k])===String(v)?' on':'')+'" aria-pressed="'+(String(rset[k])===String(v))+'" onclick="rsetF(\''+k+'\',\''+v+'\')">'+label+'</button>';
}
function focusChip(action){var el=document.querySelector('[onclick="'+action+'"]');if(el&&el.focus)el.focus()}
function rsetF(k,v){rset[k]=v;svrs(rset);reciteHome();focusChip("rsetF('"+k+"','"+v+"')")}

function reciteHome(){
  var st=rStats(), sc=rScopeCount();
  var cur=rQueue().length;
  app.innerHTML='<div class="wrap"><div class="top"><button class="back" onclick="home()">←</button>'+
   '<div class="prog">卡片背诵 · 填空</div></div>'+
   '<div class="stat"><div><b>'+sc.n90+'</b><span>第90期题目</span></div>'+
   '<div><b>'+st.seen+'</b><span>已背过</span></div>'+
   '<div><b>'+st.marked+'</b><span>已标记</span></div></div>'+
   '<div class="card"><div class="fgroup"><div class="lb">范围</div><div class="chips">'+
     rchip('scope','n90','第90期 '+sc.n90)+rchip('scope','all','全部 '+sc.all)+'</div></div>'+
   '<div class="fgroup" style="margin-bottom:4px"><div class="lb">顺序</div><div class="chips">'+
     rchip('shuffle','0','按题序')+rchip('shuffle','1','随机')+'</div></div></div>'+
   '<button class="btn" onclick="reciteStart(0)">开始背卡片（'+cur+' 张）</button>'+
   (st.marked?'<button class="btn ghost" style="margin-top:10px" onclick="reciteStart(1)">只背标记的 '+st.marked+' 张</button>':'')+
   '<p class="hint">空着的地方先自己想，点一下卡片看答案</p></div>';
}

function reciteStart(onlyMark){
  if(onlyMark===0||onlyMark===1){rset.onlyMark=onlyMark;svrs(rset)}
  R.queue=rQueue();
  if(!R.queue.length){
    app.innerHTML='<div class="wrap"><div class="empty">这个条件下没有卡片。<br>'+
      (+rset.onlyMark?'你还没标记任何卡片。':'换个范围试试。')+'</div>'+
      '<button class="btn ghost" onclick="reciteHome()">返回</button></div>';
    return;
  }
  R.pos=0;reciteRender();
}

function reciteRender(){
  R.revealed=false;
  var total=R.queue.length, now=R.pos+1;
  var c=CARDS[R.queue[R.pos]];
  app.innerHTML='<div class="wrap"><div class="top"><button class="back" onclick="reciteHome()">←</button>'+
   '<div class="prog">'+now+' / '+total+'</div><div class="tag">'+esc(c.g)+'</div></div>'+
   '<div class="bar"><i style="width:'+(now/total*100)+'%"></i></div>'+
   '<div class="rcard" id="rcard" role="button" tabindex="0" aria-expanded="false" aria-describedby="chint" onclick="cardTap()"><div class="inner" id="cbody"></div></div>'+
   '<p class="hint" id="chint"></p></div>'+
   '<div class="cfoot"><div class="in">'+
   '<button onclick="cardPrev()">← 上一张</button>'+
   '<button class="mk" id="mkbtn" onclick="toggleMark()">☆</button>'+
   '<button class="main" onclick="cardNext()">下一张 →</button>'+
   '</div></div>';
  paintCard();
}

function paintCard(){
  var idx=R.queue[R.pos], c=CARDS[idx];
  var parts=String(c.s).split(/_{3,}/), out='';
  for(var k=0;k<parts.length;k++){
    out+=esc(parts[k]);
    if(k<c.h.length){
      out+=R.revealed?'<span class="fill">'+esc(c.h[k])+'</span>':'<span class="blank"></span>';
    }
  }
  if(R.revealed&&c.note) out+='<div class="rnote">⚠ '+esc(c.note)+'</div>';
  document.getElementById('cbody').innerHTML=out;
  var card=document.getElementById('rcard');
  if(card&&card.setAttribute)card.setAttribute('aria-expanded',String(R.revealed));
  var mb=document.getElementById('mkbtn');
  if(mb){
    mb.className='mk'+(rprog.m[idx]?' on':'');mb.textContent=rprog.m[idx]?'★':'☆';
    if(mb.setAttribute){mb.setAttribute('aria-label',rprog.m[idx]?'取消标记这张卡片':'标记这张卡片');mb.setAttribute('aria-pressed',String(Boolean(rprog.m[idx])))}
  }
  var h=document.getElementById('chint');
  if(h) h.textContent=R.revealed?'再点一下收起答案、重新背　·　或点下方「下一张」':'点一下卡片，看答案';
  if(R.revealed&&!rprog.s[idx]){rprog.s[idx]=1;svr(rprog,'s',idx)}
}

/* 点卡片 = 翻开 / 收起（可反复重背）；翻页走底部「下一张」 */
function cardTap(){
  var now=Date.now();
  if(now<R.lock) return;        // 防手抖：短时间内的重复点击不生效
  R.lock=now+250;
  R.revealed=!R.revealed;
  paintCard();
}
function toggleMark(){
  var idx=R.queue[R.pos];
  if(rprog.m[idx]) delete rprog.m[idx]; else rprog.m[idx]=1;
  svr(rprog,'m',idx);paintCard();
}
function cardNext(){ if(R.pos<R.queue.length-1){R.pos++;reciteRender()} else{reciteFinish()} }
function cardPrev(){ if(R.pos>0){R.pos--;reciteRender()} }
function reciteFinish(){
  var st=rStats();
  app.innerHTML='<div class="wrap"><h1>这一轮卡片背完了</h1>'+
   '<p class="sub">本轮 '+R.queue.length+' 张</p>'+
   '<div class="stat"><div><b>'+st.seen+' / '+st.total+'</b><span>累计背过</span></div>'+
   '<div><b>'+st.marked+'</b><span>已标记</span></div></div>'+
   (st.marked?'<button class="btn ghost" style="margin-bottom:10px" onclick="reciteStart(1)">只背标记的 '+st.marked+' 张</button>':'')+
   '<button class="btn ghost" style="margin-bottom:10px" onclick="reciteStart()">再背一轮</button>'+
   '<button class="btn" onclick="home()">回到首页</button></div>';
}

/* ==================== 做题测验 ==================== */
var prog=ld(), setting=Object.assign({scope:'all',type:'all',state:'all',shuffle:0,shuffleOpt:1,confirmSingle:1},lds());
// 旧版本里可能存着「填空」题型筛选（type=2），刷题已不含填空，兜底重置
if(setting.type==='2'){setting.type='all';svs(setting)}
// S.mode: 'exam' 普通测验 / 'reinforce' 错题强化
// S.perm: 本题选项的显示顺序，S.perm[d] = 第 d 个位置放原始第几个选项
var S={queue:[],pos:0,picked:[],done:false,mode:'exam',perm:[0,1,2,3],fromPool:false};

/* 题目来源分类（对应数据里的 c 字段）：0=第90期相关 / 1=往期真题卷 / 2=网上党课 */
var SCOPECAT={n90:0, vol:1, party:2};
function buildQueue(ignoreState){
  var q=[];
  for(var i=0;i<BANK.length;i++){
    var it=BANK[i], p=prog[i];
    if(setting.scope!=='all' && it.c!==SCOPECAT[setting.scope]) continue;
    if(setting.type!=='all' && it.t!==+setting.type) continue;
    if(!ignoreState){
      if(setting.state==='todo' && p) continue;
      if(setting.state==='wrong' && !(p && !p.ok)) continue;
    }
    q.push(i);
  }
  if(+setting.shuffle){for(var j=q.length-1;j>0;j--){var k=Math.floor(Math.random()*(j+1));var t=q[j];q[j]=q[k];q[k]=t}}
  return q;
}
/* 当前范围+题型下的错题条数（不看「状态」筛选，强化模式要用全量） */
function wrongCount(){
  var b=buildQueue(true), n=0;
  for(var i=0;i<b.length;i++){ var t=b[i]; if(prog[t]&&prog[t].ok===false) n++; }
  return n;
}
function scopeCount(){
  var c={n90:0,vol:0,party:0,all:BANK.length};
  for(var i=0;i<BANK.length;i++){
    var x=BANK[i].c;
    if(x===0) c.n90++; else if(x===1) c.vol++; else c.party++;
  }
  return c;
}
function stats(){
  var done=0,ok=0;
  for(var k in prog){done++; if(prog[k].ok) ok++;}
  return {done:done,ok:ok,rate:done?Math.round(ok/done*100):0};
}

function examHome(){
  var st=stats(), c=scopeCount(), wc=wrongCount();
  var n1=BANK.filter(function(x){return x.t===0}).length;
  var n2=BANK.filter(function(x){return x.t===1}).length;
  var html='<div class="wrap"><div class="top"><button class="back" onclick="home()">←</button>'+
  '<div class="prog">做题测验</div></div>'+
  '<p class="sub">题库 '+BANK.length+' 道 · 单选 '+n1+' / 多选 '+n2+
  '<br>（含网上党课 '+c.party+' 道；填空题已移到「卡片背诵」）</p>'+
  '<div class="stat"><div><b>'+st.done+'</b><span>已练题数</span></div>'+
  '<div><b>'+st.rate+'%</b><span>正确率</span></div>'+
  '<div><b>'+Math.max(0,BANK.length-st.done)+'</b><span>还没碰过</span></div></div>';
  if(st.done) html+='<button class="btn" style="margin-bottom:14px" onclick="resume()">继续刷题</button>';
  html+='<div class="card"><div class="fgroup"><div class="lb">范围</div><div class="chips">'+
    chip('scope','all','全部 '+c.all)+chip('scope','n90','第90期相关 '+c.n90)+
    chip('scope','vol','往期真题卷 '+c.vol)+chip('scope','party','网上党课 '+c.party)+
    '</div></div><div class="fgroup"><div class="lb">题型</div><div class="chips">'+
    chip('type','all','全部')+chip('type','0','单选')+chip('type','1','多选')+
    '</div></div><div class="fgroup"><div class="lb">状态</div><div class="chips">'+
    chip('state','all','全部')+chip('state','todo','没做过的')+chip('state','wrong','做错的')+
    '</div></div><div class="fgroup" style="margin-bottom:0"><div class="lb">其他</div><div class="chips">'+
    tchip('shuffleOpt','选项乱序')+tchip('shuffle','题目随机')+tchip('confirmSingle','单选需确认')+
    '</div></div></div>'+
    '<button class="btn" onclick="start()">按以上条件开始</button>'+
    (wc?'<button class="btn warn" style="margin-top:10px" onclick="rStart()">'+
      '错题强化 · 无限刷（当前范围 '+wc+' 道错题）</button>'
     :'<button class="btn warn" style="margin-top:10px" disabled>'+
      '错题强化 · 无限刷（当前没有错题，先做一轮）</button>')+
    '<p class="hint">「选项乱序」关掉后，选项固定按 A B C D 原顺序显示</p></div>';
  app.innerHTML=html;
}
/* 开关式 chip：「选项乱序」「题目随机」这类布尔设置 */
function tchip(key,label){
  var on=+setting[key];
  return '<button type="button" class="chip'+(on?' on':'')+'" aria-pressed="'+Boolean(on)+'" onclick="togF(\''+key+'\')">'+label+(on?'：开':'：关')+'</button>';
}
function togF(k){setting[k]=+setting[k]?0:1;svs(setting);examHome();focusChip("togF('"+k+"')")}
function chip(key,val,label){
  return '<button type="button" class="chip'+(String(setting[key])===String(val)?' on':'')+'" aria-pressed="'+(String(setting[key])===String(val))+'" onclick="setF(\''+key+'\',\''+val+'\')">'+label+'</button>';
}
function setF(k,v){setting[k]=v;svs(setting);examHome();focusChip("setF('"+k+"','"+v+"')")}

function start(){
  S.mode='exam';S.fromPool=false;
  S.queue=buildQueue();S.pos=0;
  if(!S.queue.length){app.innerHTML='<div class="wrap"><div class="empty">这个条件下没有题目，换个筛选项试试。</div><button class="btn ghost" onclick="examHome()">返回</button></div>';return}
  render();
}
function resume(){
  S.mode='exam';S.fromPool=false;
  var q=buildQueue();
  if(setting.state==='all'){
    var todo=q.filter(function(i){return !prog[i]});if(todo.length)q=todo;
  }
  S.queue=q;S.pos=0;render();
}

function render(){
  var it=BANK[S.queue[S.pos]];
  S.picked=[];S.done=false;
  if(!it){app.innerHTML='<div class="wrap"><div class="empty">当前条件下没有题目，已完成或没有符合筛选的题目。</div><button class="btn ghost" onclick="examHome()">返回</button></div>';return}
  S.perm=(+setting.shuffleOpt)?shuffled(4):[0,1,2,3];   // 选项乱序，可在首页关掉
  var now=S.pos+1+(S.mode==='reinforce'?R2.offset:0), total=S.queue.length, head, barw;
  if(S.mode==='reinforce'){
    head='<div class="prog">第 '+now+' 题</div>';
    var den=R2.mastered+R2.pool.length;
    barw=den?Math.round(R2.mastered/den*100):100;
  }else{
    head='<div class="prog">'+now+' / '+total+'</div>';
    barw=total?Math.round(now/total*100):0;
  }
  app.innerHTML='<div class="wrap"><div class="top"><button class="back" onclick="'+
   (S.mode==='reinforce'?'exitReinforce()':'examHome()')+'">←</button>'+
   '<span class="ttag t'+it.t+'">'+T[it.t]+'题</span>'+head+
   '<div class="tag">'+esc(it.g)+'</div></div>'+
   '<div class="bar"><i style="width:'+barw+'%"></i></div>'+
   (S.mode==='reinforce'&&S.fromPool
     ?'<div class="rnotice">强化题 · 这题你之前做错过　|　错题池还剩 <b>'+R2.pool.length+'</b> 道</div>':'')+
   '<div class="stem" id="stem">'+esc(it.s)+'</div><div id="opts"></div><div id="jd"></div></div>'+
   '<div class="foot"><div class="in" id="foot"></div></div>';
  paint();
}

function paint(){
  var it=BANK[S.queue[S.pos]];
  var box=document.getElementById('opts');
  var h='';
  if(it.t===1&&!S.done){
    h+='<div class="mnotice">多选题 · 正确答案<b>不止一个</b>，选完后点下方「提交答案」</div>';
  }
  if(it.d&&!S.done){
    h+='<div class="mnotice" style="background:#fdeaea;border-color:#f0b8b8;color:#8a1f1f">'+
       '本题有两个选项<b>文字相同</b>（平台原始题目如此），判分时需一并选中</div>';
  }
  for(var d=0;d<it.o.length;d++){
    var oi=S.perm[d], K='ABCD'[d], cls='opt';
    var isAns=it.a.indexOf('ABCD'[oi])>=0;
    if(S.done){
      var pick=S.picked.indexOf(d)>=0;
      if(isAns) cls+=' ok';
      if(pick&&!isAns) cls='opt no';
    } else if(S.picked.indexOf(d)>=0) cls+=' sel';
    h+='<button class="'+cls+'" onclick="pick('+d+')"><span class="k">'+K+'</span><span>'+esc(it.o[oi])+'</span></button>';
  }
  box.innerHTML=h;
  var f='';
  if(!S.done){
    // 主按钮（提交）固定放**右侧**——与判分后的「下一题」同侧，拇指可以一直按右下角
    if(it.t===1){
      f+='<button class="btn ghost" onclick="skip()">不会，看答案</button>';
      f+=S.picked.length
        ? '<button class="btn" onclick="submit()">提交答案（已选 '+S.picked.length+' 项）</button>'
        : '<button class="btn ghost" onclick="submit()">请先勾选答案 · 本题可多选</button>';
    }else if(+setting.confirmSingle){
      f+='<button class="btn ghost" onclick="skip()">不会，看答案</button>';
      f+=S.picked.length
        ? '<button class="btn" onclick="submit()">确认提交</button>'
        : '<button class="btn ghost" onclick="submit()">请先选择答案</button>';
    }else{
      f+='<button class="btn ghost" onclick="skip()">不会，看答案</button>';
    }
  }else{
    f+='<button class="btn ghost" onclick="prev()">上一题</button><button class="btn" onclick="next()">下一题</button>';
  }
  document.getElementById('foot').innerHTML=f;
}

function pick(i){
  var it=BANK[S.queue[S.pos]];
  if(S.done) return;
  if(it.t===1){
    var p=S.picked.indexOf(i);
    if(p>=0) S.picked.splice(p,1); else S.picked.push(i);
    paint();
  }else if(+setting.confirmSingle){
    S.picked=[i];paint();          // 单选·需确认：只选中，等「确认提交」
  }else{
    S.picked=[i];judge();          // 单选·立即判分
  }
}
function submit(){ if(S.done||!S.picked.length) return; judge() }
function skip(){ if(S.done) return; S.picked=[]; judge() }

/* 打乱后的「正确答案」——按当前显示位置算字母 */
function dispAns(it){
  var s='';
  for(var d=0;d<4;d++){ if(it.a.indexOf('ABCD'[S.perm[d]])>=0) s+='ABCD'[d]; }
  return s;
}

function judge(){
  var it=BANK[S.queue[S.pos]], idx=S.queue[S.pos];
  var pick=S.picked.map(function(d){return 'ABCD'[S.perm[d]]}).sort().join('');   // 判分/存档：还原成原始字母
  var pickDisp=S.picked.map(function(d){return 'ABCD'[d]}).sort().join('');       // 展示：与屏幕选项同一套字母
  var ok=(pick===it.a.split('').sort().join(''));
  S.done=true;
  prog[idx]={p:pick,ok:ok,seen:1};sv(prog,idx);

  var extra='';
  if(S.mode==='reinforce'){
    R2.total++;
    var inPool=R2.pool.indexOf(idx);
    if(inPool>=0&&ok){                      // 答对 → 从错题池彻底移除
      R2.pool.splice(inPool,1);R2.mastered++;
      extra='<br><span style="font-size:13px;color:#1e7d34">✓ 这题已攻克，已移出错题池</span>';
    }else if(inPool>=0){
      extra='<br><span style="font-size:13px;color:#c62828">✗ 还在错题池里，稍后会再来一次</span>';
    }else if(!ok){                           // 普通题做错 → 直接进池
      R2.pool.push(idx);
      extra='<br><span style="font-size:13px;color:#c62828">✗ 这题已加入错题池</span>';
    }
    extra+='<br><span style="font-size:13px;color:#5f6b7a">错题池还剩 '+R2.pool.length+' 道</span>';
  }

  paint();
  document.getElementById('jd').innerHTML='<div class="judge '+(ok?'ok':'no')+'">'+
    (ok?'<b>✓ 答对了</b>':'<b>✗ 答错了</b>　'+(S.picked.length?'你选的是 '+pickDisp:'（未作答）'))+
    '<br>正确答案：<b>'+dispAns(it)+'</b>'+
    (it.t===1?'　<span style="font-size:13px">（多选，共 '+it.a.length+' 项）</span>':'')+
    extra+
    (it.n?'':'<br><span style="font-size:13px">出处：'+it.g+'</span>')+'</div>';
}
function next(){ if(S.mode==='reinforce'){R2Step();return} if(S.pos<S.queue.length-1){S.pos++;render()} else{finish()} }
function prev(){ if(S.pos>0){S.pos--;render()} }
function finish(){
  var st=stats(), w=wrongCount();
  app.innerHTML='<div class="wrap"><h1>这一轮刷完了</h1>'+
   '<p class="sub">共 '+S.queue.length+' 题'+(w?'　·　攒下 '+w+' 道错题':'')+'</p>'+
   '<div class="stat"><div><b>'+st.done+'</b><span>累计已练</span></div>'+
   '<div><b>'+st.rate+'%</b><span>累计正确率</span></div>'+
   '<div><b>'+w+'</b><span>待清错题</span></div></div>'+
   (w?'<button class="btn warn" style="margin-bottom:10px" onclick="rStart()">错题强化 · 无限刷（'+w+' 道）</button>':'')+
   '<button class="btn ghost" style="margin-bottom:12px" onclick="start()">再来一轮</button>'+
   '<button class="btn" onclick="home()">回到首页</button></div>';
}

/* ==================== 错题强化 · 无限刷 ====================
   规则：正常题按乱序循环出，每做满 gap 道就插一道错题（强化题）。
   强化题答对 → 从错题池永久移除；答错 → 留在池里，稍后再来。
   普通题答错 → 也进池。池子清空即结束。
*/
var R2={base:[],pool:[],norm:[],np:0,since:0,gap:3,mastered:0,total:0,offset:0};

function rStart(){
  S.mode='exam';
  R2.base=buildQueue(true);
  R2.pool=[];
  for(var i=0;i<R2.base.length;i++){
    var t=R2.base[i];
    if(prog[t]&&prog[t].ok===false) R2.pool.push(t);
  }
  if(!R2.pool.length){
    app.innerHTML='<div class="wrap"><div class="empty">当前范围里还没有错题。<br>先去刷一轮，做错的会自动进这里。</div>'+
      '<button class="btn ghost" onclick="examHome()">返回</button></div>';
    return;
  }
  R2.norm=shuffArr(R2.base);R2.np=0;
  R2.since=R2.gap;R2.mastered=0;R2.total=0;R2.offset=0;
  S.mode='reinforce';S.queue=[];S.pos=-1;S.fromPool=false;
  R2Step();
}

function R2Step(){
  if(!R2.pool.length){ S.mode='exam'; R2Finish(); return; }
  var idx;
  if(R2.since>=R2.gap){                      // 轮到强化题
    R2.since=0;
    idx=R2.pool[Math.floor(Math.random()*R2.pool.length)];
    S.fromPool=true;
  }else{                                     // 正常题，循环出
    if(R2.np>=R2.norm.length){R2.norm=shuffArr(R2.base);R2.np=0}
    idx=R2.norm[R2.np++];
    R2.since++;
    S.fromPool=false;
  }
  S.queue.push(idx);
  // 只保留最近 100 题供回看，题号用 offset 保持连续，避免无限模式积累历史。
  if(S.queue.length>100){S.queue.shift();R2.offset++}
  S.pos=S.queue.length-1;
  render();
}

function R2Finish(){
  app.innerHTML='<div class="wrap"><h1>错题全清了</h1>'+
   '<p class="sub">本轮做了 '+R2.total+' 题，攻克 '+R2.mastered+' 道错题</p>'+
   '<div class="stat"><div><b>'+R2.mastered+'</b><span>已攻克</span></div>'+
   '<div><b>'+R2.total+'</b><span>本轮题数</span></div>'+
   '<div><b>0</b><span>剩余错题</span></div></div>'+
   '<button class="btn" style="margin-bottom:10px" onclick="home()">回首页</button>'+
   '<button class="btn ghost" onclick="examHome()">再刷普通题</button></div>';
}

function exitReinforce(){
  S.mode='exam';
  app.innerHTML='<div class="wrap"><h1>退出强化？</h1>'+
   '<p class="sub">错题池还剩 '+R2.pool.length+' 道。已攻克的题已移出错题池。'+
     (Object.keys(pendingWrites).length?'部分进度尚未保存，请先重试保存。':'进度已保存。')+'</p>'+
   '<button class="btn" style="margin-bottom:10px" onclick="rStart()">继续强化</button>'+
   '<button class="btn ghost" onclick="examHome()">回测验首页</button></div>';
}

document.addEventListener('keydown',function(e){
  if(!document.getElementById('rcard'))return;
  if(e.target&&(/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)||e.target.isContentEditable))return;
  if(e.target&&/^(BUTTON|A)$/.test(e.target.tagName)&&(e.key===' '||e.key==='Enter'))return;
  if(e.key===' '||(e.key==='Enter'&&e.target&&e.target.id==='rcard')){e.preventDefault();cardTap()}
  else if(e.key==='ArrowRight'){e.preventDefault();cardNext()}
  else if(e.key==='ArrowLeft'){e.preventDefault();cardPrev()}
  else if(e.key==='m'||e.key==='M'){e.preventDefault();toggleMark()}
  var card=document.getElementById('rcard');
  if(card&&card.focus&&e.target&&e.target.id==='rcard')card.focus();
});
if(typeof window!=='undefined')window.addEventListener('storage',function(e){
  if(e.key===null||e.key===LS||e.key.indexOf(LS+'.')===0)prog=ld();
  if(e.key===null||e.key===LSR||e.key.indexOf(LSR+'.')===0){
    rprog=ldr();if(document.getElementById('rcard'))paintCard();
  }
});

home();
</script>
</body>
</html>
'''

html = (HTML.replace('__BANK__', DATA).replace('__CARDS__', CDATA)
        .replace('__LOG__', LOGDATA).replace('__VER__', VER))
# 成品写两处：output/ 存档一份；根目录 index.html 供 GitHub Pages 直接托管
for OUT in (os.path.join(BASE, 'output', '入党申请人复习.html'),
            os.path.join(BASE, 'index.html')):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(html)
    print('已生成: %s (%.0f KB)' % (OUT, os.path.getsize(OUT) / 1024))
