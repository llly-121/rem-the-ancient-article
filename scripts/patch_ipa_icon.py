"""给已打好的 .ipa 就地补上 App 图标（应急手段）

为什么会有这个脚本：
    iOS 的 App 图标正常由 Xcode 编译 Assets.xcassets 得到（CI 现在已经是这样）。
    但在「工程里压根没图标、又暂时连不上 GitHub 重新打包」的情况下，
    可以让 iOS 改读包内的散装 PNG：Info.plist 里写 CFBundleIconFiles，
    系统就按 base name 去找 @2x / @3x 变体。这条老机制至今仍然有效。

用它的前提：
    .ipa 是**未签名**的。签名由 Sideloadly 在用户本机完成，
    所以改包内容不会破坏任何签名——签名本来就在改完之后才做。

不要养成习惯：
    CI 的产物才是唯一真源，这个脚本只在网络不可用时用一次。
    源码侧（Assets.xcassets + ASSETCATALOG_COMPILER_APPICON_NAME）已经修好，
    网络恢复后重新打包即可，不需要再跑这个脚本。

用法：
    python scripts/patch_ipa_icon.py            # 原地替换 dist/GuwenApp-unsigned.ipa
    python scripts/patch_ipa_icon.py --out x.ipa
"""
from __future__ import annotations

import plistlib
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_icons import render  # noqa: E402  复用同一套绘制逻辑，保证与网页版同图

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "GuwenApp-unsigned.ipa"
WORK = ROOT / ".ci" / "ipa_patch"
APP_DIR = "Payload/GuwenApp.app"

# iOS 主屏图标 60pt：1x/2x/3x 三个变体，系统按设备屏幕取用
ICON_VARIANTS = {
    "AppIcon60x60.png": 60,
    "AppIcon60x60@2x.png": 120,
    "AppIcon60x60@3x.png": 180,
}


def main() -> int:
    out = SRC
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])

    if not SRC.exists():
        print(f"找不到源包 {SRC}")
        return 1

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    src_zip = zipfile.ZipFile(SRC)
    src_zip.extractall(WORK)
    # 原包里每个条目的权限位要记住：可执行文件的 +x 丢了，装上就闪退
    attrs = {i.filename: i.external_attr for i in src_zip.infolist()}
    src_zip.close()

    app = WORK / APP_DIR

    # 1) 散装图标
    for name, size in ICON_VARIANTS.items():
        render(size).save(app / name, optimize=True)

    # 2) 让系统去读它们
    plist_path = app / "Info.plist"
    plist = plistlib.loads(plist_path.read_bytes())
    base = "AppIcon60x60"
    plist["CFBundleIconFiles"] = [base]                      # 老机制
    plist["CFBundleIcons"] = {                               # 新机制（同一份文件）
        "CFBundlePrimaryIcon": {"CFBundleIconFiles": [base]}
    }
    plist_path.unlink()   # 某些环境禁止原地覆盖，先删再写
    plist_path.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_BINARY))

    # 3) 重新打包，逐个条目还原权限位
    tmp_out = out.with_suffix(".tmp")
    with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(WORK.rglob("*")):
            if not path.is_file():
                continue
            arc = path.relative_to(WORK).as_posix()
            info = zipfile.ZipInfo(arc, date_time=(2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = attrs.get(arc, 0o100644 << 16)
            z.writestr(info, path.read_bytes())

    if out.exists():
        out.unlink()      # 某些环境禁止原地覆盖，先删旧包再落盘
    tmp_out.replace(out)
    print(f"已写出 {out}  {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
