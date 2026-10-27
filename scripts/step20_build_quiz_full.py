#!/usr/bin/env python3
"""step20: quiz 全量第一批（exam_frequency 5/4 档）。

词级 296 张：三源策略——同词异义项（wrong_sense）＋ 人工词库 CURATED ＋ 长度过滤；
不足 3 个合格干扰项 → needs_manual=true，不硬凑。
句级 269 句：把句内某词项的 term_english 片段替换成该词的他句义项英译，构造整句干扰项；
可换词项不足 3 → needs_manual=true。

用法：python step20_build_quiz_full.py
输出：data/word_quiz.jsonl / data/sentence_quiz.jsonl
"""
import json
import re
import collections

W = [json.loads(l) for l in open('data/word_cards.jsonl', encoding='utf-8')]
S = [json.loads(l) for l in open('data/sentence_cards.jsonl', encoding='utf-8')]
PAIRS = [json.loads(l) for l in open('data/term_sentence_pairs.jsonl', encoding='utf-8')]

# ─────────────── 人工词库：term → [(text, error_type, explanation), …] ───────────────
CURATED = {
    '微': [('tiny', 'wrong_sense', '误取「微小」常义；「微斯人」的微是假设否定＝如果没有'),
           ('slightly', 'wrong_sense', '误作副词「稍微」；此处是假设否定连词'),
           ('subtle', 'wrong_sense', '误取「精妙」义；与假设否定无关')],
    '得': [('obtained', 'wrong_sense', '误作抽象「获得」；「得一山」是行至林尽处具体发现'),
           ('received', 'wrong_sense', '误作「收到」；语境是发现一座山'),
           ('succeeded', 'sense_shift', '误作「成功」义；此处为动词「发现」')],
    '见': [('was seen by', 'structure_error', '误作被动「被看见」；「见渔人」是主动看见渔人'),
           ('meet with', 'wrong_sense', '误作「会见」；此处为看见、发现'),
           ('appear', 'wrong_sense', '误作「出现」义；动作主体是桃花源人')],
    '绝境': [('desperate situation', 'modern_sense', '以今义「走投无路」解；古义＝与世隔绝之地'),
             ('hopeless plight', 'modern_sense', '今义偏移；此处指地理隔绝，非心理绝望'),
             ('dead end', 'modern_sense', '以今义「死路」解；古义无「绝路」含义')],
    '妻子': [('wife', 'sense_shift', '只译妻子一人，丢了「儿女」；古义＝妻子＋子女并列'),
             ('woman', 'sense_shift', '误作泛称「妇人」；古义是两个词'),
             ('spouse', 'sense_shift', '误作现代「配偶」；「妻」与「子」并列')],
    '无论': [('no matter', 'modern_sense', '以今义连词解；古义＝不要说、更不必说'),
             ('regardless of', 'modern_sense', '今义偏移；原句是「更不必说魏晋」'),
             ('whether or not', 'modern_sense', '今义选择连词；古义无此用法')],
    '既': [('already', 'wrong_sense', '误作副词「已经」单独表义；「既出」＝出来之后'),
           ('since', 'wrong_sense', '误作「既然」；此处表动作完成之后'),
           ('completely', 'wrong_sense', '误作「尽、全」义；非本句用法')],
    '克': [('overcome', 'wrong_sense', '误作「克服」抽象义；「克之」＝战胜齐军'),
           ('restrain', 'wrong_sense', '误作「克制」；语境是战争胜负'),
           ('gram', 'sense_shift', '误作重量单位「克」；古今同形异义')],
    '从而': [('therefore', 'structure_error', '以今义连词「从而」解；古义＝跟从并且'),
             ('and thus', 'structure_error', '今义连接词；「从」是实义动词'),
             ('consequently', 'structure_error', '今义偏移；应作「跟从他并且以他为师」')],
    '下': [('down', 'sense_shift', '误作方位词「向下」；「下江陵」＝攻下江陵'),
           ('below', 'sense_shift', '误作方位词；此处是动词攻占'),
           ('descend', 'sense_shift', '误作「顺流而下」；主语境是攻占城池')],
    '辞': [('refused', 'wrong_sense', '误作「推辞」；「辞楼下殿」是辞别离开'),
           ('words', 'sense_shift', '误作名词「言辞」；此处是动词'),
           ('declined', 'wrong_sense', '误作「推让」；非本句辞别义')],
    '非': [('blame', 'wrong_sense', '误作「非议」；「非秦也」＝不是秦国'),
           ('wrong', 'wrong_sense', '误作形容词「错误的」；此处是否定判断'),
           ('not be', 'structure_error', '判断句否定式不当；应作 is not Qin')],
    '族': [('clan', 'sense_shift', '误作名词「宗族」；「族秦」＝灭秦之族，动词'),
           ('tribe', 'sense_shift', '误作名词「部族」；此处动词化「灭族」'),
           ('family', 'sense_shift', '误作「家族」名词；本句谓语是消灭')],
    '使': [('envoy', 'sense_shift', '误作名词「使者」；「使六国各爱其人」＝假使'),
           ('send', 'wrong_sense', '误作「派遣」；此处是假设连词'),
           ('make', 'wrong_sense', '误作使役「让」；语境为假设')],
    '爱': [('love', 'sense_shift', '误作「爱恋」；「爱六国之人」＝爱护百姓'),
           ('like', 'sense_shift', '弱化为「喜欢」；治理语境是爱护'),
           ('be fond of', 'sense_shift', '同上；非本句治理义')],
    '指示': [('instruction', 'modern_sense', '以今义名词「指示」解；古义「指＋示」＝指给…看'),
             ('point out', 'modern_sense', '近于今义；古义是「指给王看（璧）」'),
             ('directive', 'modern_sense', '今义名词；「示」＝给…看')],
    '可以': [('can', 'modern_sense', '以今义「可以」解；古义「可＋以」＝可以凭借（之）'),
             ('may', 'modern_sense', '同上；丢失「凭借」义'),
             ('permission', 'modern_sense', '今义许可；古义是凭借某条件')],
    '成立': [('establish', 'modern_sense', '以今义「创立」解；古义＝成人自立'),
             ('found', 'modern_sense', '今义「创建」；此处指人成年'),
             ('be valid', 'modern_sense', '今义「（论点）成立」；古义指人')],
    '除': [('remove', 'wrong_sense', '以今义「删除」解；古义「除」＝授官任命'),
           ('divide', 'wrong_sense', '误作「除法」义；与本句无关'),
           ('exclude', 'wrong_sense', '今义「排除」；古义为台阶／授官')],
    '被': [('passive mark', 'structure_error', '误作被动助词；「被绮绣」通「披」＝穿着'),
           ('quilt', 'sense_shift', '误作名词「被子」；此处动词「穿」'),
           ('cover', 'sense_shift', '弱化为「覆盖」；实为身披穿着')],
    '书': [('book', 'sense_shift', '泛化作「书」；《书》特指《尚书》'),
           ('letter', 'sense_shift', '误作「书信」；此处是典籍名'),
           ('write', 'sense_shift', '误作动词「书写」；此处是名词典籍')],
    '迁': [('promoted', 'wrong_sense', '误作「升迁」；「迁客」＝贬谪之官'),
           ('move', 'wrong_sense', '误作「搬迁」；官职语境＝调动，迁灭＝灭亡'),
           ('transfer', 'wrong_sense', '中性「调动」；本句语境是贬谪/灭亡')],
    '及': [('reach', 'wrong_sense', '误作「达到」；「及为忠善者」＝以及'),
           ('catch up with', 'wrong_sense', '误作「赶上」；此处表并列'),
           ('until', 'wrong_sense', '误作「直到」；非本句义')],
    '悉': [('know', 'wrong_sense', '误作「知道」；「悉」＝全、都（范围副词）'),
           ('detailed', 'wrong_sense', '误作形容词「详尽」；此处副词「全都」'),
           ('learn', 'wrong_sense', '误作「得知」；非本句义')],
    '布衣': [('plain clothes', 'char_decompose', '拆字直译「普通的衣服」；布衣借代平民'),
             ('cotton coat', 'char_decompose', '拆作衣物；实指平民身份'),
             ('the poor', 'sense_shift', '误作「穷人」；布衣＝平民（可含士人）')],
    '察': [('investigate', 'wrong_sense', '泛化为「调查」；各句义为明察/考察举荐/一一查明'),
           ('observe', 'wrong_sense', '弱化为「观察」；文言「察」指深入辨察'),
           ('inspection', 'sense_shift', '名词化误用；此处是动词')],
    '乘': [('multiplication', 'modern_sense', '以今义「乘法」解；古义＝乘坐/共乘/趁着'),
           ('ride', 'wrong_sense', '泛化「乘坐」；「公与之乘」特指共乘一辆战车'),
           ('take advantage of', 'wrong_sense', '「因利乘便」的趁义；非共乘义')],
    '从': [('from', 'wrong_sense', '误作介词「从」；「相如从」＝跟从（动词）'),
           ('obey', 'wrong_sense', '误作「服从」；本句是随行跟随'),
           ('past', 'sense_shift', '误作形容词「从前的」；此处动词随行')],
    '谢': [('thank', 'modern_sense', '以今义「感谢」解；古义「谢」＝道歉'),
           ('wither', 'wrong_sense', '误作「凋谢」；人事语境是道歉'),
           ('decline', 'wrong_sense', '误作「辞谢拒绝」；「谢罪」是请罪')],
    '乃': [('is', 'structure_error', '误作系动词「是」；「乃大惊」＝竟然'),
           ('your', 'sense_shift', '误作第二人称「你的」（乃翁）；非本句'),
           ('only then', 'wrong_sense', '误作「才」；「乃大惊」是竟然')],
    '冠': [('hat', 'wrong_sense', '「行冠礼」处误作名词帽子；冠 guàn＝行冠礼'),
           ('crown', 'sense_shift', '误作王冠；古义＝帽子/冠礼'),
           ('champion', 'modern_sense', '今义「冠军」；古义无此')],
    '鄙': [('despise', 'wrong_sense', '误作动词「鄙视」；鄙是形容词「粗俗/浅陋」')],
    '穷': [('poor', 'modern_sense', '以今义「贫穷」解；古义穷＝尽、极、困窘')],
    '顾': [('however', 'wrong_sense', '误作转折「只是」；本句是回头看'),
           ('look back', 'wrong_sense', '误作「回头看」；「顾问」＝备咨询')],
    '相与': [('each other', 'wrong_sense', '误作「互相」；「相与」＝一同、一起')],
    '其实': [('in fact', 'modern_sense', '以今义副词解；古义「其＋实」＝它实际上'),
             ('actually', 'modern_sense', '同上；此处是代词＋名词词组')],
    '再': [('again', 'modern_sense', '以今义「再一次」解；古义＝第二次/两次')],
    '疾': [('hate', 'wrong_sense', '误作「憎恨」；各句义为病/劲疾/快')],
    '曾': [('great-grand', 'char_decompose', '误作「曾祖」的曾；各句义为竟然/通增/不曾')],
    '汤': [('soup', 'modern_sense', '以今义「菜汤」解；古义汤＝热水（赴汤蹈火）')],
    '坐': [('be punished for', 'wrong_sense', '「因…获罪」义（何坐）；本句是「坐着」，两义勿混')],
    '鼓': [('drum', 'sense_shift', '误作名词「鼓」；「鼓瑟/鼓之」是动词弹奏/击鼓'),
           ('encourage', 'wrong_sense', '误作「鼓励」；古义是击鼓')],
    '假': [('fake', 'modern_sense', '以今义「虚假」解；古义假＝借')],
    '修': [('repair', 'wrong_sense', '误作「修理」；各句义为修建/长高/备办/致敬'),
           ('slender', 'sense_shift', '误作「苗条」；修＝长、高（修八尺有余）')],
    '安': [('how', 'wrong_sense', '疑问代词「怎么」义；本句是安稳/安身等实义'),
           ('peace', 'sense_shift', '泛化「安定」；需按句取义（安身/安逸/安静）')],
    '左右': [('left and right', 'char_decompose', '拆字直译方位词；「左右」借代身边侍臣')],
    '徐公': [('the Duke of Xu', 'proper_noun', '误作爵位尊称；徐公是人名，通行 Xu Gong / Lord Xu'),
             ('slow gentleman', 'char_decompose', '拆「徐＝缓慢」误解；徐是姓氏')],
    '素': [('white', 'wrong_sense', '误作「白色」；此处理解为「一向/平素」'),
           ('unadorned', 'wrong_sense', '误作「不加装饰」；此处副词「向来」'),
           ('plain', 'wrong_sense', '误作「朴素的」；非本句义')],
    '兴': [('excited', 'wrong_sense', '今义「兴奋」；古义兴＝兴起/发扬')],
    '微斯人': [('few people', 'char_decompose', '拆「微＝稀少」误解；「微斯人」＝如果没有这样的人')],
    '相如': [('Prime Minister Xiang', 'proper_noun', '误作官职＋名；蔺相如是人名，通行 Lin Xiangru')],
}

