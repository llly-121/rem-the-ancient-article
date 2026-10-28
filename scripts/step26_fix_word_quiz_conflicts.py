"""修复词级题库里的「同词多译」与碎片干扰项。

## 三类问题

1. **同词多译 ⇒ 一题里出现两个正确答案**
   step20/step24 拿「同一个词在别的句里的英译」当干扰项，可同一个文言词在不同
   句里译法不同（天下 → the world / the empire / the realm），于是
   「天下 → the world」的选项里出现 `the empire`，学生选哪个都对。

2. **正确答案本身是错译**
   上游把整句英译挂到虚词上：鼓（一鼓作气）→ `morale had already been lost`、
   对（对曰）→ `Cao Qufu said`、盖（盖失强援）→ `deprived of`。

3. **同词同义项重复题**
   天下有 21 张卡、释义都是「全国、整个天下」，21 道题考的是同一个点，选项还
   一模一样。留 1 道代表即可，其余标记重复、退出抽题池。

## 修法

按「词 × 义项」查 `word_quiz_tables.TABLE` 拿人工写好的答案与三条干扰项，
同组只保留第一道，其余标 `needs_manual`（导入器按「干扰项不足 3 条」过滤）。

## 幂等

按「该词在表里」触发，修过的题再跑一次结果不变。
"""

import collections
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'scripts'))

import step24_build_quiz_low as s24          # noqa: E402
import word_quiz_tables as W                 # noqa: E402

SRC = os.path.join(BASE, 'data', 'word_quiz.jsonl')
CARDS = os.path.join(BASE, 'data', 'word_cards.jsonl')
MANUAL = os.path.join(BASE, 'data', 'word_quiz_conflict_manual.jsonl')
BAK = SRC + '.bak_step26'


def match_entry(term, correct, meaning):
    """返回 (序号, 答案, 三条干扰项)。'=' 开头按英文子串，否则按中文释义子串。"""
    entries = W.TABLE.get(term)
    if not entries:
        return None
    for i, (matcher, cor, ds) in enumerate(entries):
        if matcher is None:
            return i, cor, ds
        if matcher.startswith('='):
            if matcher[1:].lower() in correct.lower():
                return i, cor, ds
        elif matcher in meaning:
            return i, cor, ds
    return None


def main():
    cards = [json.loads(l) for l in open(CARDS, encoding='utf-8')]
    by_id = {c['id']: c for c in cards}
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]

    manual = {}
    if os.path.exists(MANUAL):
        for l in open(MANUAL, encoding='utf-8'):
            rec = json.loads(l)
            manual[rec['id']] = rec

    st = collections.Counter()
    seen_group = {}
    retired, fixed, bad = [], [], []
    by_table = set()

    for r in rows:
        c = by_id[r['id']]

        # 0) 人工手写覆盖优先，并登记分组，避免后面的同类题重复出
        if r['id'] in manual:
            rec = manual[r['id']]
            ds = rec['distractors'][:3]
            r['correct'] = rec.get('correct') or r['correct']
            r['distractors'] = ds
            r['needs_manual'] = len(ds) < 3
            r['note'] = '' if len(ds) >= 3 else f'手写仅 {len(ds)} 条'
            st['manual'] += 1
            seen_group.setdefault((c['term'], 'manual'), r['id'])
            continue

        # 命中过的题把表项编号写进 tbl，重跑时直接复用。
        # 不能靠「按正确答案反查」——答案被覆盖后（第 4 条把
        # 'floored by' 改成 'was made the bottom'）原键就失配，会落到默认项
        # 再改一遍。踩过一次：第二遍跑完可出题从 1078 掉到 1071。
        key = r.get('tbl')
        if key and key.split('#')[0] == c['term']:
            entries = W.TABLE.get(c['term']) or []
            idx = int(key.split('#')[1])
            cor, ds = entries[idx][1], entries[idx][2]
        else:
            hit = match_entry(c['term'], r['correct'], c['meaning_in_this_sentence'])
            if not hit:
                continue
            idx, cor, ds = hit
        new_correct = cor or r['correct']

        # 同词同义项只留第一道；后面的标重复，退出抽题池
        gkey = (c['term'], idx)
        if gkey in seen_group:
            r['distractors'] = []
            r['correct'] = new_correct
            r['needs_manual'] = True
            r['note'] = f'同词同义项重复题，词义由 {seen_group[gkey]} 代表'
            retired.append(r['id'])
            st['retired'] += 1
            continue

        texts = [new_correct] + [d['text'] for d in ds]
        if len({s24.canon(x) for x in texts}) != 4:
            bad.append((r['id'], c['term'], texts))
            st['collision'] += 1
            continue

        r['correct'] = new_correct
        r['distractors'] = [dict(d) for d in ds]
        r['needs_manual'] = False
        r['note'] = ''
        r['tbl'] = f'{c["term"]}#{idx}'
        seen_group[gkey] = r['id']
        by_table.add(r['id'])
        fixed.append(r['id'])
        st['fixed'] += 1

    print('表内命中并重写 {0} 题，手写 {1} 题，标重复 {2} 题'.format(
        st['fixed'], st['manual'], st['retired']))
    if bad:
        print('\n选项与答案冲突（未改动）:')
        for bid, term, texts in bad:
            print(' ', bid, term, texts)
        print('  → 请检查 word_quiz_tables.py 对应条目')

    # 表覆盖检查：还有哪些词的选项里有同义项残留（表内重写过的题跳过——
    # 那些选项是刻意设计的误读，跟「同义项」不是一回事）
    by_term = collections.defaultdict(list)
    for c in cards:
        by_term[c['term']].append(c)
    leftover = []
    for r in rows:
        if r['needs_manual'] or r['id'] in by_table:
            continue
        c = by_id[r['id']]
        mine = c['meaning_in_this_sentence'].split('（')[0]
        for d in r['distractors']:
            for x in by_term[c['term']]:
                if x['term_english'] == d['text'] and s24.zh_sim(
                        mine, x['meaning_in_this_sentence'].split('（')[0]) >= 0.5:
                    leftover.append((r['id'], c['term'], d['text']))
                    break
    print('仍未覆盖的同义项干扰项:', len(leftover))
    for x in leftover[:10]:
        print('  ', x)

    if '--apply' in sys.argv:
        if not os.path.exists(BAK):
            with open(BAK, 'w', encoding='utf-8') as f:
                f.writelines(open(SRC, encoding='utf-8').readlines())
            print('\n备份 →', os.path.basename(BAK))
        with open(SRC, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        ok = sum(1 for r in rows if not r['needs_manual'] and len(r['distractors']) == 3)
        print('已落盘 {0} 题，其中可出题 {1} 题'.format(len(rows), ok))
    else:
        print('\n（试运行，加 --apply 落盘）')


if __name__ == '__main__':
    main()
