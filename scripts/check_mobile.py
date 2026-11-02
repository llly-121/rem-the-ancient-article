# -*- coding: utf-8 -*-
"""网页版在手机上的验收：布局、热区、主流程、篇章、配色。

为什么需要它：iOS 版有 XCUITest 兜着，网页版没有。而网页版踩的坑恰恰是
「Windows 浏览器里看不出来、只有 iPhone 上才现形」的那一类：

  · iPhone 15 Pro Max 屏宽 430，而布局按 390 设计 → 四周一圈黑框
  · 底部 Tab 不加 safe-area → 被 Home Indicator 压住，点不到
  · 热区小于 44pt → 手指按不中
  · data.js 1.4 MB，弱网下长时间空白 → 用户以为打不开
  · 「回首页」按钮的 data-act 没有对应分支 → 点了完全没反应（纯空操作，
    连报错都没有），而小结页只有这一个按钮，用户直接卡死
  · 「未揭晓的选中」和「揭晓后的正确」用了同一套 CSS → 一起改绿就提前变绿

用法：
    python scripts/check_mobile.py            # 起本地服务并跑全部检查
    python scripts/check_mobile.py --url URL  # 检查已部署的线上版本

依赖：playwright 不需要，用系统自带的 Edge + CDP（websocket-client）。
"""
import argparse
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
WEB = os.path.join(ROOT, "web-demo")
OUT = os.path.join(WEB, "_shots")

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# 覆盖 iPhone 的屏宽两个极端：SE/mini 375、Max 430
DEVICES = [("se_375", 375, 667), ("i14_390", 390, 844), ("max_430", 430, 932)]


def free_port(start=8900):
    for p in range(start, start + 60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise RuntimeError("没有空闲端口")


def serve(directory):
    port = free_port()

    class Q(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), Q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}/index.html"


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=30)
        self.i = 0

    def send(self, method, **params):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.i:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def js(self, expr):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True)
        return r.get("result", {}).get("value")

    def shot(self, path):
        r = self.send("Page.captureScreenshot", format="png")
        data = base64.b64decode(r["data"])
        # 先写临时文件再替换：截图常被预览面板/杀软短暂占用，
        # 直接 open(path,"wb") 会 PermissionError，把整轮验收带崩。
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        for i in range(6):
            try:
                os.replace(tmp, path)
                return
            except OSError:
                time.sleep(0.2)
        # 目标被预览面板/杀软独占时连 replace 都进不去（WinError 5）。
        # 截图只是给人看的诊断物，不该让整轮验收崩掉 —— 退到带后缀的副本。
        alt = path[:-4] + "_new.png"
        try:
            os.replace(tmp, alt)
            print(f"  （{os.path.basename(path)} 被占用，截图改写到 {os.path.basename(alt)}）",
                  flush=True)
        except OSError:
            try: os.remove(tmp)
            except OSError: pass


def boot_edge(port):
    exe = next((p for p in EDGE_CANDIDATES if os.path.exists(p)), None)
    if not exe:
        raise RuntimeError("找不到 Edge，请手动指定路径")
    tmp = tempfile.mkdtemp(prefix="guwen_edge_")
    proc = subprocess.Popen(
        [exe, "--headless=new", f"--remote-debugging-port={port}",
         f"--user-data-dir={tmp}", "--no-first-run", "--no-default-browser-check",
         "--disable-gpu", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1)):
                if t["type"] == "page":
                    return proc, tmp, t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Edge 启动超时")


PROBE = r"""
(() => {
  const de = document.documentElement;
  const phone = document.getElementById('phone');
  const pr = phone.getBoundingClientRect();
  const overflow = [...document.querySelectorAll('#phone *')].filter(el => {
    const b = el.getBoundingClientRect();
    return b.width > 0 && (b.left < -1 || b.right > window.innerWidth + 1);
  }).length;
  const taps = [...document.querySelectorAll('button,[role=button],.opt')]
    .map(el => el.getBoundingClientRect()).filter(b => b.width > 0 && b.height > 0);
  const boot = document.getElementById('boot');
  const W = window.GUWEN && window.GUWEN.works;
  return {
    vw: window.innerWidth, vh: window.innerHeight,
    phoneFills: Math.abs(pr.width - window.innerWidth) < 1 && Math.abs(pr.height - window.innerHeight) < 1,
    sideMargin: Math.round(pr.left),
    overflowEls: overflow,
    tapMin: taps.length ? Math.round(Math.min(...taps.map(b => b.height))) : null,
    textareas: document.querySelectorAll('textarea').length,
    bootHidden: boot ? getComputedStyle(boot).display === 'none' : true,
    cards: window.GUWEN && window.GUWEN.cards ? window.GUWEN.cards.length : null,
    works: W ? W.length : 0,
    allSent: W ? W.reduce((n, w) => n + w.s.length, 0) : 0,
    footnotes: document.querySelectorAll('.footnote').length,
    entryTag: (document.querySelector('.entry') || {}).tagName || null,
    dictWords: (window.GUWEN_DICT && window.GUWEN_DICT.n) || 0,
  };
})()
"""


