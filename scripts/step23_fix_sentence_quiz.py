#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
step23_fix_sentence_quiz.py — 句级题库「清洗 + 补齐」一体化

三步：
  1. 删崩坏干扰项（step20 跨句替换 term_english 的产物）
       blacklist      含 "They would surely say" / "he styled himself" 等已确认的坏短语
       long_fragment  被塞入 >4 个英文词（整句碎片）
       punct          替换引入额外句读标点
  2. 删等价干扰项（与正确项同义，导致一题多解）
       case_only      仅大小写不同
       synonym        同义组内互换（therefore/so/then/thereupon、the world/the empire…）
  3. 用 step22 的错误类型变换补齐到 3 条；仍不足则标记 needs_manual

用法：
    python scripts/step23_fix_sentence_quiz.py              # dry-run
    python scripts/step23_fix_sentence_quiz.py --apply      # 落盘（自动备份）
"""
import json
import os
import re
import sys
import shutil
import difflib
import collections
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from step22_regen_sentence_distractors import gen  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'data', 'sentence_quiz.jsonl')
MANUAL = os.path.join(BASE, 'data', 'sentence_quiz_manual.jsonl')

TOK = re.compile(r"[A-Za-z']+|[^\sA-Za-z']")
SUBJ = {'They', 'He', 'She', 'It', 'We', 'You', 'This', 'These', 'Those', 'There'}
# 功能词/连接词被塞进句中位置 = 主语粘连（"is The reason the Way"）。
# 不用「所有大写词」判定，否则会误杀专名（"prepared Yueyang Tower" 是正常替换）。
FUNC_CAPS = {'The', 'A', 'An', 'This', 'That', 'These', 'Those', 'It', 'They', 'He', 'She',
             'We', 'You', 'I', 'There', 'But', 'And', 'So', 'Yet', 'If', 'When', 'Then',
             'Therefore', 'Thus', 'However', 'Because', 'Although', 'Moreover', 'Besides'}
BLACK = ('would surely say', 'styled himself', 'would surely')

SYN_GROUPS = [
    {'so', 'then', 'therefore', 'thereupon', 'thus', 'hence', 'consequently'},
    {'the world', 'the empire', 'the realm', 'all under heaven', 'the country'},
    {'lin xiangru', 'xiangru', 'lian xiangru', 'prime minister xiang', 'minister xiang'},
    {'believe', 'i believe', 'think', 'hold'},
    {'said', 'replied', 'answered'},
    {'the king of zhao', 'king zhao', 'the zhao king'},
]


def syn_group(phrase):
    p = phrase.lower().strip()
    for g in SYN_GROUPS:
        if p in g:
            return g
    return None


def broken(correct, dist):
    """返回崩坏原因，或 None"""
    a = TOK.findall(correct)
    b = TOK.findall(dist)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        new = b[j1:j2]
        old = a[i1:i2]
        words = [t for t in new if re.match(r"[A-Za-z']", t)]
        prev = a[i1 - 1] if i1 > 0 else ''
        joined = ' '.join(new).lower()
        if any(x in joined for x in BLACK):
            return 'blacklist'
        if len(words) > 4:
            return 'long_fragment'
        if new and new[0] in SUBJ and prev and (prev[-1].isalnum() or prev in ',;:'):
            return 'subject_splice'
        if new and new[0] in FUNC_CAPS and prev and (prev[-1].isalnum() or prev in ',;:—'):
            return 'subject_splice'
        if any(t in ',;.!?' for t in new) and not any(t in ',;.!?' for t in old):
            return 'punct'
        # 名词短语 → 介词短语，句子就没了主语（"Now the realm is divided" → "Now in the world is divided"）
        if old and old[0].lower() in ('the', 'a', 'an') and new \
                and new[0].lower() in ('in', 'at', 'on', 'of', 'to', 'for', 'with', 'by', 'from'):
            return 'prep_splice'
    return None


def equivalent(correct, dist):
    """返回等价原因，或 None"""
    a = TOK.findall(correct)
    b = TOK.findall(dist)
    diffs = [(a[i1:i2], b[j1:j2])
             for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
             if tag != 'equal']
    if len(diffs) != 1:
        return None
    old, new = diffs[0]
    co = ' '.join(old).lower().strip()
    cn = ' '.join(new).lower().strip()
    if co == cn:
        return 'case_only'
    go, gn = syn_group(co), syn_group(cn)
    if go and gn and go is gn:
        return 'synonym'
    return None


def dedup_key(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", ' ', s)
    s = re.sub(r'\b(a|an|the)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    apply = '--apply' in sys.argv
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]

    # 人工手写覆盖：命中则整题采用手写干扰项，不再走自动流程
    manual = {}
    if os.path.exists(MANUAL):
        for l in open(MANUAL, encoding='utf-8'):
            m = json.loads(l)
            manual[m['id']] = m['distractors']

    st = collections.Counter()
    handled = set()
    manual_list = []

    for r in rows:
        if r['id'] in manual:
            ds = manual[r['id']]
            r['distractors'] = ds[:3]
            r['needs_manual'] = len(ds) < 3
            r['note'] = '' if len(ds) >= 3 else f'手写仅 {len(ds)} 条'
            handled.add(r['id'])
            st['manual_' + ('ok' if not r['needs_manual'] else 'short')] += 1
            continue

    for r in rows:
        if r['id'] in handled:          # 手写题不再走自动清洗，否则会把人工条目再删一遍
            if not r['needs_manual']:
                st['playable'] += 1
            continue
        keep = []
        for d in r['distractors']:
            why = broken(r['correct'], d['text'])
            if why:
                st['del_' + why] += 1
                continue
            eq = equivalent(r['correct'], d['text'])
            if eq:
                st['del_' + eq] += 1
                continue
            keep.append(d)
            st['kept_total'] += 1

        seen = {dedup_key(r['correct'])}
        uniq = []
        for d in keep:
            k = dedup_key(d['text'])
            if k and k not in seen:
                seen.add(k)
                uniq.append(d)

        for d in gen(r['correct'], r['sentence_type']):
            k = dedup_key(d['text'])
            if k and k not in seen and len(uniq) < 3:
                seen.add(k)
                uniq.append(d)
                st['added_auto'] += 1

        r['distractors'] = uniq[:3]
        if len(r['distractors']) < 3:
            r['needs_manual'] = True
            r['note'] = f'仅 {len(r["distractors"])} 个可用干扰项，需人工补写'
            manual_list.append((r['id'], r['sentence_type'], len(r['distractors']),
                           r['classical_sentence'][:34]))
            st['needs_manual'] += 1
        else:
            r['needs_manual'] = False
            r['note'] = ''
            st['playable'] += 1

    print('=== 清洗统计 ===')
    for k in sorted(st):
        print(f'  {k:20s} {st[k]}')
    print(f'\n可出题 {st["playable"]} / {len(rows)}  需人工 {st["needs_manual"]}')

    print('\n=== 需人工补写的题（按句式）===')
    by_type = collections.Counter(m[1] for m in manual_list)
    print(' ', dict(by_type))
    for m in manual_list[:25]:
        print(f'  {m[0]} [{m[1]}] 缺{3-m[2]}条 | {m[3]}')

    if not apply:
        print('\n[dry-run] 未写盘。加 --apply 执行。')
        return

    bak = SRC + '.bak_step23_' + datetime.now().strftime('%Y%m%d_%H%M')
    shutil.copy2(SRC, bak)
    with open(SRC, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'\n已写盘 {SRC}\n备份 {bak}')


if __name__ == '__main__':
    main()
