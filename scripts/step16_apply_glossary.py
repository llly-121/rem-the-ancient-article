# -*- coding: utf-8 -*-
"""step16: 按《专有名词对照表》回改三篇英译

流程：备份 → 逐句手改（MANUAL）→ 机械规范化（NORM）→ 写回 → 变更日志
不改动 classical / modern，只改 english。
"""
import json
import re
import shutil
import datetime

CARDS = 'data/course_cards_v2.jsonl'
GLOSS = 'data/proper_noun_glossary.json'
LOG = 'data/glossary_apply_log.jsonl'

cards = [json.loads(l) for l in open(CARDS, encoding='utf-8')]
gloss = json.load(open(GLOSS, encoding='utf-8'))

# ══════════ 一、逐句手改（依据对照表 + 中高考翻译标准） ══════════
MANUAL = {
    # ── 出师表 ──
    55: ("The late Emperor had not half accomplished his great enterprise when he died on the way. "
         "Now the realm is divided into three, and Yizhou is worn out and exhausted—this is truly the "
         "hour of crisis, of survival or ruin.",
         "主谓错配（大业 died）+「疲弊」误作人口稀少 +「天下」误作 three countries"),
    56: ("Yet the guards and attendants within the palace are untiring in their duty, and loyal and "
         "high-minded men outside risk their lives, because they recall the late Emperor's exceptional "
         "favour and wish to repay it to Your Majesty.",
         "「内」误作 in the DPRK（朝鲜）属严重误译 +「忠志之士」窄化为 generals +「侍卫之臣」误作 close officials"),
    59: ("In promotions and punishments, in praise and blame, there should be no difference: if any "
         "commit villainy and break the law, or prove loyal and good, they should be handed over to the "
         "officials in charge to determine their punishment or reward, so as to make plain Your Majesty's "
         "equitable and enlightened rule;",
         "「有司」统一为 the officials in charge（原 the proper officials 与别处不一致）"),
    64: ("Palace Attendants, Imperial Secretaries, Chief Secretaries and Staff Officers—all these are "
         "loyal and upright ministers who would die for principle. I hope Your Majesty will draw close to "
         "them and trust them; then the rise of the Han house may be counted on by the day.",
         "四个官名按字面拆译：长史误作 historiographers，尚书泛化为 government officials"),
    71: ("Now that the south has been pacified and our arms and equipment are sufficient, I should "
         "encourage and lead the whole army north to pacify the Central Plain. I would fain exhaust my "
         "poor powers, root out the treacherous and the evil, restore the Han house, and return to the "
         "old capital.",
         "「三军」误作 the military and civilian personnel（把军队译成军民，且增出民政）"),
    73: ("As for weighing measures and interests and tendering wholehearted loyal advice, that is the "
         "duty of Guo Youzhi, Fei Yi and Dong Yun.",
         "「祎」只留姓不留名（Fei），须还原为 Fei Yi"),
    75: ("If no words for the advancement of virtue are forthcoming, then blame the negligence of Guo "
         "Youzhi, Fei Yi and Dong Yun and the others, to make their fault plain;",
         "「攸之、祎、允」被拆成三个人名音节（You, Zhi, Yun），与第 73 句处理不一致"),

    # ── 廉颇蔺相如列传 ──
    364: ("In the sixteenth year of King Huiwen of Zhao, Lian Po led Zhao's army against Qi, crushed it, "
          "took Yangjin, and was appointed a High Minister, his courage famed among the lords.",
          "「上卿」误作 Chief Minister（丞相），混淆爵位与官职"),
    365: ("Lin Xiangru was a man of Zhao, a retainer of Miao Xian, Chief Eunuch of Zhao.",
          "「宦者令」误作 eunuch and governor（增出 governor 义）"),
    371: ("Miao Xian, the Chief Eunuch, said: 'My retainer Lin Xiangru can be sent.'",
          "「宦者令缪贤」被连读成人名 Ling Miuxian，官职与姓名未切分；「舍人」误作 guest"),
    377: ("You had better bare your shoulders and back, lie face down on the executioner's block and beg "
          "for punishment; you may then be pardoned by good fortune.",
          "「斧质」只译刀刃（the axe blade），丢砧板；「伏」误作 kowtow（叩头）"),
    403: ("The King of Qin was afraid that he would smash the jade to pieces, so he apologized, earnestly "
          "begged him not to, and summoned the officials in charge to examine the map, pointing out the "
          "fifteen cities from one place to another to be handed over to Zhao.",
          "「有司」统一；「秦王」规范为 the King of Qin"),
    413: ("I know that deceiving Your Majesty deserves death; I beg to be thrown into the boiling "
          "cauldron. I only hope that Your Majesty and the ministers will deliberate on this carefully.",
          "「汤镬」误作 boiled in oil（汤＝滚水，非油）"),
    417: ("When Xiangru returned, the King of Zhao, judging him a worthy Grand Master who had not "
          "disgraced his mission among the lords, appointed him a Grand Master of the Highest Rank.",
          "「上大夫」误作 Grand Minister，把爵称译成官职"),
    421: ("The King of Qin sent an envoy to tell the King of Zhao that he wished to hold a friendly "
          "meeting with him at Mianchi, beyond the land west of the Yellow River.",
          "「西河」误作 the West River（字面直译），应为黄河以西之地"),
    430: ("The historian of Qin stepped forward and wrote: 'On such-and-such a day of such-and-such a "
          "month and year, the King of Qin and the King of Zhao drank together, and he ordered the King "
          "of Zhao to play the zither.'",
          "「秦王与赵王」并存 King Qin / King Zhao 两种不规范形式"),
    443: ("When the meeting was over and he returned to his state, because Xiangru's merit was great the "
          "King of Zhao appointed him a High Minister, with rank above Lian Po.",
          "「蔺相如」误作 Lian Xiangru（把廉颇的姓拼上）+「上卿」误作 Prime Minister +「以」误作 believed that"),
    452: ("Lin Xiangru firmly held them back, saying: 'In your judgment, how does General Lian compare "
          "with the King of Qin?'",
          "「蔺相如」误作 Lian Xiangru，与「廉将军」同姓化"),
    458: ("Hearing this, Lian Po bared his shoulders and back, carried bramble thorns on his back, and "
          "led by one of his retainers came to Lin Xiangru's gate to beg pardon.",
          "英文句中残留中文「露出上身」；「负荆」误作 wicker stick（柳条）；「谢罪」弱化为 apologize"),
    460: ("In the end they were reconciled and became friends sworn to die for each other.",
          "「刎颈之交」逐字直译为 neck-cutting friends，整体义丢失"),

    # ── 过秦论 ──
    319: ("Duke Xiao of Qin, holding the fastness of Mount Xiao and the Hangu Pass and possessing the "
          "land of Yongzhou, with ruler and ministers firmly guarding it and eyeing the Zhou royal house, "
          "cherished the ambition to sweep up the world, wrap up the whole realm, gather in the four seas "
          "and swallow the eight wilds.",
          "「崤函」误作 Xiao and Han（函谷关混作韩／汉）"),
    322: ("After Duke Xiao died, King Huiwen, King Wu and King Zhaoxiang carried on the old enterprise and "
          "followed the bequeathed policy: south they took Hanzhong, west they seized Ba and Shu, east "
          "they cut off the fertile lands, north they gathered in the strategic commanderies.",
          "「惠文、武、昭襄」省略了「王」与国名，英文成三个孤立音节"),
    325: ("At that time Qi had Lord Mengchang, Zhao Lord Pingyuan, Chu Lord Chunshen, and Wei Lord Xinling.",
          "战国四公子为封君，误作 King；且 Meng Chang / Chun Shen 名字拆错（应连写）"),
    334: ("Passing to King Xiaowen and King Zhuangxiang, their reigns were brief and the state knew no "
          "alarm.",
          "「孝文王、庄襄王」丢失「王」称号"),
    352: ("Moreover, the world was not small or weak: the land of Yongzhou and the fastness of Mount Xiao "
          "and the Hangu Pass were as they had always been.",
          "「崤函」同 319 句错法；「自若」误作 remained as before（应为「依然如故」，可接受但需与地名同步）"),
    360: ("then it made the Six Directions its home and Mount Xiao and the Hangu Pass its palace;",
          "「崤函」误作 Xiao-Han（与 319 句又不同形）"),

    426: ("If you have not returned within thirty days, we beg leave to install the crown prince as "
          "king, so as to cut off the hopes of Qin.",
          "英文句中残留中文「妄想」，属未译出；「以绝秦望」的「望」是念头、指望，非妄想"),

    373: ("Miao Xian replied: 'I once committed a crime and secretly planned to flee to Yan. My "
          "retainer Xiangru stopped me, saying: How do you know the King of Yan?'",
          "HF 语料原文在 Why do you... 处截断（quiz 抽样时发现），补全句末问句「君何以知燕王？」，"
          "句式与 #372「何以知之」平行；另「臣舍人相如」的「舍人」误作 guest，统一为 retainer（与 365 句一致）"),

    375: ("Xiangru said to me: 'Zhao is strong and Yan weak, and you enjoy the King of Zhao's favour, "
          "so the King of Yan wished to befriend you.'",
          "「谓臣曰」＝（相如）对我说，臣是缪贤自称；原译 told my messenger 把「臣」误作信使，与 #374 同型"),

    536: ('The guest said: "Lord Xu is not as handsome as you."',
          "「徐公不若君之美」主客颠倒（translation_issues T 项收口）：徐公是比照对象，"
          "须居主语位；your appearance is not as handsome as yours 语义不通"),

    374: ("I told him: 'I once followed Your Majesty to a meeting with the King of Yan on the border; "
          "the King of Yan privately took my hand and said, \"I wish to make friends with you.\" That is "
          "how I knew, and so I wanted to go there.'",
          "「臣语曰」＝我（缪贤）告诉（他）说，原译 My messenger said 把「臣」误作 messenger、"
          "「语」误作 said，主客双错"),

    # ── 机械规范化后的残留（第二轮核查发现）──
    366: ("During the reign of King Huiwen of Zhao, the Heshi Bi was obtained from Chu.",
          "「赵惠文王」音译错作 Huaiwen，应为 Huiwen（赵惠文王，非秦惠文王）"),
    367: ("King Zhaoxiang of Qin heard of it and sent a letter to the King of Zhao, wishing to trade "
          "fifteen cities for the jade.",
          "「秦昭王」被误作 King Zhao of Qin（读成「秦国的赵王」），须还原为 King Zhaoxiang of Qin"),
    431: ("Lin Xiangru came forward and said: 'The King of Zhao has privately heard that the King of Qin "
          "excels in the music of Qin; may I present this basin to the King of Qin for our mutual "
          "entertainment?'",
          "「赵王窃闻」的主语是赵王，译文原用 I 把主语换成了蔺相如本人，主体错置"),
    433: ("Then Xiangru stepped forward to offer the basin, and kneeling begged the King of Qin to play it.",
          "「跪请秦王」的宾语 the King of Qin 被简化为 him，专名丢失"),
}