def run(url, shots=True):
    os.makedirs(OUT, exist_ok=True)
    fails, notes = [], []

    # 切词正则必须两边逐字一致：index.html 在运行期切词，build_dict.py 在构建期
    # 统计词表。两边一旦不一致，就会出现「页面上能点到的词，词库里根本没有」，
    # 或者反过来——这类 bug 极难在界面上看出来，所以直接比源串。
    try:
        idx_src = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        dic_src = open(os.path.join(ROOT, "scripts", "build_dict.py"), encoding="utf-8").read()
        m1 = re.search(r"const WORD_RE = (/.*?/g);", idx_src)
        m2 = re.search(r'WORD_RE = re\.compile\(r"(.*?)"\)', dic_src)
        if not (m1 and m2):
            fails.append("切词: 两边都找不到 WORD_RE 定义，写法可能被改了")
        elif m1.group(1) != "/" + m2.group(1) + "/g":
            fails.append(f"切词: 正则不一致 —— index.html {m1.group(1)} / "
                         f"build_dict.py {m2.group(1)}")
        else:
            print("ok   切词       两边 WORD_RE 一致", flush=True)
    except Exception as e:
        fails.append(f"切词: 读取源文件失败 {e}")

    port = free_port(9400)
    proc, tmp, ws = boot_edge(port)
    fails, notes = [], []
    try:
        c = CDP(ws)
        c.send("Page.enable")
        c.send("Runtime.enable")
        for tag, w, h in DEVICES:
            c.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
                   deviceScaleFactor=3, mobile=True)
            c.send("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
            c.send("Emulation.setUserAgentOverride", userAgent=UA_IPHONE)
            c.send("Page.navigate", url=url)
            ok = False
            for _ in range(120):
                if c.js("!!window.GUWEN && !!window.GUWEN.cards.length"):
                    ok = True
                    break
                time.sleep(0.25)
            if not ok:
                fails.append(f"{tag}: 题库没加载出来（window.GUWEN 为空）")
                continue
            time.sleep(0.35)
            m = c.js(PROBE)
            if shots:
                c.shot(os.path.join(OUT, f"home_{tag}.png"))

            tag_fails = []
            if not m["phoneFills"]:
                tag_fails.append(f"没铺满屏（左右各留 {m['sideMargin']}px，会出现「手机套手机」的黑框）")
            if m["overflowEls"]:
                tag_fails.append(f"{m['overflowEls']} 个元素横向溢出被裁")
            if m["tapMin"] is not None and m["tapMin"] < 44:
                tag_fails.append(f"最小热区 {m['tapMin']}px < 44pt，手指按不中")
            if m["textareas"] != 0:
                tag_fails.append(f"页面上有 {m['textareas']} 个 textarea —— 默写已删，不该再有输入框")
            if not m["bootHidden"]:
                tag_fails.append("首屏加载层没消失，会一直盖着")
            if m["cards"] < 1346:
                tag_fails.append(f"卡片数 {m['cards']}，少于基线 1346（卡被删了？）")
            if m["works"] < 25 or m["allSent"] < 654:
                tag_fails.append(f"篇章 {m['works']} 篇 / {m['allSent']} 句，少于基线 25 篇 / 654 句")
            if m["footnotes"]:
                tag_fails.append("首页还留着 .footnote 说明文字（用户要求删掉）")
            if m["entryTag"] != "BUTTON":
                tag_fails.append(f"「按篇刷题」入口是 <{m['entryTag']}>，应为 <button>"
                                 "（div 点不了、也不进热区检查）")
            if m["dictWords"] < 2000:
                tag_fails.append(f"离线词库只有 {m['dictWords']} 词，dict.js 可能没加载或没生成")

            for f in tag_fails:
                fails.append(f"{tag}: {f}")
            print(f"{'FAIL' if tag_fails else 'ok  '} {tag:10s} "
                  f"phone={w}x{h} tapMin={m['tapMin']} cards={m['cards']} "
                  f"works={m['works']}/{m['allSent']}", flush=True)

        # 走一遍答题流程，确认改布局没把交互弄坏
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844,
               deviceScaleFactor=3, mobile=True)
        c.send("Page.navigate", url=url)
        for _ in range(120):
            if c.js("!!window.GUWEN && !!window.GUWEN.cards.length"):
                break
            time.sleep(0.25)
        time.sleep(0.3)
        c.js("document.querySelector('[data-act=start]').click()")
        time.sleep(0.5)
        # 点选 → 答案页必须当场换页。这里量的是页面内的同步耗时：
        # 旧实现在点击后先亮一下选中态、再 setTimeout 400ms 才换页，
        # 真机体感就是「点完选项愣一下」。400 这个数字回归过一次（用户报的），
        # 所以钉一条延时断言，别只断言「最终到了答案页」。
        picked = c.js("(()=>{const b=document.querySelector('[data-act=pick]');"
                      "if(!b)return null;"
                      "const t0=performance.now();b.click();"
                      "return {ms:performance.now()-t0,"
                      "answer:!!document.querySelector('[data-act=next]')}})()")
        pick_ms = round(picked["ms"], 1) if picked else None
        if picked and pick_ms > 120:
            fails.append(f"流程: 点选项到答案页用了 {pick_ms}ms，应几乎即时（<120ms）")
        time.sleep(0.9)  # 答案页有 0.22s slide-in，太早量会量到 translateX 中间态
        tf = c.js("(()=>{const cv=document.querySelector('.cover');"
                  "return cv?getComputedStyle(cv).transform:null})()")
        nxt = c.js("!!document.querySelector('[data-act=next]')")
        if not picked:
            fails.append("流程: 点了「开始一轮」但没出现选项")
        elif not picked["answer"]:
            fails.append("流程: 点完选项的同一帧里没有出现「下一题」，换页被推迟了")
        if not nxt:
            fails.append("流程: 选完选项后没有「下一题」，答案页没出来")
        if tf not in (None, "none", "matrix(1, 0, 0, 1, 0, 0)"):
            fails.append(f"流程: 答案页停留在动画中间态 transform={tf}")
        if not c.js("!!document.querySelector('.zh')"):
            fails.append("答案页: 没有白话块（.zh）")
        if shots:
            c.shot(os.path.join(OUT, "flow_answer_i14.png"))
        ok_flow = bool(picked and picked["answer"] and nxt and pick_ms is not None and pick_ms <= 120)
        print(f"{'ok  ' if ok_flow else 'FAIL'} "
              f"流程       开一轮→选一项→答案页（换页 {pick_ms}ms）", flush=True)

        # ── 点词浮卡 ─────────────────────────────────────────────
        # 三个都要查：卡有没有出来、是不是完全落在机身内（#phone 是 overflow:hidden，
        # 越界就被裁掉）、是不是在词的上方（用户明确要求「从词上方弹出」）。
        tip = c.js("""(()=>{
          const w = document.querySelector('.en .w');
          if (!w) return {found:false};
          w.click();
          const t = document.querySelector('.gw-tip');
          if (!t) return {found:true, tip:false};
          const pb = document.getElementById('phone').getBoundingClientRect();
          const r  = t.getBoundingClientRect();
          const wr = w.getBoundingClientRect();
          return {found:true, tip:true, word:w.dataset.w,
                  inside: r.left >= pb.left - 1 && r.right <= pb.right + 1 &&
                          r.top >= pb.top - 1  && r.bottom <= pb.bottom + 1,
                  above:  r.bottom <= wr.top + 1,
                  hasSay: !!t.querySelector('[data-act=say]'),
                  hasIpa: !!t.querySelector('.gw-ipa'),
                  text: t.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30)};
        })()""")
        # 等淡入结束再量、再截图：卡片有 opacity 0→1 的 160ms 过渡，
        # 在动画中途截图会拍出一张「半透明浮卡」，看着像背景没生效。
        time.sleep(0.35)
        style = c.js("""(()=>{
          const t = document.querySelector('.gw-tip'); if(!t) return {};
          const cs = getComputedStyle(t);
          return {op: parseFloat(cs.opacity), bg: cs.backgroundColor,
                  blur: cs.backdropFilter || cs.webkitBackdropFilter || '',
                  raw: t.textContent};
        })()""")
        if shots:
            c.shot(os.path.join(OUT, "flow_word_tip.png"))

        # 发音：联网时请求有道真人音；断网时必须退系统 TTS，不能点了毫无反应。
        # 这里只断言「有明确结果且不抛错」，不苛求一定拿到 mp3 ——
        # CI 机器上未必能连外网，但用户手机上要能响。
        c.send("Network.enable")
        c.js("(()=>{const b=document.querySelector('.gw-tip [data-act=say]');if(b){b.click();return true}return false})()")
        time.sleep(1.6)
        say_online = c.js("window.__say && window.__say.last")
        c.send("Network.emulateNetworkConditions", offline=True, latency=0,
               downloadThroughput=0, uploadThroughput=0)
        c.js("(()=>{const b=document.querySelector('.gw-tip [data-act=say]');if(b){b.click();return true}return false})()")
        time.sleep(1.6)
        say_off = c.js("window.__say && window.__say.last")
        c.send("Network.emulateNetworkConditions", offline=False, latency=0,
               downloadThroughput=-1, uploadThroughput=-1)
        # 点空白收卡
        c.js("(()=>{const s=document.querySelector('.cover .scroll');if(s)s.click()})()")
        time.sleep(0.2)
        tip_closed = not c.js("!!document.querySelector('.gw-tip')")

        if not tip["found"]:
            fails.append("词典: 答案页的英译里没有逐词 span（.en .w），点词无从谈起")
        elif not tip["tip"]:
            fails.append("词典: 点了单词但浮卡没出来")
        else:
            if not tip["inside"]:
                fails.append("词典: 浮卡超出机身范围，会被 overflow:hidden 裁掉")
            if not tip["above"]:
                fails.append("词典: 浮卡没出现在这个词的上方")
            if not (tip["hasSay"] and tip["hasIpa"]):
                fails.append(f"词典: 浮卡缺发音按钮或音标 {tip}")
        # 玻璃质感：底色必须不透明到能压住下面的选项（rgba 的 a ≥ .8），
        # 且淡入已完成。少了这条，浮卡透明化这种「只有截屏才看得出来」的错会漏过。
        if style and style.get("op", 0) < 0.95:
            fails.append(f"词典: 浮卡淡入没完成（opacity {style.get('op')}）")
        if style and style.get("bg", "").startswith("rgba"):
            alpha = float(style["bg"].rsplit(",", 1)[-1].strip(" )") or 1)
            if alpha < 0.8:
                fails.append(f"词典: 浮卡背景太透（{style['bg']}），下面的选项会透上来")
        # ECDICT 的多行释义是字面量 \n，忘了转义会让浮卡上出现「使\nn. 条件」这种鬼东西
        if style and "\\n" in (style.get("raw") or ""):
            fails.append("词典: 释义里残留字面量 \\n，clean_gloss 没做反转义")
        if say_off not in ("tts", "none"):
            fails.append(f"发音: 断网时没有回退到系统 TTS（状态 {say_off}）")
        if not tip_closed:
            fails.append("词典: 点卡片外面没收掉浮卡")
        tip_ok = tip["found"] and tip["tip"] and tip["inside"] and tip["above"] and tip_closed
        print(f"{'FAIL' if not tip_ok else 'ok  '} 词典       点词 {tip.get('word')} → "
              f"浮卡{'(上方)' if tip.get('above') else '(位置不对)'} → 发音 "
              f"{say_online or '-'} / 断网 {say_off or '-'}", flush=True)

        # ── 中途退出 ─────────────────────────────────────────────
        # 用户原话：「不然每次要背完 20 题才能退出到主界面」。
        # 根因是答案页顶栏只有一个空的 <span>，而这一轮 90% 的时间都停在答案页。
        exit_btn = c.js("!!document.querySelector('.cover [data-act=exit]')")
        c.js("(()=>{const b=document.querySelector('.cover [data-act=exit]');if(b){b.click();return true}return false})()")
        time.sleep(0.3)
        exit_sheet = c.js("(()=>{const h=document.querySelector('.sheet h4');return h?h.textContent.trim():''})()")
        c.js("(()=>{const b=document.querySelector('[data-act=doexit]');if(b){b.click();return true}return false})()")
        time.sleep(0.45)
        exited = c.js("!!document.querySelector('[data-act=start]') && !document.querySelector('.cover')")
        if not exit_btn:
            fails.append("退出: 答案页没有退出按钮（用户就是卡在这里）")
        if not exit_sheet:
            fails.append("退出: 点退出没弹出确认层")
        if not exited:
            fails.append("退出: 确认退出后没回到首页")
        print(f"{'FAIL' if not (exit_btn and exit_sheet and exited) else 'ok  '} "
              f"退出       答案页退出 → 确认「{exit_sheet or '-'}」→ 回首页", flush=True)

        # 重新开一轮，准备把 20 题走完
        c.js("document.querySelector('[data-act=start]').click()")
        time.sleep(0.5)

        # 20 题走完 → 小结 →「回首页」。用户报的 bug 就在这一步：
        # case "home" 当初根本没有分支，点了既不报错也不重绘。
        # 这里必须「有选项就选、没选项就下一题」交替推进：上一次已经停在答案页了。
        for _ in range(60):
            if c.js("!!document.querySelector('[data-act=pick]')"):
                c.js("document.querySelector('[data-act=pick]').click()")
                time.sleep(0.55)
                continue
            if c.js("!!document.querySelector('[data-act=next]')"):
                c.js("document.querySelector('[data-act=next]').click()")
                time.sleep(0.25)
                continue
            break
        on_summary = c.js("!!document.querySelector('.summary-title')")
        c.js("(()=>{const b=document.querySelector('[data-act=home]');if(b){b.click();return true}return false})()")
        time.sleep(0.5)
        back_home = c.js("!!document.querySelector('[data-act=start]') && !document.querySelector('.cover')")
        if not on_summary:
            fails.append("小结: 20 题答完没进小结页（.summary-title 不在）")
        if not back_home:
            fails.append("小结: 点「回首页」没回到首页 —— 这就是用户反馈的那个 bug")
        print(f"{'FAIL' if not (on_summary and back_home) else 'ok  '} 流程       20 题→小结→回首页", flush=True)

        # 篇章：目录 → 篇详情 → 点句弹层 → 刷题 → 白话 + 对错配色
        c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b){b.click();return true}return false})()")
        time.sleep(0.4)
        n_rows = c.js("document.querySelectorAll('[data-act=openwork]').length")
        # 用户要求：目录顶部那段说明改短，并明确「灰=未刷、黑=已刷」
        hint = c.js("(()=>{const p=document.querySelector('.footnote');"
                    "return p?p.textContent.replace(/\\s+/g,'').trim():''})()") or ""
        if len(hint) > 30 or "灰" not in hint or "黑" not in hint:
            fails.append(f"文案: 目录说明应短（≤30 字）且点明灰/黑含义，实际「{hint}」（{len(hint)} 字）")
        c.js("document.querySelector('[data-act=openwork]').click()")
        time.sleep(0.35)
        det = c.js("(()=>{return {text:!!document.querySelector('.worktext'),"
                   "sl:document.querySelectorAll('.sl').length,"
                   "start:!!document.querySelector('[data-act=wstart]')}})()")
        c.js("document.querySelector('.sl').click()")
        time.sleep(0.35)
        sh = c.js("(()=>{return {cl:!!document.querySelector('.sd-cl'),"
                  "np:document.querySelectorAll('.sheet-body p').length}})()")
        if shots:
            c.shot(os.path.join(OUT, "flow_work_detail.png"))
        c.js("(()=>{const b=document.querySelector('[data-act=closesheet]');if(b)b.click()})()")
        time.sleep(0.2)
        c.js("document.querySelector('[data-act=wstart]').click()")
        time.sleep(0.5)
        w_quiz = c.js("!!document.querySelector('[data-act=pick]')")

        # 配色三问：
        #   1. 揭晓后的正确项要等于 --ok
        #   2. 揭晓后的错选项要等于 --bad
        #   3. 两者不能相等
        # 只比「两者不同」是不够的：把正确项改回原来的橙色，它们同样不同。
        # （原来还有一问是「未揭晓的选中态不能是绿色」，自从点选即换页，
        #   选中态这一帧已经不存在，那一问随之作废，改由上面那条 120ms 延时断言盯着）
        JS_TOKENS = """(()=>{
          const e=document.createElement('span');
          document.body.appendChild(e);
          e.style.color='var(--ok)';  const ok=getComputedStyle(e).color;
          e.style.color='var(--bad)'; const bad=getComputedStyle(e).color;
          e.remove();
          const cor=document.querySelector('.opt.correct');
          const bad2=document.querySelector('.opt.wrong');
          return {ok, bad,
                  correct: cor ? getComputedStyle(cor).borderTopColor : null,
                  wrong: bad2 ? getComputedStyle(bad2).borderTopColor : null};
        })()"""

        zh_ok, tok = False, None
        for _ in range(4):
            if not c.js("!!document.querySelector('[data-act=pick]')"):
                break
            c.js("document.querySelector('[data-act=pick]').click()")
            time.sleep(0.5)
            zh_ok = bool(c.js("!!document.querySelector('.zh')"))
            tok = c.js(JS_TOKENS)
            if tok and tok["wrong"]:
                break
            c.js("document.querySelector('[data-act=next]').click()")
            time.sleep(0.3)

        # 篇数基准从 data.js 现读：库里会持续入库新篇，写死 25 每加一篇就误报
        n_expect = int(c.js("(window.GUWEN.works||[]).length") or 0)
        if n_rows != n_expect:
            fails.append(f"篇章: 目录里有 {n_rows} 篇，data.js 是 {n_expect} 篇")
        if not (det["text"] and det["sl"] > 0 and det["start"]):
            fails.append(f"篇章: 篇详情缺整篇原文或开始按钮 {det}")
        if not (sh["cl"] and sh["np"] >= 2):
            fails.append(f"篇章: 点句子没弹出白话/英译 {sh}")
        if not w_quiz:
            fails.append("篇章: 「开始刷本篇」之后没出现选项")
        if not zh_ok:
            fails.append("篇章: 篇内答题的答案页没有白话块")
        if not tok:
            fails.append("配色: 连答 4 题都没出现「答错」的答案页，无法比对红绿")
        else:
            if tok["correct"] != tok["ok"]:
                fails.append(f"配色: 正确项是 {tok['correct']}，应为 --ok {tok['ok']}（绿色）")
            if tok["wrong"] != tok["bad"]:
                fails.append(f"配色: 错选项是 {tok['wrong']}，应为 --bad {tok['bad']}（红色）")
        if shots:
            c.shot(os.path.join(OUT, "flow_work_answer.png"))
        ok_all = (n_rows == n_expect and det["text"] and w_quiz and zh_ok and tok
                  and tok["correct"] == tok["ok"] and tok["wrong"] == tok["bad"])
        print(f"{'FAIL' if not ok_all else 'ok  '} "
              f"篇章       目录 {n_rows} 篇→篇详情 {det['sl']} 句→刷题", flush=True)
        print(f"{'ok  ' if ok_all else 'FAIL'} "
              f"配色       正确 {tok['correct'] if tok else '-'} / 错误 {tok['wrong'] if tok else '-'}", flush=True)

        # ── 篇内题池：一轮 20 题要从「整篇题池」里抽，不能固定取前 20 张 ──
        # 用户报「随机刷题每次的 20 题都是固定的」。原来 buildWorkRound 按原文顺序
        # 从头取 20 张，长篇每轮都是同一批，退出重进更是原地踏步。这里验三件事：
        #   1. 池子 = 整篇题数（不是 20）
        #   2. 连着两轮抽出来的不是同一批
        #   3. 「整篇一遍」真能一次给出全池
        WORK_T = "滕王阁序"
        c.js("(()=>{const b=document.querySelector('.cover [data-act=exit]');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("(()=>{const b=document.querySelector('[data-act=doexit]');if(b)b.click()})()")
        time.sleep(0.4)

        def enter_work():
            c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
            time.sleep(0.35)
            c.js(f"""(()=>{{const r=[...document.querySelectorAll('[data-act=openwork]')]
              .find(x=>x.textContent.includes('{WORK_T}'));if(r)r.click();}})()""")
            time.sleep(0.35)
            c.js("""(()=>{const b=[...document.querySelectorAll('[data-act=wmode]')]
              .find(x=>x.dataset.v==='quiz');if(b)b.click();})()""")
            time.sleep(0.3)

        def take_round(nav):
            """点一个入口，抓走本轮 card id，然后退到首页。"""
            c.js(f"(()=>{{const b=document.querySelector('[data-act={nav}]');if(b)b.click()}})()")
            time.sleep(0.4)
            ids = c.js("(()=>typeof SESSION!=='undefined'&&SESSION"
                       "?SESSION.round.map(x=>x.id).join(','):'')()") or ""
            c.js("(()=>{const b=document.querySelector('.cover [data-act=exit]');if(b)b.click()})()")
            time.sleep(0.25)
            c.js("(()=>{const b=document.querySelector('[data-act=doexit]');if(b)b.click()})()")
            time.sleep(0.35)
            return [x for x in ids.split(",") if x]

        enter_work()
        pool_n = int(c.js(f"workPool('{WORK_T}').length") or 0)
        pool_hint = c.js("(()=>{const p=[...document.querySelectorAll('.footnote')].pop();"
                         "return p?p.textContent.replace(/\\s+/g,' ').trim():''})()") or ""
        r1 = take_round("wstart"); enter_work()
        r2 = take_round("wstart"); enter_work()
        r_all = take_round("wall")

        overlap = len(set(r1) & set(r2))
        if pool_n <= 20:
            fails.append(f"篇内题池: 《{WORK_T}》题池只有 {pool_n} 道，应大于一轮的 20")
        if len(r1) != 20:
            fails.append(f"篇内题池: 随机一轮出了 {len(r1)} 题，应为 20")
        if overlap >= 20:
            fails.append(f"篇内题池: 连续两轮是同一批题（重合 {overlap}/20）—— 就是用户报的「固定 20 题」")
        if len(r_all) != pool_n:
            fails.append(f"篇内题池: 整篇一遍出了 {len(r_all)} 题，应为整池 {pool_n}")
        if "随机抽" not in pool_hint:
            fails.append(f"篇内题池: 篇详情没说明「从题池随机抽」，实际「{pool_hint[:40]}」")
        ok_pool = (pool_n > 20 and len(r1) == 20 and overlap < 20
                   and len(r_all) == pool_n and "随机抽" in pool_hint)
        print(f"{'ok  ' if ok_pool else 'FAIL'} "
              f"篇内题池   池 {pool_n} 道 → 两轮各 20 题（重合 {overlap}）→ 整篇一遍 {len(r_all)} 题",
              flush=True)

        # ── 本机篇目：＋ → 表单 → 校验 → 保存 → 出现在目录 → 刷题 → 删除 ──
        # 这是唯一一个「用户自己造内容」的入口，最容易出的错是：
        # 存了但目录不刷新、行数不对齐也放行、删了之后 WORKS 里留幽灵。
        c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
        time.sleep(0.45)

        # ── 入库篇目：给 Agent 一个篇名，原文/白话/英译落库后要真出现在目录里 ──
        # 这条链路（ingest_work.py → 重建 data.js → 发布）最容易断在半路：
        # 库里有、目录没有；目录有、点开是空；能读、但「开始刷本篇」没题。
        # 每加一批篇目就往 NEW_WORKS 里加一行（篇名, 句数, 首句片段），越攒越像回归测试。
        NEW_WORKS = [
            ("兰亭集序", 17, "永和九年"),
            ("归去来兮辞", 31, "田园将芜"),
            ("项脊轩志", 33, "旧南阁子"),
            ("逍遥游（节选）", 39, "北冥有鱼"),
            ("滕王阁序", 49, "豫章故郡"),
        ]
        got_new = []
        for name, want_sent, first in NEW_WORKS:
            c.js(f"""(()=>{{const rows=[...document.querySelectorAll('[data-act=openwork]')];
              const r=rows.find(x=>x.textContent.includes('{name}'));
              if(r){{r.scrollIntoView({{block:'center'}});r.click();}}}})()""")
            time.sleep(0.45)
            nw = c.js("""(()=>({sl:document.querySelectorAll('.sl').length,
              text:(document.querySelector('.worktext')||{}).textContent||'',
              start:!!document.querySelector('[data-act=wstart]')}))()""")
            c.js("(()=>{const b=document.querySelector('[data-act=wstart]');if(b)b.click()})()")
            time.sleep(0.5)
            nw_quiz = c.js("!!document.querySelector('[data-act=pick]')")
            # 退出刷题要两步：题屏的 exit → 确认弹层的 doexit，少一步会卡在题屏，
            # 后面的「目录 + 按钮」全都会量到空
            c.js("(()=>{const b=document.querySelector('.cover [data-act=exit]');if(b)b.click()})()")
            time.sleep(0.3)
            c.js("(()=>{const b=document.querySelector('[data-act=doexit]');if(b)b.click()})()")
            time.sleep(0.45)
            c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
            time.sleep(0.4)
            got_new.append((name, nw["sl"], nw_quiz))
            if nw["sl"] != want_sent:
                fails.append(f"入库篇目: 《{name}》篇详情有 {nw['sl']} 句，应为 {want_sent}")
            if first not in nw["text"]:
                fails.append(f"入库篇目: 《{name}》的整篇原文里找不到首句「{first}」")
            if not nw["start"]:
                fails.append(f"入库篇目: 《{name}》篇详情没有「开始刷本篇」")
            if not nw_quiz:
                fails.append(f"入库篇目: 《{name}》「开始刷本篇」没有出题")
        ok_new = all(sl == w and q for (n, sl, q), (_, w, _) in zip(got_new, NEW_WORKS))
        print(f"{'ok  ' if ok_new else 'FAIL'} "
              f"入库篇目   {len(got_new)} 篇："
              + " · ".join(f"{n}{sl}句{'✓' if q else '✗'}" for n, sl, q in got_new), flush=True)

        add_btn = c.js("""(()=>{const b=document.querySelector('[data-act=newcustom]');
          if(!b) return null; const r=b.getBoundingClientRect();
          return {w:Math.round(r.width), h:Math.round(r.height)};})()""")
        if add_btn:
            c.js("document.querySelector('[data-act=newcustom]').click()")
            time.sleep(0.35)
        form = c.js("""(()=>({ta:document.querySelectorAll('.f-tx').length,
          title:!!document.querySelector('#f-t'),
          save:!!document.querySelector('[data-act=savecustom]')}))()""")

        # 空篇名直接点保存：必须拦下，而且人还留在表单页（不能把人踢回目录丢内容）
        blank = c.js("""(()=>{
          const b=document.querySelector('[data-act=savecustom]');
          if(!b) return null;
          b.click();
          const e=document.querySelector('#f-err');
          return {msg:(e?e.textContent:'').trim(), still:!!document.querySelector('#f-c')};
        })()""")

        filled = c.js("""(()=>{
          const set=(id,v)=>{const el=document.getElementById(id); if(!el) return false;
            el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); return true;};
          set('f-t','测试篇·岳阳楼记');
          set('f-a','范仲淹');
          set('f-c','庆历四年春，滕子京谪守巴陵郡。\\n越明年，政通人和，百废具兴。\\n乃重修岳阳楼，增其旧制。');
          set('f-m','庆历四年的春天，滕子京被贬到巴陵郡做太守。\\n到了第二年，政事顺利，百姓和乐，各种荒废的事业都兴办起来了。\\n于是重新修建岳阳楼，扩大它原有的规模。');
          set('f-e','In the spring of the fourth year of Qingli, Teng Zijing was banished to Baling.\\nThe next year the government was smooth and the people were at peace.\\nSo he rebuilt the Yueyang Tower and enlarged its scale.');
          const c=document.querySelector('[data-n=c]'), m=document.querySelector('[data-n=m]');
          return {c:c?c.textContent:'', m:m?m.textContent:'',
                  bad:m?m.classList.contains('bad'):null};
        })()""")
        if shots:
            c.shot(os.path.join(OUT, "flow_custom_form.png"))

        c.js("(()=>{const b=document.querySelector('[data-act=savecustom]');if(b)b.click()})()")
        time.sleep(0.5)
        # 保存后直接落到这篇的详情页（不是目录），所以先量详情，再退回目录量列表
        detail = c.js("""(()=>{
          const rows=[...document.querySelectorAll('[data-act=openwork]')];
          return {sl: document.querySelectorAll('.sl').length,
                  text: !!document.querySelector('.worktext'),
                  onList: rows.length,
                  title: (document.querySelector('.title')||{}).textContent||''};
        })()""")
        c.js("(()=>{const b=document.querySelector('[data-act=backcatalog]');if(b)b.click()})()")
        time.sleep(0.45)
        saved = c.js("""(()=>{
          const rows=[...document.querySelectorAll('[data-act=openwork]')];
          const row=rows.find(r=>r.textContent.includes('测试篇'));
          return {rows:rows.length, has:!!row,
                  badge: row?!!row.querySelector('.wtag'):false};
        })()""")

        # 自加的篇目也应该能刷题：句级四选一，干扰项从题库里抽
        c.js("""(()=>{const rows=[...document.querySelectorAll('[data-act=openwork]')];
          const r=rows.find(x=>x.textContent.includes('测试篇'));if(r)r.click();})()""")
        time.sleep(0.4)
        c.js("(()=>{const b=document.querySelector('[data-act=wstart]');if(b)b.click()})()")
        time.sleep(0.55)
        cq = c.js("!!document.querySelector('[data-act=pick]')")
        nopt = 0
        if cq:
            c.js("document.querySelector('[data-act=pick]').click()")
            time.sleep(0.6)
            nopt = c.js("document.querySelectorAll('.opt').length")
            c.js("(()=>{const b=document.querySelector('.cover [data-act=exit]');if(b)b.click()})()")
            time.sleep(0.3)
            c.js("(()=>{const b=document.querySelector('[data-act=doexit]');if(b)b.click()})()")
            time.sleep(0.45)

        # 删除：⋯ → 删除这篇 → 再确认一次
        c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
        time.sleep(0.4)
        c.js("""(()=>{const rows=[...document.querySelectorAll('[data-act=openwork]')];
          const r=rows.find(x=>x.textContent.includes('测试篇'));if(r)r.click();})()""")
        time.sleep(0.4)
        c.js("(()=>{const b=document.querySelector('[data-act=workmenu]');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("(()=>{const b=document.querySelector('[data-act=delcustom]');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("(()=>{const b=document.querySelector('[data-act=docustomdel]');if(b)b.click()})()")
        time.sleep(0.45)
        left = c.js("document.querySelectorAll('[data-act=openwork]').length")

        if not add_btn:
            fails.append("本机篇目: 目录页没有 ＋ 按钮，用户无处可点")
        elif add_btn["w"] < 44 or add_btn["h"] < 44:
            fails.append(f"本机篇目: ＋ 热区只有 {add_btn['w']}×{add_btn['h']}，按不中")
        if not (form and form["ta"] == 3 and form["title"] and form["save"]):
            fails.append(f"本机篇目: 表单缺三栏输入或保存按钮 {form}")
        if not blank or not blank["msg"] or not blank["still"]:
            fails.append(f"本机篇目: 空篇名点保存没被拦下 / 人被踢出了表单 {blank}")
        if not filled or filled["c"].strip() != "3 句" or filled["bad"]:
            fails.append(f"本机篇目: 行数提示不对 {filled}")
        if not (saved and saved["has"] and saved["badge"]):
            fails.append(f"本机篇目: 保存后目录里没有带「本机」徽章的这篇 {saved}")
        if not (detail and detail["text"] and detail["sl"] == 3):
            fails.append(f"本机篇目: 保存后没落到详情页 / 句数不对 {detail}")
        if saved and saved["rows"] != n_expect + 1:
            fails.append(f"本机篇目: 保存后目录里有 {saved['rows']} 篇，应为 {n_expect + 1}")
        if not cq:
            fails.append("本机篇目: 自己加的篇目点了「开始刷本篇」没有题")
        elif nopt != 4:
            fails.append(f"本机篇目: 句级四选一的选项有 {nopt} 个，应为 4")
        if left != n_expect:
            dbg = c.js("""(()=>({sheets:document.querySelectorAll('.sheet').length,
              rows:document.querySelectorAll('[data-act=openwork]').length,
              text:(document.querySelector('.scroll')||{}).textContent?
                   document.querySelector('.scroll').textContent.slice(0,40):''}))()""")
            fails.append(f"本机篇目: 删除后目录里还剩 {left} 篇，应为 {n_expect}；现场 {dbg}")
        ok_custom = bool(add_btn and form and form["ta"] == 3 and blank and blank["msg"]
                         and saved and saved["has"] and cq and nopt == 4 and left == n_expect)
        print(f"{'ok  ' if ok_custom else 'FAIL'} "
              f"本机篇目   ＋ →表单（{form['ta'] if form else 0} 栏）→拦空篇名→"
              f"存 {detail['sl'] if detail else 0} 句→刷题 {nopt} 选项→删除后回到 {left} 篇", flush=True)

        # ── 弹层里的按钮 ─────────────────────────────────────────
        # 这里曾经有个静默的大坑：遮罩挂 data-act="closesheet"、面板挂
        # onclick="event.stopPropagation()"，面板把事件拦在冒泡路上，document 上的
        # 事件委托根本收不到 —— 改档、换主题、切发音、清除记录、单练这句全都点不动，
        # 而且不报任何错。所以专门钉两条。
        c.js("(()=>{const b=document.querySelector('.lv-btn');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("""(()=>{const b=document.querySelector('.sheet [data-act=setlv][data-v="1"]');
          if(b)b.click()})()""")
        time.sleep(0.4)
        lv_now = c.js("""(()=>{const b=document.querySelector('.lv-btn');
          return {txt:b?b.textContent.trim():'', sheet:document.querySelectorAll('.sheet').length};})()""")
        # 改回自动，别把这次测试的档位留在库里
        c.js("(()=>{const b=document.querySelector('.lv-btn');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("""(()=>{const b=document.querySelector('.sheet [data-act=setlv][data-v="0"]');
          if(b)b.click()})()""")
        time.sleep(0.35)

        c.js("(()=>{const b=document.querySelector('[data-act=tab][data-v=home]');if(b)b.click()})()")
        time.sleep(0.4)
        c.js("(()=>{const b=document.querySelector('[data-act=sheet]');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("""(()=>{const b=document.querySelector('.sheet [data-act=theme][data-v="dark"]');
          if(b)b.click()})()""")
        time.sleep(0.4)
        theme_now = c.js("document.documentElement.dataset.theme||''")
        c.js("(()=>{const b=document.querySelector('[data-act=sheet]');if(b)b.click()})()")
        time.sleep(0.3)
        c.js("""(()=>{const b=document.querySelector('.sheet [data-act=theme][data-v="auto"]');
          if(b)b.click()})()""")
        time.sleep(0.3)

        if not lv_now or "重点" not in lv_now["txt"] or lv_now["sheet"]:
            fails.append(f"弹层: 改档没生效（按钮还是「{lv_now['txt'] if lv_now else '-'}」）"
                         f" —— 多半是遮罩把点击拦住了")
        if theme_now != "dark":
            fails.append(f"弹层: 换深色没生效（data-theme={theme_now or '空'}）")
        print(f"{'ok  ' if (lv_now and '重点' in lv_now['txt'] and theme_now == 'dark') else 'FAIL'} "
              f"弹层       改档 → 「{lv_now['txt'] if lv_now else '-'}」 · 换主题 → "
              f"{theme_now or '未变'}", flush=True)

    finally:
        proc.terminate()
        time.sleep(0.4)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fails:
        for f in fails:
            print("×", f)
        return 1
    print(f"全部通过（{len(DEVICES)} 种屏宽 + 主流程）；截图在 web-demo/_shots/")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="检查线上地址；不给则起本地服务")
    args = ap.parse_args()
    srv = None
    if args.url:
        url = args.url
    else:
        srv, url = serve(WEB)
        print("本地预览:", url)
    try:
        return run(url)
    finally:
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
