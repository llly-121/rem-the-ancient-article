"""Step 6: expand & enrich the course card pool.

Inputs
  - data/course_cards.jsonl                  (571 cards, 21 pian, from step5)
  - D:/guwen-cache/parquet/train.parquet     (972,467 rows: info/modern/classical/english)
  - data/wiki_text_chenqingbiao.txt          (wikisource full text)
  - data/wiki_text_songdongyang.txt          (wikisource full text)

What it does
  1. 富贵不能淫 / 生于忧患死于安乐  -> cards from HF 孟子 sections (native modern+english)
  2. 论语十二章                     -> rebuilt from HF 论语 via 12 textbook anchors
                                       (replaces yuwen lunyu1 "十则" version in v2)
  3. 陈情表 / 送东阳马生序          -> cards from wikisource text; modern & english are
                                       AI-drafted translations, clearly labelled
  4. English attach pass            -> every card's classical is CJK-key matched against
                                       the whole HF corpus; english + english_source
                                       attached when found (ambiguous flagged)

Output
  - data/course_cards_v2.jsonl   (schema: 9 original fields + title + english +
                                  english_source + english_ambiguous)
  - data/step6_audit.txt
"""
import json
import re
import sys

BASE = "E:/Users/asus/workbuddy/guwen-project"
PARQUET = "D:/guwen-cache/parquet/train.parquet"
OUT_JSONL = f"{BASE}/data/course_cards_v2.jsonl"
OUT_AUDIT = f"{BASE}/data/step6_audit.txt"

MIN_LEN, MAX_LEN = 4, 50
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
SPLIT = re.compile(r"(?<=[。！？；])|(?<=[。！？；][”’」』）])")
N_END = re.compile(r"[。！？]")


def cjk_len(s):
    return len(CJK.findall(s or ""))


def cjk_key(s):
    """punctuation/whitespace-insensitive key for cross-corpus matching"""
    return "".join(CJK.findall(s or ""))


def split_sentences(para):
    parts = [p.strip() for p in SPLIT.split(para) if p and p.strip()]
    return [p for p in parts if p]


def align_paragraph(rp, tp):
    sents = split_sentences(rp)
    if not sents:
        return []
    if len(N_END.findall(rp)) == len(N_END.findall(tp)):
        trs = split_sentences(tp)
        if len(trs) == len(sents):
            return [(s, t, "句") for s, t in zip(sents, trs)]
    return [(s, tp, "段") for s in sents]