MANUAL_FLAG = {
    'w0491': ('correct 锚点「Pillowed on one another」承载的是「枕藉」而非「相与」本身义，'
              '正确项需人工重写后再出题'),
}

# 按卡覆盖：correct 较长时通用词库被长度比过滤，逐卡写加长版干扰项
CURATED_BY_ID = {
    'w0016': [('hot soup', 'modern_sense', '以今义「汤食」解；「浩浩汤汤」汤读 shāng，水势浩大')],
    'w0054': [('Few men like this', 'char_decompose', '误作「稀少」；「微」＝如果没有'),
              ('Tiny as they are', 'wrong_sense', '误取「微小」常义；此处是假设否定连词'),
              ('Slightly such men', 'wrong_sense', '误作副词「稍微」；非本句义')],
    'w0133': [('know well', 'wrong_sense', '误作「知道」；「悉」＝全、都'),
              ('learn all', 'wrong_sense', '误作「得知」；此处范围副词「全都」')],
    'w0169': [('excitement', 'wrong_sense', '今义「兴奋」；「兴德之言」＝发扬美德')],
    'w0185': [('being poor', 'modern_sense', '以今义「贫穷」解；「欲穷其林」＝走到尽头')],
    'w0198': [('knew like people outside', 'wrong_sense', '误作「知道」；「悉」＝全、都'),
              ('in detail like people outside', 'wrong_sense', '误作「详尽」；此处副词「全都」'),
              ('learned like people outside', 'wrong_sense', '误作「得知」；非本句义')],
    'w0202': [('appeared', 'wrong_sense', '误作「出现」；动作主体是桃花源人，见＝看见')],
    'w0203': [('therefore', 'structure_error', '误作「因此」；「乃大惊」的乃＝竟然')],
    'w0209': [('wife only', 'sense_shift', '只译妻子一人，丢了「儿女」；古义两词并列'),
              ('wife and sons only', 'sense_shift', '误作偏正词组；古义「妻」与「子」并列无先后'),
              ('the women', 'sense_shift', '误作泛称「妇女」；此处「妻子＋儿女」')],
    'w0342': [('start', 'sense_shift', '弱化为「开始」；「风雨兴焉」＝风雨在此兴起'),
              ('excite', 'wrong_sense', '今义「使兴奋」；古义＝兴起（产生）'),
              ('launch', 'sense_shift', '误作「发动（战争）」；此处是风雨自然兴起')],
    'w0269': [('peace and ease', 'sense_shift', '误作「安定」；「衣食所安」＝安身之物')],
    'w0301': [('twice again', 'modern_sense', '以今义「又一次」解；古义「再」＝第二次')],
    'w0303': [('beat a drum to signal attack', 'sense_shift', '名词「鼓」误作；「公将鼓之」＝击鼓进军'),
              ('encouraged the troops', 'wrong_sense', '误作「鼓励」；古义是击鼓')],
    'w0330': [('hated', 'wrong_sense', '误作「憎恨」；「声非加疾」＝洪亮劲疾')],
    'w0340': [('pretending', 'modern_sense', '以今义「假装」解；「善假于物」＝借助')],
    'w0342': [('excited', 'wrong_sense', '今义「兴奋」；「风雨兴焉」＝兴起')],
    'w0454': [('going downstream', 'sense_shift', '误作「顺流而下」；「下江陵」＝攻下'),
              ('descended', 'sense_shift', '误作「下降」；此处是攻占城池')],
    'w0526': [('a speech', 'sense_shift', '误作名词「言辞」；「辞楼下殿」是动词辞别'),
              ('refusal', 'wrong_sense', '误作「推辞」；此处是辞别离开')],
    'w0573': [('clan name', 'sense_shift', '误作名词「宗族」；「族秦」＝灭秦之族，动词')],
    'w0839': [('punish', 'wrong_sense', '「因…获罪」义误入；本句「坐章台」是坐在'),
              ('for', 'structure_error', '误作介词「因为」；坐＝坐在')],
    'w0857': [('repair it', 'wrong_sense', '误作「修理」；「修敬」＝致意、表示敬意')],
    'w0931': [('from there', 'wrong_sense', '误作介词「从」；「相如从」＝随行跟从'),
              ('obeyed him', 'wrong_sense', '误作「服从」；此处是跟随')],
    'w1025': [('contemptible', 'wrong_sense', '误作动词性的「可鄙」；鄙贱之人＝粗陋卑贱的人'),
              ('despising others', 'wrong_sense', '误作动词「鄙视」；鄙是形容词「粗俗卑贱」')],
    'w1116': [('calm', 'sense_shift', '误作「安静」；「安求」＝怎么要求'),
              ('settled', 'sense_shift', '误作「安定」；此处疑问代词「怎么」')],
    'w1153': [('studied decorum', 'wrong_sense', '误作「修习」；「修八尺有余」＝身长'),
              ('slender build', 'sense_shift', '误作「苗条」；修＝长、高')],
    'w1188': [('only then issued', 'wrong_sense', '误作「才」；「乃下令」＝于是')],
    'w1203': [('wears a hat', 'sense_shift', '误作名词「帽子」；「丈夫之冠」guàn＝行冠礼')],
    'w1212': [('how could they', 'wrong_sense', '误作疑问「怎么」；「安居」＝安静地居处')],
    'w1230': [('how could it', 'wrong_sense', '误作疑问「怎么」；「安乐」＝安逸享乐')],
    'w1240': [('it is possible', 'modern_sense', '以今义「可以」解；「可以为师」＝可以凭借（之）为师'),
              ('may do so', 'modern_sense', '同今义许可；古义含「凭借」义')],
    'w1258': [('set up', 'modern_sense', '误作「设立」；「至于成立」＝成人自立')],
    'w1389': [('by', 'structure_error', '误作被动标记；「被绮绣」通「披」＝穿着')],
    'w1403': [('because of which', 'structure_error', '误作「因为」；「坐大厦之下」＝坐在')],
    'w1408': [('falsely claim', 'modern_sense', '以今义「虚假」解；「假诸人」＝向人借')],
}

