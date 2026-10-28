"""生成 PWA / 主屏图标

图形语汇直接取自 App 本身：一个「文」字 + 下方一道划线的横杠。
那道杠不是装饰——「选出划线词的释义」是这个 App 的核心交互。

输出到 web-demo/icons/：
  icon-180.png  iOS「添加到主屏幕」用的 apple-touch-icon
  icon-192.png  Android / manifest
  icon-512.png  manifest 与安装弹窗
  icon-maskable-512.png  安卓自适应图标（留安全边距，系统会裁）

用法：python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 与 Theme.swift 同源的取色
BG = (42, 33, 26)        # #2A211A 深色主题底色
INK = (245, 230, 211)    # #F5E6D3 纸色
ACCENT = (201, 123, 74)  # #C97B4A 主色（划线）

CHAR = "文"
# 楷体比宋体更贴近文言气质；找不到就退回宋体
FONT_CANDIDATES = [
    ("C:/Windows/Fonts/simkai.ttf", 0),
    ("C:/Windows/Fonts/simsun.ttc", 0),
]

OUT = Path(__file__).resolve().parent.parent / "web-demo" / "icons"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path, index in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=index)
    raise SystemExit("找不到中文字体，无法生成图标")


def render(size: int, scale_content: float = 1.0) -> Image.Image:
    """画一张正方形图标。

    scale_content 用来给 maskable 版本留安全边距：
    安卓自适应图标会按圆形/方形裁切，内容必须收在中央 80% 内。
    """
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)

    font_size = int(size * 0.62 * scale_content)
    font = load_font(font_size)

    # 用 bbox 精确取字形实际占地：直接按 size/2 对齐会因为字形上下留白而偏
    box = draw.textbbox((0, 0), CHAR, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    # 「字 + 间距 + 横线」三者当作一个整体来居中，
    # 只让字居中会让横线探到底边，整张图看着偏上
    gap = size * 0.09
    bar_h = max(3, int(size * 0.028))
    group_h = th + gap + bar_h
    top = (size - group_h) / 2

    x = (size - tw) / 2 - box[0]
    y = top - box[1]
    draw.text((x, y), CHAR, font=font, fill=INK)

    # 划线：宽度是字宽的 78%
    bar_w = int(tw * 0.78)
    bar_x = (size - bar_w) / 2
    bar_y = top + th + gap
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=bar_h / 2,
        fill=ACCENT,
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for size in (180, 192, 512):
        render(size).save(OUT / f"icon-{size}.png", optimize=True)
        print(f"icon-{size}.png")

    # maskable：内容缩到 78%，四周留出裁切余量
    render(512, scale_content=0.78).save(OUT / "icon-maskable-512.png", optimize=True)
    print("icon-maskable-512.png")

    # iOS 主屏图标不允许透明通道，统一转 RGB 已经保证；再核一遍尺寸
    for p in sorted(OUT.glob("*.png")):
        with Image.open(p) as im:
            print(f"  {p.name}: {im.size} {im.mode} {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
