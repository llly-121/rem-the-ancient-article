# -*- coding: utf-8 -*-
"""拍某一篇的三张图：目录定位 / 篇详情 / 点句弹层。

    python scripts/shot_work.py 滕王阁序

新篇入库后想肉眼确认「真的进来了、断句对不对、白话英译有没有串行」时用。
只走浏览器渲染，不写任何数据。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_mobile import CDP, boot_edge, free_port, serve  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web-demo")
OUT = os.path.join(WEB, "_shots")

# 用 %s 而不是三引号拼接：篇名里带全角括号时，拼接少一个引号就会变成
# `includes('')`——它恒为 true，于是"找到了"第一行，拍出来是错的篇目，
# 而且不报错。这种错必须靠 % 这种一眼能看出占位符的写法躲开。
JS_SCROLL = """(()=>{const sc=document.querySelector('.scroll');
  const r=[...document.querySelectorAll('[data-act=openwork]')]
    .find(x=>x.textContent.includes('%s'));
  if(!sc||!r) return 'missing';
  const d=r.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop;
  sc.scrollTop = Math.max(0, d - 120);
  return Math.round(sc.scrollTop);})()"""

JS_OPEN = """(()=>{const r=[...document.querySelectorAll('[data-act=openwork]')]
    .find(x=>x.textContent.includes('%s'));
  if(!r) return 'missing';
  r.click(); return 'clicked';})()"""


def main():
    title = sys.argv[1] if len(sys.argv) > 1 else "兰亭集序"
    srv, url = serve(WEB)
    # 端口不能写死：上次没杀干净的 Edge 还占着端口时，boot_edge 会连到那个旧实例上，
    # 拍出来的还是上一次的页面，看起来像「截图没生效」
    proc, tmp, ws = boot_edge(free_port(9100))
    try:
        c = CDP(ws)
        c.send("Page.enable")
        c.send("Runtime.enable")
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844,
               deviceScaleFactor=2, mobile=True)
        c.send("Page.navigate", url=url)
        time.sleep(2.5)

        # 目录：先滚到这一篇再拍（长库末尾的篇目，不滚就截不到）
        c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
        time.sleep(0.7)
        n_rows = c.js("document.querySelectorAll('[data-act=openwork]').length")
        print(f"目录 {n_rows} 篇", flush=True)
        print(f"滚动到 {title}: {c.js(JS_SCROLL % title)}", flush=True)
        time.sleep(0.5)
        c.shot(os.path.join(OUT, f"{title}_catalog.png"))

        # 篇详情
        print(f"点开: {c.js(JS_OPEN % title)}", flush=True)
        time.sleep(0.8)
        cur = c.js("(()=>({t:(document.querySelector('.title')||{}).textContent||'',"
                   "sl:document.querySelectorAll('.sl').length}))()")
        print(f"当前页: {cur}", flush=True)
        c.shot(os.path.join(OUT, f"{title}_detail.png"))

        # 点第一句 → 白话/英译弹层
        c.js("(()=>{const s=document.querySelector('.sl');if(s)s.click()})()")
        time.sleep(0.7)
        c.shot(os.path.join(OUT, f"{title}_sentence.png"))
        print("shots ok")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    main()