TYPE_CN = {'wrong_sense': '多义项误选', 'modern_sense': '以今义解古义',
           'sense_shift': '整体义偏移', 'char_decompose': '拆字误解',
           'structure_error': '固定结构还原错误', 'proper_noun': '专名混淆'}

# ─────────────── 词级 ───────────────
byte = collections.defaultdict(list)
te_mean = {}
for r in W:
    byte[r['term']].append(r)
    te_mean.setdefault((r['term'], r['term_english']), r['meaning_in_this_sentence'])

quiz, manual_n = [], 0
for r in W:
    if r['exam_frequency'] < 4:
        continue
    correct = r['term_english']
    L = max(len(correct), 1)
    used = {correct}
    ds = []

    def add(text, etype, expl):
        if not text or text in used:
            return False
        if not (0.4 <= len(text) / L <= 2.6):
            return False
        used.add(text)
        ds.append({'text': text, 'error_type': etype, 'explanation': expl})
        return True

    # 1) 同词异义项
    others = sorted({x['term_english'] for x in byte[r['term']]} - {correct})
    for t in others:
        if len(ds) >= 3:
            break
        m = te_mean.get((r['term'], t), '他句义项')
        add(t, 'wrong_sense', f'误取「{r["term"]}」在他句的义项（{m[:22]}…）' if len(m) > 22
            else f'误取「{r["term"]}」在他句的义项（{m}）')
    # 2) 按卡覆盖词库（长 correct 专用加长版）
    for t, et, ex in CURATED_BY_ID.get(r['id'], []):
        if len(ds) >= 3:
            break
        add(t, et, ex)
    # 3) 通用人工词库
    for t, et, ex in CURATED.get(r['term'], []):
        if len(ds) >= 3:
            break
        add(t, et, ex)

    flag = MANUAL_FLAG.get(r['id'])
    needs_manual = len(ds) < 3 or bool(flag)
    if needs_manual:
        manual_n += 1
    quiz.append({
        'id': r['id'], 'term': r['term'], 'char_count': r['char_count'],
        'correct': correct, 'distractors': ds,
        'needs_manual': needs_manual,
        'note': (flag or ('干扰项不足 3 个，仅 %d 个' % len(ds))) if needs_manual else '',
    })

