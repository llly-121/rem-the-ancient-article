# -*- coding: utf-8 -*-
"""step14: 生成翻译质量问题样本 data/translation_issues.jsonl

抽检范围（非随机抽样，而是定向覆盖）：
  A. 多字词整体性：654 句中命中官制/礼俗/文化固定词 32 句（加冠、布衣、太学、有司、
     万乘、六合、八荒、陛下、寡人、伏惟、肉袒、汤镬、刎颈、缊袍、结草、汤汤）
  B. 句级问题：判断句（者…也）40 句、被动句 31 句、宾语前置 9 句、连词「而」≥2 的 36 句、
     「之」取独结构 60+ 句，逐句比对英文是否落点
共扫描 654 / 654 句（覆盖全量），确认 15 条问题。
"""
import json

C = 'data/course_cards_v2.jsonl'
OUT = 'data/translation_issues.jsonl'

cards = [json.loads(l) for l in open(C, encoding='utf-8')]


def c(i):
    return cards[i]


issues = [
    # ── A 类：多字词整体性 ──
    dict(
        item_type='term',
        term='肉袒负荆',
        sentence=c(458)['classical'],
        source=f"廉颇蔺相如列传（course_cards_v2 第 458 行）",
        issue_type='多字词未整体处理 + 译文夹带未译中文',
        current_english=c(458)['english'],
        suggested_english=("Hearing this, Lian Po bared his shoulders and back, carried bramble thorns "
                           "on his back, and led by one of his retainers came to Lin Xiangru's gate to "
                           "beg pardon."),
        reason=("① 英文句中直接残留中文「露出上身」，属硬性缺陷；② 「肉袒」是整体词（脱去上衣、露出肩背），"
                "译作 took off his coat 只译出「脱衣」一半，丢了「袒（裸露）」；③ 「负荆」的荆是荆条/荆棘，"
                "用于受鞭打示罚，wicker stick（柳条杖）既非荆条也丢掉了「背负请罚」的礼俗含义。"),
        severity='high',
    ),
    dict(
        item_type='term',
        term='刎颈之交',
        sentence=c(460)['classical'],
        source='廉颇蔺相如列传（第 460 行）',
        issue_type='多字词拆字直译、整体义偏移',
        current_english=c(460)['english'],
        suggested_english='In the end they were reconciled and became friends sworn to die for each other.',
        reason=("「刎颈之交」是固定成语，指「同生共死、可为之刎颈的朋友」，整体义是『生死之交』。"
                "译作 neck-cutting friends 是逐字直译（刎+颈+之+交），英文读者只会理解为「割脖子的朋友」，"
                "既不通也无典故感。应整体译为 sworn friends unto death / friends ready to die for each other。"),
        severity='high',
    ),
    dict(
        item_type='term',
        term='汤镬',
        sentence=c(413)['classical'],
        source='廉颇蔺相如列传（第 413 行）',
        issue_type='多字词整体义偏移（刑名误译）',
        current_english=c(413)['english'],
        suggested_english=("I know that deceiving Your Majesty deserves death; I beg to be thrown into "
                           "the boiling cauldron. I only hope that Your Majesty and the ministers will "
                           "deliberate on this carefully."),
        reason=("「汤镬」是古代酷刑名：汤＝滚水，镬＝无足大鼎，即『投入滚水大鼎烹死』。"
                "译作 boiled in oil 把「汤（水）」误作「油」，刑名整体偏移；且 就汤镬＝就刑，"
                "be willing to be boiled 弱化了「请受此刑」的决绝语气。"),
        severity='high',
    ),
    dict(
        item_type='term',
        term='斧质',
        sentence=c(377)['classical'],
        source='廉颇蔺相如列传（第 377 行）',
        issue_type='多字词整体义偏移（刑具误译 + 动词误译）',
        current_english=c(377)['english'],
        suggested_english=("You had better bare your shoulders and back, lie face down on the executioner's "
                           "block, and beg for punishment; you may then be pardoned by good fortune."),
        reason=("「斧质」是刑具整体：斧＝刑刀，质（锧）＝受刑时伏卧的砧板。译作 the axe blade 只取「刀刃」，"
                "丢掉「砧板」；「伏」是伏卧其上，译作 kowtow（叩头）把动作换成跪拜礼，与受刑场景不符。"),
        severity='medium',
    ),
    dict(
        item_type='term',
        term='长史（并及尚书、侍中、参军）',
        sentence=c(64)['classical'],
        source='出师表（第 64 行）',
        issue_type='官职专名逐字猜译',
        current_english=c(64)['english'],
        suggested_english=("Palace Attendants, Imperial Secretaries, Chief Secretaries and Staff Officers—"
                           "all these are loyal and upright ministers who would die for principle. I hope "
                           "Your Majesty will draw close to them and trust them; then the revival of the "
                           "Han house may be counted on by the day."),
        reason=("四个官名被按字面拆解：长史译作 historiographers（史官）属误译——长史是丞相/将军府属官之首，"
                "掌文书、总务，应作 Chief Secretary；尚书译作 government officials 泛化失指（应为 Imperial Secretary）；"
                "参军作 staff officers 尚可，侍中作 Palace Attendants 可。官名是文化专名，须整体对应而非逐字直译。"),
        severity='medium',
    ),
    dict(
        item_type='term',
        term='费祎（原文「祎」）',
        sentence=c(73)['classical'],
        source='出师表（第 73 行）',
        issue_type='人名声译残缺',
        current_english=c(73)['english'],
        suggested_english=("As for weighing measures and interests and tendering wholehearted loyal advice, "
                           "that is the duty of Guo Youzhi, Fei Yi and Dong Yun."),
        reason=("原文「攸之、祎、允」为三人省称：郭攸之、费祎、董允。译文把「祎」直接音译成 Fei，"
                "只留姓不留名，读者会误以为是另一位「费」姓者；应补全为 Fei Yi。"),
        severity='medium',
    ),
    dict(
        item_type='term',
        term='崤函',
        sentence=c(319)['classical'] + ' ／ ' + c(360)['classical'],
        source='过秦论（第 319、360 行）',
        issue_type='地名整体处理失当（音译混淆）',
        current_english=c(319)['english'] + ' ／ ' + c(360)['english'],
        suggested_english=("…holding the fastness of Mount Xiao and the Hangu Pass and possessing the land "
                           "of Yongzhou… ／ then it made the whole world its home and Mount Xiao and the "
                           "Hangu Pass its palace;"),
        reason=("「崤函」是「崤山＋函谷关」的并称专名。译文作 Xiao and Han / Xiao-Han，把「函（谷关）」译成 Han，"
                "与「韩国」「汉朝」完全混同；且两处译法不一致（and / 连字符）。应统一为 Mount Xiao and the Hangu Pass。"),
        severity='medium',
    ),
    dict(
        item_type='term',
        term='滁人',
        sentence=c(43)['classical'],
        source='醉翁亭记（第 43 行）',
        issue_type='地名指称混淆',
        current_english=c(43)['english'],
        suggested_english=("…coming and going without cease—these are the people of Chuzhou out enjoying "
                           "the hills."),
        reason=("「滁人」指滁州百姓。译作 the people of Chu 会被读成「楚国人/楚地人」，与春秋战国之「楚」混淆；"
                "欧阳修贬所是滁州（今安徽滁州），应作 Chuzhou。"),
        severity='medium',
    ),

    # ── B 类：句级问题 ──
    dict(
        item_type='sentence',
        term=None,
        sentence=c(56)['classical'],
        source='出师表（第 56 行）',
        issue_type='实词误译（严重）',
        current_english=c(56)['english'],
        suggested_english=("Yet the guards and attendants within the palace are untiring in their duties, "
                           "and the loyal and public-spirited men outside risk their lives on the battlefield, "
                           "because they recall the late Emperor's exceptional treatment of them and wish to "
                           "repay it to Your Majesty."),
        reason=("「不懈于内」的「内」指宫中、朝内，译文作 in the DPRK（朝鲜民主主义人民共和国），"
                "是缩写误配造成的严重错误，必须改为 within the palace / at court。"),
        severity='high',
    ),
    dict(
        item_type='sentence',
        term='忠志之士',
        sentence=c(56)['classical'],
        source='出师表（第 56 行）',
        issue_type='实词词义窄化',
        current_english=c(56)['english'],
        suggested_english='…the loyal and high-minded men outside risk their lives…',
        reason=("「士」在此泛指有志节的臣民/将士，译文作 generals（将领）把范围窄化为武将；"
                "「忠志」是「忠诚有志节」，译作 loyal and brave（忠勇）偏移为「勇敢」。"
                "另「忘身于外」的「于外」指在外（战场/朝外），译文补作 on the battlefield 属增译，可保留但需与「士」的宽泛所指协调。"),
        severity='medium',
    ),
    dict(
        item_type='sentence',
        term=None,
        sentence=c(55)['classical'],
        source='出师表（第 55 行）',
        issue_type='主语省略未还原（句式）',
        current_english=c(55)['english'],
        suggested_english=("The late Emperor had not half accomplished his great enterprise when he died "
                           "on the way. Now the realm is divided into three, and Yizhou is worn out and "
                           "exhausted—this is truly a moment of crisis, of survival or ruin."),
        reason=("「创业未半而中道崩殂」的主语是「先帝」，「崩殂」是天子死亡的专称。译文把主语接成了 "
                "The great cause…and died in the middle，字面上成了「大业死了」，主谓错配；"
                "「中道」是「中途/半路」，作 in the middle 也与「功业未半」重复含混。"),
        severity='high',
    ),
    dict(
        item_type='sentence',
        term='可以一战',
        sentence=c(129)['classical'],
        source='曹刿论战（第 129 行）',
        issue_type='古今异义 + 虚词「以」功能丢失',
        current_english=c(129)['english'],
        suggested_english=('"This shows that he does his duty by the people," replied Cao Gui. '
                           '"You may fight on the strength of this."'),
        reason=("「可以」在此是两个词：可（可以）＋以（凭借），「可以一战」＝「可以凭借（这一点）打一仗」。"
                "译文作 and one can fight，把「以」的凭借义整个丢掉，读者看不出「凭什么是这一条」。"
                "另「忠之属也」是判断句「（这）属于忠这一类」，「属」是「类」，译作 only doing one's duty "
                "既丢了判断语气，又用 only 添加了原文没有的限定义。"),
        severity='high',
    ),
    dict(
        item_type='sentence',
        term='行道之人',
        sentence=c(520)['classical'],
        source='鱼我所欲也（第 520 行）',
        issue_type='实词误译（与下句混同）',
        current_english=c(520)['english'],
        suggested_english=('If you shout at him to take it, even a passer-by will not accept it;'),
        reason=("「行道之人」是「走在路上的人、过路的人」，与下句「蹴尔而与之，乞人不屑也」的「乞人（乞丐）」"
                "是两个不同主体。译文作 a beggar on the road，把下一句的「乞人」提前挪用，"
                "导致两句主体重复、原文「过路人尚且不受 / 乞丐也不屑」的递进消失。"),
        severity='high',
    ),
    dict(
        item_type='sentence',
        term='淫',
        sentence=c(558)['classical'],
        source='富贵不能淫（第 558 行）',
        issue_type='词类活用（使动）未体现 + 实词义偏移',
        current_english=c(558)['english'],
        suggested_english=("Riches and honours cannot corrupt him, poverty and low station cannot shake him, "
                           "power and force cannot bend him—such a one is called a great man."),
        reason=("「富贵不能淫」是使动用法：淫＝惑乱、使……迷惑（心志），即「富贵不能使他的心志惑乱」。"
                "译文作 one should not be excessive，把「淫」理解成「过分」，既丢了使动，也把客观陈述"
                "（外界不能动摇他）改成了主观劝诫（人不该过分），三句并列的「不能＋使动」结构完全瓦解；"
                "后两句用 one's will should not waver 同样是劝诫语气，与「此之谓大丈夫」的定义句不接。"),
        severity='high',
    ),
    dict(
        item_type='sentence',
        term=None,
        sentence=c(627)['classical'],
        source='送东阳马生序（第 627 行）',
        issue_type='句级对齐失效（整段译文复用）',
        current_english=c(627)['english'],
        suggested_english=("After I came of age I admired the way of the sages all the more, yet worried that "
                           "I had no learned masters or famous men to associate with; I once hurried a hundred "
                           "li to seek out a venerable elder of my district, clasping the classics to ask his "
                           "instruction."),
        reason=("该句 english 字段装的是整段 9 句的译文（从 In my youth I was already fond of learning 起），"
                "与本句「既加冠，益慕圣贤之道……」无法句级对应；陈情表、送东阳马生序两篇共 171 句均如此。"
                "作为单句对照材料不可用，须按句切分（上列即本句应独立的译文）。"),
        severity='high',
    ),
]

with open(OUT, 'w', encoding='utf-8') as f:
    for i, it in enumerate(issues, 1):
        it['issue_id'] = f'T{i:02d}'
        f.write(json.dumps(it, ensure_ascii=False) + '\n')

print(f'写入 {OUT}：{len(issues)} 条')
import collections
print('问题类型分布:', collections.Counter(x['severity'] for x in issues))
print('A类(term):', sum(1 for x in issues if x['item_type'] == 'term'),
      ' B类(sentence):', sum(1 for x in issues if x['item_type'] == 'sentence'))
for x in issues:
    assert x['suggested_english'] and x['reason'], x['issue_id']
print('校验：全部条目均含具体修订建议与理由')
