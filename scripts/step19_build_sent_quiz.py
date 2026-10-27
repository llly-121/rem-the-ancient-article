# -*- coding: utf-8 -*-
"""句级干扰项样本（30 条）—— 误译模式限定三类：
  sense_error     实词误解：关键实词换成另一常见义项
  func_error      虚词功能丢失或误判（之/而/以/于/其/者/所以/语气词等）
  structure_error 特殊句式误读（判断句译成叙述句、被动译成主动、宾语前置未还原）
正确项一律取 sentence_cards.jsonl 的 full_english，脚本只提供干扰项并做校验。
"""
import json
import re
import collections

CARDS = {r['id']: r for r in (json.loads(l) for l in open('data/sentence_cards.jsonl', encoding='utf-8'))}

ERROR_TYPES = {'sense_error', 'func_error', 'structure_error'}

# ────────────────────────── 30 条手写干扰项 ──────────────────────────
# D = [(text, error_type, explanation), ...]
QUIZ = {
 's0316': [
  ("With such an advantage, yet they terrorised Qin's accumulated might, paring and carving land day by day, drifting toward ruin.",
   'structure_error', '「为秦人积威之所劫」被动未还原，劫掠方向反转：六国由被胁迫者变成施动者。'),
  ("With such an advantage, yet kidnapped by Qin's accumulated might, they were pared daily, carved monthly, drifting toward ruin.",
   'sense_error', '「劫」＝胁迫、挟制（国势被挟制），不是绑架（kidnap）。'),
  ("With such an advantage, yet terrorised by Qin's accumulated might, they were pared daily and carved monthly because they tended to ruin.",
   'func_error', '「以趋于亡」的「以」表结果（以致于走向灭亡），不是表原因的 because。'),
 ],
 's0362': [
  ("yet when one man rose in revolt he destroyed the seven ancestral temples and killed the ruler with his own hand, and the world laughed at him. Why?",
   'structure_error', '「为天下笑」被动未还原，被译成陈涉主动施暴；「身死人手」的施受关系随之改写。'),
  ("yet when one man rose in revolt the seven ancestral temples were burned down, its ruler died at another's hand, a laughing-stock to the world. Why?",
   'sense_error', '「隳」＝毁坏、倾覆，译作纵火属无据增译，陈涉起事并未焚庙。'),
  ("yet he who rose in revolt, whose temples crumbled, who died at another's hand and was laughed at by the world — why him?",
   'func_error', '「为天下笑者，何也」的「者」是提顿（……的原因），被误作定语「的人」，主语由「秦亡」错移到作难者本人。'),
 ],
 's0369': [
  ("The King of Zhao consulted with General Lian Po and the great ministers: to give it, yet Qin's cities might never come, and they would deceive Qin in vain;",
   'structure_error', '「徒见欺」被动未还原，「见」表被动被漏译，变成赵国去欺骗秦国。'),
  ("The King of Zhao consulted with General Lian Po and the great ministers: to give it, yet Qin's cities might never come, and they would certainly be deceived;",
   'sense_error', '「徒」＝白白地、徒然，不是「必定」(certainly)。'),
  ("The King of Zhao consulted with General Lian Po and the great ministers: to give it, yet Qin's cities are feared and cannot be obtained, and they would be deceived in vain;",
   'func_error', '「恐不可得」是「恐怕得不到」的推测语气，「恐」不是以城池为宾语的谓语动词。'),
 ],
 's0411': [
  ("I truly feared to deceive Your Majesty and to fail Zhao, so I had a man carry the jade back, and it has already reached Zhao by a secret way.",
   'structure_error', '「见欺于王」＝被大王欺骗，被动未还原后欺骗方向反转：变成我骗大王。'),
  ("I truly feared to be deceived by Your Majesty and to carry Zhao on my back, so I had a man carry the jade back, and it has already reached Zhao by a secret way.",
   'sense_error', '「负赵」＝辜负赵国，不是「背负赵国」。'),
  ("I truly feared to be deceived by Your Majesty and to fail Zhao, so I had a man carry the jade back, and it reached Zhao after an interval.",
   'func_error', '「间至赵」的「间」名词作状语＝抄小路、秘密地，不是时间间隔。'),
 ],
 's0224': [
  ("When he broke Jingzhou and took Jiangling, sailing east down the stream, his prows stretched a thousand li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; but now what is he?",
   'structure_error', '「安在」＝在哪里（疑问代词宾语前置），被误作问身份「是什么」。'),
  ("When he broke Jingzhou and took Jiangling, sailing east down the stream, his prows stretched a thousand li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; but now is he safe and sound?",
   'sense_error', '「安」是疑问代词「哪里」，不是「安全」。'),
  ("When he broke Jingzhou and took Jiangling, sailing east down the stream, his prows stretched a thousand li, banners veiling the sky, pouring wine on the river, lance athwart, chanting poems—he was truly the hero of an age; but now where did the hero of an age go — no one can say.",
   'func_error', '「安在哉」双重反问（哪里还找得到呢），译成陈述句后疑问代词与语气词「哉」的功能全部丢失。'),
 ],
 's0373': [
  ("The King of Zhao asked: \"Why do you know about it?\"",
   'func_error', '「何以」＝凭借什么（问依据），误作询问原因的 why。'),
  ("The King of Zhao asked: \"How do you know the King of Yan?\"",
   'sense_error', '「之」代「他能胜任此事」，不是指某个人。'),
  ("The King of Zhao asked: \"Do you know how?\"",
   'structure_error', '「何以知之」＝以何知之（疑问代词作介宾前置），被拆散成一般疑问句，前置结构消失。'),
 ],
 's0453': [
  ("Lin Xiangru firmly held them back, saying: 'In your judgment, is General Lian on the same side as the King of Qin?'",
   'structure_error', '「孰与」＝与……相比哪一个更……，比较结构被拆成「与……同伙/在一起」。'),
  ("Lin Xiangru firmly held them back, saying: 'Public opinion sees General Lian compare with the King of Qin?'",
   'sense_error', '「公」＝您（尊称），不是「公众」(the public)。'),
  ("Lin Xiangru firmly held them back, saying: 'Your looking at General Lian — who compares with the King of Qin?'",
   'func_error', '「公之视」的「之」取消主谓独立性（您看来），被误作代词性所有格，主谓结构散架。'),
 ],
 's0470': [
  ("Confucius said: \"What crudeness does he have?\"",
   'structure_error', '「何陋之有」＝有何陋（宾语前置），被误读成「他有什么陋习」，宾语被当作主语的所有物。'),
  ("Confucius said: \"What vulgarity is there?\"",
   'sense_error', '「陋」指居室简陋，不是人品粗俗(vulgarity)。'),
  ("Confucius said: \"Is there crudeness or not?\"",
   'func_error', '「何……之有」固定结构＝「有什么……呢」，被还原成一般选择疑问，反问语气与前置结构双重丢失。'),
 ],
 's0531': [
  ("In the morning, he dressed well, looked in the mirror, and said to his wife, \"Who is together with Lord Xu of the north city, the beautiful one?\"",
   'structure_error', '「孰与」比较结构被拆成「谁与……在一起」，比较义全失。'),
  ("In the morning, he dressed well, looked in the mirror, and said to his wife, \"Compared to Lord Xu, am I beautiful too?\"",
   'sense_error', '「孰与……美」问的是「哪个更美」，不是「我也美吗」的求证。'),
  ("In the morning, he dressed well, looked in the mirror, and said to his wife, \"The Lord Xu in the north of the city — who is he?\"",
   'func_error', '比较问句被误作询问身份的特指问，「孰与」的语法功能整个丢失。'),
 ],
 's0534': [
  ("Ji did not believe himself, and further asked his concubine: \"Who is handsomer, Lord Xu or I?\"",
   'structure_error', '「不自信」＝不信之（代词「自」作宾语前置，指妻子的话），不是现代词「自信」。'),
  ("Ji did not believe it, and again asked his wife instead: \"Who is handsomer, Lord Xu or I?\"",
   'sense_error', '「妾」＝妾室，不是妻子；「复问其妾」的问话对象被错置。'),
  ("Ji did not believe it, but asked his concubine again: \"Who is handsomer, Lord Xu or I?\"",
   'func_error', '「而」表承接（接着又问），误作转折 but。'),
 ],
 's0030': [
  ("Chu encircles all the mountains.",
   'structure_error', '判断句「……也」被译成叙述句且主宾倒置：环绕与被环绕的关系反转。'),
  ("The area around Chu is mostly mountains.",
   'sense_error', '「皆」＝全、都，不是「大多」(mostly)。'),
  ("All the mountains around Chu also surround it.",
   'func_error', '「也」是判断语气词，被误作副词「也(also)」。'),
 ],
 's0031': [
  ("Its peaks to the southwest, with woods and ravines of exceptional beauty, look lush, deep and graceful — it is called Langya Mountain.",
   'structure_error', '「……者，……也」判断结构丢失，被译成叙述句加「被称作」。'),
  ("Its peaks to the southwest, with woods and ravines of unique beauty, look lush, deep and graceful—that is Langya.",
   'sense_error', '「尤」＝格外、特别，不是「唯一」(unique)。'),
  ("Its many peaks to the southwest, with woods and ravines of exceptional beauty, look lush yet deep and graceful—that is Langya.",
   'func_error', '「蔚然而深秀」的「而」表并列，误作转折 yet。'),
 ],
 's0033': [
  ("A pavilion with wings perches on the spring and turns together with the winding peaks; it is the Old Drunkard's Pavilion.",
   'structure_error', '「峰回路转」是路径曲折的背景交代，被改写成亭子随峰转动，句间关系重组。'),
  ("As the path winds round the peaks, there stands a pavilion perching like a bird with spread wings, about to fall on the spring—that is the Old Drunkard's Pavilion.",
   'sense_error', '「临」＝居高面下、靠近（临于泉上），不是「即将落下」。'),
  ("As the path winds round the peaks, there stands a pavilion perching like wings, then approaching the spring—that is the Old Drunkard's Pavilion.",
   'func_error', '「翼然」的「然」是形容词词尾「……的样子」，误作连词 then。'),
 ],
 's0041': [
  ("When the sun rises the forest mists disperse, and when clouds return the caves grow dark; the dark and bright then change each other in the mountain's mornings and evenings.",
   'structure_error', '「……者，……也」判断被抹平成叙述，「晦明变化者」由主语变成谓语动作。'),
  ("Now, when the sun rises, the mists of the forest disperse; when clouds return, the caves go to sleep—this alternation of dark and bright is morning and evening in the mountains.",
   'sense_error', '「暝」＝昏暗，不是「睡觉」。'),
  ("As usual, when the sun rises, the mists of the forest disperse; when clouds return, the caves grow dark—this alternation of dark and bright is morning and evening in the mountains.",
   'func_error', '「若夫」是发语词（至于说到/像那），误作「像平常那样」。'),
 ],
 's0042': [
  ("Wild flowers bloom and are fragrant, fine trees are luxuriant and shady, the wind and frost are lofty and pure, the water falls and the rocks emerge, in the mountains at four seasons.",
   'structure_error', '「……者，……也」判断被抹掉，「四时」由判断句表语降为时间状语「在四季」。'),
  ("Wild grasses sprout with hidden fragrance, fine trees bloom with deep shade, wind and frost lofty and pure, water fallen and rocks emerging—these are the four seasons in the mountains.",
   'sense_error', '「芳」指花；「秀」指茂盛滋长（草木开花曰荣），两处实词均错位。'),
  ("Wild flowers bloom but give hidden fragrance, fine trees grow luxuriant but with deep shade, wind and frost lofty and pure, water fallen and rocks emerging—these are the four seasons in the mountains.",
   'func_error', '「发而幽香」「秀而繁阴」的「而」表承接（开而即香），误作转折 but。'),
 ],
 's0003': [
  ("So he rebuilt Yueyang Tower, enlarged its old structure, and used the poems and fu of worthy men of the Tang and his own time to engrave it.",
   'structure_error', '「刻……于其上」后置状语＝把诗赋刻在楼上，被误作「用诗赋来雕刻」的工具结构。'),
  ("So he rebuilt Yueyang Tower, enlarged its old system, and engraved on it the poems and fu of worthy men of the Tang and his own time.",
   'sense_error', '「制」指建筑的规模形制，不是「制度」(system)。'),
  ("So he rebuilt Yueyang Tower, enlarged its old structure, and engraved on them the poems and fu of worthy men of the Tang and his own time.",
   'func_error', '「其」指岳阳楼（刻在楼的上边），误作指诗赋作品自身。'),
 ],
 's0009': [
  ("Yet, since it connects north to the Wu Gorge and south to the Xiao and Xiang rivers, demoted officials and wandering poets for the most part met here before.",
   'structure_error', '「多会于此」＝（常常）在这里聚会；「多」表频率，「于此」后置状语表处所，被误作「大多数……曾经」。'),
  ("Yet, since it connects north to the Wu Gorge and south to the Xiao and Xiang rivers, retired officials and wandering poets often gather here.",
   'sense_error', '「迁客」＝被贬谪调迁的官吏，不是退休官员。'),
  ("Yet, since it connects north to the Wu Gorge and reaches the South Pole of the Xiao and Xiang rivers, demoted officials and wandering poets often gather here.",
   'func_error', '「南极潇湘」＝向南直达潇水湘水（「南」名词作状语、「极」＝直达），误作名词「南极」。'),
 ],
 's0066': [
  ("I was originally a commoner, plowing Nanyang myself, seeking only to preserve my life in troubled times, not striving to be known among the feudal lords.",
   'structure_error', '「躬耕于南阳」的「于南阳」后置状语被吞掉，状中结构变成动宾结构「耕南阳」。'),
  ("I was originally a commoner, tilling my own fields at Nanyang, seeking only to preserve my life in troubled times, not striving to hear of and reach the feudal lords.",
   'sense_error', '「闻达」＝闻名显达（一个整体词），被拆成「听到」和「到达」。'),
  ("I was originally a commoner, tilling my own fields as Nanyang, seeking only to preserve my life from the troubled times, not striving to be known among the feudal lords.",
   'func_error', '「于」表处所「在」，不是「从」；「于乱世」＝在乱世中。'),
 ],
 's0068': [
  ("Later, I encountered the defeat, was appointed by the defeated army at the critical moment. Since then, it has been a full 21 years.",
   'structure_error', '「受任于败军之际」＝在兵败之际接受任命，「于败军之际」后置状语被误作施动者「被败军任命」。'),
  ("Later, I was valued during the defeat, took on heavy responsibilities when the army was defeated, and accepted the mission at a critical moment. Since then, it has been a full 21 years.",
   'sense_error', '「值」＝遇到、遇上（值倾覆），不是「有价值/被看重」。'),
  ("Later, I encountered setbacks in the military, took on heavy responsibilities when the army was defeated, and accepted the mission at a critical moment. Since then, you have been twenty-one years old.",
   'func_error', '「二十有一年」的「有」通「又」＝二十一年（时长），不是年龄；「尔来」＝自从那时以来也被吞掉。'),
 ],
 's0132': [
  ("The Duke rode his chariot, and the battle was at Changshao.",
   'structure_error', '「与」＝和（偕同他共乘），误作「乘坐」；「战于长勺」后置状语被抽成独立判断句。'),
  ("The Duke rode with him on a horse, and they gave battle at Changshao.",
   'sense_error', '「乘」＝同乘一辆兵车，春秋时期无骑兵作战，不是骑马。'),
  ("The Duke rode in his place, and the battle was at Changshao.",
   'func_error', '「与之乘」的「与」表偕同，误作「替代」义；「之」代曹刿的指代功能随之丢失。'),
 ],
 's0010': [
  ("Their feelings at the sight of these sights are nothing unusual, are they?",
   'structure_error', '「得无……乎」＝怎能不……呢（反问），被读成委婉否定「大概没有不同吧」。'),
  ("Have they gained nothing different from these sights?",
   'sense_error', '「得无」是固定结构（莫非/怎能不），不能拆出动词「得」。'),
  ("How could their feelings at the sight of these sights fail to differ from this?",
   'func_error', '「乎」表疑问语气，误作介词「于」（不同于……）。'),
 ],
 's0019': [
  ("And sometimes the long mist clears entirely, the bright moon shines over a thousand li, floating light leaps like gold and the still reflection sinks like a disc of jade, as fishermen's songs answer one another—such joy, how extreme it is!",
   'sense_error', '「极」＝穷尽（动词，「哪有穷尽」），不是形容词「极端」。'),
  ("And sometimes the long mist clears entirely, the huge moon shines over a thousand li, floating light leaps like gold and the still reflection sinks like a disc of jade, as fishermen's songs answer one another—such joy is boundless!",
   'sense_error', '「皓」＝洁白明亮，误作「巨大」。'),
  ("And sometimes the long mist clears entirely, the bright moon shines over a thousand li, floating light leaps like gold and the still reflection sinks like a disc of jade, as fishermen's songs answer one another—what joy is this!",
   'structure_error', '「此乐何极」＝这快乐哪有穷尽（反问感叹），被读成「这是什么样的快乐」的一般疑问。'),
 ],
 's0026': [
  ("But what time do they enjoy?",
   'structure_error', '「何时而乐」＝什么时候才快乐，被拆成动宾「享受什么时间」。'),
  ("But when, then, could they get music?",
   'sense_error', '「乐」＝快乐（形容词/动词），不是「音乐」。'),
  ("But when they will be joyful?",
   'func_error', '「何时而乐」的「而」连接时间状语与谓语，被吞掉后句子残缺不成问句。'),
 ],
 's0028': [
  ("Such men are few; who shall associate with me?",
   'structure_error', '「微」＝（如果）没有，误作「稀少」；「吾谁与归」宾语前置（我与谁归）被拆成主动问句，方向反转。'),
  ("If there were no such men, with whom should I go home?",
   'sense_error', '「归」＝归依（归依同道），不是「回家」。'),
  ("Except such men, with whom should I associate?",
   'func_error', '「微」表假设否定「如果没有」，误作介词 except。'),
 ],
 's0178': [
  ("Men are not born going there; who can be without doubts?",
   'func_error', '「生而知之」的「之」代知识和道理，不是动词「往」。'),
  ("Men are not born knowing everything; which one can be without doubts?",
   'sense_error', '「孰」＝谁（泛指任何人），不是特定范围内的「哪一个」。'),
  ("Man is not born, but knows things; who can be without doubts?",
   'structure_error', '「非……者」否定判断（人不是生下来就懂得道理的）被误读成「人不是生出来的，但是懂道理」。'),
 ],
 's0006': [
  ("It bites the distant mountains and swallows the Yangtze River, vast and mighty, boundless in every direction;",
   'sense_error', '「衔」＝用口含着（包容、连接），不是「咬」。'),
  ("It holds distant mountains in its mouth and swallows the Yangtze River, like hot soup, boundless in every direction;",
   'sense_error', '「汤汤(shāng shāng)」＝水势浩大，不是「汤」（古今异义+多音）。'),
  ("It holds distant mountains and is swallowed by the Yangtze River, vast and mighty, boundless in every direction;",
   'structure_error', '「衔远山，吞长江」主语一致（洞庭湖吞长江），被误作被动后吞与被吞方向反转。'),
 ],
 's0021': [
  ("I have tried to fathom the mind of the ancient benevolent men—someone differs from both of these.",
   'sense_error', '「或」＝或许、大概（揣测语气），不是「有人」。'),
  ("I have begged for the mind of the ancient benevolent men—it may differ from both of these.",
   'sense_error', '「求」＝探求、思索，不是「乞求」。'),
  ("I have tried to fathom the mind of the ancient benevolent men—it may differ from both of these behaviours.",
   'func_error', '「二者之为」的「为」指心理活动（这两种心情），不是外在行为。'),
 ],
 's0027': [
  ("They would surely say: \"Before the world's sorrow comes, worry about oneself first; after the world's joy arrives, enjoy it last.\"",
   'structure_error', '「先天下之忧而忧」＝在天下人忧之前忧，「先/后」是介宾状语，被误作「为天下的忧乐」服务关系。'),
  ("They would surely say: \"To be superior to the world in worrying, and to be below the world in rejoicing.\"",
   'sense_error', '「先」＝在……之前（时间次序），不是「优于」；「后」＝在……之后，不是「低于」。'),
  ("They would surely say: \"To be the first in the world to worry but to rejoice last.\"",
   'func_error', '「先忧而忧」「后乐而乐」的「而」表承接，误作转折 but。'),
 ],
 's0056': [
  ("The late Emperor had not half accomplished his great enterprise when he died on the way. Now the realm is divided into three, and Yizhou is worn out and exhausted—this is truly the autumn of crisis, of survival or ruin.",
   'sense_error', '「秋」＝时刻、关头（存亡之秋），不是季节秋天。'),
  ("The late Emperor had not half accomplished his great enterprise when his dynasty collapsed midway. Now the realm is divided into three, and Yizhou is worn out and exhausted—this is truly the hour of crisis, of survival or ruin.",
   'sense_error', '「崩殂」专指帝王之死，不是王朝中途崩溃。'),
  ("The late Emperor had completed half of his great enterprise when he died on the way. Now the realm is divided into three, and Yizhou is worn out and exhausted—this is truly the hour of crisis, of survival or ruin.",
   'func_error', '「未半」的否定（没有完成一半）被丢失，「而」表承接（刚到中途就死了），句意反转。'),
 ],
 's0062': [
  ("To be close to worthy ministers and to go far with petty men—this is why the Earlier Han flourished;",
   'sense_error', '「远」＝疏远（形容词作动词），不是「走远/远离此地」。'),
  ("To be close to worthy ministers and keep petty men at a distance—this is the method by which the Earlier Han was made to flourish;",
   'func_error', '「所以……也」＝……的原因（判断句固定结构），误作「用来……的方法」。'),
  ("Cherish worthy ministers, stay away from petty men — the Earlier Han thus flourished;",
   'structure_error', '「此……也」判断句被译成因果叙述，判断语气丢失。'),
 ],
}