# ----------------------------------------------------------------------
# AI-drafted translations for the two wikisource texts (clearly labelled)
# ----------------------------------------------------------------------
CHEN_PARAS = [
    # (classical paragraph, modern, english)
    ("臣密言：臣以险衅，夙遭闵凶。生孩六月，慈父见背。行年四岁，舅夺母志。祖母刘愍臣孤弱，躬亲抚养。臣少多疾病，九岁不行；零丁孤苦，至于成立。既无伯叔，终鲜兄弟；门衰祚薄，晚有儿息。外无期功强近之亲，内无应门五尺之僮；茕茕孑立，形影相吊。而刘夙婴疾病，常在床蓐；臣侍汤药，未曾废离。",
     "臣子李密陈言：我因为命运坎坷，幼年就遭遇不幸。生下来才六个月，慈父就去世了。到了四岁，舅父强迫母亲改变守节的心愿改嫁。祖母刘氏怜悯我孤苦弱小，亲自抚养我。我小时候经常生病，九岁还不能走路，孤苦零丁，一直到成人自立。既没有叔叔伯伯，又缺少兄弟；门庭衰微、福分浅薄，很晚才有儿子。外面没有比较亲近的亲戚，家里没有照应门户的僮仆，孤孤单单独自生活，只有自己的身子和影子互相安慰。而祖母刘氏早被疾病缠绕，常年卧床不起，我侍奉她饮食汤药，从来没有停止侍奉而离开。",
     "Your subject Mi states: because of my ill fate I met with misfortune early in life. Six months after I was born, my kind father passed away. When I was four, my uncle pressed my mother to remarry against her will. My grandmother Liu, pitying me for being orphaned and frail, raised me with her own hands. I was often ill as a child and could not walk at nine; lonely and destitute I remained until I came of age. I had neither uncles nor brothers; our house declined and my fortune was thin, so I had a son late. Outside, no close relatives within the mourning grades; inside, no servant boy even five feet tall to answer the door. I stood alone and solitary, with only my shadow for company. Meanwhile Granny Liu had long been beset by illness and lay in bed constantly; I attended her food and medicine and never once left her side."),
    ("逮奉圣朝，沐浴清化。前太守臣逵察臣孝廉；后刺史臣荣举臣秀才；臣以供养无主，辞不赴命。诏书特下，拜臣郎中；寻蒙国恩，除臣洗马。猥以微贱，当侍东宫，非臣陨首所能上报。臣具以表闻，辞不就职。诏书切峻，责臣逋慢。郡县逼迫，催臣上道；州司临门，急于星火。臣欲奉诏奔驰，则刘病日笃；欲苟顺私情，则告诉不许。臣之进退，实为狼狈。",
     "到了圣朝建立，我蒙受清明的政治教化。先是太守逵推举我为孝廉，后来刺史荣推举我为秀才，我因为供养祖母的事无人主持，都辞谢没有接受任命。朝廷又特地下了诏书，任命我为郎中，不久又蒙受国家恩命，任命我为洗马。凭我这样微贱的人去侍奉太子，这不是我杀身捐躯所能报答的。我把这些苦衷一一上表禀报，辞谢不去就职。可是诏书急切严峻，责备我逃避命令、有意怠慢；郡县长官催促我立刻上路，州官登门督促，比流星还要急。我想奉命奔赴京城为国效力，可祖母刘氏的病一天比一天重；想姑且迁就自己的私情，可申诉又不被允许。我进也不是退也不是，实在狼狈。",
     "When I came to serve the sagely dynasty I was bathed in its pure civilising influence. First Governor Kui recommended me as Filial and Incorrupt, later Inspector Rong nominated me as Flourishing Talent; because no one was left to care for my grandmother, I declined both. An edict came down specially appointing me Palace Gentleman; soon, favoured by imperial grace, I was made Expositor-in-Waiting. That one as lowly as I should serve the heir apparent is more than I could repay by losing my head. I reported all this in a memorial and declined the post. Yet the edict grew urgent and stern, reproaching me for evasion and insolence; the commandery and county pressed me onto the road, the prefecture officials called at my door, swifter than a falling star. If I obey the edict and hasten to serve, Granny Liu's illness deepens by the day; if I follow my private feelings, my petitions are not granted. Advancing or retreating, I am truly caught in a wretched plight."),
    ("伏惟圣朝以孝治天下，凡在故老，犹蒙矜育；况臣孤苦，特为尤甚。且臣少仕伪朝，历职郎署，本图宦达，不矜名节。今臣亡国贱俘，至微至陋，过蒙拔擢，宠命优渥；岂敢盘桓，有所希冀！但以刘日薄西山，气息奄奄，人命危浅，朝不虑夕。臣无祖母，无以至今日；祖母无臣，无以终馀年。母孙二人，更相为命；是以区区，不能废远。臣密今年四十有四，祖母刘今年九十有六，是臣尽节于陛下之日长，报养刘之日短也。乌鸟私情，愿乞终养！",
     "我俯伏思量，圣朝用孝道治理天下，凡是年老有德的旧臣尚且受到怜悯养育，何况我的孤苦程度特别严重呢。而且我年轻时曾在伪朝做官，历任郎官职务，本来就希图仕途显达，并不顾惜名节。现在我成了亡国的卑贱俘虏，最微小最鄙陋，却受到过分的提拔，恩宠十分优厚，哪里还敢犹豫观望、另有企求呢！只因祖母刘氏已像太阳迫近西山，气息微弱，生命垂危，早晨不能料到晚上。我没有祖母，无法活到今天；祖母没有我，也无法度完她的余年。祖孙二人相依为命，因此我心怀恳切，不能废止奉养而远离。臣李密今年四十四岁，祖母刘氏今年九十六岁，我为陛下尽节的日子还长，报答刘氏的日子却很短。怀着乌鸦反哺般的私情，我乞求准许我为祖母养老送终！",
     "I humbly reflect that the sagely dynasty rules the realm by filial piety: even aged former officials receive compassion and care — how much more I, whose orphaned bitterness is exceptional! Moreover, in my youth I served the fallen dynasty, holding office in its secretariat, aiming only at advancement and caring nothing for name or integrity. Now, a lowly captive of a conquered state, most insignificant and base, I have been promoted beyond measure with lavish favour — how would I dare linger and harbour other hopes! Only because Granny Liu is like the sun nearing the western hills, her breath faint, her life precarious: the morning cannot reckon on the evening. Without my grandmother I could not have lived to this day; without me she cannot end her remaining years. The two of us, grandmother and grandson, depend on each other for life; hence this earnest plea — I cannot abandon her care and go far away. I, Mi, am forty-four this year; Granny Liu is ninety-six. The days I may serve Your Majesty are long; the days I may repay her are short. With the private feeling of the crow that repays its parents, I beg leave to nurse her to the end!"),
    ("臣之辛苦，非独蜀之人士及二州牧伯所见明知；皇天后土，实所共鉴。愿陛下矜悯愚诚，听臣微志；庶刘侥幸，保卒馀年。臣生当陨首，死当结草。",
     "我的辛酸苦楚，不只是蜀地的人士和二州的长官亲眼所见、明明白白知道的，就连天地神明也都看得清清楚楚。希望陛下怜悯我愚拙的诚心，成全我微小的心愿，或许祖母刘氏能够侥幸地保全余年版终天年。我活着应当献出生命，死了也应当像结草老人那样报答陛下的恩情。",
     "My hardships are plainly known not only to the gentry of Shu and the governors of the two provinces; Heaven and Earth have truly witnessed them all. I beg Your Majesty to pity my foolish sincerity and grant my humble wish, so that Granny Liu may by good fortune be spared to live out her years. Living, I shall lay down my life for You; dead, I shall repay Your grace like the old man who knotted grass."),
    ("臣不胜犬马怖惧之情，谨拜表以闻。",
     "臣怀着犬马一样不胜恐惧的心情，恭恭敬敬地呈上这份表章来禀告陛下。",
     "Your subject, trembling with the fear of dog and horse, respectfully submits this memorial for Your Majesty's perusal."),
]

