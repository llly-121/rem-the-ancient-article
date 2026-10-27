import SwiftUI
import UIKit

/// 设计令牌（ui_spec §1）。深浅两套值，跟随系统外观，代码中只引用 Token 名。
enum Theme {
    private static func token(_ lightHex: String, _ darkHex: String) -> Color {
        Color(uiColor: UIColor { trait in
            trait.userInterfaceStyle == .dark
                ? UIColor(hexString: darkHex)
                : UIColor(hexString: lightHex)
        })
    }

    /// 主背景（宣纸色 / 墨色宣纸底）
    static let bg = token("#F5E6D3", "#2A211A")
    /// 卡片/输入框底色
    static let surface = token("#FFFBF4", "#3A2E24")
    /// 强调色：只作装饰（边框/底色/按钮/对勾/下划线），禁止用于正文文字
    static let accent = token("#C97B4A", "#D99462")
    /// 正文、古文
    static let textPrimary = token("#3E2C1E", "#F0E4D4")
    /// 出处、时间、辅助说明
    static let textSecondary = token("#7A6552", "#B5A08C")
    /// 错误反馈（柔和灰紫），禁用高对比红
    static let errorTone = token("#8B7A8B", "#A892A8")
    /// 分割线、未选中描边
    static let divider = token("#E3D3BF", "#4A3B2E")

    /// 高亮底色（两套模式通用）
    static let highlight = accent.opacity(0.25)

    // 字体（ui_spec §1.2）
    static let classicalFont = Font.custom("Songti SC", size: 28, relativeTo: .title)
    static let recallClassicalFont = Font.custom("Songti SC", size: 32, relativeTo: .largeTitle)
    static let serifEnglishFont = Font.system(size: 17, design: .serif)
    /// 正文 16pt（callout 字号 = 16pt，随 Dynamic Type 缩放）
    static let bodyCN = Font.system(.callout, design: .default)
    /// 辅助说明 13pt（footnote 字号 = 13pt，随 Dynamic Type 缩放）
    static let caption = Font.system(.footnote, design: .default)
}

extension UIColor {
    convenience init(hexString: String) {
        var h = hexString.trimmingCharacters(in: .whitespaces)
        if h.hasPrefix("#") { h.removeFirst() }
        var value: UInt64 = 0
        Scanner(string: h).scanHexInt64(&value)
        let r = CGFloat((value >> 16) & 0xFF) / 255.0
        let g = CGFloat((value >> 8) & 0xFF) / 255.0
        let b = CGFloat(value & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b, alpha: 1)
    }
}

/// 尺寸令牌（ui_spec §1.3）
enum Metrics {
    static let cardCornerRadius: CGFloat = 16
    static let optionSpacing: CGFloat = 12
    static let pagePadding: CGFloat = 20
    static let strokeWidthNormal: CGFloat = 1
    static let strokeWidthEmphasis: CGFloat = 1.5
    static let selectToAnswerDelay: TimeInterval = 0.4
}
