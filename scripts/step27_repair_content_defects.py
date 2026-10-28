#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
step27_repair_content_defects.py — 交付前最后一轮内容缺陷修复 + 质检闸门

修复三类缺陷（同一根因的不同变体）：
  A. 词条级错译污染下游：及 → "At the prefecture seat"、延/及 → "Passing to"
     这两个短语是 term_english 错译，既出现在卡片里，也被当成干扰项塞进词题/句题。
  B. 同义等价干扰项：天下 → the world / the empire；先帝 → late / former emperor
     拿同义译文当干扰项 = 两个正确答案。
  C. 跨句替换造成的语法崩坏：of in the world、the empire's、's's、
     "terrorised Qin's might"（丢介词）、"so he beg pardon"（动词形态）等。

做法：手写替换表（(id, 选项下标, 正确答案内旧串, 新串)），新文本由 correct 派生，
保证句子骨架不被破坏；每条都断言旧串在 correct 中恰好出现一次。

用法：
    python scripts/step27_repair_content_defects.py            # 只质检（默认）
    python scripts/step27_repair_content_defects.py --apply    # 修复并质检
"""
import collections
import difflib
import json
import os
import re
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(BASE, 'data', *p)

# ---------------------------------------------------------------- A. 卡片错译
CARD_FIX = [
    ('word_cards.jsonl', 'w0220', 'term_english', 'At the prefecture seat', 'reached'),
    ('word_cards.jsonl', 'w0704', 'term_english', 'Passing to', 'extended to'),
    ('word_cards.jsonl', 'w0705', 'term_english', 'Passing to', 'extended'),
    ('sentence_cards.jsonl', 's0335', 'full_english',
     'Passing to King Xiaowen', 'Extending to King Xiaowen'),
]

# ------------------------------------------------------------ B. 句题 correct
SENT_CORRECT_FIX = [
    ('s0446', 'If I meet Lian Xiangru', 'If I meet Lin Xiangru'),      # 廉颇 vs 蔺相如：上游译名混用
    ('s0449', 'Lian Xiangru quickly asked', 'Xiangru quickly asked'),
    ('s0335', 'Passing to King Xiaowen', 'Extending to King Xiaowen'),
]

# ------------------------------------------------- 全字段文本修正（含 correct）
TXT_FIX = [
    ('s0346', 'his son sons and grandsons', 'his sons and grandsons'),   # 上游译文笔误
]

# ------------------------------------------------------- C. 句题干扰项重建表# (id, idx, correct 中的旧串, 新串, error_type, 中文解释)
SENT_OPT = [
    # 天下 → the empire（同义）
    ('s0027', 0, 'To be the first in the world to worry, and the last in the world to rejoice',
     'To be the last in the world to worry, and the first in the world to rejoice',
     'wrong_logic', '「先天下之忧而忧，后天下之乐而乐」是先忧后乐，此处把先后颠倒'),
    ('s0027', 1, 'first in the world to worry', 'first in the court to worry',
     'wrong_sense', '「天下」指天下人，非「朝廷」'),
    ('s0056', 0, 'Now the realm is divided into three', 'Now the realm is divided into two',
     'wrong_num', '「今天下三分」是分为三国，不是两分'),
    ('s0056', 1, 'Now the realm is divided into three', 'Now the court is divided into three',
     'wrong_sense', '「天下」指全国，非「朝廷」'),
    ('s0330', 0, 'the lords of the world', 'the lords of the court',
     'wrong_sense', '「天下诸侯」指天下各国诸侯，非朝中大臣'),
    ('s0330', 1, 'the lords of the world', 'the kings of the world',
     'wrong_sense', '「诸侯」是受封的国君，不等同于「天下的王」'),
    ('s0330', 2, 'were already exhausted', 'were not yet exhausted',
     'wrong_neg', '「已困矣」是已经疲惫，否定词把意思反转'),
    ('s0333', 0, 'split the rivers and mountains', 'united the rivers and mountains',
     'wrong_logic', '「分裂山河」是分裂国土，非统一'),
    ('s0333', 1, 'carved up the world', 'carved up the court',
     'wrong_sense', '「宰割天下」的对象是天下，非朝廷'),
    ('s0333', 2, 'split the rivers and mountains', 'split the states of Zhao and Wei',
     'wrong_sense', '「山河」泛指国土，不是特指赵、魏两国'),
    ('s0343', 0, 'collected the arms of the world', 'collected the horses of the world',
     'wrong_sense', '「收天下之兵」的「兵」是兵器，不是马匹'),
    ('s0343', 1, 'gathered them at Xianyang', 'gathered them at Luoyang',
     'wrong_sense', '「聚之咸阳」是集中到咸阳，不是洛阳'),
    ('s0343', 2, 'cast them into twelve golden giants', 'cast them into twelve bronze bells',
     'wrong_sense', '「铸以为金人十二」是铸成十二个铜人，不是铜钟'),
    ('s0351', 0, 'the world gathered like clouds', 'the world scattered like clouds',
     'wrong_logic', '「云集响应」是像云一样聚集，非四散'),
    ('s0351', 1, 'the world gathered like clouds', 'the feudal lords gathered like clouds',
     'wrong_sense', '「天下」指天下百姓，不只是诸侯'),
    ('s0351', 2, 'answered like echo', 'answered like thunder',
     'wrong_sense', '「响应」是像回声一样应和，不是雷声'),
    ('s0353', 0, 'the world was not small or weak', 'the world was small and weak',
     'wrong_neg', '「非小弱也」是否定判断，去掉否定就反了'),
    ('s0353', 1, 'the world was not small or weak', 'the court was not small or weak',
     'wrong_sense', '「天下」指天下疆土，非朝廷'),
    ('s0353', 2, 'were as they had always been', 'had all been lost',
     'wrong_logic', '「自若也」是依然如故，非丧失'),
    ('s0557', 0, 'the struggles in the world stop', 'the struggles in the court stop',
     'wrong_sense', '「天下熄」指天下战乱止息，非朝廷内部'),
    ('s0557', 1, 'the struggles in the world stop', 'the struggles among the princes stop',
     'wrong_sense', '「天下」指天下，非仅诸侯之间'),
    ('s0557', 2, 'the struggles in the world stop', 'the struggles in the world continue',
     'wrong_logic', '「熄」是止息，不是继续'),
    # 先帝 → late / former emperor（同义）
    ('s0057', 0, "recall the late Emperor's exceptional favour",
     "recall the late Emperor's harsh punishment",
     'wrong_sense', '「殊遇」是特殊的恩遇，非严惩'),
    ('s0057', 1, 'wish to repay it to Your Majesty', 'wish to repay it to the court',
     'wrong_role', '「报之于陛下」的受事是陛下本人，非朝廷'),
    ('s0073', 0, 'to express my gratitude to the late Emperor',
     'to express my resentment to the late Emperor',
     'wrong_sense', '「报先帝」是报答，非抱怨'),
    ('s0073', 1, 'to fulfil my duty of loyalty to Your Majesty',
     'to fulfil my duty of loyalty to the court',
     'wrong_role', '「忠陛下」的对象是陛下本人，非朝廷'),
    ('s0075', 0, 'report it to the spirit of the late Emperor',
     'report it to the spirit of Heaven',
     'wrong_sense', '「以告先帝之灵」是禀告先帝之灵，不是告天'),
    ('s0075', 1, 'then punish my crime', 'then reward my merit',
     'wrong_sense', '「治臣之罪」是治罪，非赏功'),
    # 跨句替换造成的语法崩坏
    ('s0277', 0, 'the people of the empire', 'the people of the capital',
     'wrong_sense', '「天下之人」指天下人，非京城之人'),
    ('s0277', 1, 'the people of the empire', 'the nobles of the empire',
     'wrong_sense', '「天下之人」是百姓，非贵族'),
    ('s0316', 1, "yet terrorised by Qin's accumulated might",
     "yet trusting in Qin's accumulated might",
     'wrong_sense', '「为秦人积威之所劫」是被胁迫，非倚仗'),
    ('s0318', 0, "their power weaker than Qin's", "their power stronger than Qin's",
     'wrong_logic', '「其势弱于秦」是弱于秦，非强于秦'),
    ('s0318', 1, 'were all feudal lords', 'were all barbarian tribes',
     'wrong_sense', '「皆诸侯」是诸侯国，非蛮夷'),
    ('s0362', 1, 'a laughing-stock to the world', 'a warning to the world',
     'wrong_sense', '「为天下笑」是被天下耻笑，非警示'),
    ('s0392', 1, 'The King of Qin sat on the Zhangtai stage',
     'The King of Qin was punished on the Zhangtai stage',
     'wrong_sense', '「坐章台」是坐在章台，非获罪受罚'),
    ('s0392', 2, 'The King of Qin sat on the Zhangtai stage',
     'The King of Qin stood on the Zhangtai stage',
     'wrong_sense', '「坐」是坐着接见，非站立'),
    ('s0393', 1, 'passed around to his concubines and attendants',
     'passed around to his generals and ministers',
     'wrong_sense', '「美人及左右」是妃嫔与近侍，非将相大臣'),
    ('s0393', 2, 'passed around to his concubines and attendants',
     'passed around to his concubines alone',
     'wrong_sense', '「及左右」不可漏译，除妃嫔外还有近侍'),
    ('s0404', 1, 'so he apologized', 'so he sighed',
     'wrong_sense', '「辞谢」是婉言道歉，非叹气'),
    ('s0404', 2, 'so he apologized', 'so he grew angry',
     'wrong_logic', '「辞谢固请」是道歉并坚决请求，非发怒'),
    ('s0369', 0, 'to give it', 'to take it',
     'wrong_logic', '「欲予秦」是想给秦国，非夺取'),
    ('s0369', 1, 'they would be deceived in vain', 'they would gain the cities in vain',
     'wrong_logic', '「徒见欺」是白白被欺骗，非白白得城'),
    ('s0369', 2, 'consulted with General Lian Po', 'quarrelled with General Lian Po',
     'wrong_sense', '「谋」是商议，非争吵'),
    ('s0289', 0, 'they could not survive alone', 'they could survive alone',
     'wrong_neg', '「不能独完」是不能独自保全，否定词被删'),
    ('s0289', 2, 'deprived of strong allies', 'relying on strong allies',
     'wrong_sense', '「失强援」是失去强援，非倚仗强援'),
    ('s0198', 0, "the gentlemen's wisdom proves less than theirs",
     "the gentlemen's wisdom proves greater than theirs",
     'wrong_logic', '「其智乃反不能及」是反而比不上，非超过'),
    ('s0198', 1, "the gentlemen's wisdom proves less than theirs",
     "the officials' wisdom proves less than theirs",
     'wrong_sense', '「君子」指士大夫，此处说的是君子之智，非泛指官员'),
    ('s0201', 0, 'not the equal of Confucius in worth', 'not the equal of Confucius in age',
     'wrong_sense', '「其贤不及孔子」说的是才德，非年龄'),
    ('s0201', 1, 'Men like Tanzi', 'The disciples of Tanzi',
     'wrong_sense', '「郯子之徒」指郯子这一类人，非其弟子'),
    ('s0357', 0, 'could not match the men of former times',
     'could not surpass the men of former times',
     'wrong_logic', '「非及乡时之士」是比不上，非超过'),
    ('s0357', 1, 'the men of former times', 'the men of later times',
     'wrong_time', '「乡时」是从前，非后世'),
    ('s0532', 0, 'how could Lord Xu compare with you', 'how could the King of Qi compare with you',
     'wrong_role', '「徐公」是齐国的美男子徐公，非齐王'),
    ('s0335', 0, 'their reigns were brief', 'their reigns were long',
     'wrong_logic', '「享国之日浅」是在位时间短，非长'),
    ('s0335', 2, 'the state knew no alarm', 'the state was in turmoil',
     'wrong_logic', '「国家无事」是国中太平，非动乱'),
    ('s0407', 2, 'fast for five days', 'fast for three days',
     'wrong_num', '「斋五日」是五天，非三天'),
    ('s0408', 1, 'escaped from the small road', 'escaped along the main road',
     'wrong_sense', '「从径道亡」是走小路，非大路'),
    ('s0437', 1, 'were all shocked and stepped back', 'all drew their swords',
     'wrong_logic', '「左右皆靡」是都退却了，非拔刀'),
    ('s0459', 2, "came to Lin Xiangru's gate", 'came to the gate of the King of Zhao',
     'wrong_role', '「至蔺相如门」是到蔺相如门前，非赵王宫门'),
    ('s0617', 0, 'and the governors of the two provinces',
     'but also to the people of the two provinces',
     'wrong_role', '「二州牧伯」是两州的长官，非百姓'),
    ('s0617', 1, 'are plainly known not only to', 'are not plainly known even to',
     'wrong_neg', '「非独……所见明知」是不仅被……明明白白知道，改成 not even 反转'),
    # 「相如」简称 vs 全称：同一人，不能互斥
    ('s0366', 1, 'Xiangru was a man of Zhao', 'Xiangru was a man of Qin',
     'wrong_sense', '「赵人也」是赵国人，非秦国人'),
    ('s0403', 1, 'looked obliquely at the pillar', 'looked straight at the pillar',
     'wrong_sense', '「睨柱」是斜着眼看柱子，非直视'),
    ('s0446', 0, 'If I meet Lin Xiangru', 'If I meet Lian Po',
     'wrong_role', '「我见相如」指蔺相如，非廉颇'),
    ('s0449', 1, 'Not long after, Xiangru went out', 'Not long after, Lian Po went out',
     'wrong_role', '「相如出」是蔺相如出门，非廉颇'),
    ('s0394', 0, 'giving a city to Zhao', 'taking a city from Zhao',
     'wrong_logic', '「偿赵城」是给赵国城池，非从赵国夺取'),
    ('s0346', 0, 'The world had been pacified', 'The world had been divided',
     'wrong_sense', '「天下已定」是天下已安定，非已分裂'),
    # 换人名（廉相如）不算翻译错误，改成实义错误
    ('s0366', 0, 'Chief Eunuch of Zhao.', 'Chief Minister of Zhao.',
     'wrong_role', '「宦者令」是宦官之长，非国相'),
    ('s0388', 0, 'go as envoy.', 'go as a hostage.',
     'wrong_sense', '「往使」是去做使者，非去做人质'),
    ('s0403', 0, 'and was about to hit it.', 'and was about to strike the King of Qin.',
     'wrong_sense', '「欲以击柱」是想拿璧撞柱子，非袭击秦王'),
    ('s0407', 1, 'stay in the Guangcheng guesthouse.', 'stay in the Zhangtai palace.',
     'wrong_sense', '「舍相如广成传」是安置在广成传舍，非章台宫'),
    ('s0408', 0, 'sending the treasure back to the State of Zhao.',
     'sending the treasure back to the State of Qin.',
     'wrong_sense', '「归璧于赵」是把璧送回赵国，非秦国'),
    ('s0409', 1, 'the envoy of Zhao, Lin Xiangru.', 'the envoy of Qin, Lin Xiangru.',
     'wrong_sense', '「赵使者」是赵国的使者，非秦国'),
    ('s0437', 0, 'glared at the attendants and yelled', 'glared at the King of Qin and yelled',
     'wrong_sense', '「叱之」叱的是左右侍从，非秦王'),
    ('s0446', 1, 'definitely humiliate him.', 'definitely apologise to him.',
     'wrong_sense', '「必辱之」是必定羞辱他，非向他道歉'),
    ('s0446', 2, 'will definitely humiliate him.', 'will kill him on sight.',
     'wrong_sense', '「辱之」是羞辱，非杀害'),
    ('s0449', 0, 'to avoid him.', 'to drive forward and greet him.',
     'wrong_logic', '「引车避匿」是掉转车头躲开，非上前迎接'),
    ('s0449', 2, 'to avoid him.', 'to follow him at a distance.',
     'wrong_sense', '「避匿」是躲避，非远远跟随'),
    ('s0459', 0, 'bared his shoulders and back', 'put on his armour',
     'wrong_sense', '「肉袒」是脱去上衣露出身体，非穿上铠甲'),
]


# ------------------------------------------- 句子整体重写（绝对文本，幂等覆盖）
# 这一批是 step22「跨句塞入 term_english」的残留：把词义硬塞进语法槽位，
# 产出 "Without such men"→"slightly, with whom..." / "to borrowed" 这类破碎英文。
# 无法用替换修补，只能整条重写；错误仍落在「否定/数量/对象/方向」这些可判读的点上。
SENT_CORRECT_TEXT = {
    's0281': 'Those who destroyed the Qin were the Qin themselves, not the rest of the world.',
    's0485': "When the sovereign's orders must be sped, one sometimes leaves Baidi at dawn and reaches Jiangling by dusk—a thousand two hundred li between; even riding a galloping horse or the wind, one would not be swifter.",
}

SENT_REWRITE = [
    # 微斯人，吾谁与归？
    ('s0028', 0, 'With such men, with whom should I associate?',
     'wrong_neg', '「微」是假设否定（如果没有），译成肯定即反转原意'),
    ('s0028', 1, 'Without such men, with whom should I take my leave?',
     'wrong_sense', '「归」是归依、同归，非辞别'),
    ('s0028', 2, 'Without such men, with whom should I return home?',
     'wrong_sense', '「谁与归」问与谁同道，非问与谁回家'),
    # 见渔人，乃大惊，问所从来
    ('s0093', 0, 'Seeing the fisherman, they were not astonished and asked where he came from.',
     'wrong_neg', '「乃大惊」是极为惊讶，非毫不惊讶'),
    ('s0093', 1, 'Seeing the fisherman, they were greatly astonished and asked where he was going.',
     'wrong_sense', '「所从来」是问他从哪里来，非往哪里去'),
    ('s0093', 2, 'Seeing the fisherman, they were greatly astonished and asked who he was.',
     'wrong_sense', '「问所从来」问的是来历，非身份'),
    # 既出，得其船，便扶向路，处处志之
    ('s0102', 0, 'Once out, he found his boat and followed the new route back, marking the way everywhere.',
     'wrong_sense', '「向路」是从前走过的路，非新路'),
    ('s0102', 1, 'Once out, he lost his boat and followed the old route back, marking the way everywhere.',
     'wrong_logic', '「得其船」是找到船，非丢失'),
    ('s0102', 2, 'Once out, he found his boat and followed the old route back, marking nothing along the way.',
     'wrong_neg', '「处处志之」是处处做标记，非不做标记'),
    # 全石以为底
    ('s0109', 0, 'The whole pool is lined with one stone; near the shore the curved stone bottom curls up, forming islets, islelets, crags and rocks of various shapes.',
     'wrong_sense', '「全石以为底」是整块石头作池底，非用石头镶砌'),
    ('s0109', 1, 'The whole pool is floored by many stones; near the shore the curved stone bottom curls up, forming islets, islelets, crags and rocks of various shapes.',
     'wrong_num', '「全石」是一整块石头，非许多块'),
    # 君子生非异也，善假于物也
    ('s0159', 0, 'The intelligence and nature of a gentleman are no different from that of an ordinary person, it is only that a gentleman is different in nature from ordinary people.',
     'wrong_logic', '「生非异也」正说天性没有差别，不能再说天性不同'),
    ('s0159', 1, 'The intelligence and nature of a gentleman are no different from that of an ordinary person, it is only that a gentleman is good at borrowing things from other people.',
     'wrong_sense', '「假于物」是借助外物，非向人借东西'),
    ('s0159', 2, 'The intelligence and nature of a gentleman are no different from that of an ordinary person, it is only that a gentleman refuses to rely on external things.',
     'wrong_logic', '「善假于物」是善于借助外物，非拒绝依靠'),
    # 师道之不传也久矣
    ('s0184', 0, 'Alas, the tradition of honouring teachers has long been well transmitted!',
     'wrong_neg', '「之不传」是不流传，非流传久远'),
    # 客有吹洞箫者，倚歌而和之
    ('s0217', 0, 'One of the guests played the dongxiao flute, drowning out the song.',
     'wrong_sense', '「和之」是依歌应和，非盖过歌声'),
    ('s0217', 1, 'One of the guests played the dongxiao flute, ignoring the song.',
     'wrong_sense', '「倚歌而和」是随着歌声应和，非不理歌声'),
    ('s0217', 2, 'One of the guests played the dongxiao flute, and the song stopped.',
     'wrong_logic', '箫声与歌声相和，歌并未停止'),
    # 方其破荆州，下江陵
    ('s0224', 0, 'When he broke Jingzhou and lost Jiangling, sailing east down the stream, his prows stretched a thousand li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; and where is he now?',
     'wrong_logic', '「下江陵」是攻下江陵，非丢失江陵'),
    ('s0224', 1, 'When he broke Jingzhou and took Jiangling, sailing west up the stream, his prows stretched a thousand li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; and where is he now?',
     'wrong_sense', '「顺流而东」是顺流向东，非逆流向西'),
    ('s0224', 2, 'When he broke Jingzhou and took Jiangling, sailing east down the stream, his prows stretched a hundred li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; and where is he now?',
     'wrong_num', '「舳舻千里」是千里，非百里'),
    # 相与枕藉乎舟中
    ('s0240', 0, 'Lying apart in the boat, they knew not how the east grew light.',
     'wrong_sense', '「枕藉」是交错枕着睡，非各睡各的'),
    ('s0240', 1, 'Pillowed on one another in the boat, they knew how the east grew light.',
     'wrong_neg', '「不知」是没察觉，非察觉'),
    ('s0240', 2, 'Pillowed on one another in the boat, they knew not how the west grew dark.',
     'wrong_sense', '「东方之既白」是天已亮，非西边天黑'),
    # 族秦者，秦也，非天下也
    ('s0281', 0, 'Those who destroyed the Qin were the Six States, not the rest of the world.',
     'wrong_role', '「秦也」指秦国自身，非六国'),
    ('s0281', 1, 'Those who destroyed the Qin were the Qin themselves, and also the rest of the world.',
     'wrong_logic', '「非天下也」是并非天下人，不能说「也是」'),
    ('s0281', 2, 'Those who preserved the Qin were the Qin themselves, not the rest of the world.',
     'wrong_sense', '「族秦」是灭掉秦国，非保全'),
    # 使六国各爱其人
    ('s0282', 0, 'Had the Six States each hated their people, they would have been enough to resist Qin.',
     'wrong_sense', '「爱其人」是爱护百姓，非憎恶'),
    ('s0282', 1, 'Had the Six States each loved their people, they would have been unable to resist Qin.',
     'wrong_logic', '「足以拒秦」是足以抵抗秦国，非不能'),
    ('s0282', 2, 'Had Qin each loved the people of the Six States, they would have been enough to resist Qin.',
     'wrong_role', '「使六国各爱其人」主语是六国，非秦'),
    # 使秦复爱六国之人
    ('s0283', 0, 'Had Qin again hated the people of the Six States, it could have passed down through three generations to ten thousand, and who could have destroyed its line?',
     'wrong_sense', '「复爱」是重新爱护，非憎恶'),
    ('s0283', 1, 'Had Qin again loved the people of the Six States, it could have passed down through thirty generations to ten thousand, and who could have destroyed its line?',
     'wrong_num', '「递三世」是传三世，非三十世'),
    ('s0283', 2, 'Had Qin again loved the people of the Six States, it could not have passed down through three generations to ten thousand, and who could have destroyed its line?',
     'wrong_neg', '「可至万世」是能传至万世，非不能'),
    # 赂秦而力亏
    ('s0287', 0, 'Resisting Qin drained their strength—that was the road to destruction.',
     'wrong_sense', '「赂秦」是贿赂秦国，非抵抗秦国'),
    ('s0287', 1, 'Bribing Qin strengthened them—that was the road to destruction.',
     'wrong_logic', '「力亏」是国力亏损，非增强'),
    # 子孙视之不甚惜，举以予人
    ('s0296', 0, 'Their heirs held them of little worth, keeping them from others like discarding a blade of grass.',
     'wrong_logic', '「举以予人」是拿来送人，非扣住不给'),
    ('s0296', 1, 'Their heirs held them of great worth, handing them over to others like discarding a blade of grass.',
     'wrong_sense', '「不甚惜」是不很爱惜，非极为珍视'),
    # 然后践华为城
    ('s0344', 0, 'Then he made Mount Hua his wall and the Yellow River his moat, holding the city walls a hundred million feet high and looking down on the fathomless deep, deeming it dangerous.',
     'wrong_logic', '「以为固」是认为坚固，非认为危险'),
    ('s0344', 1, 'Then he made Mount Hua his wall and the Yellow River his moat, holding the city walls a hundred million feet high and looking up at the fathomless deep, deeming it secure.',
     'wrong_sense', '「临不测之渊」是居高俯视深渊，非仰望'),
    # 然秦以区区之地，致万乘之势
    ('s0360', 1, 'Yet Qin, from a mere patch of ground, attained the weakness of ten thousand chariots, marshalled the eight provinces and made its fellow lords pay court, for more than a hundred years;',
     'wrong_logic', '「万乘之势」是万乘之势，非衰弱'),
    ('s0360', 2, 'Yet Qin, from a vast territory, attained the might of ten thousand chariots, marshalled the eight provinces and made its fellow lords pay court, for more than a hundred years;',
     'wrong_sense', '「区区之地」是小小的地方，非广袤疆土'),
    # 廉颇为赵将伐齐
    ('s0365', 0, 'In the sixteenth year of King Huiwen of Zhao, Lian Po led Zhao\'s army against Qi, crushed it, took Yangjin, and was dismissed as High Minister, his courage famed among the lords.',
     'wrong_logic', '「拜为上卿」是被任命为上卿，非被罢免'),
    ('s0365', 1, 'In the sixteenth year of King Huiwen of Zhao, Lian Po led Zhao\'s army against Qi, crushed it, lost Yangjin, and was appointed a High Minister, his courage famed among the lords.',
     'wrong_logic', '「取阳晋」是攻取阳晋，非丢失'),
    ('s0365', 2, 'In the sixteenth year of King Huiwen of Zhao, Lian Po led Qi\'s army against Zhao, crushed it, took Yangjin, and was appointed a High Minister, his courage famed among the lords.',
     'wrong_role', '廉颇是赵将伐齐，非齐将伐赵'),
    # 臣以为布衣之交尚不相欺
    ('s0395', 0, 'I believe that even ordinary people may deceive each other, let alone great nations!',
     'wrong_neg', '「尚不相欺」是尚且不欺骗，非可以欺骗'),
    ('s0395', 1, 'I believe that even kings and ministers should not deceive each other, let alone great nations!',
     'wrong_sense', '「布衣之交」指平民之间的交往，非君臣'),
    ('s0395', 2, 'I do not believe that even ordinary people should not deceive each other, let alone great nations!',
     'wrong_logic', '「臣以为」是臣认为，非不认为'),
    # 赵王以为贤大夫
    ('s0418', 0, 'When Xiangru returned, the King of Zhao, judging him an unworthy Grand Master who had not disgraced his mission among the lords, appointed him a Grand Master of the Highest Rank.',
     'wrong_sense', '「贤大夫」是贤能的大夫，非不贤'),
    ('s0418', 1, 'When Xiangru returned, the King of Zhao, judging himself a worthy Grand Master who had not disgraced his mission among the lords, appointed him a Grand Master of the Highest Rank.',
     'wrong_role', '「以为贤大夫」是赵王认为相如贤能，非赵王自认为'),
    # 拜为上卿，位在廉颇之右
    ('s0444', 0, 'When the meeting was over and he returned to his state, because Xiangru\'s merit was great the King of Zhao appointed him a High Minister, with rank below Lian Po.',
     'wrong_sense', '「位在廉颇之右」是位次在廉颇之上，秦汉以右为尊'),
    ('s0444', 1, 'When the meeting was over and he returned to his state, because Lian Po\'s merit was great the King of Zhao appointed him a High Minister, with rank above Lian Po.',
     'wrong_role', '「以相如功大」说的是相如功大，非廉颇'),
    ('s0444', 2, 'When the meeting was over and he returned to his state, because Xiangru\'s merit was great the King of Zhao dismissed him from High Minister, with rank above Lian Po.',
     'wrong_logic', '「拜为上卿」是任命为上卿，非免职'),
    # 乃下令
    ('s0546', 0, 'So he issued a warning: "Ministers, officials and people who face-reprove my faults to me shall receive the highest reward;"',
     'wrong_sense', '「下令」是下达命令，非发出警告'),
    ('s0546', 1, 'So he issued an order: "Ministers, officials and people who face-reprove my faults to me shall receive the lowest reward;"',
     'wrong_logic', '「受上赏」是得上等奖赏，非下等'),
    ('s0546', 2, 'So he issued an order: "Ministers, officials and people who praise my virtues to me shall receive the highest reward;"',
     'wrong_sense', '「面刺寡人之过」是当面指摘过错，非赞美'),
    # 家贫，无从致书以观
    ('s0624', 0, 'My family was poor and could obtain books to read, so I often borrowed from families with collections, copied them out by hand, and counted the days to return them on time.',
     'wrong_neg', '「无从致书」是没办法得到书，非能够得到'),
    ('s0624', 1, 'My family was rich and could not obtain books to read, so I often borrowed from families with collections, copied them out by hand, and counted the days to return them on time.',
     'wrong_sense', '「家贫」是家境贫寒，非富有'),
    ('s0624', 2, 'My family was poor and could not obtain books to read, so I often bought books from families with collections, copied them out by hand, and counted the days to return them on time.',
     'wrong_sense', '「假借」是借来，非买来'),
    # 以是人多以书假余
    ('s0627', 0, 'That is why most people were unwilling to lend me books, and so I was able to read widely.',
     'wrong_neg', '「多以书假余」是大多愿意借给我，非不愿'),
    ('s0627', 1, 'That is why most people were willing to lend others books, and so I was able to read widely.',
     'wrong_role', '「假余」是借给我，非借给别人'),
    ('s0627', 2, 'That is why most people were willing to lend me books, and so I was unable to read widely.',
     'wrong_logic', '「得遍观群书」是能广泛阅读，非不能'),
    # 至于负者歌于途…（「至于」被换成别的义项，句首碎裂）
    ('s0044', 0, 'Nevertheless, carriers singing on the road, travellers resting under trees, those in front calling and those behind answering, old bent folk leading children by the hand, coming and going without cease—that is the people of Chu on their excursions.',
     'wrong_logic', '「至于」在此是转折连词「至于」，非「然而」式的强转折'),
    ('s0044', 1, 'Moreover, carriers singing on the road, travellers resting under trees, those in front calling and those behind answering, old bent folk leading children by the hand, coming and going without cease—that is the people of Chu setting out for war.',
     'wrong_sense', '「滁人游也」是滁州人出游，非出征'),
    ('s0044', 2, 'Moreover, riders singing on the road, travellers resting under trees, those in front calling and those behind answering, old bent folk leading children by the hand, coming and going without cease—that is the people of Chu on their excursions.',
     'wrong_sense', '「负者」是背着东西的人，非骑马的人'),
    # 至于斟酌损益…（同上）
    ('s0074', 0, 'As for weighing measures and interests and tendering wholehearted loyal advice, that is not the duty of Guo Youzhi, Fei Yi and Dong Yun.',
     'wrong_neg', '「则攸之、祎、允之任也」正是这几位臣子的职责'),
    ('s0074', 1, 'As for weighing measures and interests and tendering flattering advice, that is the duty of Guo Youzhi, Fei Yi and Dong Yun.',
     'wrong_sense', '「进尽忠言」是进献忠言，非进献谄媚之言'),
    ('s0074', 2, 'As for weighing measures and interests and tendering wholehearted loyal advice, that is the duty of the King of Shu alone.',
     'wrong_role', '「攸之、祎、允之任」是郭攸之等人的职责，非君主独任'),
    # 圣人之所以为圣
    ('s0189', 0, 'Is it not all from this that the sage became a fool and the fool became a sage?',
     'wrong_role', '圣愚的结果被对调'),
    ('s0189', 1, 'Is it not all from this that the sage was born sage and the fool was born fool?',
     'wrong_logic', '本句强调「出于此」即后天成因，非天生'),
    # 至于夏水襄陵
    ('s0484', 0, 'In summer the waters recede from the hills, blocking both down and upstream passage.',
     'wrong_logic', '「夏水襄陵」是水涨上山陵，非退落'),
    ('s0484', 1, 'In summer the waters swell to the hills, leaving both down and upstream passage open.',
     'wrong_logic', '「沿溯阻绝」是上下航路都被阻断，非畅通'),
    ('s0484', 2, 'In winter the waters swell to the hills, blocking both down and upstream passage.',
     'wrong_time', '「夏水」是夏季水涨，非冬季'),
    # 诸侯恐惧（主语短语被换后丢了大写与数的一致）
    ('s0324', 0, 'The emperor was thus filled with dread and consternation, meeting to form alliances and deliberate on countermeasures to weaken Qin.',
     'wrong_role', '「诸侯」是各诸侯国，非天子'),
    ('s0324', 1, 'The lords were thus filled with joy and delight, meeting to form alliances and deliberate on countermeasures to weaken Qin.',
     'wrong_logic', '「恐惧」是恐惧，非欣喜'),
    ('s0324', 2, 'The nobles were thus filled with dread and consternation, meeting to submit to Qin.',
     'wrong_logic', '「谋弱秦」是谋划削弱秦国，非臣服于秦'),
    # 城北徐公（只需补大写，语义错在「徐」与「公」）
    ('s0533', 1, 'The slow gentleman in the north of the city is a handsome man in Qi.',
     'wrong_sense', '「徐公」是姓徐的先生，非「缓慢的绅士」'),
    ('s0533', 2, 'The Duke of Xu in the north of the city is a handsome man in Qi.',
     'wrong_role', '「徐公」是尊称徐姓男子，非封君'),
    # 赂秦而力亏（补大写）
    ('s0287', 2, 'The lands given to Qin drained their strength—that was the road to destruction.',
     'wrong_sense', '「赂秦」是贿赂秦国，译成「割让的土地」偷换了主语'),
    # 有时朝发白帝，暮到江陵（正确答案本身也是半截句，整题重写）
    ('s0485', 0, "When the sovereign's orders must be sped, one sometimes leaves Baidi at dawn and reaches Jiangling by dusk—a thousand two hundred li between; even riding a galloping horse or the wind, one would be much slower.",
     'wrong_logic', '「不似疾也」是还不如它快，非慢得多'),
    ('s0485', 1, "When the sovereign's orders must be sped, one sometimes leaves Baidi at dawn and reaches Jiangling by dusk—a hundred and twenty li between; even riding a galloping horse or the wind, one would not be swifter.",
     'wrong_num', '「千二百里」是一千二百里，非一百二十里'),
    ('s0485', 2, "When the sovereign's orders must be sped, one sometimes leaves Jiangling at dawn and reaches Baidi by dusk—a thousand two hundred li between; even riding a galloping horse or the wind, one would not be swifter.",
     'wrong_sense', '「朝发白帝，暮到江陵」是从白帝到江陵，方向被倒置'),
]

# ------------------------------------------------------------- 词题修复表
WORD_CORRECT_FIX = [
    ('w0705', 'Passing to', 'extended'),      # 延及孝文王：延 = 延续、延伸到
]
WORD_OPT = [
    ('w0705', 0, 'invited', 'wrong_sense', '「延及」的「延」是延续、延伸到，非邀请'),
    ('w0705', 1, 'delayed', 'wrong_sense', '「延」在此为延及（时间上延续到），非拖延'),
    ('w0705', 2, 'cut short', 'wrong_logic', '「延及」是延续下去，与截断相反'),
    ('w0004', 0, 'In the same year', 'wrong_time', '「越明年」是到第二年，非同年'),
    ('w0004', 1, 'Ten years later', 'wrong_num', '「越明年」只隔一年，非十年后'),
    ('w0212', 0, 'delayed', 'wrong_sense', '「延」在此为延请、邀请，非拖延'),
    ('w0692', 0, 'invited', 'wrong_sense', '「延」在此为迎击（延敌），非邀请'),
    ('w0703', 0, 'Weak states', 'wrong_sense', '「强国」是强国，非弱国'),
    ('w1374', 0, 'Leaving the lodge', 'wrong_logic', '「至舍」是到达客舍，非离开'),
    ('w1374', 1, 'At the city gate', 'wrong_sense', '「舍」是客舍，非城门'),
]

# --------------------------------------------------------------- 质检规则
TOK = re.compile(r"[A-Za-z']+|[^\sA-Za-z']")
ART = ('At the prefecture seat', 'Passing to', 'at the prefecture seat', 'passing to')
PREP = r'(?:of|in|on|at|to|for|with|from|by|into|upon|within|without)'
# 「speakable of in the same breath」里 of 属于形容词搭配，不是介词叠用
ALLOW = ('of in the same breath', 'speakable of in')
RX = {
    'artifact': re.compile('|'.join(re.escape(a) for a in ART)),
    'prep_double': re.compile(r'\b' + PREP + r'\s+' + PREP + r'\b', re.I),
    'poss_double': re.compile(r"'s's\b|\bs's\b"),
    'verb_form': re.compile(r'\b(?:he|she|it|Qin|Xiangru|Zhao)\s+(?:beg|decline|give|take|agree|consult|refuse|accept)\b', re.I),
}
BAD_CAP = {'At', 'In', 'On', 'Of', 'To', 'For', 'With', 'By', 'From', 'Passing', 'Only',
           'But', 'And', 'So', 'Yet', 'Then', 'When', 'If', 'Unless', 'Because', 'Although',
           'Moreover', 'Besides', 'Now', 'It', 'There', 'Having', 'Being'}
SYN = [
    (r'\bthe (world|empire|realm|country)\b', 'THEWORLD'),
    (r'\ball under heaven\b', 'THEWORLD'),
    (r'\b(late|former) emper(or|ess)\b', 'LATEEMPEROR'),
    (r'\b(so|then|therefore|thereupon|thus|hence|consequently)\b', 'THEREFORE'),
]


def canon(s):
    t = s.lower()
    for p, r in SYN:
        t = re.sub(p, r, t)
    t = re.sub(r"[^a-z0-9 ]+", ' ', t)
    t = re.sub(r'\b(a|an|the)\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def cap_splice(t):
    """句中突然出现大写功能词（跨句碎片的典型痕迹）"""
    for m in re.finditer(r'(?<=[a-z,;:])\s+([A-Z][a-z]+)', t):
        if m.group(1) in BAD_CAP:
            # 排除从句首/引号后等正常位置
            pre = t[:m.start()].rstrip()
            if pre and pre[-1] not in ':;.!?"\u201c':
                return m.group(1)
    return None


def poss_splice(correct, dist):
    """替换把某个词换成了所有格（the world → the empire's），句子就崩了。
    只在「原位置不是所有格、新位置是所有格」时判定，避免误伤正常的 Qin's / man's。"""
    a = TOK.findall(correct)
    b = TOK.findall(dist)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        new, old = b[j1:j2], a[i1:i2]
        if new and new[-1].lower().endswith("'s") \
                and not (old and old[-1].lower().endswith("'s")):
            return new[-1]
    return None


def balanced(s):
    return all(s.count(a) == s.count(b) for a, b in (('（', '）'), ('「', '」'), ('『', '』')))


def truncated(s):
    """上游按字符数硬截断：要么括号没闭合，要么以「…」收尾。"""
    return (not balanced(s)) or bool(re.search(r'…\s*[）」』]?$', s))


def fix_expl(e):
    """修复被字符截断的解释，保留释义主体，只砍掉不完整的尾巴。

    模板形如「误取『X』在他句的义项（通『嘱』，劝酒（举匏尊以相属：举葫芦杯互相劝…）」，
    上游在固定字数处切断，留下悬空的内层括号。策略：
      1. 前缀（第一个顶层「（」之前）原样保留；
      2. 正文里找到**第一个顶层开括号**，从这里砍断 —— 它对内层引例，砍掉不影响释义；
      3. 没有内层括号时，退到最后一个顶层分隔符，砍掉半截分句；
      4. 补齐收尾「）」。
    绝不再整段删除括号内容（早前一版这么做，释义信息量掉得太多）。"""
    if not e:
        return e
    if not truncated(e):
        return e
    body0 = re.sub(r'[）」』…\s]+$', '', e)
    i = body0.find('（')
    prefix, body = (body0[:i], body0[i + 1:]) if i >= 0 else (body0, '')
    if not body:
        return e

    cut = -1
    depth = 0
    for k, ch in enumerate(body):
        if ch == '（':
            if depth == 0 and k > 0:
                cut = k           # 第一个顶层内嵌括号：从这里砍
                break
            depth += 1
        elif ch == '）':
            depth = max(0, depth - 1)
    if cut < 0:
        depth = 0
        for k, ch in enumerate(body):
            if ch == '（':
                depth += 1
            elif ch == '）':
                depth = max(0, depth - 1)
            elif ch in '，、；：,;' and depth == 0:
                cut = k
    cand = body[:cut].rstrip('，、；：,; ') if cut >= 0 else body.rstrip('，、；：,; ')
    if not cand or not re.search(r'[\u4e00-\u9fffA-Za-z]', cand):
        return e

    if i >= 0:
        return f'{prefix}（{cand}）'
    return cand


# 上游释义在这些位置被截断，尾句只剩半截，整段丢掉更干净
TAIL_FIX = {'语意完整处为句': '语意完整处为句、语意未完处为读'}
TAIL_DROP = {
    '本句为', '本句为外交', '本句为廉', '本句谓', '本句谓项', '本句谓引其', '本句谓蒙受',
    '本句谓蔺相如位', '本句谓源中人', '本句指天下诸', '本句指受秦威', '本句与骐骥',
    '语意未', '由九名傧相', '秦联合六', '秦联合六国分别击破的', '意为全部占',
    '指内政修明不战而', '诸葛亮追述时',
}


def drop_tail(e):
    m = re.search(r'[，、；：]([^，、；：（）「」『』]{2,12})[）]$', e)
    if not m:
        return e
    tail = m.group(1)
    if tail in TAIL_FIX:
        return e[:m.start()] + '，' + TAIL_FIX[tail] + '）'
    if tail in TAIL_DROP:
        return e[:m.start()] + '）'
    return e


# 上游模板本身重复套嵌 / 尾部残留，逐条定向清理（一次性模式，跑过即消失，天然幂等）
EXPL_RULES = [
    # X」在本句为「①本句为『到达」，…  →  X」在本句为「到达」，…
    (re.compile('\u672c\u53e5\u4e3a\u300c[\u2460-\u2463]?\u672c\u53e5\u4e3a([^\u300e\u300d]{0,4})\u300e([^\u300d\u300f]*)\u300f?\u300d'),
     lambda m: '\u672c\u53e5\u4e3a\u300c' + m.group(1) + m.group(2) + '\u300d'),
    # …（固定结构『无）」）  →  …
    (re.compile('\uff08[^\uff08\uff09]*\uff09\u300d\uff09$'), lambda m: '\u300d'),
    (re.compile('\uff0c\uff09'), '\uff09'),
    # 个别过短的模板化解释补全
    (re.compile('\u8bef\u4f5c\u95ee\u65f6\u95f4'),
     '\u300c\u4f55\u4ee5\u300d\u95ee\u51ed\u501f\u4ec0\u4e48\uff0c\u6b64\u5904\u95ee\u7684\u662f\u4f9d\u636e\uff0c\u4e0d\u662f\u65f6\u95f4'),
    # 本句为「本句为… → 本句为「…
    (re.compile('\u672c\u53e5\u4e3a\u300c\u672c\u53e5\u4e3a'), '\u672c\u53e5\u4e3a\u300c'),
    # 本句为「『只是』」 → 本句为「只是」
    (re.compile('\u672c\u53e5\u4e3a\u300c\u300e([^\u300f]*)\u300f\u300d'), '\u672c\u53e5\u4e3a\u300c\\1\u300d'),
    # 名词活用类解释补全
    (re.compile('\uff08\u672c\u53e5\u4e3a\u540d\u8bcd\u4f5c\u52a8\u8bcd\u300e\u8d50\u798f\uff09'),
     '\uff08\u672c\u53e5\u540d\u8bcd\u4f5c\u52a8\u8bcd\uff0c\u4e49\u4e3a\u300c\u8d50\u798f\u300d\uff09'),
    (re.compile('\uff08\u672c\u53e5\u4e3a\u540d\u8bcd\u4f5c\u72b6\u8bed\u300e\u50cf\u86c7\u722c\u884c\u4e00\uff09'),
     '\uff08\u672c\u53e5\u540d\u8bcd\u4f5c\u72b6\u8bed\uff0c\u4e49\u4e3a\u300c\u50cf\u86c7\u4e00\u6837\u722c\u884c\u300d\uff09'),
    (re.compile('\uff08\u672c\u53e5\u300e\u5919\u5a74\u75be\u75c5\u300f\u4e4b\u5919\u4e3a\u300e\u4e45\uff09'),
     '\uff08\u300e\u5919\u5a74\u75be\u75c5\u300f\u4e2d\u5919\u4e3a\u300c\u65e9\u300d\u4e49\uff0c\u4e0e\u6b64\u5904\u4e0d\u540c\uff09'),
]


def repair_brackets(s):
    """按栈修复括号/引号：收尾符对不上时先补齐内层，多余的收尾符直接丢弃。

    上游截断会留下「（非『劲疾）」）」这类错配序列，机器无法知道原意，
    但可以肯定的是：每个「（」「『」都必须有对应的收尾。"""
    pairs = {'（': '）', '「': '」', '『': '』'}
    closers = {v: k for k, v in pairs.items()}
    out, st = [], []
    for ch in s:
        if ch in pairs:
            out.append(ch)
            st.append(ch)
        elif ch in closers:
            while st and pairs[st[-1]] != ch:
                # 内层没闭合：先补上内层的收尾符，直到外层能对上
                out.append(pairs[st.pop()])
            if st and pairs[st[-1]] == ch:
                out.append(ch)
                st.pop()
            elif not st:
                continue                      # 多余的收尾符，丢掉
            else:
                out.append(ch)                # 忍不了的情况，原样保留
        else:
            out.append(ch)
    for op in reversed(st):
        out.append(pairs[op])
    return ''.join(out)


def tidy_expl(e):
    """定向清理模板套嵌与尾部残迹，最后统一修复错配的括号/引号。"""
    if not e:
        return e
    for _ in range(4):
        before = e
        for rx, rep in EXPL_RULES:
            e = rx.sub(rep, e)
        if e == before:
            break
    return repair_brackets(e)


def check(rows, kind):
    bad = []
    for r in rows:
        ds = r.get('distractors') or []
        c = r.get('correct') or ''
        if len(ds) == 0:
            continue                      # 退役题（义项簇去重后主动退出抽题池）
        if len(ds) < 3:
            bad.append((r['id'], 'count', f'{len(ds)} 条'))
        texts = [c] + [d['text'] for d in ds]
        if len(set(texts)) != len(texts):
            bad.append((r['id'], 'dup', '选项重复'))
        cn = canon(c)
        for i, d in enumerate(ds):
            t = d['text']
            for name, rx in RX.items():
                if kind == 'word_quiz.jsonl' and name == 'bare_poss':
                    continue          # 词题干扰项本身是短语，结尾 's 属正常所有格
                m = rx.search(t)
                if m and any(a in t for a in ALLOW):
                    continue
                if m:
                    bad.append((r['id'], name, f'[{i}] {m.group(0)}'))
            if kind != 'word_quiz.jsonl':
                ps = poss_splice(c, t)
                if ps:
                    bad.append((r['id'], 'poss_splice', f'[{i}] {ps}'))
            cap = cap_splice(t)
            if cap:
                bad.append((r['id'], 'cap_splice', f'[{i}] {cap}'))
            if canon(t) == cn:
                bad.append((r['id'], 'equivalent', f'[{i}] {t[:60]}'))
            expl = d.get('explanation') or ''
            if len(expl) < 4:
                bad.append((r['id'], 'no_expl', f'[{i}]'))
            elif not balanced(expl):
                bad.append((r['id'], 'expl_unbal', f'[{i}] {expl[:34]}'))
            elif re.search(r'.{8,}(?<!…)…(?!…)[」）]', expl):
                bad.append((r['id'], 'expl_cut', f'[{i}] {expl[:34]}'))
    return bad


def apply_sent(rows):
    by_id = {r['id']: r for r in rows}
    for sid, old, new in TXT_FIX:
        r = by_id[sid]
        for f in ('correct',):
            if old in r[f]:
                r[f] = r[f].replace(old, new)
        for d in r['distractors']:
            if old in d['text']:
                d['text'] = d['text'].replace(old, new)
    for sid, old, new in SENT_CORRECT_FIX:
        r = by_id[sid]
        if old not in r['correct']:
            assert new in r['correct'], (sid, old)
            continue
        assert r['correct'].count(old) == 1, (sid, old)
        r['correct'] = r['correct'].replace(old, new)
    done = skipped = 0
    for sid, idx, old, new, et, expl in SENT_OPT:
        r = by_id[sid]
        assert r['correct'].count(old) == 1, (sid, old, r['correct'])
        txt = r['correct'].replace(old, new)
        d = r['distractors'][idx]
        if d['text'] == txt:
            skipped += 1
            continue
        assert d['text'] != txt
        d['text'], d['error_type'], d['explanation'] = txt, et, expl
        done += 1
    return done, skipped


def apply_rewrite(rows):
    """整句重写：直接覆盖成人工写好的文本，重复执行无副作用。"""
    by = {r['id']: r for r in rows}
    n = 0
    for sid, idx, text, et, expl in SENT_REWRITE:
        r = by[sid]
        d = r['distractors'][idx]
        if d['text'] == text and d['error_type'] == et and d['explanation'] == expl:
            continue
        assert text != r['correct'], (sid, idx)
        d['text'], d['error_type'], d['explanation'] = text, et, expl
        n += 1
    for sid, text in SENT_CORRECT_TEXT.items():
        r = by[sid]
        if r['correct'] != text:
            r['correct'] = text
            n += 1
    return n


def apply_word(rows):
    by_id = {r['id']: r for r in rows}
    for wid, old, new in WORD_CORRECT_FIX:
        r = by_id[wid]
        if r['correct'] == new:
            continue
        assert r['correct'] == old, (wid, r['correct'])
        r['correct'] = new
    done = 0
    for wid, idx, new, et, expl in WORD_OPT:
        d = by_id[wid]['distractors'][idx]
        if d['text'] == new:
            continue
        d['text'], d['error_type'], d['explanation'] = new, et, expl
        done += 1
    return done


def load(name):
    p = D(name)
    if not os.path.exists(p):
        return None
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def save(name, rows):
    p = D(name)
    shutil.copy2(p, p + '.bak_step27_' + datetime.now().strftime('%Y%m%d_%H%M'))
    with open(p, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def main():
    apply = '--apply' in sys.argv
    files = {}
    for name in ('word_cards.jsonl', 'sentence_cards.jsonl', 'word_quiz.jsonl', 'sentence_quiz.jsonl'):
        rows = load(name)
        if rows is not None:
            files[name] = rows

    print('=== 修复前质检 ===')
    before = {}
    for name in ('sentence_quiz.jsonl', 'word_quiz.jsonl'):
        b = check(files[name], name)
        before[name] = b
        print(f'  {name}: {len(b)} 处')
        for x in b[:10]:
            print('    ', x)

    if not apply:
        print('\n[dry-run] 未写盘。加 --apply 执行修复。')
        return 0

    # A. 卡片错译
    for fname, cid, field, old, new in CARD_FIX:
        rows = files[fname]
        r = next(x for x in rows if x['id'] == cid)
        if new in (r.get(field) or ''):
            continue
        assert old in (r.get(field) or ''), (cid, field, r.get(field))
        r[field] = r[field].replace(old, new)
        print(f'  卡片修正 {cid}.{field}: {old!r} → {new!r}')

    print('\n=== 句题修复 ===')
    print('  干扰项重建', apply_sent(files['sentence_quiz.jsonl']))
    print('  整句重写', apply_rewrite(files['sentence_quiz.jsonl']))
    print('=== 词题修复 ===')
    print('  条目更新', apply_word(files['word_quiz.jsonl']))

    print('\n=== 解释截断修正 ===')
    for name in ('sentence_quiz.jsonl', 'word_quiz.jsonl'):
        n = 0
        for r in files[name]:
            for d in r.get('distractors') or []:
                new = fix_expl(d.get('explanation') or '')
                new = tidy_expl(new)
                if name == 'word_quiz.jsonl':
                    new = drop_tail(new)
                if new != d.get('explanation'):
                    d['explanation'] = new
                    n += 1
        print(f'  {name}: 修正 {n} 条')

    for name in files:
        save(name, files[name])
        print(f'  已写盘 data/{name}')

    print('\n=== 修复后质检 ===')
    rc = 0
    for name in ('sentence_quiz.jsonl', 'word_quiz.jsonl'):
        a = check(files[name], name)
        print(f'  {name}: {len(before[name])} → {len(a)} 处')
        for x in a[:20]:
            print('    ', x)
        rc |= 1 if a else 0

    sq = files['sentence_quiz.jsonl']
    print(f'\n句题 {len(sq)} 道，可出题 {sum(1 for r in sq if len(r["distractors"]) >= 3)}')
    return rc


if __name__ == '__main__':
    sys.exit(main())