SONG_PARAS = [
    ("余幼时即嗜学。家贫，无从致书以观，每假借于藏书之家，手自笔录，计日以还。天大寒，砚冰坚，手指不可屈伸，弗之怠。录毕，走送之，不敢稍逾约。以是人多以书假余，余因得遍观群书。既加冠，益慕圣贤之道，又患无硕师名人与游，尝趋百里外，从乡之先达执经叩问。先达德隆望尊，门人弟子填其室，未尝稍降辞色。余立侍左右，援疑质理，俯身倾耳以请；或遇其叱咄，色愈恭，礼愈至，不敢出一言以复；俟其欣悦，则又请焉。故余虽愚，卒获有所闻。",
     "我小时候就特别爱好读书。家里穷，没有办法买书回来读，常常向有藏书的人家去借，亲手抄录，计算着约定的日子按期归还。天气特别寒冷时，砚台里的墨结成坚硬的冰，手指冻得不能弯曲伸直，也不敢懈怠。抄完后，赶快跑去还书，不敢稍微超过约定的期限。因此人们大多愿意把书借给我，我也因此能够广泛地阅读各种书籍。成年以后，更加仰慕圣贤的学说，又担心没有学问渊博的老师、名人与他们交往，曾经赶到百里之外，捧着经书向同乡有道德学问的前辈请教。前辈德高望重，学生挤满他的屋子，他从不稍微把言辞放委婉些、把脸色放温和些。我站着侍候在他身边，提出疑难、询问道理，弯下身子侧着耳朵来请教；有时遭到他的斥责，我的神情更加恭敬，礼节更加周到，不敢说一句话来顶撞；等到他高兴了，就再去请教。所以我虽然愚笨，最终还是有所收获。",
     "In my youth I was already fond of learning. My family was poor and could not obtain books to read, so I often borrowed from families with collections, copied them out by hand, and counted the days to return them on time. In bitter cold the ink froze solid in the inkstone and my fingers could neither bend nor stretch, yet I did not slacken. When the copying was done I hurried to return the books, never daring to exceed the agreed term by a hair. That is why most people were willing to lend me books, and so I was able to read widely. After coming of age I admired the way of the sages all the more, yet worried that I had no profound masters or famous men to keep company with. I once hurried a hundred li to question a learned elder of my home region, clasping the classics. The elder was of high renown; his disciples filled his room, and he never softened his words or countenance the slightest degree. I stood in attendance, raised doubts and questioned principles, bending down with ears intent; when I met his rebukes my manner grew more respectful, my courtesy more scrupulous, not daring to utter a word in reply; when he grew pleased I would ask again. Thus, dull as I was, I in the end gained real instruction."),
    ("当余之从师也，尝负箧曳屣，行深山巨谷中。穷冬烈风，大雪深数尺，足肤皲裂而不知。至舍，四支僵劲不能动，媵人持汤沃灌，以衾拥覆，久而乃和。寓逆旅，主人日再食，无鲜肥滋味之享。同舍生皆被绮绣，戴珠缨宝饰之帽，腰白玉之环，左佩刀，右备容臭，烨然若神人。余则缊袍敝衣处其间，略无慕艳意。以中有足乐者，不知口体之奉不若人也。盖余之勤且艰若此。今虽耄老，未有所成，犹幸预君子之列，而承天子之宠光，缀公卿之后，日侍坐备顾问，四海亦谬称其氏名，况才之过于余者乎？",
     "当我跟老师学习的时候，曾经背着书箱、拖着鞋子，行走在深山大谷之中。隆冬刮着猛烈的寒风，大雪深达几尺，脚上的皮肤冻裂了也不知道。到了客舍，四肢冻僵不能动弹，服侍的人拿热水来浇洗，用被子把我裹盖起来，很久才暖和过来。住在客店里，店主每天只供应两顿饭，没有新鲜肥美的东西可以享受。跟我同住的同学都穿着绣花的绸缎衣服，戴着缀有红缨和宝石的帽子，腰间挂着白玉环，左边佩刀，右边挂着香袋，光彩鲜明得像神仙一样。我却穿着破棉袍、旧衣服生活在他们中间，一点也没有羡慕的意思。因为内心有足以快乐的事，就不觉得吃的穿的不如别人了。我求学的辛勤艰苦大概就是这样。如今我虽然年老，没有取得什么成就，还幸而能跻身于君子的行列，承受天子的恩宠光彩，跟随在公卿大人后面，每天陪侍皇帝、听候询问，天下人也错误地称扬我的姓名，何况才能超过我的人呢？",
     "When I went to seek my teachers I carried book-boxes on my back and trailed shoes through deep mountains and great valleys. In deep winter, under fierce wind and snow several feet deep, the skin of my feet cracked without my noticing. On reaching the lodge, my limbs were frozen stiff and would not move; the serving maid poured hot water over me and wrapped me in quilts, and only after a long while did warmth return. Lodging at the inn, the host gave two meals a day, with nothing fresh or rich to enjoy. My fellow lodgers wore embroidered silks and caps hung with pearl tassels and jewels, girdles of white jade, a knife at the left, a scent-bag at the right, radiant as gods. I, in worn padded gown and ragged clothes, dwelt among them without the least envy, for what sufficed to make me happy was within: I did not feel my food and clothing inferior. Such were the toil and hardship of my studies. Now, though old with nothing achieved, I have luckily joined the ranks of gentlemen, enjoying the Emperor's glorious favour, trailing behind dukes and ministers, daily in attendance for consultation, and my name is, undeservedly, known across the realm — how much more those whose talent surpasses mine!"),
    ("今诸生学于太学，县官日有廪稍之供，父母岁有裘葛之遗，无冻馁之患矣；坐大厦之下而诵《诗》《书》，无奔走之劳矣；有司业、博士为之师，未有问而不告、求而不得者也；凡所宜有之书，皆集于此，不必若余之手录、假诸人而后见也。其业有不精、德有不成者，非天质之卑，则心不若余之专耳，岂他人之过哉！",
     "如今学生们在太学学习，朝廷每天供给粮食，父母每年赠送冬夏的衣服，没有受冻挨饿的忧愁了；坐在高大的房屋里诵读《诗》《书》，没有东奔西走的劳苦了；有司业、博士做他们的老师，没有问了不告诉、求了得不到的了；凡是应该有的书都集中在这里，不必再像我那样亲手抄录、向别人借来才能看到了。如果他们的学业还有不精通、品德还有没养成的，那不是天资低下，就是用心不像我那样专一罢了，哪里是别人的过错呢！",
     "Now the students study at the Imperial Academy: the government supplies daily grain, parents send yearly winter and summer clothing, so there is no fear of cold and hunger; they sit beneath great halls reciting the Songs and Documents, with no toil of running about; Assistant Supervisors and Erudites serve as their teachers — none asks without being told, none seeks without obtaining; all the books one ought to have are gathered here, with no need, like mine, to copy by hand or borrow from others before seeing them. If their learning is still unrefined and their virtue imperfect, it is either that their natural endowment is lowly or that their concentration falls short of mine — how could it be the fault of others!"),
    ("东阳马生君则，在太学已二年，流辈甚称其贤。余朝京师，生以乡人子谒余，撰长书以为贽，辞甚畅达；与之论辩，言和而色夷。自谓少时用心于学甚劳，是可谓善学者矣。其将归见其亲也，余故道为学之难以告之。谓余勉乡人以学者，余之志也；诋我夸际遇之盛而骄乡人者，岂知予者哉！",
     "东阳的书生马君则，在太学已经两年了，同辈的人都很称赞他的贤能。我到京城朝见皇帝时，马生以同乡晚辈的身份拜见我，写了一封长信作为见面礼，文辞十分畅达；同他辩论，言辞谦和、脸色平和。他自己说少年时在学习上用心很辛苦，这可以说是善于学习的人了。他将要回家探望父母，我特意把求学的艰难告诉他。说我是勉励同乡人努力学习，这是我的本意；诋毁我是夸耀自己际遇好而在同乡面前骄傲，那是不了解我的人啊！",
     "Ma Junze of Dongyang has been at the Academy for two years, and his contemporaries greatly praise his worth. When I came to the capital for audience, the young man called on me as a fellow-provincial junior, presenting a long letter as his gift, its style fluent and lucid; in debate with him his words were mild and his countenance even. He says that in his youth he laboured hard at learning — he may truly be called a good learner. As he is about to return home to see his parents, I therefore tell of the difficulty of learning to instruct him. To say I encourage my townsmen to study — that is my intent; to say I vaunt my good fortune and am proud before my townsmen — that is to know me not!"),
]

