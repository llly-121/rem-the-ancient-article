"""词级题库的人工义项表。

## 为什么需要这张表

step20 / step24 生成干扰项的做法是「拿同一个词在别的句子里的英译来顶」。
同一个文言词在不同句里被译成不同的英文，于是：

    天下 → the world / the empire / the realm / the empire's / the whole empire
    赂秦 → bribing Qin / bribe Qin / bribed Qin / the lands given to Qin
    异   → different / may differ / no difference / were different

把后者塞进前者的选项里，学生选哪个都对。字符串归一化救不了——`the world`
和 `the empire` 差得远，但义项相同。

更要命的是有些 `correct` 本身就是错译（上游把整句英译挂到了虚词上）：

    鼓（一鼓作气）→ morale had already been lost   ← 这是「竭」的义项
    对（对曰）  → Cao Qufu said                    ← 把人名当成了动词
    盖（盖失强援）→ deprived of                    ← 义项完全不对
    至于（至于夏水襄陵）→ In summer                 ← 「至于」是「到了」，不是「夏天」
    寡人（上书谏寡人者）→ those who remonstrate by letter  ← 整句碎片

## 结构

    TABLE[term] = [(matcher, correct_or_None, [三条干扰项]), ...]

matcher 三种写法：
    None         默认，兜底用（放在列表最后）
    '=xxx'       与 canon(正确答案) 相等时命中，用于「同词不同义项」
    '中文子串'    该子串出现在 meaning_in_this_sentence 里时命中

correct 为 None 表示沿用原答案；给了值就覆盖（用于修正错译）。

## 维护

改动这里的任何一条，都要重跑 step26 —— 它是幂等的，全组自动生效。
新建 dict 时注意不要写重复键：Python 会静默覆盖，本项目已踩过两次
（见 step20 的 assert_no_duplicate_keys）。
"""


def D(text, expl, etype='wrong_sense'):
    return {'text': text, 'error_type': etype, 'explanation': expl}


TABLE = {}

TABLE['相如'] = [(None, 'Lin Xiangru', [
    D('Lian Po', '「廉颇」是赵国另一员大将，与蔺相如常被并提而混淆'),
    D('the King of Zhao', '赵王是国君；「相如」是人名'),
    D('Cao Mo', '「曹沫」是《史记》另一人物，同书并见易混'),
])]

TABLE['天下'] = [(None, None, [
    D('the feudal lords', '「诸侯」是天下分封的各国君主，不等于「天下」'),
    D('the four seas', '「四海」是天下的代称，但本词字面只作「天下」'),
    D('the Central Plains', '「中原」只是天下的一部分，且偏地域'),
])]

TABLE['诸侯'] = [(None, 'the feudal lords', [
    D('the vassal states', '「诸侯」指君主本人，不是他们所封的国家'),
    D('the Son of Heaven', '「天子」是天下共主，位在诸侯之上'),
    D('the retainers', '「家臣」是卿大夫的属吏，与诸侯差着等级'),
])]

TABLE['徐公'] = [(None, 'Lord Xu', [
    D('a slow gentleman', '把「徐」按字面读成 slow、「公」读成 gentleman'),
    D('Lord Lin', '「蔺相如」是赵国上卿，与齐国徐公不相干'),
    D('the King of Wei', '齐威王是国君；徐公是齐国美男子'),
])]

TABLE['赂秦'] = [(None, 'bribing Qin', [
    D('attacking Qin', '「赂」是割地求和，不是攻打'),
    D('serving Qin', '「事秦」是奉事秦国；「赂秦」是用土地贿赂'),
    D('allying with Qin', '「赂秦」是单方面献地，不是结盟'),
])]

TABLE['所以'] = [
    ('=this is why', 'This is why', [
        D('the means by which', '「所以」在此表原因，不表凭借'),
        D('the man who did it', '把「所以」误当作指人的结构'),
        D('in this place', '误作处所；本句说的是先汉兴隆的缘故'),
    ]),
    ('=the reason', 'The reason why', [
        D('the means by which', '本句问的是缘故，不是凭借的工具'),
        D('the man who did it', '把「所以」误当作指人的结构'),
        D('the moment when', '误作时间；「所以去亲戚」说的是原因'),
    ]),
    (None, 'the means by which', [
        D('the reason why', '「所以传道」是「用来……的」，不是「……的原因」'),
        D('the man who taught', '把「所以」误当作指人的结构'),
        D('the result of this', '「所以」引出凭借，不引出结果'),
    ]),
]

