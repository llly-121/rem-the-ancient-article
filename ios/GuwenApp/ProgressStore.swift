import Foundation
import Observation
import SwiftData

/// 学习状态存储：内存缓存 + SwiftData 持久化（引擎 §1，与只读题库解耦）
@Observable
final class ProgressStore {
    private(set) var states: [String: ProgressState] = [:]
    private(set) var mistakes: [MistakeEntry] = []
    private let context: ModelContext

    init(context: ModelContext) {
        self.context = context
        load()
    }

    // MARK: - 读取

    private func load() {
        var result: [String: ProgressState] = [:]
        let desc = FetchDescriptor<ProgressRecord>()
        if let records = try? context.fetch(desc) {
            for r in records {
                result[r.id] = ProgressState(
                    status: CardStatus(rawValue: r.statusRaw) ?? .new,
                    consecutiveCorrect: r.consecutiveCorrect,
                    totalAttempts: r.totalAttempts,
                    totalCorrect: r.totalCorrect,
                    lastSeenAt: r.lastSeenAt,
                    inMistakeBook: r.inMistakeBook)
            }
        }
        states = result

        let mDesc = FetchDescriptor<MistakeRecord>(sortBy: [SortDescriptor(\.addedAt, order: .reverse)])
        if let rows = try? context.fetch(mDesc) {
            mistakes = rows.map { MistakeEntry(cardID: $0.cardID, addedAt: $0.addedAt) }
        }
    }

    func state(for id: String) -> ProgressState {
        states[id] ?? ProgressState()
    }

    /// 统计（首页用）
    var statusCounts: (new: Int, learning: Int, mastered: Int) {
        var c: (Int, Int, Int) = (0, 0, 0)
        for s in states.values {
            switch s.status {
            case .new: c.0 += 1
            case .learning: c.1 += 1
            case .mastered: c.2 += 1
            }
        }
        return c
    }

    var totalAttempts: Int { states.values.reduce(0) { $0 + $1.totalAttempts } }

    // MARK: - 作答记录（引擎 §3）

    /// - Parameters:
    ///   - countsTowardStatus: false 用于错题本「再练一次」与 mastered 补位题（P8 / P2）
    ///     —— 只计 total_attempts / total_correct，不动 consecutive_correct 与 status。
    func recordAnswer(card: Card, isCorrect: Bool, countsTowardStatus: Bool = true, now: Date = Date()) {
        var s = state(for: card.id)
        s.totalAttempts += 1

        if countsTowardStatus {
            if isCorrect {
                s.totalCorrect += 1
                s.consecutiveCorrect += 1
                if s.consecutiveCorrect >= 3 {
                    s.status = .mastered                     // S3
                } else {
                    s.status = .learning                     // S2/S3
                }
            } else {
                s.consecutiveCorrect = 0                     // S4/S5
                s.status = .learning
            }
        } else if isCorrect {
            s.totalCorrect += 1
        }

        s.lastSeenAt = now
        states[card.id] = s
        persist(card: card, state: s)
    }

    // MARK: - 错题本（引擎 §5）

    /// 重复加入置顶不新增（M2）
    func addToMistakeBook(card: Card, now: Date = Date()) {
        var s = state(for: card.id)
        s.inMistakeBook = true
        states[card.id] = s
        persist(card: card, state: s)

        if let idx = mistakes.firstIndex(where: { $0.cardID == card.id }) {
            mistakes[idx] = MistakeEntry(cardID: card.id, addedAt: now)
            upsertMistake(cardID: card.id, addedAt: now)
        } else {
            mistakes.insert(MistakeEntry(cardID: card.id, addedAt: now), at: 0)
            context.insert(MistakeRecord(cardID: card.id, addedAt: now))
        }
        try? context.save()
    }

    /// 左滑删除（U11）
    func removeFromMistakeBook(cardID: String) {
        mistakes.removeAll { $0.cardID == cardID }
        let desc = FetchDescriptor<MistakeRecord>(predicate: #Predicate { $0.cardID == cardID })
        if let rows = try? context.fetch(desc) { for r in rows { context.delete(r) } }

        if let card = libraryCard(id: cardID) {
            var s = state(for: cardID)
            s.inMistakeBook = false
            states[cardID] = s
            persist(card: card, state: s)
        }
        try? context.save()
    }

    /// mastered 卡「重新学习」入口（引擎 P11）：清零回 new
    func resetCard(cardID: String) {
        let s = ProgressState()
        states[cardID] = s
        if let card = libraryCard(id: cardID) { persist(card: card, state: s) }
        try? context.save()
    }

    func clearAllProgress() {
        states = [:]
        mistakes = []
        if let rows = try? context.fetch(FetchDescriptor<ProgressRecord>()) { for r in rows { context.delete(r) } }
        if let rows = try? context.fetch(FetchDescriptor<MistakeRecord>()) { for r in rows { context.delete(r) } }
        try? context.save()
    }

    // MARK: - 私有

    /// 注入的弱引用：避免循环依赖，仅用于 persist 时补 typeRaw
    weak var libraryRef: Library?

    private func libraryCard(id: String) -> Card? { libraryRef?.cards[id] }

    private func persist(card: Card, state: ProgressState) {
        // #Predicate 只能捕获简单局部值，不能直接引用 card.id 这类成员访问
        let cid = card.id
        let desc = FetchDescriptor<ProgressRecord>(predicate: #Predicate { $0.id == cid })
        if let existing = try? context.fetch(desc).first {
            existing.statusRaw = state.status.rawValue
            existing.consecutiveCorrect = state.consecutiveCorrect
            existing.totalAttempts = state.totalAttempts
            existing.totalCorrect = state.totalCorrect
            existing.lastSeenAt = state.lastSeenAt
            existing.inMistakeBook = state.inMistakeBook
        } else {
            context.insert(ProgressRecord(
                id: card.id, typeRaw: card.type.rawValue, statusRaw: state.status.rawValue,
                consecutiveCorrect: state.consecutiveCorrect, totalAttempts: state.totalAttempts,
                totalCorrect: state.totalCorrect, lastSeenAt: state.lastSeenAt,
                inMistakeBook: state.inMistakeBook))
        }
        try? context.save()
    }

    private func upsertMistake(cardID: String, addedAt: Date) {
        let desc = FetchDescriptor<MistakeRecord>(predicate: #Predicate { $0.cardID == cardID })
        if let existing = try? context.fetch(desc).first {
            existing.addedAt = addedAt
        } else {
            context.insert(MistakeRecord(cardID: cardID, addedAt: addedAt))
        }
    }
}
