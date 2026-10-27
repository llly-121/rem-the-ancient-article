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
        // 每换一题重建视图身份，重置选中/锁定状态（path 弹回 root 后 state 不残留）
        .id(session.currentIndex)
    }

    private func content(for card: Card) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            progressBar
            ScrollView {
                VStack(spacing: 24) {
                    Text(card.classical)
                        .font(Theme.classicalFont)
                        .lineSpacing(14)
                        .foregroundStyle(Theme.textPrimary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                    options(for: card)
                }
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.top, 8)
            }
        }
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
            ForEach(texts, id: \.self) { text in
                Button {
                    handleSelect(text: text, card: card)
                } label: {
                    OptionCard(
                        text: text,
                        state: optionState(text: text, card: card))
                }
                .buttonStyle(.plain)
                .disabled(isLocked)
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