# ══════════ 二、机械规范化（适用于未手改的句子） ══════════
NORM = [
    # 注意：'King Zhao of Qin'（秦昭王的错误英译形态）不能被下面的规则二次拆解
    (re.compile(r'(?<![Tt]he )\bKing Qin\b'), 'the King of Qin'),
    (re.compile(r'(?<![Tt]he )\bKing Zhao\b(?! of Qin)'), 'the King of Zhao'),
    (re.compile(r'(?<![Tt]he )\bKing of Qin\b'), 'the King of Qin'),
    (re.compile(r'(?<![Tt]he )\bKing of Zhao\b'), 'the King of Zhao'),
    (re.compile(r'\bking of Qin\b'), 'the King of Qin'),
    (re.compile(r'\bking of Zhao\b'), 'the King of Zhao'),
    (re.compile(r'\bMiu Xian\b'), 'Miao Xian'),
    (re.compile(r'\bMiuxian\b'), 'Miao Xian'),
    (re.compile(r'\bHuaiwen\b'), 'Huiwen'),
]
SENT_START = [
    (re.compile(r'(^|[.!?;:—]\s+|\"\s*)the King of Qin'), r'\1The King of Qin'),
    (re.compile(r'(^|[.!?;:—]\s+|\"\s*)the King of Zhao'), r'\1The King of Zhao'),
]