TABLE['于是'] = [(None, 'Thereupon', [
    D('Although', '「于是」顺承上文结果，不是转折'),
    D('Unless', '误作条件；原句是既成事实之后的承接'),
    D('Meanwhile', '「于是」表因果承接，不是时间并行'),
])]

TABLE['异'] = [
    ('=greatly amazed', 'greatly amazed', [
        D('the same as others', '「异之」是意动「以之为异」，不是「与人相同」'),
        D('a strange sight', '把意动用法读成了名词短语'),
        D('deeply moved', '「异」是惊异，不是感动'),
    ]),
    ('=no difference', 'no difference', [
        D('different from each other', '「不宜异同」是「不应有不同」，不是「彼此不同」'),
        D('strange', '「异同」指差别，不是怪异'),
        D('inferior', '「异同」无高下义'),
    ]),
    ('=may differ', 'may differ', [
        D('must be the same', '「或异二者之为」是「或许不同于」，不是「必定相同」'),
        D('truly admirable', '「异」是不同，不是赞美'),
        D('far inferior', '「异」无高下义'),
    ]),
    (None, 'different', [
        D('the same', '「异」正是「不同」，不能译成相同'),
        D('strange', '本句「异」指差别，不指怪异'),
        D('amazed', '意动「惊异」是另一义项；本句说的是「不同」'),
    ]),
]

TABLE['绝'] = [(None, None, [
    D('to ferry across', '「绝」在此是断绝，不是「横渡」（横渡是「绝江河」）'),
    D('to be extremely', '「绝」作副词「极」是另一用法，本句是动词'),
    D('to reject', '「绝」是断绝缘分/往来，不是当面拒绝'),
])]

TABLE['以为'] = [
    ('=floored by', 'was made the bottom', [
        D('was regarded as a pond', '「全石以为底」是「以全石为底」，不是「被认为是池塘」'),
        D('was covered with stones', '「以为底」是「作为潭底」'),
        D('was hollowed out', '「以为底」说的是潭底材料，不是凿空'),
    ]),
    ('=making them', 'making them', [
        D('renaming them', '「以为桂林、象郡」是「把……设为」，重在设置而非改名'),
        D('attacking them', '「以为郡」是设郡，不是攻取'),
        D('granting them to', '设郡是中央直辖，不是封赏'),
    ]),
    (None, 'considered', [
        D('was made into', '「以为」在此是「认为」，不是「把……做成」'),
        D('was appointed as', '「以为贤大夫」是赵王「认为」他贤能'),
        D('was regarded by others', '「自以为不如」的主语是自己，不是别人'),
    ]),
]

TABLE['私'] = [
    # 顺序有讲究：'=private' 会先命中 'my private feelings'，所以「私情」那条
    # 必须排在「私下/私人的」前面
    ('=privately', 'privately', [
        D('openly', '「私握臣手」是私下握手，与「公开」相反'),
        D('by force', '「私」是私下，不是强行'),
        D('in person', '「私」表隐秘，不表亲自'),
    ]),
    ('=feeling', 'personal feelings', [
        D('public duty', '「私情」是私人感情，与「公义」相对'),
        D('official business', '「私情」无关公务'),
        D('personal gain', '「私情」是感情，不是利益'),
    ]),
    ('=private', 'personal', [
        D('public', '「私仇」是私人的仇怨，与「公」相对'),
        D('shared', '「私仇」是一己之仇，不是共同的'),
        D('borrowed', '把「私」误读成「私自借用」'),
    ]),
    (None, 'favoured', [
        D('hated', '「私」是偏爱，与「恨」相反'),
        D('feared', '同句「妾畏臣」才是害怕；「私臣」是偏爱我'),
        D('envied', '「私」是偏爱，不是忌妒'),
    ]),
]

TABLE['数'] = [(None, None, [
    D('countless', '「数百步」「数十步」是约数「几」，不是「无数」'),
    D('the fated number', '「数」作名词「命数」是另一义项，本句是数词'),
    D('exactly ten', '「数十」是约数「几十」，不是确数'),
])]

