# -*- coding: utf-8 -*-
"""过秦论 清洗记录（131 条）

action: keep / fix / del
记录格式: idx: (action, term, meaning, term_english, note?)
  - term/meaning 为 None 表示保持原值
  - term_english 必须是对应 english 的连续子串
"""

R = {
    # ── 第一段：秦孝公据崤函之固 ──
    681: ("fix", None, "古九州之一，秦据有其地（今陕西一带）", "Yongzhou"),
    682: ("fix", None, "全国、整个天下", "the world"),
    683: ("keep", None, None, "the four seas"),
    684: ("fix", None, "崤山与函谷关，秦国东面的险要关塞", "Xiao and Han"),
    685: ("fix", None, "本句『包举』连用，意为全部占有、囊括（非『被攻占』）", "wrap up"),
    686: ("fix", None, "本句为『窥伺、暗中图谋』（以窥周室）", "eyeing"),
    687: ("keep", None, None, "sweep up"),
    688: ("keep", None, None, "gather in"),
    689: ("keep", None, None, "the eight wilds"),

    # ── 商君佐之 ──
    690: ("fix", "务耕织", "致力于耕织（务：致力、专力从事）", "devoted to ploughing and weaving"),
    691: ("fix", None, "分封的各国君主，本句指受秦威胁的六国", "the lords"),
    692: ("fix", None, "本句『连衡』即连横，秦联合六国分别击破的策略（衡通『横』）", "the Lianheng alliance"),
    693: ("fix", None, "本句为使动『使……相斗』（斗诸侯：使诸侯互斗）", "set the lords against one another"),
    694: ("keep", None, None, "Lord Shang"),
    695: ("fix", None, "本句『法度』即法令制度（非『推测』）", "laws and statutes"),
    696: ("fix", None, "本句为『整治、备办』（修守战之具）", "prepared"),

    # ── 于是秦人拱手而取西河之外 ──
    697: ("fix", None, "在这种情况下，因此", "Therefore"),
    698: ("fix", None, "两手相合，毫不费力", "using two hands to clap"),
    699: ("keep", None, None, "west of the Yellow River"),

    # ── 孝公既没……因遗策 ──
    700: ("fix", "因遗策", "沿袭前代留下的策略（因：沿袭；遗策：遗留的国策）", "followed the bequeathed strategies"),
    701: ("fix", None, "本句为『攻取、占领』（西举巴、蜀）", "took"),
    702: ("keep", None, None, "inherited"),
    703: ("keep", None, None, "fertile lands"),
    704: ("keep", None, None, "Hanzhong"),
    705: ("fix", None, "本句为军事上险要之地（北收要害之郡）", "crucial"),

    # ── 诸侯恐惧，会盟而谋弱秦 ──
    706: ("keep", None, None, "The feudal lords"),
    707: ("keep", None, None, "weaken"),
    708: ("fix", None, "害怕、恐惧", "dread"),

    # ── 不爱珍器重宝肥饶之地 ──
    709: ("fix", None, "全国、整个天下（本句指天下之人才）", "the talents of the world"),
    710: ("fix", None, "相互、一同（相与为一：彼此结为一体）", "became as one"),
    711: ("keep", None, None, "the North-South alliance"),
    712: ("fix", None, "本句为『招纳、招致』（以致天下之士）", "gathered"),

    # ── 齐有孟尝，赵有平原 ──
    713: ("fix", "孟尝", "孟尝君田文，齐国公子，战国四公子之一", "Meng Chang"),
    714: ("fix", None, "平原君赵胜，赵国公子，战国四公子之一", "Pingyuan"),
    715: ("fix", None, "春申君黄歇，楚国公子，战国四公子之一", "Chun Shen"),
    716: ("fix", None, "信陵君魏无忌，魏国公子，战国四公子之一", "Xinling"),

    # ── 约从离衡 ──
    717: ("fix", None, "本句『离衡』即离散连横（衡通『横』）", "the Horizontal"),
    718: ("fix", None, "中山国，战国时白狄所建诸侯国", "Zhongshan"),

    # ── 叩关而攻秦 ──
    719: ("keep", None, None, "knocked at the pass"),

    # ── 九国之师，逡巡而不敢进 ──
    720: ("keep", None, None, "the nine states"),
    721: ("keep", None, None, "hesitated"),
    722: ("fix", None, "本句为『迎入、迎击』（开关延敌）", "receive the enemy"),

    # ── 天下诸侯已困矣 ──
    723: ("fix", None, "全国、整个天下（天下诸侯：天下各国诸侯）", "the world"),
    724: ("fix", None, "分封的各国君主，本句指天下诸侯", "the lords"),

    # ── 从散约败，争割地而赂秦 ──
    725: ("fix", None, "在这种情况下，因此", "So"),
    726: ("fix", None, "割地贿赂秦国（赂：以财物求免）", "bribe Qin"),

    # ── 追亡逐北 ──
    727: ("fix", None, "本句为『追击』（追亡逐北：追击逃亡败北之敌）", "pursued"),

    # ── 因利乘便，宰割天下 ──
    728: ("keep", None, None, "the world"),
    729: ("fix", "分裂", "分割（分裂山河：分割国土山河）", "split"),
    730: ("fix", None, "乘着有利形势（因利乘便：凭借有利条件、抓住便利时机）", "Turning advantage to profit"),
    731: ("keep", None, None, "carved up"),

    # ── 强国请服，弱国入朝 ──
    732: ("fix", None, "本句『弱国』指弱小之国，弱为形容词", "weak"),
    733: ("fix", None, "强大的诸侯国", "Strong states"),

    # ── 延及孝文王、庄襄王 ──
    734: ("fix", None, "本句『延及』即延续到", "Passing to"),
    735: ("fix", None, "本句『延及』为延续到（非『迎战』）", "Passing to"),
    736: ("fix", None, "在位、享有国祚（享国之日浅：在位时间短）", "reigns"),

    # ── 及至始皇 ──
    737: ("fix", None, "本句『及至』即等到", "Then came"),
    738: ("fix", None, "全国、整个天下（鞭笞天下：奴役天下之人）", "the world"),
    739: ("keep", None, None, "the four seas"),
    740: ("fix", None, "分封的各国君主，本句指被秦所灭的六国", "the lords"),

    # ── 南取百越之地，以为桂林、象郡 ──
    741: ("keep", None, None, "making them"),
    742: ("fix", None, "秦所置郡名，在今广西一带", "Xiang"),
    743: ("keep", None, None, "the Baiyue"),

    # ── 百越之君，俯首系颈 ──
    744: ("keep", None, None, "the Baiyue"),
    745: ("keep", None, None, "ropes about their necks"),
    746: ("keep", None, None, "committing their lives"),

    # ── 乃使蒙恬北筑长城 ──
    747: ("fix", "蒙恬", "秦将蒙恬，始皇时北逐匈奴、筑长城", "Meng Tian"),
    748: ("keep", None, None, "the Xiongnu"),
    749: ("keep", None, None, "the frontier fence"),
    750: ("fix", "筑长城", "修筑长城（筑：修建）", "build the Great Wall"),

    # ── 士不敢弯弓而报怨 ──
    751: ("keep", None, None, "bend the bow"),
    752: ("keep", None, None, "avenge their wrongs"),

    # ── 废先王之道，焚百家之言 ──
    753: ("fix", None, "在这种情况下，于是", "Then"),
    754: ("keep", None, None, "common people"),
    755: ("fix", None, "本句为『废除、废弃』（废先王之道）", "dispensed with"),

    # ── 隳名城，杀豪杰 ──
    756: ("fix", "隳名城", "毁坏名城（隳 huī：毁坏）", "razed famous cities"),
    757: ("fix", "杀豪杰", "杀害豪杰之士（豪杰：才能出众的人）", "slaughtered heroes"),

    # ── 收天下之兵，聚之咸阳 ──
    758: ("fix", None, "全国、整个天下（天下之兵：天下的兵器）", "the world"),
    759: ("fix", "销锋镝", "销毁兵器（锋：刀刃；镝 dí：箭头）", "melted blades and arrowheads"),
    760: ("fix", None, "本句『铸以为』即铸成、铸作", "cast them into"),
    761: ("fix", None, "本句为使动『使……削弱』（以弱天下之民）", "weakening"),
    762: ("keep", None, None, "Xianyang"),

    # ── 践华为城，因河为池 ──
    763: ("fix", None, "本句『以为固』即把……当作坚固的凭借", "deeming it secure"),
    764: ("fix", None, "据守华山（践：登、据；华：华山）", "Mount Hua his wall"),
    765: ("fix", None, "深不可测（不测之渊：深不可测的深渊）", "fathomless"),
    766: ("keep", None, None, "the fathomless deep"),
    767: ("keep", None, None, "the Yellow River"),
    768: ("fix", None, "护城河（因河为池：以黄河为护城河）", "moat"),
    769: ("fix", "亿丈之城", "极高的城墙（亿丈：夸张说法，极言其高）", "the city walls a hundred million feet high"),

    # ── 良将劲弩守要害之处 ──
    770: ("fix", None, "本句为军事上险要之地", "the most important places"),
    771: ("keep", None, None, "strong bows"),
    772: ("keep", None, None, "crack troops"),

    # ── 天下已定，始皇之心 ──
    773: ("fix", None, "全国、整个天下", "The world"),
    774: ("fix", None, "本句『自以为』即自认为（非『把……作为』）", "saw the firmness of Guanzhong as"),
    775: ("keep", None, None, "Guanzhong"),
    776: ("keep", None, None, "a golden city"),
    777: ("keep", None, None, "to be emperors"),

    # ── 余威震于殊俗 ──
    778: ("keep", None, None, "regions of different customs"),

    # ── 然陈涉瓮牖绳枢之子 ──
    779: ("fix", "迁徙", "被征发流徙（迁徙之徒：被征发戍边的人）", "banished conscript"),
    780: ("del", None, None, None),
    781: ("keep", None, None, "broken-window"),
    782: ("keep", None, None, "rope-hinged door"),

    # ── 才能不及中人 ──
    783: ("fix", None, "本句『不及』即比不上、不如", "fell short of"),

    # ── 蹑足行伍之间，倔起阡陌之中 ──
    784: ("keep", None, None, "the furrows"),
    785: ("fix", None, "本句『数百』表约数，几、若干（非『命数』）", "a few hundred men"),

    # ── 天下云集响应，赢粮而景从 ──
    786: ("fix", None, "全国、整个天下（天下云集：天下人如云聚集）", "the world"),
    787: ("fix", None, "本句通『影』，名词作状语，像影子一样（景从：如影随形）", "as shadow follows form"),

    # ── 山东豪俊遂并起 ──
    788: ("keep", None, None, "east of the mountains"),

    # ── 且夫天下非小弱也 ──
    789: ("fix", None, "全国、整个天下", "the world"),
    790: ("fix", None, "古九州之一，秦据有其地", "Yongzhou"),
    791: ("fix", "自若", "依然如故、像原来一样（自若也：还是老样子）", "remained as before"),
    792: ("fix", None, "崤山与函谷关，秦国东面的险要关塞", "Xiao and Han"),
    793: ("fix", None, "本句『小弱』指变小变弱，弱为形容词（非使动）", "weak"),

    # ── 陈涉之位，非尊于……中山之君 ──
    794: ("fix", None, "中山国，战国时白狄所建诸侯国", "Zhongshan"),

    # ── 锄櫌棘矜 ──
    795: ("fix", None, "本句『棘矜』指棘木做的戟柄（矜 qín：矛戟之柄，非『怜惜』）", "thorn shafts"),

    # ── 谪戍之众，非抗于九国之师 ──
    796: ("keep", None, None, "the nine states"),

    # ── 非及乡时之士也 ──
    797: ("fix", None, "本句『非及』即比不上", "match"),

    # ── 成败异变，功业相反，何也 ──
    798: ("fix", "何也", "为什么（疑问代词『何』+ 语气词『也』）", "Why"),
    799: ("fix", None, "本句『异变』指变化不同（非意动）", "were different"),

    # ── 试使山东之国与陈涉度长絜大 ──
    800: ("keep", None, None, "east of the mountains"),
    801: ("fix", None, "本句为『谈论、相提并论』（同年而语）", "speakable of"),
    802: ("fix", None, "本句『度长』即量长短（度 duó：量，非『推测』）", "measured lengths"),

    # ── 致万乘之势，序八州而朝同列 ──
    803: ("keep", None, None, "ten thousand chariots"),
    804: ("fix", None, "本句为『达到、获得』（致万乘之势）", "attained"),
    805: ("fix", None, "本句『区区』形容小（区区之地：小小一块地盘，非『拳拳私心』）", "a mere patch of ground"),
    806: ("fix", None, "本句指同列的诸侯（原指位次相同）", "its fellow lords"),
    807: ("fix", "序八州", "安排八州的次序，即控制八州（序：排列次序）", "marshalled the eight provinces"),

    # ── 以六合为家，崤函为宫 ──
    808: ("fix", None, "崤山与函谷关，秦国东面的险要关塞", "Xiao-Han"),

    # ── 一夫作难而七庙隳 ──
    809: ("fix", None, "全国、整个天下（为天下笑：被天下人耻笑）", "to the world"),
    810: ("fix", "何也", "为什么（疑问代词『何』+ 语气词『也』）", "Why"),

    # ── 仁义不施而攻守之势异也 ──
    811: ("fix", None, "本句『异』为不同（攻守之势异：攻与守的形势不同）", "are different"),
}
