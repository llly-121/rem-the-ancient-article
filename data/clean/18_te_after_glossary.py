# -*- coding: utf-8 -*-
"""18: 专名回改后，同步更新受影响的 term_english

改英译会让原 term_english 不再是指定句的子串（56 条失效）。
本模块只覆盖这些词的英文片段，term/meaning 保持原值（action='keep'）。
载入顺序排在 17_ 之后，step12 合并时自动覆盖前值。
"""

R = {
    # ── 出师表 ──
    102: ("keep", None, None, "the realm"),
    103: ("keep", None, None, "The late Emperor"),
    105: ("keep", None, None, "the late Emperor"),
    118: ("keep", None, None, "rule"),
    119: ("keep", None, None, "the officials in charge"),
    133: ("keep", None, None, "Palace Attendants"),
    134: ("keep", None, None, "Imperial Secretaries"),
    135: ("keep", None, None, "Chief Secretaries"),
    136: ("keep", None, None, "I hope Your Majesty will draw close"),
    137: ("keep", None, None, "loyal and upright"),
    138: ("keep", None, None, "all these are"),
    158: ("keep", None, None, "my poor powers"),
    159: ("keep", None, None, "root out"),
    160: ("keep", None, None, "the treacherous and the evil"),
    166: ("keep", None, None, "weighing measures and interests"),
    167: ("keep", None, None, "measures and interests"),

    # ── 过秦论 ──
    684: ("keep", None, None, "Mount Xiao and the Hangu Pass"),
    700: ("keep", None, None, "followed the bequeathed policy"),
    702: ("keep", None, None, "carried on the old enterprise"),
    705: ("keep", None, None, "strategic commanderies"),
    713: ("keep", None, None, "Lord Mengchang"),
    715: ("keep", None, None, "Lord Chunshen"),
    791: ("keep", None, None, "as they had always been"),
    792: ("keep", None, None, "Mount Xiao and the Hangu Pass"),
    808: ("keep", None, None, "Mount Xiao and the Hangu Pass"),

    # ── 廉颇蔺相如列传 ──
    816: ("keep", None, None, "a High Minister"),    819: ("keep", None, None, "a man of Zhao"),
    837: ("keep", None, None, "How do you"),
    841: ("keep", None, None, "I told him"),
    880: ("keep", None, None, "the King of Qin"),
    913: ("keep", None, None, "The King of Qin"),
    919: ("keep", None, None, "the King of Qin"),
    920: ("keep", None, None, "The King of Zhao"),
    929: ("keep", None, None, "The King of Qin"),
    932: ("keep", None, None, "the King of Qin"),
    945: ("keep", None, None, "the King of Qin"),
    952: ("keep", None, None, "the boiling cauldron"),
    953: ("keep", None, None, "The King of Qin"),
    977: ("keep", None, None, "the land west of the Yellow River"),
    985: ("keep", None, None, "The King of Zhao"),
    994: ("keep", None, None, "the King of Qin"),
    997: ("keep", None, None, "the King of Zhao"),
    999: ("keep", None, None, "The King of Zhao"),
    1002: ("keep", None, None, "the King of Qin"),
    1003: ("keep", None, None, "the King of Zhao"),
    1007: ("keep", "赵王", None, "The King of Zhao has privately heard"),
    1012: ("keep", None, None, "the King of Qin"),
    1014: ("keep", None, None, "kneeling"),
    1042: ("keep", None, None, "a High Minister"),
    1043: ("keep", None, None, "Xiangru's merit"),
    1045: ("keep", None, None, "the meeting was over"),
    1074: ("keep", None, None, "the King of Qin"),
    1075: ("keep", None, None, "Lin Xiangru"),
    1076: ("keep", None, None, "how does General Lian compare with"),
    1094: ("keep", None, None, "bared his shoulders and back"),
    1095: ("keep", None, None, "carried bramble thorns on his back"),
    1096: ("keep", None, None, "beg pardon"),
    1099: ("keep", None, None, "sworn to die for each other"),
}
