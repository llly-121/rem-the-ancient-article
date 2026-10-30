# -*- coding: utf-8 -*-
"""拍某一篇的三张图：目录定位 / 篇详情 / 点句弹层。

    python scripts/shot_work.py 兰亭集序

新篇入库后想肉眼确认「真的进来了、断句对不对、白话英译有没有串行」时用。
只走浏览器渲染，不写任何数据。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_mobile import CDP, boot_edge, serve  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web-demo")
OUT = os.path.join(WEB, "_shots")


def main():
    title = sys.argv[1] if len(sys.argv) > 1 else "兰亭集序"
    slug = {"兰亭集序": "lanting"}.get(title, "work")
    srv, url = serve(WEB)
    proc, tmp, ws = boot_edge(9022)
    try:
        c = CDP(ws)
        c.send("Page.enable")
        c.send("Runtime.enable")
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844,
               deviceScaleFactor=2, mobile=True)
        c.send("Page.navigate", url=url)
        time.sleep(2.2)

        # 目录（滚到《兰亭集序》那一行，否则它在「普通」分组末尾，图里看不到）
        c.js("(()=>{const b=document.querySelector('[data-act=tocatalog]');if(b)b.click()})()")
        time.sleep(0.6)
        c.js("""(()=>{const rows=[...document.querySelectorAll('[data-act=openwork]')];
          const r=rows.find(x=>x.textContent.includes('''+title+'''));
          if(r)r.scrollIntoView({block:'center'});})()""")
        time.sleep(0.5)
        c.shot(os.path.join(OUT, f"{slug}_catalog.png"))

        # 篇详情
        c.js("""(()=>{const rows=[...document.querySelectorAll('[data-act=openwork]')];
          const r=rows.find(x=>x.textContent.includes('兰亭集序'));
          if(r){r.scrollIntoView({block:'center'});r.click();}})()""")
        time.sleep(0.7)
        c.shot(os.path.join(OUT, f"{slug}_detail.png"))

        # 点第一句 → 白话/英译弹层
        c.js("(()=>{const s=document.querySelector('.sl');if(s)s.click()})()")
        time.sleep(0.7)
        c.shot(os.path.join(OUT, f"{slug}_sentence.png"))
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
