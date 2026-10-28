# -*- coding: utf-8 -*-
"""生成给手机扫码用的二维码，以及一张「三步装到主屏」说明图。

为什么要二维码：链接形如
    https://guwen-flashcards.app.workbuddy.host/?sharecode=5BOBJUPCXS
66 个字符，手输必错；微信里转发长链也容易被折叠。扫一下是最省事的方式。
"""
import os
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from PIL import Image, ImageDraw, ImageFont

URL = "https://guwen-flashcards.app.workbuddy.host/?sharecode=5BOBJUPCXS"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "share"))
os.makedirs(OUT, exist_ok=True)

PAPER = (245, 230, 211)
INK = (62, 44, 30)
SUB = (122, 101, 82)
ACCENT = (201, 123, 74)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Deng.ttf",
]
SONG = [r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc"]


def font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_qr():
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=12, border=3)
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color="white").convert("RGB")
    img.save(os.path.join(OUT, "qrcode.png"))
    print("qrcode.png", img.size, "modules:", qr.modules_count)
    return img


def make_card(qr_img):
    """一张能直接微信发出去的卡片：标题 + 二维码 + 三步。"""
    W, H = 900, 900
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    f_title = font(SONG, 58)
    f_sub = font(FONT_CANDIDATES, 28)
    f_step = font(FONT_CANDIDATES, 30)
    f_tiny = font(FONT_CANDIDATES, 24)

    # 标题
    t = "古文英译刷词"
    tw = d.textlength(t, font=f_title)
    d.text(((W - tw) / 2, 70), t, font=f_title, fill=INK)
    s = "iPhone 扫码 · 30 秒装到主屏 · 不用下载、不过期"
    sw = d.textlength(s, font=f_sub)
    d.text(((W - sw) / 2, 152), s, font=f_sub, fill=SUB)

    # 二维码（白底 + 细边框）
    q = qr_img.resize((440, 440), Image.NEAREST)
    box_x, box_y = (W - 440) // 2, 230
    d.rectangle([box_x - 22, box_y - 22, box_x + 440 + 22, box_y + 440 + 22],
                fill="white", outline=ACCENT, width=3)
    img.paste(q, (box_x, box_y))

    # 三步
    steps = [
        ("1", "用 iPhone 相机扫上面这个码"),
        ("2", "点底部「分享」→「添加到主屏幕」"),
        ("3", "桌面多一个「古文刷词」，点开即用"),
    ]
    y = 740
    for n, text in steps:
        d.ellipse([80, y + 4, 118, y + 42], fill=ACCENT)
        nw = d.textlength(n, font=f_step)
        d.text((99 - nw / 2, y + 8), n, font=f_step, fill=(255, 255, 255))
        d.text((140, y + 8), text, font=f_step, fill=INK)
        y += 70

    # 脚注
    note = [
        "第一次打开要加载约 10 秒，之后断网也能用",
        "做题记录存在手机本地，不需要注册登录",
    ]
    y += 16
    for line in note:
        d.text((80, y), "· " + line, font=f_tiny, fill=SUB)
        y += 40

    p = os.path.join(OUT, "share_card.png")
    img.save(p)
    print("card ->", p, img.size)


if __name__ == "__main__":
    make_card(make_qr())
