import SwiftUI

/// 页面二：答案展示页（ui_spec §3）
struct AnswerView: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    let session: RoundSession
    @Binding var path: [FlowStep]

    @State private var selectedOption: String?
    @State private var addedToMistakeBook = false
    @State private var showToast = false
    @State private var contextExpanded = false

    var body: some View {
        Group {
            if let card = session.currentCard {
                content(for: card)
            } else {
                EmptyView()
            }
        }
        .background(Theme.bg.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        .onAppear {
            // 每次进入答案页都按当前题重置本地状态（NavigationStack 复用同一 .answer 目的地时 @State 会残留）
            selectedOption = QuizResultBridge.shared.lastSelection
            addedToMistakeBook = store.state(for: session.currentCard?.id ?? "").inMistakeBook
            showToast = false
            contextExpanded = false
        }
        .overlay(alignment: .bottom) {
            if showToast {
                ToastOverlay(message: "已加入错题本")
                    .padding(.bottom, 96)
            }
        }
    }

    // MARK: - 主体

    private func content(for card: Card) -> some View {
        VStack(spacing: 0) {
            header(card: card)
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    classicalSection(card: card)
                    optionsSection(card: card)
                    englishSection(card: card)
                    infoCard(card: card)
                    sourceSection(card: card)
                }
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.bottom, 24)
            }
            actionBar(card: card)
        }
    }

    private func header(card: Card) -> some View {
        HStack {
            Text(session.mode == .retrain ? "错题再练" : "第 \(session.currentIndex + 1)/\(session.round.count) 题")
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
            Spacer()
        }
        .padding(.horizontal, Metrics.pagePadding)
        .padding(.top, 8)
    }

    // MARK: - 古文区（词级 term 加下划线；句级不加）

    @ViewBuilder
    private func classicalSection(card: Card) -> some View {
        if card.type == .word, let attributed = underlinedClassical(for: card) {
            Text(attributed)
                .font(Theme.classicalFont)
                .lineSpacing(14)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            Text(card.classical)
                .font(Theme.classicalFont)
                .lineSpacing(14)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    /// term 下划线：全部出现处（§3.5 规则 1/2，U5）；定位失败返回 nil（改在释义卡提示）
    private func underlinedClassical(for card: Card) -> AttributedString? {
        let ranges = TermLocator.ranges(of: card.term, in: card.classical)
        guard !ranges.isEmpty else { return nil }
        var attributed = AttributedString(card.classical)
        for r in ranges {
            // String.Index 范围 → AttributedString 范围（AttributedString 没有 range(from:) 方法）
            guard let ar = Range(r, in: attributed) else { continue }
            // 只设下划线样式：underlineColor 属于 UIKit 属性域，跨域赋值会报二义性错误
            attributed[ar].underlineStyle = Text.LineStyle.single
        }
        return attributed
    }

    private var termNotFound: Bool {
        guard let card = session.currentCard, card.type == .word else { return false }
        return TermLocator.ranges(of: card.term, in: card.classical).isEmpty
    }

    // MARK: - 选项结果展示（§3.4：对→accent+对勾；错→所选 errorTone+叉、正确项 accent 标出）

    @ViewBuilder
    private func optionsSection(card: Card) -> some View {
        if let quiz = library.quizzes[card.id] {
            VStack(spacing: Metrics.optionSpacing) {
                ForEach(session.options(for: card.id), id: \.self) { text in
                    OptionCard(text: text, state: resultState(text: text, quiz: quiz))
                }
            }
        }
    }

    private func resultState(text: String, quiz: QuizItem) -> OptionCard.OptionState {
        guard let selected = selectedOption else { return .dimmed }
        if text == quiz.correct { return .correct }
        if text == selected { return .wrong }
        return .dimmed
    }

    // MARK: - 英译区（词级片段高亮；句级整句/分句高亮）

    @ViewBuilder
    private func englishSection(card: Card) -> some View {
        switch card.type {
        case .word:
            if let attributed = highlightedEnglish(for: card) {
                Text(attributed)
                    .font(Theme.serifEnglishFont)
                    .lineSpacing(6)
                    .foregroundStyle(Theme.textPrimary)
            } else {
                Text(card.fullEnglish)
                    .font(Theme.serifEnglishFont)
                    .foregroundStyle(Theme.textPrimary)
            }
        case .sentence:
            let lines = TermLocator.splitLongEnglish(card.fullEnglish)
            if lines.count > 1 {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(lines, id: \.self) { line in
                            Text(line)
                                .font(Theme.serifEnglishFont)
                                .lineSpacing(6)
                                .foregroundStyle(Theme.textPrimary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(6)
                                .background(Theme.highlight)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                    }
                }
                .frame(maxHeight: 320)
            } else {
                Text(card.fullEnglish)
                    .font(Theme.serifEnglishFont)
                    .lineSpacing(6)
                    .foregroundStyle(Theme.textPrimary)
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Theme.highlight)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
    }

    /// term_english 片段首个匹配高亮（§3.5 规则 4）
    private func highlightedEnglish(for card: Card) -> AttributedString? {
        var attributed = AttributedString(card.fullEnglish)
        guard let ar = attributed.range(of: card.termEnglish) else { return nil }
        attributed[ar].backgroundColor = Theme.highlight
        return attributed
    }

    // MARK: - 释义卡 / 句型卡

    @ViewBuilder
    private func infoCard(card: Card) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            switch card.type {
            case .word:
                HStack(spacing: 8) {
                    TypeBadge(type: .word)
                    Text(card.term)
                        .font(Theme.bodyCN.weight(.medium))
                        .foregroundStyle(Theme.textPrimary)
                }
                if termNotFound {
                    Text("原句写作『\(card.term)』（含标点变化，未加下划线）")
                        .font(Theme.caption)
                        .foregroundStyle(Theme.errorTone)
                }
                infoRow(title: "本句义", value: card.meaning)
                if !card.otherSenses.isEmpty {
                    infoRow(title: "其他义项", value: card.otherSenses.joined(separator: "；"))
                }
                if !card.errorMode.isEmpty {
                    infoRow(title: "常见错法", value: card.errorMode)
                }
            case .sentence:
                HStack(spacing: 8) {
                    TypeBadge(type: .sentence)
                    Text(card.sentenceType)
                        .font(Theme.bodyCN.weight(.medium))
                        .foregroundStyle(Theme.textPrimary)
                    Text("考频 \(card.examFrequency)")
                        .font(Theme.caption)
                        .foregroundStyle(Theme.textSecondary)
                }
                if let explanation = selectedExplanation(for: card) {
                    infoRow(title: "干扰项解析", value: explanation)
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius))
    }

    private func infoRow(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
            Text(value)
                .font(Theme.bodyCN)
                .foregroundStyle(Theme.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    /// 与用户所选对应的干扰项解析
    private func selectedExplanation(for card: Card) -> String? {
        guard let selected = selectedOption,
              let quiz = library.quizzes[card.id],
              let d = quiz.distractors.first(where: { $0.text == selected }) else { return nil }
        return d.explanation
    }

    // MARK: - 出处与上下文

    @ViewBuilder
    private func sourceSection(card: Card) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(card.sourceWork)
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
            if let prev = card.prevSentence {
                contextLine(prefix: "前：", text: prev)
            }
            if let next = card.nextSentence {
                contextLine(prefix: "后：", text: next)
            }
        }
    }

    private func contextLine(prefix: String, text: String) -> some View {
        Button {
            withAnimation(.easeOut(duration: 0.18)) { contextExpanded.toggle() }
        } label: {
            Text(prefix + text)
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
                .lineLimit(contextExpanded ? nil : 1)
                .frame(maxWidth: .infinity, alignment: .leading)
                .multilineTextAlignment(.leading)
        }
        .buttonStyle(.plain)
    }

    // MARK: - 底部按钮（§3.4）

    private func actionBar(card: Card) -> some View {
        HStack(spacing: 12) {
            OutlineButton(
                title: addedToMistakeBook ? "已加入" : "加入错题本",
                disabled: addedToMistakeBook
            ) {
                store.addToMistakeBook(card: card)
                addedToMistakeBook = true
                showToast = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) { showToast = false }
            }
            .frame(maxWidth: .infinity)
            .accessibilityIdentifier("btn_add_mistake")

            FilledButton(title: nextButtonTitle) { goNext(card: card) }
                .frame(maxWidth: .infinity)
                .accessibilityIdentifier("btn_next")
        }
        .padding(.horizontal, Metrics.pagePadding)
        .padding(.vertical, 10)
        .background(Theme.bg)
    }

    private var nextButtonTitle: String {
        session.mode == .retrain ? "完成" : "下一题"
    }

    private func goNext(card: Card) {
        if session.mode == .retrain {
            flow.endSession()
            return
        }
        if session.currentIndex + 1 < session.round.count {
            session.currentIndex += 1
            path = []   // 回到选择题页（root），进入下一题
        } else {
            session.prepareRecall()
            path = [.recall]
        }
    }
}

/// 选择页 → 答案页传递用户所选文本的桥（避免在 path 里塞复杂载荷）
final class QuizResultBridge {
    static let shared = QuizResultBridge()
    var lastSelection: String?
}