LUNYU_ANCHORS = [
    "学而时习之", "吾日三省吾身", "吾十有五而志于学", "温故而知新",
    "学而不思则罔", "贤哉回也", "知之者不如好之者", "饭疏食饮水",
    "三人行，必有我师焉", "逝者如斯夫", "三军可夺帅也", "博学而笃志",
]

# 孟子 sections (HF info values, with 书名号)
MENGZI_SECTIONS = [
    ("富贵不能淫", "《孟子·滕文公章句下·第二节》"),
    ("生于忧患死于安乐", "《孟子·告子章句下·第十五节》"),
]


def make_card(title, classical, modern, source_work, author, prev_s, next_s,
              para_index, scope, english=None, eng_src=None, amb=False):
    return {
        "classical": classical, "modern": modern,
        "source_work": source_work, "author": author,
        "prev_sentence": prev_s, "next_sentence": next_s,
        "char_length": cjk_len(classical), "para_index": para_index,
        "translation_scope": scope, "title": title,
        "english": english, "english_source": eng_src, "english_ambiguous": amb,
    }


def load_hf():
    import pyarrow.parquet as pf
    t = pf.read_table(PARQUET, columns=["info", "modern", "classical", "english"])
    return {
        "info": t.column("info").to_pylist(),
        "modern": t.column("modern").to_pylist(),
        "classical": t.column("classical").to_pylist(),
        "english": t.column("english").to_pylist(),
    }


