# -*- coding: utf-8 -*-
"""step12：应用 data/clean/*.py 清洗记录，生成
  ① data/terms_candidates_clean.jsonl  清洗后词项池（按句聚合）
  ② data/term_sentence_pairs.jsonl     全量词项-英译片段对
未标注的词项保留原样但 needs_revision=True（note=未标注），便于分篇渐进补齐。
"""
import json, glob, importlib.util, os, sys
from collections import OrderedDict

flat = json.load(open('data/flat_terms.json', encoding='utf-8'))

# 载入所有清洗记录
records = {}
files = sorted(glob.glob('data/clean/*.py'))
for fp in files:
    name = os.path.splitext(os.path.basename(fp))[0]
    spec = importlib.util.spec_from_file_location(name, fp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for idx, rec in m.R.items():
        records[idx] = rec
print(f'载入清洗记录: {len(records)} 条，来自 {len(files)} 个文件')

pairs, problems, stats = [], [], {'keep': 0, 'fix': 0, 'del': 0, 'unlabeled': 0}
for r in flat:
    idx = r['idx']
    rec = records.get(idx)
    if rec is None:
        stats['unlabeled'] += 1
        pairs.append({
            'idx': idx, 'sent_id': r['sent_id'], 'title': r['title'],
            'term': r['term'], 'term_type': r['term_type'],
            'meaning_in_this_sentence': r['meaning'],
            'classical_sentence': r['classical'],
            'full_english': r['english'],
            'term_english': None, 'match_type': None,
            'needs_revision': True, 'note': '未标注',
        })
        continue
    action, term, meaning, te = rec[:4]
    note = rec[4] if len(rec) > 4 else ""
    stats[action] += 1
    if action == 'del':
        continue
    term = term or r['term']
    meaning = meaning or r['meaning']
    mt = None
    if te:
        if te in r['english']:
            mt = 'substring'
        else:
            mt = 'MISMATCH'
            problems.append((idx, term, te, r['english']))
    pairs.append({
        'idx': idx, 'sent_id': r['sent_id'], 'title': r['title'],
        'term': term, 'term_type': r['term_type'],
        'meaning_in_this_sentence': meaning,
        'classical_sentence': r['classical'],
        'full_english': r['english'],
        'term_english': te, 'match_type': mt,
        'needs_revision': not bool(te) or mt == 'MISMATCH' or bool(note),
        'note': note,
    })

with open('data/term_sentence_pairs.jsonl', 'w', encoding='utf-8', newline='\n') as f:
    for p in pairs:
        f.write(json.dumps(p, ensure_ascii=False) + '\n')

# 清洗后词项池（按句聚合，去掉 del 项并改用修正后的 term/meaning）
by_sent = OrderedDict()
for p in pairs:
    by_sent.setdefault(p['sent_id'], {
        'id': p['sent_id'], 'title': p['title'],
        'classical_sentence': p['classical_sentence'], 'terms': []
    })['terms'].append({
        'term': p['term'], 'char_count': len([c for c in p['term'] if '\u4e00' <= c <= '\u9fff']),
        'term_type': p['term_type'], 'meaning_in_this_sentence': p['meaning_in_this_sentence'],
        'term_english': p['term_english'], 'needs_review': bool(p['needs_revision']),
    })
with open('data/terms_candidates_clean.jsonl', 'w', encoding='utf-8', newline='\n') as f:
    for v in by_sent.values():
        f.write(json.dumps(v, ensure_ascii=False) + '\n')

n = len(pairs)
labeled = sum(1 for p in pairs if p['term_english'])
sub = sum(1 for p in pairs if p['match_type'] == 'substring')
nr = sum(1 for p in pairs if p['needs_revision'])
print(f"总词项: {n}（del {stats['del']} 条已剔除 → 清洗后 {n}）")
print(f"标注: {labeled} / 未标注: {stats['unlabeled']}")
print(f"子串命中: {sub} ({sub/max(labeled,1)*100:.1f}% of labeled)")
print(f"needs_revision: {nr} ({nr/n*100:.1f}%)")
if problems:
    print('\n子串校验失败:')
    for p in problems:
        print(' ', p[0], p[1], '|', p[2][:60])
