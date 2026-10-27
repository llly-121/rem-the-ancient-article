import Foundation

/// 抽题引擎（learning_engine.md v1.0 §2 / §8 / §4.1）
enum Scheduler {

    // MARK: - 每轮 20 题（§8 伪代码的完整实现）

    /// 返回本轮 20 题与其中 mastered 补位题的 id 集合（P2：补位题不计入状态流转）
    static func pickRound(now: Date, wordRatio: Double, library: Library,
                          store: ProgressStore) -> (round: [Card], fillIDs: Set<String>) {
        // 1. 词句比例（R1）
        let nWord = Int((20.0 * wordRatio).rounded())
        let nSent = 20 - nWord

        // 候选池划分；只抽有选择题数据的卡（quiz 分批交付期间的自然约束）
        func pool(_ type: CardType, _ pred: (ProgressState) -> Bool) -> [Card] {
            library.cards.values.filter { card in
                card.type == type
                    && library.quizzes[card.id] != nil
                    && pred(store.state(for: card.id))
            }
        }
        let newWord = pool(.word) { $0.status == .new }
        let newSent = pool(.sentence) { $0.status == .new }
        let dueWord = pool(.word) { $0.isDue(now: now) }
        let dueSent = pool(.sentence) { $0.isDue(now: now) }

        // 2. 前 5 题：全 new（R2），按比例分摊（默认 3 词 + 2 句）
        var round: [Card] = []
        round += sampleWeighted(weighted(newWord, store), min(3, nWord))
        round += sampleWeighted(weighted(newSent, store), min(2, nSent))

        // 3. 第 6–20 题：learning.due 优先（R3a）
        let tailWord = max(0, nWord - round.filter { $0.type == .word }.count)
        let tailSent = max(0, nSent - round.filter { $0.type == .sentence }.count)
        var tail: [Card] = []
        tail += sampleWeighted(weighted(dueWord, store), tailWord)
        tail += sampleWeighted(weighted(dueSent, store), tailSent)

        // 4. learning.due 不足 → new 补位，尾段 new ≤ 3（R3b/R3c）
        var usedNewIDs = Set(round.map(\.id) + tail.map(\.id))
        let shortage = (tailWord + tailSent) - tail.count
        if shortage > 0 {
            var newPool = (newWord + newSent).filter { !usedNewIDs.contains($0.id) }
            newPool.shuffle()
            for card in newPool.prefix(min(3, shortage)) {
                tail.append(card)
                usedNewIDs.insert(card.id)
            }
        }

        // 5. 仍不足 → mastered 按 exam_frequency 降序补位（P2 = a），不计状态流转
        var fillIDs: Set<String> = []
        let stillShort = (tailWord + tailSent) - tail.count
        if stillShort > 0 {
            let excluded = Set(round.map(\.id) + tail.map(\.id))
            let mastered = library.cards.values.filter {
                store.state(for: $0.id).status == .mastered
                    && library.quizzes[$0.id] != nil
                    && !excluded.contains($0.id)
            }
            for card in mastered.sorted(by: { $0.examFrequency > $1.examFrequency }).prefix(stillShort) {
                tail.append(card)
                fillIDs.insert(card.id)
            }
        }
        round += tail

        // 6. 多字词保底（R6）：char_count ≥ 2 的词级题 ≥ 3
        round = ensureMultiCharWords(round, minCount: 3, library: library, store: store)

        // 7. 轮内去重兜底（R7）
        var seen = Set<String>()
        round = round.filter { seen.insert($0.id).inserted }

        // 8. 输出顺序：前 5 题（new 头部）保持，其余打乱
        let headCount = min(5, round.count)
        var result = Array(round.prefix(headCount))
        result.append(contentsOf: round.dropFirst(headCount).shuffled())
        return (result, fillIDs)
    }

    // MARK: - 高错率加权（R5：error_rate > 0.5 且 attempts ≥ 3 → 权重 ×2）