scope = set(gloss['scope'])
stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
shutil.copy2(CARDS, CARDS.replace('.jsonl', f'.bak_{stamp[:10]}.jsonl'))

logs = []
for i, c in enumerate(cards):
    if c['title'] not in scope:
        continue
    old = c['english'] or ''
    new = old
    reason = ''
    if i in MANUAL:
        new, reason = MANUAL[i]
        new = re.sub(r'\s+', ' ', new).strip()
    else:
        for pat, rep in NORM:
            new = pat.sub(rep, new)
        for pat, rep in SENT_START:
            new = pat.sub(rep, new)
        # 清理重复冠词（The the / the the）
        new = re.sub(r'\bThe the\b', 'The', new)
        new = re.sub(r'\bthe the\b', 'the', new)
        if new != old:
            reason = '专名规范化（秦王／赵王统一为 the King of + 国名）'
    if new != old:
        c['english'] = new
        logs.append({'idx': i, 'title': c['title'], 'classical': c['classical'],
                     'old_english': old, 'new_english': new,
                     'mode': 'manual' if i in MANUAL else 'normalize',
                     'reason': reason})

with open(CARDS, 'w', encoding='utf-8') as f:
    for c in cards:
        f.write(json.dumps(c, ensure_ascii=False) + '\n')

with open(LOG, 'w', encoding='utf-8') as f:
    for r in logs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f'回改完成：{len(logs)} 句（手改 {sum(1 for r in logs if r["mode"]=="manual")} + '
      f'机械规范化 {sum(1 for r in logs if r["mode"]=="normalize")}）')
print(f'变更日志：{LOG}')
print('备份：', CARDS.replace('.jsonl', f'.bak_{stamp[:10]}.jsonl'))
print('\n机械规范化明细：')
for r in logs:
    if r['mode'] == 'normalize':
        print(f"  #{r['idx']} [{r['title']}] {r['classical'][:26]}")
