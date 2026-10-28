#!/usr/bin/env python3
"""ui_spec 中「代码里不存在某类东西」的静态验收（U13 + 深色模式）

README 验收清单原本把这几项列成「需人眼判断」，但它们本质上是可静态判定的：

  U13-a  插图全部代码绘制     → 除 App 图标外，工程里不该存在位图或 Image("图片名")
  图标   主屏图标可用         → 1024×1024、无 alpha、已挂到 target（否则桌面显示白板）
  U13-b  完全离线            → 源码里不该出现任何网络 API 或 URL 字面量
  深色模式  无硬编码色残留      → 除 Theme.swift 外，视图层不该直接写死颜色
  深色模式  token 必须成对     → Theme 里每个颜色令牌都要同时给出浅色/深色两个值

用法：
    python scripts/check_static_acceptance.py
退出码 0 = 全部通过，1 = 有问题（CI 据此判定失败）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "ios" / "GuwenApp"
THEME = APP / "Theme.swift"

# 视图层允许出现的非令牌颜色：clear 表示透明（测试探针用），不参与配色
ALLOWED_COLORS = {"clear"}

HARDCODED_COLOR_PATTERNS = [
    # Color.red / .foregroundStyle(.white) / .fill(.black) 这类系统色直写
    (re.compile(r"\bColor\.(black|white|red|orange|yellow|green|blue|purple|pink|gray|brown|cyan|mint|indigo|teal)\b"),
     "直接使用系统颜色 Color.xxx"),
    (re.compile(r"\bColor\(\s*red\s*:"), "用 Color(red:green:blue:) 写死 RGB"),
    (re.compile(r"\bUIColor\.(?!\{)(?!init)(\w+)"), "直接使用 UIColor.xxx"),
    # .foregroundStyle(.red) 这类简写
    (re.compile(r"\.(foregroundStyle|background|fill|stroke|tint|foregroundColor)\(\s*\.(black|white|red|orange|yellow|green|blue|purple|pink|gray)\b"),
     "样式修饰符里直接写系统色"),
]

NETWORK_PATTERNS = [
    (re.compile(r"\bURLSession\b"), "URLSession"),
    (re.compile(r"\bURLRequest\b"), "URLRequest"),
    (re.compile(r"\bNSURLConnection\b"), "NSURLConnection"),
    (re.compile(r"\bimport\s+Network\b"), "import Network"),
    (re.compile(r"\bimport\s+Alamofire\b"), "import Alamofire"),
    (re.compile(r"https?://"), "URL 字面量"),
    (re.compile(r"\bWKWebView\b"), "WKWebView"),
]

BITMAP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".pdf", ".svg"}
BITMAP_IMAGE_PATTERN = re.compile(r'Image\(\s*"([^"]+)"')

# App 图标是唯一的合法位图：插图必须代码绘制，但主屏图标没法用代码画。
# 白名单精确到文件，避免「顺手加了一张 Assets」被默认放行。
APPICON_DIR = APP / "Assets.xcassets" / "AppIcon.appiconset"
APPICON_FILES = {"icon-1024.png"}
PBXPROJ = ROOT / "ios" / "GuwenApp.xcodeproj" / "project.pbxproj"

# Theme 颜色令牌：static let name = token("#light", "#dark")
TOKEN_PATTERN = re.compile(
    r'static\s+let\s+(\w+)\s*=\s*token\(\s*"(#[0-9A-Fa-f]{6})"\s*,\s*"(#[0-9A-Fa-f]{6})"\s*\)'
)
TOKEN_CALL_PATTERN = re.compile(r"static\s+let\s+(\w+)\s*=\s*token\(")

failures: list[str] = []
notes: list[str] = []


def swift_files() -> list[Path]:
    return sorted(APP.rglob("*.swift"))


def check_bitmaps() -> None:
    """U13-a：插图必须全部代码绘制；App 图标是唯一放行的位图"""
    assets = [a for a in APP.rglob("*.xcassets") if a != APP / "Assets.xcassets"]
    if assets:
        failures.append(
            f"[U13-a] 存在额外的 Assets 目录（可能夹带插图位图）：{[str(a.relative_to(ROOT)) for a in assets]}"
        )

    bitmaps = [p for p in APP.rglob("*") if p.is_file() and p.suffix.lower() in BITMAP_SUFFIXES]
    allowed = {APPICON_DIR / name for name in APPICON_FILES}
    strays = [p for p in bitmaps if p not in allowed]
    if strays:
        failures.append(
            f"[U13-a] 发现 {len(strays)} 个位图/矢量文件（仅允许 App 图标）："
            + ", ".join(str(p.relative_to(ROOT)) for p in strays[:5])
        )

    for path in swift_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = BITMAP_IMAGE_PATTERN.search(line)
            if m:
                failures.append(
                    f"[U13-a] {path.relative_to(ROOT)}:{lineno} 用 Image(\"{m.group(1)}\") 引用图片资源"
                    "（插图应全部用 SwiftUI Shape 绘制）"
                )

    notes.append(
        f"U13-a 插图：无 Image(\"名称\") 引用，位图仅 App 图标 {len(allowed & set(bitmaps))}/{len(APPICON_FILES)}"
    )


def check_appicon() -> None:
    """App 图标：必须存在、1024×1024、无 alpha、且真的挂到了 target 上

    这条不是洁癖。第一次打真机包时工程里根本没有 Assets.xcassets，
    装到手机上会显示成一块白板图标——而编译、签名、安装全都不会报错。
    """
    png = APPICON_DIR / "icon-1024.png"
    if not png.exists():
        # 用 display 而非硬 relative_to：路径若在仓库外（自检场景）会抛 ValueError
        shown = png.relative_to(ROOT) if ROOT in png.parents else png
        failures.append(f"[图标] 缺少 {shown}（跑 python scripts/make_icons.py 生成）")
        return

    raw = png.read_bytes()
    if len(raw) < 26 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        failures.append("[图标] icon-1024.png 不是合法 PNG")
        return

    # IHDR 紧跟 8 字节签名 + 4 字节长度 + 4 字节类型，宽高在偏移 16..24，色深 24，颜色类型 25
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    color_type = raw[25]

    if (width, height) != (1024, 1024):
        failures.append(f"[图标] 尺寸应为 1024×1024，实际 {width}×{height}")
    # 4 = 灰度+alpha，6 = RGBA；iOS 图标带 alpha 会被判为无效图标
    if color_type in (4, 6):
        failures.append(f"[图标] 含 alpha 通道（PNG color type {color_type}），iOS 会拒绝该图标")

    contents = APPICON_DIR / "Contents.json"
    if not contents.exists() or "icon-1024.png" not in contents.read_text(encoding="utf-8"):
        failures.append("[图标] AppIcon.appiconset/Contents.json 未引用 icon-1024.png")

    if PBXPROJ.exists():
        if "ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;" not in PBXPROJ.read_text(encoding="utf-8"):
            failures.append(
                "[图标] project.pbxproj 未设置 ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon，"
                "资源目录不会被编译，桌面仍显示白板图标"
            )

    notes.append(f"图标：1024×1024 / PNG color type {color_type}（无 alpha）/ 已挂到 target")



def check_network() -> None:
    """U13-b：完全离线，不得出现网络 API"""
    hits = 0
    for path in swift_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, label in NETWORK_PATTERNS:
                if pattern.search(line):
                    failures.append(
                        f"[U13-b] {path.relative_to(ROOT)}:{lineno} 出现 {label}，破坏「完全离线」"
                    )
                    hits += 1
    if hits == 0:
        notes.append("U13-b 离线：源码中无 URLSession / 网络库 / URL 字面量")


def check_hardcoded_colors() -> None:
    """深色模式：视图层只允许引用 Theme 令牌"""
    checked = 0
    for path in swift_files():
        if path == THEME:
            continue  # 令牌定义处本来就该写 hex
        checked += 1
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("//"):
                continue
            for pattern, label in HARDCODED_COLOR_PATTERNS:
                m = pattern.search(line)
                if not m:
                    continue
                if set(m.groups()) & ALLOWED_COLORS:
                    continue
                failures.append(
                    f"[深色] {path.relative_to(ROOT)}:{lineno} {label}：{line.strip()[:70]}"
                )
    notes.append(f"深色模式：已扫描 {checked} 个视图文件，颜色应全部来自 Theme 令牌")


def check_token_pairs() -> None:
    """深色模式：每个颜色令牌都必须成对给出浅色/深色"""
    if not THEME.exists():
        failures.append("[深色] 找不到 Theme.swift")
        return
    text = THEME.read_text(encoding="utf-8")
    paired = {m.group(1) for m in TOKEN_PATTERN.finditer(text)}
    all_tokens = {m.group(1) for m in TOKEN_CALL_PATTERN.finditer(text)}
    missing = sorted(all_tokens - paired)
    if missing:
        failures.append(
            "[深色] 以下令牌没有同时给出浅色与深色两个值："
            + ", ".join(missing)
            + "（暗色模式下会退化成同一颜色）"
        )
    notes.append(f"深色模式：{len(paired)} 个颜色令牌均为「浅色/深色」双值")


def main() -> int:
    check_bitmaps()
    check_appicon()
    check_network()
    check_hardcoded_colors()
    check_token_pairs()

    print("=" * 62)
    print("静态验收（U13 无位图 / 断网 · 深色模式无硬编码色）")
    print("=" * 62)
    for note in notes:
        print(f"  [说明] {note}")

    if failures:
        print()
        for item in failures:
            print(f"  [失败] {item}")
        print(f"\n共 {len(failures)} 项不通过")
        return 1

    print("\n全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