TABLE['鼓'] = [
    ('=play', 'played', [
        D('beat the drum', '「鼓瑟」是弹瑟，不是击鼓'),
        D('urged them on', '「鼓瑟」是演奏，不是督战'),
        D('sang to the music', '「鼓瑟」是弹奏，不是歌唱'),
    ]),
    (None, 'beat the drum', [
        D('played the zither', '「鼓」在此是名词作动词「击鼓进军」'),
        D('urged the troops on', '「鼓之」是击鼓，鼓声本身即号令'),
        D('sounded the retreat', '「鼓」是进军之号，退兵用「金」'),
    ]),
]

TABLE['对'] = [(None, 'replied', [
    D('asked', '「对曰」是应答，不是发问'),
    D('the King of Lu said', '把「对」误当作人名/称谓，句子失去谓语'),
    D('refused', '「对曰」只是回答，不含拒绝'),
])]

TABLE['度'] = [(None, 'estimated', [
    D('measured', '「度」读 duó 是推测，不是量长短'),
    D('crossed over', '「度」通「渡」是另一用法，本句是揣度'),
    D('took as law', '「度」作「法度」是名词义，本句是动词'),
])]

TABLE['坐'] = [(None, None, [
    D('was punished for a crime', '「坐」作「因罪获罚」是另一义项，本句是「坐」这个动作'),
    D('was seated in the seat of honour', '本句只写坐的位置，无尊卑义'),
    D('stood up', '「坐」与「起」相对，不能译成站起'),
])]

TABLE['盖'] = [
    ('=in truth', 'it turned out that', [
        D('because', '「盖竹柏影也」是推究语气「原来是」，不是因果'),
        D('although', '「盖」无转折义'),
        D('suddenly', '「盖」表推究，不表突发'),
    ]),
    (None, 'because', [
        D('although', '「盖失强援」是「因为失去强援」，不是虽然'),
        D('it turned out that', '本句「盖」表原因，不表推究'),
        D('only then', '「盖」不是「才」'),
    ]),
]

TABLE['至于'] = [
    ('=in summer', 'when it came to', [
        D('as for', '「至于夏水襄陵」是「到了夏天」，不是「至于（另提一事）」'),
        D('in summer', '「至于」是「到了」，不是「在夏天」'),
        D('from', '「至于」表到达，不表起点'),
    ]),
    (None, 'as for', [
        D('when it came to', '本句「至于」是另提一事，不是时间上的「到了」'),
        D('because of', '「至于」不表原因'),
        D('apart from', '「至于」是转题，不是排除'),
    ]),
]

TABLE['相与'] = [(None, 'together', [
    D('one after another', '「相与」是一同，不是先后相继'),
    D('face to face', '「相与」不表相对而坐'),
    D('each on his own', '「相与」正强调共同，与各自相反'),
])]

TABLE['假'] = [
    ('=lend', 'lent', [
        D('borrowed', '「以书假余」是别人借给我，方向相反'),
        D('sold', '「假」是借，不是卖'),
        D('gave away', '「假」是要还的，不是白送'),
    ]),
    (None, 'borrow', [
        D('lend', '「每假借于藏书之家」是我向人借，方向相反'),
        D('buy', '「假」是借，不是买'),
        D('copy out', '「假」是借来，抄写是下一步'),
    ]),
]

TABLE['寡人'] = [(None, 'my humble self', [
    D('Your Majesty', '「寡人」是君主自称，不是臣下称呼君主'),
    D('the widow', '「寡人」与「寡妇」无关，是「寡德之人」'),
    D('a lonely man', '「寡人」是谦称，不是字面的孤独'),
])]

TABLE['伐'] = [(None, 'attacked', [
    D('cut down', '「伐」作「砍伐」是另一义项，本句是征讨'),
    D('praised', '「伐」无称颂义（「自伐」才是自夸）'),
    D('defended', '「伐齐」是攻齐，与防守相反'),
])]

TABLE['竭'] = [(None, 'was exhausted', [
    D('was abundant', '「竭」是枯竭，与充足相反'),
    D('was advancing', '「彼竭我盈」说的是士气，不是进退'),
    D('was trapped', '「竭」是耗尽，不是被困'),
])]

TABLE['悉'] = [(None, 'all', [
    D('none', '「悉如外人」是全都，与「没有一个」相反'),
    D('some of them', '「悉」是全部，不是部分'),
    D('each separately', '「悉」强调整体全数，不是各自'),
])]

TABLE['布衣'] = [(None, 'a commoner', [
    D('a nobleman', '「布衣」借指平民，与贵族相反'),
    D('a merchant', '「布衣」泛指平民，不特指商人'),
    D('a scholar-official', '「布衣」正指未出仕者，与官员相对'),
])]