print(f'词级 5/4 档：{len(quiz)} 张，needs_manual {manual_n}')
ty = collections.Counter(d['error_type'] for q in quiz for d in q['distractors'])
print('词级 error_type 分布:', dict(ty.most_common()))
with open('data/word_quiz.jsonl', 'w', encoding='utf-8') as f:
    for q in quiz:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')

# ─────────────── 句级 ───────────────
pby = collections.defaultdict(list)
for p in PAIRS:
    pby[p['sent_id']].append(p)
# 词项 → 可用替换文本（他句义项 + 人工词库）
swap_pool = collections.defaultdict(set)
for p in PAIRS:
    for x in byte.get(p['term'], []):
        if x['term_english'] != p['term_english']:
            swap_pool[p['term']].add(x['term_english'])
    for t, _, _ in CURATED.get(p['term'], []):
        swap_pool[p['term']].add(t)

squiz, smanual = [], 0
for r in S:
    if r['exam_frequency'] < 4:
        continue
    n = int(r['id'][1:]) - 1
    full = r['full_english']
    correct = full
    used = {correct}
    ds = []
    for p in pby.get('c%03d' % (n + 1), []):
        if len(ds) >= 3:
            break
        frag = p['term_english']
        if not frag or frag not in full:
            continue
        for alt in sorted(swap_pool.get(p['term'], [])):
            if len(ds) >= 3:
                break
            new = full.replace(frag, alt, 1)
            if new in used or new == full:
                continue
            used.add(new)
            ds.append({'text': new, 'error_type': 'wrong_sense',
                       'explanation': f'「{p["term"]}」在本句为「'
                                      f'{p["meaning_in_this_sentence"][:16]}…」，'
                                      f'误作他句义项 {alt!r}'})
    needs_manual = len(ds) < 3
    if needs_manual:
        smanual += 1
    squiz.append({
        'id': r['id'], 'classical_sentence': r['classical_sentence'],
        'correct': correct, 'sentence_type': r['sentence_type'],
        'source_work': r['source_work'], 'distractors': ds,
        'needs_manual': needs_manual,
        'note': '可换词项不足 3 个，需人工补写' if needs_manual else '',
    })

print(f'句级 5/4 档：{len(squiz)} 句，needs_manual {smanual}')
ty = collections.Counter(d['error_type'] for q in squiz for d in q['distractors'])
print('句级 error_type 分布:', dict(ty.most_common()))
with open('data/sentence_quiz.jsonl', 'w', encoding='utf-8') as f:
    for q in squiz:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')
