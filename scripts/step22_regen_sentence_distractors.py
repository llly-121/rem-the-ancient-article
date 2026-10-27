#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
step22_regen_sentence_distractors.py — 按「错误类型」生成句级干扰项

为什么重做 step20 的做法：
    step20 把 correct 里该 term 的英文片段，换成该词在**别句**里的 term_english。
    但 term_english 是短语级、随句而变（曰 → "They would surely say"），跨句替换必然崩坏，
    产出 "His fellow villagers They would surely say: ..." 这种一眼假的句子。

本模块只做「语法安全」的变换：每条变换都不改词性、不动搭配，只翻转语义。
    NEG_DROP       删去否定词                    → 肯定/否定颠倒
    NEG_TO_ALWAYS  never → always                → 否定变全称肯定
    NEG_ADD        句无否定时插入 not            → 肯定变否定
    CONJ_FLIP      if↔unless / because↔although  → 逻辑关系反转
    NUM_SHIFT      明确大数错位（十五→五十）      → 数量错
    COPULA_TENSE   判断句 is→was / are→were      → 现在判断误作过去

刻意**不用**的变换（已实测会产出崩坏英文，故废弃）：
    DIR_FLIP     old→new 会把专名改成 "New Drunkard's"，方向词换位又常生 "near below"
    SCOPE_SHIFT  each→no 生成 "no competed"
    MODAL_SHIFT  might→shall 落到名词位生成 "accumulated shall"
    POSS_FLIP    his→their 区分度过弱，学生无从判断
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'data', 'sentence_quiz.jsonl')

NUM_MAP = {
    'fifteen': 'fifty', 'fifty': 'fifteen',
    'thirteen': 'thirty', 'thirty': 'thirteen',
    'fourteen': 'forty', 'forty': 'fourteen',
    'sixteen': 'sixty', 'sixty': 'sixteen',
    'seventeen': 'seventy', 'seventy': 'seventeen',
    'eighteen': 'eighty', 'eighty': 'eighteen',
    'thousand': 'hundred', 'hundred': 'thousand',
    'ten thousand': 'a thousand', 'a thousand': 'ten thousand',
}
CONJ_MAP = {
    'because': 'although', 'although': 'because',
    'if': 'unless', 'unless': 'if',
    'when': 'before', 'before': 'after', 'after': 'before',
    'so that': 'unless',
}
NEG_TOKENS = [' not', ' never', "n't", ' no ', 'cannot', 'none ', 'nothing ']
HAS_NEG = re.compile(r"\b(not|never|no|none|nothing|nobody|cannot|neither|nor)\b|n't")
AUX = ['will', 'would', 'can', 'could', 'shall', 'should', 'may', 'might', 'must',
       'is', 'are', 'was', 'were', 'has', 'have', 'had', 'does', 'do', 'did']


def tidy(s):
    """删除替换后必须重排空白，否则会拼出 'hadtime' 这类词"""
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s+([,.;:!?])', r'\1', s)
    s = re.sub(r'([,;:])(?=\S)', r'\1 ', s)
    return s.strip()


def apply_word_map(text, mapping):
    for old, new in mapping.items():
        pat = re.compile(r'\b' + re.escape(old) + r'\b', re.IGNORECASE)
        m = pat.search(text)
        if m:
            orig = m.group(0)
            rep = new
            if orig[0].isupper():
                rep = rep[0].upper() + rep[1:]
            return tidy(text[:m.start()] + rep + text[m.end():]), f'{orig}→{rep}'
    return None


def neg_drop(text):
    # 必须用词边界：朴素 find(' not') 会在 " notes" 里命中 " not" 的前四字符，
    # 删掉后得到 "lingering  es" 这种垃圾
    pat = re.compile(r"\b(not|never|no|none|nothing|cannot)\b|n't", re.IGNORECASE)
    m = pat.search(text)
    if m:
        tok = m.group(0)
        low = tok.lower()
        if low == 'cannot':
            # cannot = can + not，只能去掉 not，不能整个删掉，否则 "this suddenly be won"
            rep = 'Can' if tok[0].isupper() else 'can'
            new = text[:m.start()] + rep + text[m.end():]
        elif low == "n't":
            new = text[:m.start()] + text[m.end():]      # isn't → is
        else:
            new = text[:m.start()] + ' ' + text[m.end():]
        return tidy(new), f'删去否定「{tok}」'
    return None


def neg_to_always(text):
    m = re.search(r'\bnever\b', text)
    if m:
        orig = m.group(0)
        rep = 'Always' if orig[0].isupper() else 'always'
        return tidy(text[:m.start()] + rep + text[m.end():]), 'never→always（否定变全称肯定）'
    return None


def neg_add(text):
    if HAS_NEG.search(text):
        return None
    for aux in AUX:
        m = re.search(r'\b' + aux + r'\b', text)
        if m:
            return tidy(text[:m.end()] + ' not' + text[m.end():]), f'在 {aux} 后插入 not'
    return None


def copula_tense(text):
    """判断句专用：is→was / are→were（现在判断误作过去）"""
    for old, new in ((' is ', ' was '), (' are ', ' were ')):
        idx = text.find(old)
        if idx >= 0:
            return tidy(text[:idx] + new + text[idx + len(old):]), f'{old.strip()}→{new.strip()}'
    return None


ERR_DESC = {
    'NEG_DROP': '否定脱落：原文的否定被译成了肯定',
    'NEG_TO_ALWAYS': '否定变全称：把「从不/未曾」译成了「总是」',
    'NEG_ADD': '无中生有：原文无否定，译文却加了否定',
    'CONJ_FLIP': '逻辑关系反转：因果、条件或时间先后被译反',
    'NUM_SHIFT': '数量错位：数字或量级被译错',
    'COPULA_TENSE': '时态错位：把「是」的现在判断译成了过去',
}


def gen(correct, sentence_type=''):
    out = []
    plans = [
        ('NEG_DROP', neg_drop),
        ('NEG_TO_ALWAYS', neg_to_always),
        ('CONJ_FLIP', lambda t: apply_word_map(t, CONJ_MAP)),
        ('NUM_SHIFT', lambda t: apply_word_map(t, NUM_MAP)),
        ('NEG_ADD', neg_add),
    ]
    if sentence_type in ('判断句', '疑问句'):
        plans.insert(2, ('COPULA_TENSE', copula_tense))

    for code, fn in plans:
        r = fn(correct)
        if not r:
            continue
        text, note = r
        if text == correct or text in [o['text'] for o in out]:
            continue
        out.append({
            'text': text,
            'error_type': code.lower(),
            'explanation': f'{ERR_DESC[code]}（{note}）',
        })
        if len(out) >= 3:
            break
    return out


def main():
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
    if '--stats' in sys.argv:
        import collections
        dist = collections.Counter()
        for r in rows:
            dist[len(gen(r['correct'], r['sentence_type']))] += 1
        print('每题可生成数:', dict(sorted(dist.items())))
        print(f'凑满 3 条: {dist[3]} / {len(rows)}')
        return

    ids = sys.argv[1:] or ['s0033', 's0122', 's0177', 's0515']
    for r in rows:
        if r['id'] in ids:
            print('=' * 74)
            print(f"{r['id']} [{r['sentence_type']}] {r['classical_sentence']}")
            print('正:', r['correct'])
            for d in gen(r['correct'], r['sentence_type']):
                print(f"  [{d['error_type']}] {d['text']}")


if __name__ == '__main__':
    main()
