"""Step 7: extract exam-worthy 1-3 char terms from sentences.jsonl.

Input : data/sentences_sample.jsonl (200 lines, 汉书·地理志)
Output: data/terms_sample.jsonl + brief stats

Per classical-chinese-term-extractor skill:
  - prefer 2/3-char words & proper nouns; single chars only as filler (<40%)
  - term must be a verbatim substring of classical_sentence
  - meaning_in_this_sentence is contextual, not dictionary-copy
  - uncertain items get needs_review=true, never guessed

ID policy: the source sentences carry no id field, so we emit s001..sNNN
by line order and pass source_work through as `source`.
"""
import json
import re
import sys

BASE = "E:/Users/asus/workbuddy/guwen-project"
SRC = f"{BASE}/data/sentences_sample.jsonl"
OUT = f"{BASE}/data/terms_sample.jsonl"

CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def cjk_key(s):
    return "".join(CJK.findall(s or ""))


# ----------------------------------------------------------------------
# 词表：term -> (语境释义模板, 典型错误模式)
# ----------------------------------------------------------------------
DICT2 = {
    # 官职·仕履
    "视事": ("官员到职后亲自处理政务", "误拆为「视＋事」，按字面解作『看事情』"),
    "用事": ("掌权当政", "误解为『运用事物』"),
    "下车": ("官员刚到任所", "以今律古：误按乘车下车字面理解"),
    "致仕": ("交还官职、退休", "误拆为『致＋仕』，解作『导致做官』"),
    "解褐": ("脱去布衣、开始做官", "误按『脱下褐色衣服』字面解"),
    "释褐": ("脱去布衣、开始做官", "误按『脱下褐色衣服』字面解"),
    "践祚": ("登上皇位", "不识「祚」为帝位，误拆单字"),
    "移病": ("上书称病、请求离职", "误解为『转移疾病』"),
    "移疾": ("上书称病、请求离职", "误解为『疾病转移』"),
    "洗沐": ("官员例假休息", "误按『洗头洗澡』字面解"),
    "具狱": ("备齐案卷、定案", "误按『具备监狱』解"),
    "亢礼": ("以对等之礼相待", "不识「亢」通「抗」，误按『亢奋』解"),
    "款附": ("诚心归附", "误解为『款项依附』"),
    "款塞": ("叩塞门前来归降", "误解为『款项关塞』"),
    "敛衽": ("整饬衣襟以示恭敬", "误按『收衣服』字面解"),
    "介胄": ("披甲戴盔，代指武士", "不识「介」为甲，拆字误解"),
    "靖难": ("平定变乱", "误解为『使危难安定』语序"),
    "口实": ("话柄、借端", "以今律古：误按现代『食物』或『借口』泛义解"),
    "宽假": ("宽容、饶恕", "误解为『宽的假货』或拆字"),
    "旷职": ("旷废职守", "与今义近但易望文生义"),
    "陵折": ("欺压、折辱", "误按『丘陵曲折』解"),
    # 凝固结构（双字）
    "至于": ("①本句为『到达、来到』义（地理走向）；②他句或引出新话题", "以今律古：现代义只剩『提起另一事』，误读地理句"),
    "是以": ("因此、所以", "误拆为『这是用』"),
    "是故": ("因此、所以", "误拆为『这缘故』"),
    "然则": ("既然如此，那么", "误拆为『然而就』"),
    "虽然": ("虽然如此（词组，非今连词）", "以今律古：误当现代转折连词"),
    "于是": ("在这个时候／在此地（词组）", "以今律古：误当现代承接连词"),
    "以为": ("把……作为（『以之为』省略）", "以今律古：误当现代『认为』"),
    "其实": ("它实际上（词组）", "以今律古：误当现代副词"),
    # 地理志高频
    "侯国": ("列侯的封国，本句谓该地为此县之侯国（不设县令，改称相）", "误拆为『侯＋国』两个单字"),
    "盐官": ("朝廷设于盐产地、主管盐政的官署", "误指为『盐做成的官』或漏抽"),
    "铁官": ("朝廷设于铁产地、主管冶铸的官署", "误指为『铁打的官』或漏抽"),
    "橘官": ("朝廷设于产地、主管进贡柑橘的官署", "漏抽或误解为树名"),
    "工官": ("朝廷设于产地、主管手工业制造（如漆器、兵器）的官署", "误解为『工匠』泛称"),
    "木官": ("朝廷设于产地、主管木材采伐的官署", "漏抽"),
    "水官": ("主管水利的官职", "误解为『水上官员』"),
    "都尉": ("武官名，郡一级掌军事", "与『太尉』『郡尉』混淆"),
    "太守": ("郡的最高行政长官", "误拆『太＋守』"),
    "刺史": ("州一级监察长官", "误按『刺激历史』望文生义"),
    "禹贡": ("《禹贡》，《尚书》篇名，记载大禹时九州地理", "漏看书名号，拆为单字"),
    "内史": ("官名，掌京师地方行政", "误按『宫内史官』泛解；汉景帝时改称京兆尹"),
    "桑钦": ("人名，汉代学者，著有《水经》", "误当双字普通词，不知为专名"),
    # 帝称（本语料高频）
    "高帝": ("汉高祖刘邦（庙号尊称），本句纪年即以其在位年数计", "误拆『高＋帝』或误为泛称"),
    "武帝": ("汉武帝刘彻", "误为泛称『武功之帝』"),
    "宣帝": ("汉宣帝刘询", "误为泛称"),
    "文帝": ("汉文帝刘恒", "误为泛称"),
    "景帝": ("汉景帝刘启", "误为泛称"),
    # 年号
    "元鼎": ("汉武帝年号，本句『元鼎三年』以年号纪年", "不知为年号，误按字面『元月之鼎』解"),
    "元狩": ("汉武帝年号", "不知为年号"),
    "元封": ("汉武帝年号", "不知为年号"),
    "太初": ("汉武帝年号", "误按『太初』哲学义解"),
    # 《禹贡》土壤·地理术语
    "四海": ("天下、全国（古人以为中国四周环海）", "误按字面『四面都是海』"),
    "白壤": ("《禹贡》土壤分类：色白而质柔松的土", "误拆『白＋壤』，漏其分类术语义"),
    "周官": ("《周官》即《周礼》，记载周代官制", "漏看书名号"),
    "春秋": ("《春秋》，鲁国编年史", "以今律古：误按『春天秋天』季节义"),
    "中国": ("中原、黄河中下游一带（非今国名）", "以今律古：误按现代国家名解"),
    "山东": ("崤山／华山以东地区（非今山东省）", "以今律古：误按今省名解"),
    "河东": ("黄河以东地区（今山西西南）", "误按字面泛指河东边"),
    "河内": ("黄河以北地区", "误按字面解"),
    "天下": ("全国、整个天下", "误解为『天底下』"),
    "户口": ("住户与人口（『户』指户、『口』指人头）", "误当现代一词泛解"),
    "社稷": ("土神与谷神，代指国家", "误按『社会与庄稼』拆解"),
    "宗庙": ("天子诸侯供奉祖先的庙，代指王室", "误解为『宗族的庙会』"),
    "改元": ("皇帝更改年号", "误解为『更改元年』"),
    "即位": ("登上帝王之位", "与『继位』『践祚』辨析"),
    "崩殂": ("帝王去世", "不识『殂』为死，漏抽"),
    "北面": ("面向北（臣子朝拜之位）", "误解为『北边』方位"),
    "南面": ("面向南（君王听政之位）", "误解为『南边』方位"),
    "东宫": ("太子居所，代指太子", "误按『东边的宫殿』字面解"),
    "万乘": ("万辆兵车，代指天子大国", "误按『一万次』解"),
    "布衣": ("平民百姓（穿麻布衣者）", "误按『布做的衣服』字面解"),
    "黔首": ("平民百姓（以黑巾裹头者）", "不识『黔』为黑，拆字误解"),
    "编户": ("编入户籍的平民", "误解为『编辑户口』"),
    "缙绅": ("士大夫（插笏于带者）", "不识『缙』为插，拆字误解"),
    "耆旧": ("年高而有德望的老人", "不识『耆』为老，漏抽"),
    "宿儒": ("老成博学的读书人", "误按『住宿的儒生』解"),
    "处士": ("有才德而不做官的人", "误按『住处』解"),
}
DICT3 = {
    "乞骸骨": ("官员自请退休，使骸骨得归葬故乡", "漏抽整体，只留『乞』或『骸骨』；或误译『乞求尸骨』"),
    "山陵崩": ("君主去世的委婉说法", "误按『山陵坍塌』字面解"),
    "中道崩殂": ("中途去世", "拆字或不识『殂』"),
    "举孝廉": ("被推举为孝廉（汉代察举科目）", "误拆为『举＋孝＋廉』三个单字"),
    "尚书令": ("官名，尚书省长官，掌枢要", "漏抽官名整体"),
    "大司马": ("官名，掌军政最高长官", "漏抽官名整体"),
    "大司农": ("官名，掌国家财政钱谷", "漏抽官名整体"),
    "御史大夫": ("官名，副丞相（4字，本语料若出现按3字截取不计）", "漏抽"),
}
# 单字（仅在无多字词可抽或确有考点时补）
DICT1 = {
    "曰": ("说，此处『莽曰』即『王莽时改称为』", "误与前后连读为『莽曰X』整句人话"),
    "及": ("到、到达；或『以及』", "与『及物』今义混淆"),
    "克": ("战胜、攻下", "误按现代『能够』解"),
    "迁": ("调动官职（一般指升）", "误按『迁移』字面解"),
    "拜": ("授予官职", "误按『拜见』解"),
    "徙": ("调动／迁徙", "与『迁』混淆"),
    "领": ("兼任（以本官兼领他职）", "误按『带领』解"),
    "录": ("总领（如『录尚书事』）", "误按『记录』解"),
    "坐": ("因……获罪", "误按『坐下』解"),
    "慑": ("恐惧、震慑", "生僻漏读"),
    "厎": ("至、导致（通『底』『致』）", "通假字，误按本字『磨刀石』解"),
    "匦": ("匣子（『包匦菁茅』谓装匣）", "生僻漏读"),
    "纁": ("浅红色的丝帛", "生僻漏读"),
    "乱": ("横渡（『乱于河』谓横渡黄河，《禹贡》贡道术语）", "误按『混乱』解"),
    "浮": ("乘舟沿水路行进（《禹贡》贡道术语）", "误按『漂浮』解"),
    "厥": ("其、那（《禹贡》习语『厥土』＝那里的土）", "误当生僻字跳过"),
    "惟": ("是、为（『厥土惟白壤』的判断词）", "误按现代『惟独』解"),
    "纣": ("商朝末代君主帝辛，人名", "误当普通字"),
}

