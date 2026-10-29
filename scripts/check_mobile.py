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
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))


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
  };
})()
"""


def run(url, shots=True):
    os.makedirs(OUT, exist_ok=True)
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
            if m["cards"] != 1346:
                tag_fails.append(f"卡片数 {m['cards']}，应为 1346")
            if m["works"] != 25 or m["allSent"] != 654:
                tag_fails.append(f"篇章 {m['works']} 篇 / {m['allSent']} 句，应为 25 篇 / 654 句")

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
        picked = c.js("(()=>{const b=document.querySelector('[data-act=pick]');"
                      "if(b){b.click();return true}return false})()")
        time.sleep(0.9)  # 答案页有 0.22s slide-in，太早量会量到 translateX 中间态
        tf = c.js("(()=>{const cv=document.querySelector('.cover');"
                  "return cv?getComputedStyle(cv).transform:null})()")
        nxt = c.js("!!document.querySelector('[data-act=next]')")
        if not picked:
            fails.append("流程: 点了「开始一轮」但没出现选项")
        if not nxt:
            fails.append("流程: 选完选项后没有「下一题」，答案页没出来")
        if tf not in (None, "none", "matrix(1, 0, 0, 1, 0, 0)"):
            fails.append(f"流程: 答案页停留在动画中间态 transform={tf}")
        if not c.js("!!document.querySelector('.zh')"):
            fails.append("答案页: 没有白话块（.zh）")
        if shots:
            c.shot(os.path.join(OUT, "flow_answer_i14.png"))
        print(f"{'FAIL' if (not picked or not nxt) else 'ok  '} 流程       开一轮→选一项→答案页", flush=True)

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
        #   1. 未揭晓的选中态 .opt.sel 不能等于「正确色」（点一下就提前变绿的那个坑）
        #   2. 揭晓后的正确项要等于 --ok
        #   3. 揭晓后的错选项要等于 --bad
        # 只比「两者不同」是不够的：把正确项改回原来的橙色，它们同样不同。
        JS_TOKENS = """(()=>{
          const e=document.createElement('span');
          document.body.appendChild(e);
          e.style.color='var(--ok)';  const ok=getComputedStyle(e).color;
          e.style.color='var(--bad)'; const bad=getComputedStyle(e).color;
          e.remove();
          const sel=document.querySelector('.opt.sel');
          const cor=document.querySelector('.opt.correct');
          const bad2=document.querySelector('.opt.wrong');
          return {ok, bad,
                  sel: sel ? getComputedStyle(sel).borderTopColor : null,
                  correct: cor ? getComputedStyle(cor).borderTopColor : null,
                  wrong: bad2 ? getComputedStyle(bad2).borderTopColor : null};
        })()"""

        zh_ok, tok, sel_tok = False, None, None
        for _ in range(4):
            if not c.js("!!document.querySelector('[data-act=pick]')"):
                break
            c.js("document.querySelector('[data-act=pick]').click()")
            time.sleep(0.12)          # 选中态只在 400ms 内存在，要抢在这之前量
            sel_tok = c.js(JS_TOKENS)
            time.sleep(0.5)
            zh_ok = bool(c.js("!!document.querySelector('.zh')"))
            tok = c.js(JS_TOKENS)
            if tok and tok["wrong"]:
                break
            c.js("document.querySelector('[data-act=next]').click()")
            time.sleep(0.3)

        if n_rows != 25:
            fails.append(f"篇章: 目录里有 {n_rows} 篇，应为 25")
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
        if sel_tok and sel_tok["sel"] and sel_tok["sel"] == sel_tok["ok"]:
            fails.append("配色: 选中尚未揭晓时就已经是绿色，用户看不出「还没公布答案」")
        if shots:
            c.shot(os.path.join(OUT, "flow_work_answer.png"))
        ok_all = (n_rows == 25 and det["text"] and w_quiz and zh_ok and tok
                  and tok["correct"] == tok["ok"] and tok["wrong"] == tok["bad"])
        print(f"{'FAIL' if not ok_all else 'ok  '} "
              f"篇章       目录 25 篇→篇详情 {det['sl']} 句→刷题", flush=True)
        print(f"{'ok  ' if ok_all else 'FAIL'} "
              f"配色       正确 {tok['correct'] if tok else '-'} / 错误 {tok['wrong'] if tok else '-'} "
              f"/ 选中 {sel_tok['sel'] if sel_tok else '-'}", flush=True)
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
