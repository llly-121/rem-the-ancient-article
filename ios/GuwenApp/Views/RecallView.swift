import SwiftUI

/// 页面三：检查默写页（ui_spec §4）
struct RecallView: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    let session: RoundSession
    @Binding var path: [FlowStep]

    @State private var input = ""
    @State private var hintUsed = false
    @State private var hintInserted = ""
    @State private var revealed = false
    @State private var judgedCorrect: Bool?
    @State private var showExitConfirm = false

    private var total: Int { max(session.recallIDs.count, 1) }

    var body: some View {
        Group {
            if let card = currentCard {
                content(for: card)
            } else {
                VStack(spacing: 16) {
                    Text("默写已结束")
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
    }

    private var currentCard: Card? {
        guard session.recallIndex < session.recallIDs.count else { return nil }
        let id = session.recallIDs[session.recallIndex]
        return session.card(for: id) ?? library.cards[id]
    }

    private func content(for card: Card) -> some View {
        VStack(spacing: 0) {
            header
            ScrollView {
                VStack(spacing: 20) {
                    prompt(for: card)
                    if !revealed {
                        editor(for: card)
                        actions(for: card)
                    } else {
                        comparison(for: card)
                        nextButton
                    }
                }
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.top, 12)
            }
        }
        .onAppear(perform: restoreDraft)
    }

    // MARK: - 头部

    private var header: some View {
        HStack {
            Text("检查 \(session.recallIndex + 1)/\(total)")
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
            Spacer()
            Button("退出") { showExitConfirm = true }
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
        .padding(.horizontal, Metrics.pagePadding)
        .padding(.top, 8)
        .alert("退出默写？", isPresented: $showExitConfirm) {
            Button("继续默写", role: .cancel) {}
            Button("退出", role: .destructive) { flow.endSession() }
        } message: {
            Text("已判分的默写题计数会保留，剩余默写题不再进行。")
        }
    }

    // MARK: - 题面（词级 = term + 所在句；句级 = 整句）

    @ViewBuilder
    private func prompt(for card: Card) -> some View {
        if card.type == .word {
            Text(card.term)
                .font(Theme.recallClassicalFont)
                .foregroundStyle(Theme.textPrimary)
                .frame(maxWidth: .infinity)
            Text(card.classical)
                .font(Theme.classicalFont)
                .lineSpacing(14)
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity)
        } else {
            Text(card.classical)
                .font(Theme.recallClassicalFont)
                .lineSpacing(16)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity)
        }
    }

    // MARK: - 输入区

    private func editor(for card: Card) -> some View {
        // TextEditor 没有原生 placeholder，叠一层不可点击的提示文字
        ZStack(alignment: .topLeading) {
            TextEditor(text: $input)
                .font(Theme.bodyCN)
                .scrollContentBackground(.hidden)
                .padding(12)

            if input.isEmpty {
                Text(card.type == .word
                     ? "默写「\(card.term)」在本句的英文释义"
                     : "默写这一句的英文译文")
                    .font(Theme.bodyCN)
                    .foregroundStyle(Theme.textSecondary.opacity(0.7))
                    .padding(.horizontal, 17)
                    .padding(.vertical, 20)
                    .allowsHitTesting(false)
            }
        }
        .frame(minHeight: 120, maxHeight: 200)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius))
        .overlay(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius)
            .stroke(Theme.divider, lineWidth: Metrics.strokeWidthNormal))
    }

    private func actions(for card: Card) -> some View {
        VStack(spacing: 12) {
            if hintUsed {
                Text("已插入：\(hintInserted)")
                    .font(Theme.caption)
                    .foregroundStyle(Theme.textSecondary)
            }
            HStack(spacing: 12) {
                OutlineButton(
                    title: hintUsed ? "已使用提示" : "提示",
                    disabled: hintUsed
                ) { applyHint() }
                .frame(maxWidth: .infinity)
                .accessibilityIdentifier("btn_hint")

                OutlineButton(title: "查看答案", disabled: false) { revealAnswer(card: card) }
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("btn_reveal")
            }
        }
    }

    /// 提示：取 correct 前 2 个字母（跳过非字母字符，保留大小写），插入输入末尾（§4.3）
    private func applyHint() {
        guard let card = currentCard else { return }
        let hint = Scheduler.hintPrefix(for: card.recallAnswer)
        input += hint
        hintInserted = hint
        hintUsed = true
    }

    /// 查看答案（P8 联动：可先于提示点；写 total_attempts，对才写 total_correct；不动 cc/status）
    private func revealAnswer(card: Card) {
        session.drafts[card.id] = input
        if card.type == .word {
            let isCorrect = Scheduler.judgeWordRecall(input: input, answer: card.recallAnswer)
            // P9 = b：用提示判对只计 total_attempts，不计 total_correct
            let countsAsCorrect = isCorrect && !hintUsed
            store.recordAnswer(card: card, isCorrect: countsAsCorrect,
                               countsTowardStatus: false)
            judgedCorrect = isCorrect
        } else {
            // 句级：等待自评按钮，先不记
        }
        revealed = true
    }

    // MARK: - 对比态（§4.5 word-level LCS）

    @ViewBuilder
    private func comparison(for card: Card) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 8) {
                Text("你的默写")
                    .font(Theme.caption)
                    .foregroundStyle(Theme.textSecondary)
                if card.type == .word {
                    Text(input.isEmpty ? "（未输入）" : input)
                        .font(Theme.serifEnglishFont)
                        .foregroundStyle(Theme.textPrimary)
                } else {
                    inputDiffLine(answer: card.recallAnswer, input: input)
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("正确答案")
                    .font(Theme.caption)
                    .foregroundStyle(Theme.textSecondary)
                answerDiffLine(answer: card.recallAnswer, input: input)
            }
            if card.type == .word {
                judgeResultBadge(isCorrect: judgedCorrect ?? false)
            } else {
                HStack(spacing: 12) {
                    OutlineButton(title: "判对") { selfJudge(card: card, correct: true) }
                        .frame(maxWidth: .infinity)
                        .accessibilityIdentifier("btn_self_correct")
                    OutlineButton(title: "判错") { selfJudge(card: card, correct: false) }
                        .frame(maxWidth: .infinity)
                        .accessibilityIdentifier("btn_self_wrong")
                }
            }
        }
    }

    private func answerDiffLine(answer: String, input: String) -> some View {
        let tokens = DiffBuilder.diff(answer: answer, input: input).answerTokens
        return diffText(tokens: tokens)
    }

    private func inputDiffLine(answer: String, input: String) -> some View {
        let tokens = DiffBuilder.diff(answer: answer, input: input).inputTokens
        return diffText(tokens: tokens)
    }

    private func diffText(tokens: [DiffToken]) -> Text {
        var result = AttributedString("")
        for token in tokens {
            var part = AttributedString(token.text + " ")
            switch token.kind {
            case .matched:
                part.foregroundColor = Theme.textPrimary
            case .missing:
                part.foregroundColor = Theme.textPrimary
                part.backgroundColor = Theme.highlight
                part.underlineStyle = Text.LineStyle.single
            case .extra:
                part.foregroundColor = Theme.errorTone
                part.strikethroughStyle = Text.LineStyle.single
            }
            result += part
        }
        return Text(result)
    }

    private func judgeResultBadge(isCorrect: Bool) -> some View {
        Label(isCorrect ? "默写判对" : "默写判错", systemImage: isCorrect ? "checkmark" : "xmark")
            .font(Theme.caption)
            .foregroundStyle(isCorrect ? Theme.accent : Theme.errorTone)
    }

    private func selfJudge(card: Card, correct: Bool) {
        guard judgedCorrect == nil else { return }
        store.recordAnswer(card: card, isCorrect: correct, countsTowardStatus: false)
        judgedCorrect = correct
        if correct { session.recallCorrectCount += 1 }
    }

    // MARK: - 下一题 / 草稿恢复

    private var nextButton: some View {
        FilledButton(
            title: session.recallIndex + 1 < total ? "下一题" : "完成默写",
            disabled: currentCard.map { $0.type == .sentence && judgedCorrect == nil } ?? false
        ) {
            guard let card = currentCard else { return }
            // 词级已在 revealAnswer 计数；句级须先自评
            if session.recallIndex + 1 < total {
                session.recallIndex += 1
                resetForNext()
            } else {
                path.append(.summary)
            }
            _ = card
        }
        .accessibilityIdentifier("btn_recall_next")
    }

    private func resetForNext() {
        input = ""
        hintUsed = false
        hintInserted = ""
        revealed = false
        judgedCorrect = nil
    }

    private func restoreDraft() {
        guard let card = currentCard else { return }
        input = session.drafts[card.id] ?? ""
    }
}

/// 默写小结：回首页
struct RecallSummaryView: View {
    @Environment(AppFlow.self) private var flow
    let session: RoundSession
    @Binding var path: [FlowStep]

    var body: some View {
        VStack(spacing: 28) {
            Spacer()
            ScrollIllustration()
            VStack(spacing: 8) {
                Text("本轮完成")
                    .font(Theme.recallClassicalFont)
                    .foregroundStyle(Theme.textPrimary)
                Text("默写 \(session.recallIDs.count) 题已计入统计")
                    .font(Theme.bodyCN)
                    .foregroundStyle(Theme.textSecondary)
            }
            FilledButton(title: "回首页") { flow.endSession() }
                .padding(.horizontal, Metrics.pagePadding)
                .accessibilityIdentifier("btn_home")
            Spacer()
        }
        .frame(maxWidth: .infinity)
        .background(Theme.bg.ignoresSafeArea())
        .toolbar(.hidden, for: .navigationBar)
    }
}