    private static func weighted(_ cards: [Card], _ store: ProgressStore) -> [(Card, Double)] {
        cards.map { card in
            let s = store.state(for: card.id)
            let w = (s.totalAttempts >= 3 && s.errorRate > 0.5) ? 2.0 : 1.0
            return (card, w)
        }
    }

    /// 加权随机不放回抽取
    private static func sampleWeighted(_ items: [(Card, Double)], _ n: Int) -> [Card] {
        guard n > 0 else { return [] }
        var pool = items
        var out: [Card] = []
        while out.count < n && !pool.isEmpty {
            let total = pool.reduce(0.0) { $0 + $1.1 }
            var r = Double.random(in: 0..<total)
            var pickIndex = 0
            for (i, pair) in pool.enumerated() {
                r -= pair.1
                if r <= 0 { pickIndex = i; break }
            }
            out.append(pool.remove(at: pickIndex).0)
        }
        return out
    }

    /// 多字词保底：不足 3 道时替换单字词（优先换出 exam_frequency 最低者）
    private static func ensureMultiCharWords(_ round: [Card], minCount: Int,
                                             library: Library, store: ProgressStore) -> [Card] {
        var r = round
        func multiCount() -> Int { r.filter { $0.type == .word && $0.charCount >= 2 }.count }
        guard multiCount() < minCount else { return r }

        let excludedIDs = Set(r.map(\.id))
        let candidates = library.cards.values.filter {
            $0.type == .word && $0.charCount >= 2
                && library.quizzes[$0.id] != nil
                && !excludedIDs.contains($0.id)
        }
        // 换入优先级：learning.due > new > mastered（补位）
        let now = Date()
        let due = candidates.filter { store.state(for: $0.id).isDue(now: now) }
        let fresh = candidates.filter { store.state(for: $0.id).status == .new }
        let mastered = candidates.filter { store.state(for: $0.id).status == .mastered }
        var queue = due.sorted { $0.examFrequency > $1.examFrequency }
            + fresh.sorted { $0.examFrequency > $1.examFrequency }
            + mastered.sorted { $0.examFrequency > $1.examFrequency }

        let singles = r.enumerated().filter { $0.element.type == .word && $0.element.charCount == 1 }
            .sorted { $0.element.examFrequency < $1.element.examFrequency }
        for (idx, _) in singles {
            guard !queue.isEmpty else { break }
            r[idx] = queue.removeFirst()
            if multiCount() >= minCount { break }
        }
        return r
    }

    // MARK: - 默写抽样 10 题（§4.1，P6 = a）

    /// 优先抽本轮答错的题，不足按 exam_frequency 降序补齐；词句比例跟随本轮（不强制）
    static func pickRecallIDs(round: [Card], wrongCardIDs: Set<String>, count: Int = 10) -> [String] {
        var result: [String] = []
        for card in round where wrongCardIDs.contains(card.id) {
            if result.count < count { result.append(card.id) }
        }
        if result.count < count {
            let remaining = round
                .filter { !result.contains($0.id) }
                .sorted { $0.examFrequency > $1.examFrequency }
            for card in remaining {
                if result.count >= count { break }
                result.append(card.id)
            }
        }
        return result
    }

    // MARK: - 词级默写判分（§4.4，P7 = b：忽略大小写、首尾空格、开头冠词）

    static func judgeWordRecall(input: String, answer: String) -> Bool {
        func normalize(_ s: String) -> String {
            var t = s.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            for article in ["the ", "a ", "an "] where t.hasPrefix(article) {
                t = String(t.dropFirst(article.count))
                break
            }
            return t.trimmingCharacters(in: .whitespaces)
        }
        return normalize(input) == normalize(answer)
    }

    // MARK: - 提示：正确答案前 2 个字母（§4.3，跳过非字母字符，保留大小写）

    static func hintPrefix(for answer: String) -> String {
        String(answer.filter { $0.isLetter && $0.isASCII }.prefix(2))
    }

    // MARK: - 选择题判分

    static func judgeQuiz(selected: String, quiz: QuizItem) -> Bool {
        selected == quiz.correct
    }
}
