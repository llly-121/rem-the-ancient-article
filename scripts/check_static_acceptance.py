#!/usr/bin/env python3
"""ui_spec 中「代码里不存在某类东西」的静态验收（U13 + 深色模式）

README 验收清单原本把这几项列成「需人眼判断」，但它们本质上是可静态判定的：

  U13-a  插图全部代码绘制     → 工程里不该存在任何位图资源或 Image("图片名")
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
    """U13-a：不得存在位图资源或按图片名取图的写法"""
    assets = list(APP.rglob("*.xcassets"))
    if assets:
        failures.append(f"[U13-a] 存在 Assets 目录（可能含位图）：{[str(a.relative_to(ROOT)) for a in assets]}")

    bitmaps = [p for p in APP.rglob("*") if p.is_file() and p.suffix.lower() in BITMAP_SUFFIXES]
    if bitmaps:
        failures.append(
            f"[U13-a] 发现 {len(bitmaps)} 个位图/矢量文件："
            + ", ".join(str(p.relative_to(ROOT)) for p in bitmaps[:5])
        )

    for path in swift_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = BITMAP_IMAGE_PATTERN.search(line)
            if m:
                failures.append(
                    f"[U13-a] {path.relative_to(ROOT)}:{lineno} 用 Image(\"{m.group(1)}\") 引用图片资源"
                    "（插图应全部用 SwiftUI Shape 绘制）"
                )

    notes.append("U13-a 插图：工程内无 Assets、无位图文件、无 Image(\"名称\") 引用")


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