TABLE['兴'] = [(None, 'restore', [
    D('rise up', '「兴复汉室」是复兴，不是兴起'),
    D('prosper', '「兴复」重在恢复，不是变得兴旺'),
    D('abolish', '「兴复」是复兴，与废除相反'),
])]

TABLE['其实'] = [(None, 'in fact', [
    D('in the end', '「其实百倍」是「它实际上」，不表最终'),
    D('on the contrary', '「其实」是据实说明，不表转折'),
    D('by comparison', '「其实」不表比较，比较在前半句已完成'),
])]

TABLE['再'] = [(None, 'twice', [
    D('again and again', '「再」在古汉语是「两次」，不是「一次又一次」'),
    D('a second time only', '「后秦击赵者再」是两次，不是第二次'),
    D('once more', '「再」是确数两次'),
])]

TABLE['及'] = [
    ('=then came', 'when it came to', [
        D('reaching', '「及至」是「等到」，不是空间上的到达'),
        D('as well as', '「及至始皇」是时间推进，不表并列'),
        D('overtaking', '「及」无追赶义'),
    ]),
    (None, 'reaching', [
        D('until', '「延及」是延续到，重在延伸'),
        D('as well as', '「延及」不表并列'),
        D('overtaking', '「及」无追赶义'),
    ]),
]

TABLE['致'] = [
    ('=attained', 'attained', [
        D('sent', '「致万乘之势」是达到，不是送去'),
        D('caused', '「致」在此是取得，不是致使'),
        D('presented', '「致」无进献义，本句说的是国力'),
    ]),
    (None, 'obtain', [
        D('send', '「无从致书」是没法得到书，不是送书'),
        D('cause', '「致书」不是「致使」'),
        D('present', '「致」在此是取得，不是进献'),
    ]),
]

TABLE['疾'] = [(None, 'illness', [
    D('swiftness', '「疾」作「快」是另一义项，本句是病'),
    D('hatred', '「疾」作「痛恨」是另一义项'),
    D('loudness', '「疾」作「洪亮」是另一义项'),
])]

TABLE['孰与'] = [(None, 'compared with', [
    D('is less than', '「孰与」是「与……比，谁更……」，不是「不如」'),
    D('is equal to', '「孰与」是发问比较，不是判断相等'),
    D('is unlike', '「孰与」不表相异'),
])]

TABLE['俱'] = [(None, 'both', [
    D('neither', '「俱为一体」是全都是，与「都不是」相反'),
    D('one of them', '「俱」是全部，不是其中之一'),
    D('separately', '「俱」强调整体一致，与分开相反'),
])]

TABLE['跪'] = [
    ('=kneeling', 'kneeling', [
        D('legs', '「跪请秦王」是跪下，不是蟹腿义'),
        D('bowing', '「跪」是屈膝，与弯腰不同'),
        D('standing', '「跪」与「站」相反'),
    ]),
    (None, 'legs', [
        D('knees', '「蟹六跪」指蟹腿，不是膝盖'),
        D('claws', '「二螯」才是钳子；「六跪」是腿'),
        D('feet', '「跪」在此指蟹的步足'),
    ]),
]

TABLE['念'] = [(None, 'thought of', [
    D('recited', '「念」在此是想到，不是诵读'),
    D('missed home', '「念无与为乐者」是想没人同乐'),
    D('studied', '「念」是思虑，不是研习'),
])]

TABLE['毕'] = [(None, 'finished', [
    D('began', '「毕礼而归之」是礼仪完毕'),
    D('was cancelled', '「毕」是完成，不是取消'),
    D('was delayed', '「毕」是结束，不是拖延'),
])]

TABLE['无以'] = [(None, 'had no way to', [
    D('was unable to refuse', '「无以」是「没有用来……的办法」'),
    D('had no reason to', '「无以」表凭借缺失，不表理由'),
    D('was not allowed to', '「无以」是自身无凭借，不是不被允许'),
])]

TABLE['穷'] = [(None, 'poor and desperate', [
    D('exhausted a forest', '「穷」作「走到尽头」是另一义项'),
    D('extremely cold', '「穷冬」是另一义项；本句「穷乏」是困窘'),
    D('reached the end', '本句指生活困窘，不是走到尽头'),
])]