def main():
    audit = ["Step 6 扩充与英译补齐审计", "=" * 78]

    # ---- existing cards ----
    old = [json.loads(l) for l in open(f"{BASE}/data/course_cards.jsonl", encoding="utf-8")]
    # title map via yuwen metadata provenance
    yuwen = json.load(open("D:/guwen-env/.tmp/yuwen_gw.json", encoding="utf-8"))
    TITLE2KEY = [
        ("岳阳楼记", "yueyanglouji"), ("醉翁亭记", "zuiwengtingji"),
        ("出师表", "chushibiao"), ("桃花源记", "taohuayuanji"),
        ("小石潭记", "xiaoshitanji"), ("曹刿论战", "caoguilunzhan"),
        ("论语十二章", "lunyu1"), ("劝学", "quanxue"), ("师说", "shishuo"),
        ("赤壁赋", "chibifu"), ("阿房宫赋", "epanggongfu"), ("六国论", "liuguolun"),
        ("过秦论", "guoqinlun"), ("廉颇蔺相如列传", "lianpo"), ("陋室铭", "loushiming"),
        ("爱莲说", "ailianshuo"), ("三峡", "sanxia"), ("记承天寺夜游", "chengtiansi"),
        ("马说", "mashuo"), ("鱼我所欲也", "yuwosuoyu"), ("邹忌讽齐王纳谏", "zouji"),
    ]
    prov2title = {}
    for title, key in TITLE2KEY:
        meta = yuwen[key]["metadata"]
        prov2title[(meta.get("provenance") or "", meta.get("author") or "")] = title
    # 书名冲突对：同一 (书名, 作者) 对应两篇，用 yuwen 原文句子集合区分
    AMBIG = {"《韩昌黎文集》": {"师说": "shishuo", "马说": "mashuo"},
             "《东坡志林》": {"赤壁赋": "chibifu", "记承天寺夜游": "chengtiansi"}}
    sent2title = {}
    for prov, m in AMBIG.items():
        for title, key in m.items():
            raw = yuwen[key]["content"]["raw"] or ""
            for s in split_sentences(raw.replace("\n\n", "。")):
                sent2title[cjk_key(s)] = title
    unmatched = 0
    for r in old:
        t = prov2title.get((r["source_work"], r["author"]))
        if t is not None:
            for prov, m in AMBIG.items():
                if r["source_work"] == prov:
                    t = sent2title.get(cjk_key(r["classical"]), t)
                    break
        else:
            unmatched += 1
        r["title"] = t or ""
    audit.append(f"[旧卡] 571 张补 title，未匹配 {unmatched} 张")

    # v2 = old minus old lunyu cards (replaced below)
    v2 = [r for r in old if r["title"] != "论语十二章"]
    audit.append(f"[旧卡] 论语十二章(十则版) 移除 {len(old) - len(v2)} 张，将由 HF 论语十二章重建")

    hf = load_hf()

    # ---- 1) 孟子 two sections ----
    for title, info in MENGZI_SECTIONS:
        idxs = [i for i, x in enumerate(hf["info"]) if x == info]
        kept = []
        for i in idxs:
            c, m, e = hf["classical"][i], hf["modern"][i], hf["english"][i]
            if not (MIN_LEN <= cjk_len(c) <= MAX_LEN):
                continue
            kept.append((c, m, e))
        for j, (c, m, e) in enumerate(kept):
            v2.append(make_card(
                title, c, m, info, "孟子",
                kept[j - 1][0] if j > 0 else None,
                kept[j + 1][0] if j + 1 < len(kept) else None,
                j, "句", e, "HF语料(Gemini机翻)", False))
        audit.append(f"[新增] {title}: HF {info} 行数={len(idxs)} 保留卡片={len(kept)}")

    # ---- 2) 论语十二章 rebuild ----
    lunyu_idx = [i for i, x in enumerate(hf["info"]) if x and x.startswith("《论语")]
    lun_keys = {cjk_key(hf["classical"][i]): i for i in lunyu_idx}
    audit.append(f"[论语] HF 论语行数={len(lunyu_idx)}")
    n_ok = 0
    for anchor in LUNYU_ANCHORS:
        ak = cjk_key(anchor)
        cands = [i for k, i in lun_keys.items() if ak and ak in k]
        if not cands:
            audit.append(f"  [MISS] 锚点未命中: {anchor}")
            continue
        # 最精确（最短包含锚点的行）
        i = min(cands, key=lambda x: cjk_len(hf["classical"][x]))
        c, m, e = hf["classical"][i], hf["modern"][i], hf["english"][i]
        if not (MIN_LEN <= cjk_len(c) <= MAX_LEN):
            audit.append(f"  [SKIP] 锚点行超长: {anchor} ({cjk_len(c)}字)")
            continue
        v2.append(make_card("论语十二章", c, m, hf["info"][i], "孔子及其弟子",
                            None, None, n_ok, "句", e, "HF语料(Gemini机翻)", False))
        audit.append(f"  [OK] {anchor} -> {hf['info'][i]} ({cjk_len(c)}字)")
        n_ok += 1
    audit.append(f"[新增] 论语十二章(HF重建): {n_ok}/12 章")

    # ---- 3) wikisource texts with AI translations ----
    for title, fname, paras, author, prov in [
        ("陈情表", "wiki_text_chenqingbiao.txt", CHEN_PARAS, "李密", "维基文库·陳情表(西晉)"),
        ("送东阳马生序", "wiki_text_songdongyang.txt", SONG_PARAS, "宋濂", "维基文库·送东阳马生序"),
    ]:
        wiki_raw = [p.strip() for p in open(f"{BASE}/data/{fname}", encoding="utf-8").read().split("\n\n") if p.strip()]
        audit.append(f"[新增] {title}: 维基文库段落={len(wiki_raw)}  译文段落={len(paras)}")
        if len(wiki_raw) != len(paras):
            audit.append(f"  [WARN] 段落数不一致，按可用段处理")
        doc = []
        for pi, (rp, tp, ep) in enumerate(paras):
            if pi >= len(wiki_raw):
                break
            # 校验脚本内原文与落盘原文一致（防手误）
            if cjk_key(rp) != cjk_key(wiki_raw[pi]):
                audit.append(f"  [WARN] 段{pi} 原文与维基文库文件不一致，采用文件版")
                rp = wiki_raw[pi]
            for s, t, lv in align_paragraph(rp, tp):
                if not (MIN_LEN <= cjk_len(s) <= MAX_LEN):
                    continue
                doc.append(make_card(title, s, t, prov, author, None, None,
                                     pi, lv, ep, "AI试译(小沃)", False))
        kept = [r for r in doc]
        for i, r in enumerate(kept):
            r["prev_sentence"] = kept[i - 1]["classical"] if i > 0 else None
            r["next_sentence"] = kept[i + 1]["classical"] if i + 1 < len(kept) else None
        v2.extend(kept)
        audit.append(f"  保留卡片={len(kept)} (现代文与英文均为 AI 试译)")

    # ---- 4) english attach pass ----
    eng_map = {}
    for i in range(len(hf["info"])):
        e = hf["english"][i]
        if not e:
            continue
        k = cjk_key(hf["classical"][i])
        if not k:
            continue
        eng_map.setdefault(k, []).append((hf["info"][i], e))
    n_hit = n_amb = n_new = 0
    for r in v2:
        if r.get("english"):
            n_hit += 1
            continue
        cands = eng_map.get(cjk_key(r["classical"]))
        if not cands:
            continue
        engs = {e for _, e in cands}
        n_hit += 1
        if len(engs) == 1:
            r["english"] = cands[0][1]
            r["english_source"] = "HF语料(Gemini机翻)"
            r["english_ambiguous"] = False
            n_new += 1
        else:
            # 同书优先：卡片 source_work 的书名与 HF info 的首书名一致者
            m = re.match(r"《([^·》]+)", r["source_work"] or "")
            book = m.group(1) if m else ""
            same_book = [e for info, e in cands if info.startswith(f"《{book}")]
            pick = same_book[0] if same_book else sorted(engs)[0]
            r["english"] = pick
            r["english_source"] = "HF语料(Gemini机翻)"
            r["english_ambiguous"] = not same_book
            n_amb += 0 if same_book else 1
    audit.append(f"[英文] 可英译卡片={n_hit}  本次新补={n_new}  歧义保留={n_amb}")

    # ---- write v2 ----
    order = ["classical", "modern", "source_work", "author", "prev_sentence",
             "next_sentence", "char_length", "para_index", "translation_scope",
             "title", "english", "english_source", "english_ambiguous"]
    with open(OUT_JSONL, "w", encoding="utf-8", newline="\n") as f:
        for r in v2:
            f.write(json.dumps({k: r.get(k) for k in order}, ensure_ascii=False) + "\n")

    # ---- per-title stats ----
    from collections import Counter
    stat = Counter(r["title"] for r in v2)
    audit.append("-" * 78)
    for t, n in stat.most_common():
        audit.append(f"  {t or '(无题)':14s} {n:4d} 句")
    audit.append(f"合计 v2 卡片 {len(v2)} 句 / {len(stat)} 个篇目")

    with open(OUT_AUDIT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(audit) + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(audit))


if __name__ == "__main__":
    main()