# ────────────────────────── 校验与输出 ──────────────────────────
def wc(s):
    return len(re.findall(r"[A-Za-z']+", s))

errors = []
for sid, ds in QUIZ.items():
    card = CARDS[sid]
    texts = [d[0] for d in ds]
    if len(ds) != 3:
        errors.append(f'{sid}: 干扰项数量 {len(ds)} != 3')
    if len(set(texts)) != 3:
        errors.append(f'{sid}: 干扰项文本重复')
    correct = card['full_english']
    for t, et, exp in ds:
        if et not in ERROR_TYPES:
            errors.append(f'{sid}: 非法 error_type {et}')
        if t.strip() == correct.strip() or t in correct or correct in t:
            errors.append(f'{sid}: 干扰项与正确项语义重叠风险: {t[:40]}')
        if not exp or len(exp) < 8:
            errors.append(f'{sid}: explanation 缺失')
        r = wc(t) / wc(correct)
        if not (0.10 <= r <= 3.0):
            errors.append(f'{sid}: 长度比超界 {r:.2f}')
    if len({d[1] for d in ds}) < 2:
        errors.append(f'{sid}: 同一条内 error_type 只有一种')

if errors:
    print('校验失败', len(errors))
    for e in errors:
        print(' ', e)
    raise SystemExit(1)

out = []
for sid, ds in QUIZ.items():
    card = CARDS[sid]
    out.append({
        'id': sid,
        'classical_sentence': card['classical_sentence'],
        'correct': card['full_english'],
        'sentence_type': card['sentence_type'],
        'source_work': card['source_work'],
        'distractors': [{'text': t, 'error_type': et, 'explanation': exp} for t, et, exp in ds],
    })

with open('data/sentence_quiz_sample.jsonl', 'w', encoding='utf-8') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# 统计
tc = collections.Counter(d['error_type'] for r in out for d in r['distractors'])
st = collections.Counter(r['sentence_type'] for r in out)
print('样本', len(out), '条')
print('error_type 分布', dict(tc))
print('句型分布', dict(st))
