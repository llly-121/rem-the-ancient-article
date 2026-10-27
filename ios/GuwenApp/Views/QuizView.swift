import SwiftUI

/// 页面一：选择题页（ui_spec §2）
struct QuizView: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    let session: RoundSession
    @Binding var path: [FlowStep]

    @State private var selectedOption: String?
    @State private var isLocked = false
    @State private var showExitConfirm = false

    var body: some View {
        Group {
            if let card = session.currentCard {
                content(for: card)
            } else {
                // 候选不足兜底（题库覆盖有限时可能整轮 < 20 题）
                VStack(spacing: 16) {
                    Text("本轮已结束")
                        .font(Theme.bodyCN)
                        .foregroundStyle(Theme.textPrimary)
                    FilledButton(title: "回首页") { flow.endSession() }
                }
                .padding(Metrics.pagePadding)
            }
        }
        .background(Theme.bg.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        // 换题时显式重置选择态。
        // 注意：不能靠 .id(index) —— 写在 body 内部只重建子树，不会重置本视图的 @State，
        // 会导致第 2 题起选项全部处于 isLocked=true 的死状态。
        .onChange(of: session.currentIndex) { _, _ in
            selectedOption = nil
            isLocked = false
            showExitConfirm = false
        }
    }

    private func content(for card: Card) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            progressBar
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 10) {
                        // 词级题的选项是「某一个词」的释义，不标出是哪个词就没法作答
                        // （题面是一整段古文，四个选项却是 encourage/played/play/drum）
                        if card.type == .word, hasLocatableTerm(card) {
                            Text("选出划线词的释义")
                                .font(Theme.caption)
                                .foregroundStyle(Theme.textSecondary)
                        }
                        stem(for: card)
                    }
                    options(for: card)
                }
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.top, 8)
            }
        }
    }

    /// 词级题面：把 term 的所有出现处加下划线，指明考的是哪个词
    @ViewBuilder
    private func stem(for card: Card) -> some View {
        if card.type == .word, let attributed = underlinedClassical(for: card) {
            Text(attributed)
                .font(Theme.classicalFont)
                .lineSpacing(14)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
        } else {
            Text(card.classical)
                .font(Theme.classicalFont)
                .lineSpacing(14)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
        }
    }

    private func hasLocatableTerm(_ card: Card) -> Bool {
        !TermLocator.ranges(of: card.term, in: card.classical).isEmpty
    }

    private func underlinedClassical(for card: Card) -> AttributedString? {
        let ranges = TermLocator.ranges(of: card.term, in: card.classical)
        guard !ranges.isEmpty else { return nil }
        var attributed = AttributedString(card.classical)
        for r in ranges {
            guard let ar = Range(r, in: attributed) else { continue }
            attributed[ar].underlineStyle = Text.LineStyle.single
        }
        return attributed
    }

    // MARK: - 头部

    private var header: some View {
        HStack {
            Text(headerTitle)
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
            Spacer()
            Button("退出") { showExitConfirm = true }
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
        .padding(.horizontal, Metrics.pagePadding)
        .padding(.top, 8)
        .alert("退出本轮？", isPresented: $showExitConfirm) {
            Button("继续做题", role: .cancel) {}
            Button("退出", role: .destructive) { flow.endSession() }
        } message: {
            Text("已作答题目的计数会保留，本轮剩余题目不再进行。")
        }
    }

    private var headerTitle: String {
        if session.mode == .retrain {
            return "错题再练"
        }
        return "第 \(session.currentIndex + 1)/\(session.round.count) 题"
    }

    @ViewBuilder
    private var progressBar: some View {
        if session.mode == .normal {
            ProgressSegmentBar(total: session.round.count, completed: session.currentIndex)
                .frame(maxWidth: .infinity)
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.top, 6)
                .padding(.bottom, 4)
        }
    }

    // MARK: - 选项（U2：锁定后二次点击无任何变化）

    private func options(for card: Card) -> some View {
        let texts = session.options(for: card.id)
        return VStack(spacing: Metrics.optionSpacing) {
            ForEach(Array(texts.enumerated()), id: \.element) { index, text in
                Button {
                    handleSelect(text: text, card: card)
                } label: {
                    OptionCard(
                        text: text,
                        state: optionState(text: text, card: card))
                }
                .buttonStyle(.plain)
                .disabled(isLocked)
                .accessibilityIdentifier("option_\(index)")   // UI 冒烟测试锚点
            }
        }
    }

    private func optionState(text: String, card: Card) -> OptionCard.OptionState {
        guard let selected = selectedOption else { return .idle }
        return text == selected ? .selected : .idle
    }

    private func handleSelect(text: String, card: Card) {
        guard !isLocked else { return }              // U2
        selectedOption = text
        isLocked = true

        Task { @MainActor in
            // 0.4s 延迟后写入结果并进入答案页（ui_spec §2.3 / §1.3）
            try? await Task.sleep(nanoseconds: UInt64(Metrics.selectToAnswerDelay * 1_000_000_000))
            QuizResultBridge.shared.lastSelection = text
            let quiz = library.quizzes[card.id]
            let isCorrect = quiz.map { Scheduler.judgeQuiz(selected: text, quiz: $0) } ?? false

            let countsTowardStatus = session.mode == .normal && !session.fillIDs.contains(card.id)
            store.recordAnswer(card: card, isCorrect: isCorrect, countsTowardStatus: countsTowardStatus)
            if !isCorrect {
                session.wrongCardIDs.insert(card.id)  // 默写抽样优先本轮答错（P6）
            }
            path.append(.answer)
        }
    }
}
