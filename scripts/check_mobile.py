# -*- coding: utf-8 -*-
"""网页版在手机上的验收：布局、热区、输入框、首屏加载层。

为什么需要它：iOS 版有 XCUITest 兜着，网页版没有。而网页版踩的坑恰恰是
「Windows 浏览器里看不出来、只有 iPhone 上才现形」的那一类：

  · iPhone 15 Pro Max 屏宽 430，而布局按 390 设计 → 四周一圈黑框
  · 底部 Tab 不加 safe-area → 被 Home Indicator 压住，点不到
  · textarea 的 font:16px/1.5 inherit 是非法 shorthand → 掉回 13.33px，
    iOS 聚焦时强制放大页面（user-scalable=no 拦不住）
  · 热区小于 44pt → 手指按不中
  · data.js 1.25 MB，弱网下长时间空白 → 用户以为打不开

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
  const ta = document.createElement('textarea');
  document.getElementById('app').appendChild(ta);
  const taCs = getComputedStyle(ta);
  const taFont = parseFloat(taCs.fontSize);
  ta.remove();
  const boot = document.getElementById('boot');
  return {
    vw: window.innerWidth, vh: window.innerHeight,
    phoneFills: Math.abs(pr.width - window.innerWidth) < 1 && Math.abs(pr.height - window.innerHeight) < 1,
    sideMargin: Math.round(pr.left),
    overflowEls: overflow,
    tapMin: taps.length ? Math.round(Math.min(...taps.map(b => b.height))) : null,
    textareaFont: taFont,
    textareaFamily: taCs.fontFamily.slice(0, 20),
    bootHidden: boot ? getComputedStyle(boot).display === 'none' : true,
    cards: window.GUWEN && window.GUWEN.cards ? window.GUWEN.cards.length : null,
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
            if m["textareaFont"] < 16:
                tag_fails.append(f"textarea 字号 {m['textareaFont']}px < 16px，"
                                 "iOS 聚焦时会强制放大整页")
            if not m["bootHidden"]:
                tag_fails.append("首屏加载层没消失，会一直盖着")
            if m["cards"] != 1346:
                tag_fails.append(f"卡片数 {m['cards']}，应为 1346")

            for f in tag_fails:
                fails.append(f"{tag}: {f}")
            print(f"{'FAIL' if tag_fails else 'ok  '} {tag:10s} "
                  f"phone={w}x{h} tapMin={m['tapMin']} textarea={m['textareaFont']}px "
                  f"cards={m['cards']}", flush=True)

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
        if shots:
            c.shot(os.path.join(OUT, "flow_answer_i14.png"))
        print(f"{'FAIL' if (not picked or not nxt) else 'ok  '} 流程       开一轮→选一项→答案页", flush=True)
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