TABLE['豆'] = [(None, 'a food vessel', [
    D('a bean', '「豆」在先秦是盛食器皿，不是豆子'),
    D('a bowl of soup', '「一豆羹」的「豆」是器皿，「羹」才是汤'),
    D('a measure of grain', '「豆」在此是容器，不是量词'),
])]

TABLE['版筑'] = [(None, 'building walls by tamping earth', [
    D('selling fish and salt', '这是同句「胶鬲举于鱼盐之中」'),
    D('herding cattle', '这是同句「百里奚举于市」一类的出身'),
    D('weaving mats', '「版筑」是筑墙，不是编席'),
])]

TABLE['向'] = [(None, 'the previous', [
    D('the opposite', '「寻向所志」是找先前做的标记'),
    D('the direction', '「向」在此是「先前的」，不是名词方向'),
    D('the new one', '「向」是先前，与「新」相反'),
])]

TABLE['用心'] = [(None, 'because his mind', [
    D('with great effort', '「用心一也」是「因为心思专一」'),
    D('using his heart', '「用」在此是「因为」，不是「使用」'),
    D('by nature', '「用心一」说的是心思专一，不是天性'),
])]

TABLE['庸'] = [(None, 'how', [
    D('only', '「庸」是反问「难道」，不是「只」'),
    D('surely', '「庸知」是反问，不是肯定'),
    D('why not', '「庸」表反问，不含建议'),
])]

TABLE['或师焉'] = [(None, 'some seek a teacher', [
    D('none seek a teacher', '「或」是「有的」，不是「没有」'),
    D('all seek a teacher', '「或」是部分，不是全部'),
    D('sometimes seek a teacher', '把「或」读成「有时」；此处「或」指「有的人」'),
])]

TABLE['或不焉'] = [(None, 'some do not', [
    D('none of them refuse', '「或」是「有的」，不是「没有」'),
    D('all of them refuse', '「或」是部分，不是全部'),
    D('he alone refuses', '把「或」读成第三人称；此处指「有的人」'),
])]

TABLE['奈何'] = [(None, 'what is to be done', [
    D('what is it', '「奈何」是问对策，不是问是什么'),
    D('why is that', '「奈何」问怎么办，不是问原因'),
    D('how much', '「奈何」不表数量'),
])]

TABLE['邪'] = [(None, 'a question particle', [
    D('an exclamation', '「邪」通「耶」，是疑问语气'),
    D('a statement of fact', '「其真无马邪」是反问，不是陈述'),
    D('a negative', '「邪」是语气词，不表否定'),
])]

TABLE['戒'] = [(None, 'warned her', [
    D('forbade her', '「戒之曰」是告诫，不是禁止'),
    D('blessed her', '「戒」是训诫，不是祝福'),
    D('followed her', '「戒」是告诫，不是跟随'),
])]

TABLE['猥'] = [(None, 'humbly', [
    D('basely', '「猥」在此是谦词「辱、屈尊」，非「卑鄙」'),
    D('suddenly', '「猥」无突发义'),
    D('repeatedly', '「猥」不表频次'),
])]

TABLE['蒙'] = [(None, 'have received', [
    D('have been dismissed', '「过蒙拔擢」是承蒙提拔'),
    D('have refused', '「蒙」是承受，与拒绝相反'),
    D('have forgotten', '「蒙」是蒙受，不是遗忘'),
])]

TABLE['俟'] = [(None, 'wait until', [
    D('leave before', '「俟其欣悦」是等他高兴'),
    D('ask for', '「俟」是等待，不是请求'),
    D('refuse', '「俟」无拒绝义'),
])]

TABLE['由是'] = [(None, 'because of this', [
    D('in spite of this', '「由是感激」是因此感激，不是尽管如此'),
    D('after that', '「由是」表因果，不表时间先后'),
    D('instead', '「由是」是因此，不是代替'),
])]

TABLE['从而'] = [(None, 'follow him', [
    D('therefore', '这是今义「因此」的误读；本句「从」是跟从、「而」是连词'),
    D('obey him', '「从」是跟从、追随，不是服从'),
    D('refuse him', '「从而师之」是跟从他并拜他为师，与拒绝相反'),
])]

TABLE['乱'] = [(None, 'in disarray', [
    D('in perfect order', '「吾视其辙乱」是车轮印混乱'),
    D('in retreat', '「乱」指杂乱，不是撤退'),
    D('in silence', '「乱」与静无关'),
])]