# ----------------------------------------------------------------------
# 规则抽取
# ----------------------------------------------------------------------
def extract_terms(sent):
    """返回 [(term, char_count, term_type, meaning, error_mode, needs_review)]"""
    spans = []  # (start, end, term, meaning, err, review) —— 全部为原句绝对位置

    def take_span(s, e, term, meaning, err, review=False):
        if any(not (e <= x[0] or s >= x[1]) for x in spans):
            return
        spans.append((s, e, term, meaning, err, review))

    def take(m, meaning, err, review=False):
        """m 必须是对原句 finditer/search 得到的整匹配"""
        s, e = m.span()
        take_span(s, e, m.group(0), meaning, err, review)

    def take_group(m, gi, meaning, err, review=False):
        """取 m 的第 gi 组，换算回原句绝对位置"""
        s = m.start(gi)
        term = m.group(gi)
        take_span(s, s + len(term), term, meaning, err, review)

    # 1) 词典命中（先三字后双字）
    for d, _tt in ((DICT3, "三字词"), (DICT2, "双字词")):
        for term, (mng, err) in d.items():
            for m in re.finditer(re.escape(term), sent):
                take(m, mng, err)

    # 2) 莽曰X：新莽改名的县名（专名，2-3字）
    for m in re.finditer(r"莽曰([\u4e00-\u9fff]{2,3})", sent):
        take_group(m, 1,
                   "（专名·县名）王莽当政时此县改用的新县名",
                   "漏抽专名整体；或误解为普通动词宾语", False)

    # 3) 水名：X水/X江/X河 + 方位动词或标点
    for m in re.finditer(r"([\u4e00-\u9fff]{1,2}[水江河])(?=[所出入东南西北至合过既乃皆，。、])", sent):
        if m.group(1) in ("江", "河", "水"):
            continue
        take(m, "（专名·水名）本句所记河流，句中方位动词指明其流向或发源地",
             "漏抽专名整体，只当普通名词『水／江／河』", True)
    # 3b) 山名：X山 + 方位/在
    for m in re.finditer(r"([\u4e00-\u9fff]{1,2}山)(?=[在东西南北])", sent):
        take(m, "（专名·山名）本句所记山，方位词指明其在县境的位置",
             "漏抽专名整体，只当普通名词『山』", True)

    # 4) 书名号内容（≤3字）
    SPECIAL_BOOK = {"诗": "《诗》即《诗经》，本句谓引其文为据",
                    "书": "《书》即《尚书》，本句谓引其文为据"}
    for m in re.finditer(r"[《【]([\u4e00-\u9fff]{1,3})[》】]", sent):
        x = m.group(1)
        take_group(m, 1, SPECIAL_BOOK.get(x, "（专名·书名）本句所引篇名，与地理考证相关"),
                   "漏看书名号，拆成普通词", False)
    # 4b) 《禹贡》九州州名
    for m in re.finditer(r"([青徐扬荆豫冀兖雍梁幽并营])州", sent):
        take_group(m, 0, "（专名·州名）古九州之一，本句述其山川物产或疆界",
                   "漏抽州名，或误为普通双字词", False)

    # 5) 离宫/苑囿/台馆：有X宫 或 X宫/台在…
    for m in re.finditer(r"有([\u4e00-\u9fff]{1,3}[宫馆台苑池])|([\u4e00-\u9fff]{1,2}[宫馆台苑池])(?=[在。）]|$)", sent):
        gi = 1 if m.group(1) else 2
        take_group(m, gi, "（专名·宫馆名）本句谓该地有此离宫／苑馆／高台，为帝王游猎或驻跸之所",
                   "漏抽专名整体，误按字面解『有座X的宫殿』", False)

    # 5b) 户口数字句：户／口为统计单位
    if re.match(r"^\s*户[\u4e00-\u9fff0-9]+，口", sent):
        for ch, mng in (("户", "（统计单位）本句谓此郡国编户数，数字即其辖下民户总量"),
                        ("口", "（统计单位）本句谓此郡国人口数，数字即其辖下人口总量")):
            m = re.search(re.escape(ch), sent)
            take(m, mng, "误当现代『户口』一词泛解，不知两字各为一项统计口径", False)

    # 5c) 「故X」定义句 → 2-3字专名
    m0g = re.match(r"^\s*故([\u4e00-\u9fff]{2,3})[。，]", sent)
    if m0g:
        take_group(m0g, 1, "（专名·待考）『故』谓其原为（某乡／某国），本词为该地原名，具体性质待查",
                   "漏抽专名，或误把『故』当『所以』连词", True)

    # 5d) 更名X：改称的新名
    for m in re.finditer(r"更名([\u4e00-\u9fff]{1,3})[。，]", sent):
        take_group(m, 1, "（专名·新名）本句谓该郡／国／县此时改用的新名称",
                   "漏抽新名，或误当普通词", False)

    # 5e) 县N：X → 治所县名
    for m in re.finditer(r"县[\u4e00-\u9fff0-9一二三四五六七八九十百]*[：:]([\u4e00-\u9fff]{2,3})[，。]", sent):
        take_group(m, 1, "（专名·县名）本郡首县／治所，句中『县N』谓本郡共辖N县",
                   "漏抽治所县名", False)

    # 5f) 句首朝代名
    m0d = re.match(r"^\s*(秦|汉|周|殷|夏|楚|燕|越)(?=遂|并|兴|亡|灭|王|之)", sent)
    if m0d:
        take(m0d, "（专名·朝代名）本句以朝代为主语，叙述其政治地理沿革",
             "误当普通形容词作修饰语解", False)

    # 6) 句首定义式「X，……邑／国／县／置」
    m0 = re.match(r"^\s*(?:故\s*)?([\u4e00-\u9fff]{1,3})\s*，", sent)
    if m0 and re.search(r"[，。]\s*[^，。]{0,8}(邑|国|县|郡|置|莽曰)", sent):
        take_group(m0, 1, "（专名·郡县名）本句首词为该条目所记郡／县名，后文交代设置朝代或归属",
                   "漏抽郡县名，或误当普通词", True)

    # 7) 逗号枚举链：连续 1-3 字专名候选（虚词单元跳过；带郡/国/县/州后缀者放行）
    STOP = re.compile(r"[姓后之而以所为曰于其有及年罢置复属省都治故初帝王公侯县０-９0-9]")
    SUFFIX = re.compile(r"[\u4e00-\u9fff]{1,2}[郡国县州]$")
    parts = re.split(r"[，；：]", sent)
    off = 0
    for p in parts:
        cn = CJK.findall(p)
        if cn:
            core = "".join(cn)
            first = p.find(cn[0])
            if len(core) <= 3 and (not STOP.search(core) or SUFFIX.search(core)):
                start = off + first
                m = re.match(re.escape("".join(cn)), sent[start:])
                if m and cjk_key(m.group(0)) == cjk_key(core):
                    if SUFFIX.search(core):
                        take_span(start, start + len(core), core,
                                  "（专名·郡国名）本句所记郡／国名，后文交代其设置或归属",
                                  "漏抽专名，或误当普通双字词解其字面义", False)
                    else:
                        take_span(start, start + len(core), core,
                                  "（专名·待考）逗号并列的县名／邑名，具体所指待查",
                                  "漏抽专名，或误当普通双字词解其字面义", True)
        off += len(p) + 1

    # 8) 顿号枚举串 → 专名候选
    parts = re.split(r"[、]", sent)
    off = 0
    for p in parts:
        cn = CJK.findall(p)
        first = p.find(cn[0]) if cn else -1
        if first >= 0:
            core = "".join(cn)
            if 2 <= len(core) <= 3:
                start = off + first
                m = re.match(re.escape(core), sent[start:])
                if m and cjk_key(m.group(0)) == cjk_key(core):
                    take_span(start, start + len(core), core,
                              "（专名·待考）顿号并列的专名（山名／水名／县名），具体所指待查",
                              "漏抽专名，或误当普通双字词解其字面义", True)
        off += len(p) + 1

    # 9) 单字补充（不与已命中的多字词重叠）
    used = [(x[0], x[1]) for x in spans]
    for term, (mng, err) in DICT1.items():
        for m in re.finditer(re.escape(term), sent):
            s, e = m.span()
            if any(not (e <= a or s >= b) for a, b in used):
                continue
            spans.append((s, e, term, mng, err, False))
            break

    # 去重、按位置排序、组装
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out, seen = [], set()
    for s, e, term, mng, err, review in spans:
        if term in seen:
            continue
        seen.add(term)
        n = len(CJK.findall(term))
        if n > 3:
            continue
        tt = {1: "单字词", 2: "双字词", 3: "三字词"}[n]
        d = {"term": term, "char_count": n, "term_type": tt,
             "meaning_in_this_sentence": mng, "typical_error_mode": err}
        if review:
            d["needs_review"] = True
        out.append(d)
    return out

def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    n_terms = {"单字词": 0, "双字词": 0, "三字词": 0}
    n_review = 0
    empty = []
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for i, r in enumerate(rows, 1):
            sent = r["classical"]
            terms = extract_terms(sent)
            for t in terms:
                n_terms[t["term_type"]] += 1
                n_review += 1 if t.get("needs_review") else 0
            if not terms:
                empty.append((i, sent))
            rec = {"id": f"s{i:03d}", "source": r.get("source_work", ""),
                   "classical_sentence": sent, "terms": terms}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total = sum(n_terms.values())
    multi = n_terms["双字词"] + n_terms["三字词"]
    brief = [
        f"句子数: {len(rows)}  词项总数: {total}",
        f"分布: 单字 {n_terms['单字词']} / 双字 {n_terms['双字词']} / 三字 {n_terms['三字词']}",
        f"双字+三字占比: {multi / total * 100:.1f}%",
        f"needs_review: {n_review}",
        f"空 terms 句: {len(empty)} {[s for _, s in empty[:5]]}",
    ]
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(brief))
    with open(OUT.replace(".jsonl", "_brief.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(brief) + "\n")


if __name__ == "__main__":
    main()
