import SwiftUI

// MARK: - 进度条：20 段方块分格（ui_spec P9 = b）

struct ProgressSegmentBar: View {
    let total: Int
    let completed: Int

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<total, id: \.self) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(index < completed ? Theme.accent : Theme.divider)
                    .frame(width: 12, height: 6)
            }
        }
        .accessibilityLabel("已完成 \(completed) / \(total) 题")
        // U1 验收锚点：XCUITest 读 label 即可断言「已填充段数 = 已答题数」
        .accessibilityIdentifier("progress_bar")
    }
}

// MARK: - 类型徽标（ui_spec §7：词=「文」方章，句=「句」圆章）

struct TypeBadge: View {
    let type: CardType

    var body: some View {
        Group {
            if type == .word {
                Text("文")
                    .font(.system(size: 11, weight: .medium))
                    .frame(width: 20, height: 20)
                    .background(Theme.accent.opacity(0.10))
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .overlay(RoundedRectangle(cornerRadius: 4).stroke(Theme.accent, lineWidth: 1))
            } else {
                Text("句")
                    .font(.system(size: 11, weight: .medium))
                    .frame(width: 20, height: 20)
                    .background(Theme.accent.opacity(0.10))
                    .clipShape(Circle())
                    .overlay(Circle().stroke(Theme.accent, lineWidth: 1))
            }
        }
        .foregroundStyle(Theme.textPrimary)
    }
}

// MARK: - 选择题选项卡（ui_spec §2.4）

struct OptionCard: View {
    let text: String
    let state: OptionState

    enum OptionState {
        case idle
        case selected            // 选择题页：仅 accent 边框，不提前揭示对错
        case correct             // 答案页：accent 边框 + 对勾
        case wrong               // 答案页：errorTone 边框 + 叉号
        case dimmed              // 答案页：其他无关项
    }

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            Text(text)
                .font(Theme.bodyCN)
                .foregroundStyle(Theme.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .multilineTextAlignment(.leading)
                .fixedSize(horizontal: false, vertical: true)
            marker
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius))
        .overlay(
            RoundedRectangle(cornerRadius: Metrics.cardCornerRadius)
                .stroke(borderColor, lineWidth: borderWidth)
        )
        .opacity(state == .dimmed ? 0.6 : 1)
    }

    private var borderColor: Color {
        switch state {
        case .idle, .dimmed: Theme.divider
        case .selected, .correct: Theme.accent
        case .wrong: Theme.errorTone
        }
    }

    private var borderWidth: CGFloat {
        switch state {
        case .idle, .dimmed: Metrics.strokeWidthNormal
        default: Metrics.strokeWidthEmphasis
        }
    }

    @ViewBuilder
    private var marker: some View {
        switch state {
        case .correct:
            Image(systemName: "checkmark").foregroundStyle(Theme.accent)
        case .wrong:
            Image(systemName: "xmark").foregroundStyle(Theme.errorTone)
        default:
            EmptyView()
        }
    }
}

// MARK: - 描边/填充按钮

struct OutlineButton: View {
    let title: String
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(Theme.bodyCN)
                .foregroundStyle(disabled ? Theme.textSecondary : Theme.textPrimary)
                .frame(maxWidth: .infinity, minHeight: 44)
                .background(Theme.surface)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.divider, lineWidth: 1))
        }
        .disabled(disabled)
    }
}

struct FilledButton: View {
    let title: String
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(Theme.bodyCN.weight(.medium))
                .foregroundStyle(Theme.bg)
                .frame(maxWidth: .infinity, minHeight: 44)
                .background(disabled ? Theme.divider : Theme.accent)
                .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .disabled(disabled)
    }
}

// MARK: - Toast

struct ToastOverlay: View {
    let message: String

    var body: some View {
        Text(message)
            .font(Theme.caption)
            .foregroundStyle(Theme.bg)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Theme.textSecondary.opacity(0.9))
            .clipShape(Capsule())
            .transition(.opacity)
    }
}

// MARK: - 自绘插图（ui_spec §7，纯 SwiftUI Shape，无位图）

/// 远山（空状态背景装饰）
struct MountainView: View {
    var body: some View {
        ZStack {
            MountainPath()
                .fill(Theme.textSecondary.opacity(0.15))
                .offset(y: 12)
            MountainPath()
                .fill(Theme.accent.opacity(0.12))
        }
    }
}

struct MountainPath: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: 0, y: rect.height))
        p.addLine(to: CGPoint(x: rect.width * 0.18, y: rect.height * 0.35))
        p.addLine(to: CGPoint(x: rect.width * 0.38, y: rect.height * 0.75))
        p.addLine(to: CGPoint(x: rect.width * 0.58, y: rect.height * 0.20))
        p.addLine(to: CGPoint(x: rect.width * 0.80, y: rect.height * 0.65))
        p.addLine(to: CGPoint(x: rect.width, y: rect.height * 0.40))
        p.addLine(to: CGPoint(x: rect.width, y: rect.height))
        p.closeSubpath()
        return p
    }
}

/// 竹（装饰）
struct BambooView: View {
    var body: some View {
        VStack(spacing: 3) {
            ForEach(0..<4, id: \.self) { _ in
                Capsule().fill(Theme.textSecondary.opacity(0.25))
                    .frame(width: 5, height: 22)
            }
        }
    }
}

/// 书卷
struct ScrollIllustration: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 6)
                .fill(Theme.accent.opacity(0.35))
                .frame(width: 120, height: 78)
            VStack(spacing: 10) {
                ForEach(0..<3, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 1)
                        .fill(Theme.divider)
                        .frame(width: 88 - CGFloat(i) * 14, height: 4)
                }
            }
            HStack {
                Capsule().fill(Theme.accent.opacity(0.55)).frame(width: 8, height: 86)
                Spacer()
                Capsule().fill(Theme.accent.opacity(0.55)).frame(width: 8, height: 86)
            }
        }
    }
}

/// 灯烛（错题本空状态主插图：烛 + 书卷 + 远山）
struct CandleBookIllustration: View {
    var body: some View {
        ZStack {
            MountainView()
            VStack(spacing: 18) {
                CandleView()
                ScrollIllustration()
            }
        }
        .frame(height: 220)
    }
}

struct CandleView: View {
    var body: some View {
        VStack(spacing: 2) {
            FlameShape()
                .fill(Theme.accent.opacity(0.6))
                .frame(width: 16, height: 22)
            Capsule()
                .fill(Theme.textSecondary.opacity(0.35))
                .frame(width: 22, height: 46)
        }
    }
}

struct FlameShape: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: rect.midX, y: rect.minY))
        p.addQuadCurve(
            to: CGPoint(x: rect.midX, y: rect.maxY),
            control: CGPoint(x: rect.maxX, y: rect.midY))
        p.addQuadCurve(
            to: CGPoint(x: rect.midX, y: rect.minY),
            control: CGPoint(x: rect.minX, y: rect.midY))
        return p
    }
}
