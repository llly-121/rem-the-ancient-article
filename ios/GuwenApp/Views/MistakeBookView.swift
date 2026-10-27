import SwiftUI

/// 页面四：错题本页（ui_spec §5）
struct MistakeBookView: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    @State private var filterWork: String? = nil

    private var entries: [MistakeEntry] {
        let all = store.mistakes   // 已按 addedAt 降序（M1/M2）
        guard let work = filterWork else { return all }
        // source_work 全文前缀匹配（M3：筛选项显示篇名，匹配用全文前缀）
        return all.filter { entry in
            library.cards[entry.cardID]?.sourceWork.hasPrefix(work) ?? false
        }
    }

    /// 筛选项：列表内 source_work 去重，按出现次数降序；显示括号前篇名
    private var filterOptions: [String] {
        let works = store.mistakes.compactMap { library.cards[$0.cardID]?.workName }
        let counted = Dictionary(grouping: works, by: { $0 }).mapValues(\.count)
        return counted.sorted { $0.value > $1.value }.map(\.key)
    }

    var body: some View {
        NavigationStack {
            Group {
                if entries.isEmpty {
                    emptyState
                } else {
                    list
                }
            }
            .background(Theme.bg)
            .navigationTitle("错题本")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    filterMenu
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Text("共 \(entries.count) 条")
                        .font(Theme.caption)
                        .foregroundStyle(Theme.textSecondary)
                }
            }
        }
    }

    // MARK: - 列表（两行摘要，P10 = a）

    private var list: some View {
        List {
            ForEach(entries) { entry in
                if let card = library.cards[entry.cardID] {
                    row(for: card, entry: entry)
                }
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(Theme.bg)
    }

    private func row(for card: Card, entry: MistakeEntry) -> some View {
        HStack(alignment: .top, spacing: 10) {
            TypeBadge(type: card.type)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(card.classical)
                    .font(Theme.bodyCN)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(2)
                Text(card.sourceWork)
                    .font(Theme.caption)
                    .foregroundStyle(Theme.textSecondary)
                Text(relativeTime(entry.addedAt))
                    .font(Theme.caption)
                    .foregroundStyle(Theme.textSecondary)
            }
        }
        .padding(.vertical, 4)
        // 右滑：再练一次（进入单题模式，选项重新洗牌；计数 P8 = b）
        .swipeActions(edge: .leading, allowsFullSwipe: false) {
            Button {
                flow.startRetrain(card: card, library: library)
            } label: {
                Label("再练一次", systemImage: "arrow.counterclockwise")
            }
            .tint(Theme.accent)
        }
        // 左滑：删除（errorTone 文字，非红色）
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button {
                store.removeFromMistakeBook(cardID: card.id)
            } label: {
                Text("删除")
            }
            .tint(Theme.errorTone)
        }
        // 长按菜单：mastered 卡「重新学习」入口（引擎 P11）
        .contextMenu {
            Button {
                store.resetCard(cardID: card.id)
                store.removeFromMistakeBook(cardID: card.id)
            } label: {
                Label("重新学习（清零状态）", systemImage: "arrow.uturn.backward")
            }
        }
    }

    // MARK: - 筛选

    @ViewBuilder
    private var filterMenu: some View {
        Menu {
            Button("全部") { filterWork = nil }
            ForEach(filterOptions, id: \.self) { work in
                Button(work) { filterWork = work }
            }
        } label: {
            HStack(spacing: 4) {
                Text(filterWork ?? "全部")
                Image(systemName: "chevron.down")
                    .font(.system(size: 10))
            }
            .font(Theme.caption)
            .foregroundStyle(Theme.textPrimary)
        }
    }

    // MARK: - 空状态（§5.1：灯烛＋书卷插图）

    private var emptyState: some View {
        VStack(spacing: 20) {
            CandleBookIllustration()
            Text("还没有错题，继续做题吧")
                .font(Theme.bodyCN)
                .foregroundStyle(Theme.textPrimary)
            Text("答案页可随时把题目收进来")
                .font(Theme.caption)
                .foregroundStyle(Theme.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - 相对时间

    private func relativeTime(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date()) + "加入"
    }
}
