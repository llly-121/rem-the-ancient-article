import SwiftUI

/// 首页（ui_spec §6：Tab「今日」）——统计概览 + 开始一轮
struct HomeView: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    @AppStorage("word_ratio") private var wordRatio = 0.6
    @State private var showClearConfirm = false

    private var quizCoverage: Int { library.quizzes.count }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    header
                    statsCard
                    ratioCard
                    startButton
                    footnote
                }
                .padding(.horizontal, Metrics.pagePadding)
                .padding(.vertical, 24)
            }
            .background(Theme.bg)
            .navigationTitle("古文英译刷词")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("清除全部学习记录", role: .destructive) { showClearConfirm = true }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .alert("清除全部学习记录？", isPresented: $showClearConfirm) {
                Button("取消", role: .cancel) {}
                Button("清除", role: .destructive) { store.clearAllProgress() }
            } message: {
                Text("所有卡片的状态将回到「新卡」，错题本同时清空，此操作不可恢复。")
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("古文英译刷词")
                .font(Theme.recallClassicalFont)
                .foregroundStyle(Theme.textPrimary)
            Text("文言文 · 英译 · 间隔重复")
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
    }

    private var statsCard: some View {
        let counts = store.statusCounts
        return VStack(alignment: .leading, spacing: 14) {
            Text("学习进度")
                .font(Theme.bodyCN.weight(.medium))
                .foregroundStyle(Theme.textPrimary)
            HStack {
                statBlock(value: counts.new, label: "新卡")
                statBlock(value: counts.learning, label: "学习中")
                statBlock(value: counts.mastered, label: "已掌握")
            }
            Divider().overlay(Theme.divider)
            HStack {
                statBlock(value: library.cardCount, label: "题库卡片")
                statBlock(value: quizCoverage, label: "可选卡片")
                statBlock(value: store.totalAttempts, label: "累计作答")
            }
        }
        .padding(16)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius))
    }

    private func statBlock(value: Int, label: String) -> some View {
        VStack(spacing: 4) {
            Text("\(value)")
                .font(.system(size: 22, weight: .semibold, design: .serif))
                .foregroundStyle(Theme.textPrimary)
            Text(label)
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }

    private var ratioCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("词句比例")
                .font(Theme.bodyCN.weight(.medium))
                .foregroundStyle(Theme.textPrimary)
            Picker("词句比例", selection: $wordRatio) {
                Text("5:5").tag(0.5)
                Text("6:4").tag(0.6)
                Text("7:3").tag(0.7)
                Text("8:2").tag(0.8)
            }
            .pickerStyle(.segmented)
            Text("每轮 20 题，词级 \(Int((20.0 * wordRatio).rounded())) 题 / 句级 \(20 - Int((20.0 * wordRatio).rounded())) 题")
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
        .padding(16)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Metrics.cardCornerRadius))
    }

    private var startButton: some View {
        FilledButton(title: "开始一轮") {
            flow.startRound(library: library, store: store, wordRatio: wordRatio)
        }
        .accessibilityIdentifier("btn_start_round")
    }

    private var footnote: some View {
        Text("题库：word_cards 1418 + sentence_cards 654；选择题数据覆盖考频 5/4 档（\(quizCoverage) 张），其余卡轮空。\n轮次含 20 题选择题与 10 题默写检查。")
            .font(Theme.caption)
            .foregroundStyle(Theme.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}
