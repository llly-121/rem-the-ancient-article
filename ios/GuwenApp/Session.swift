import Foundation
import SwiftUI

/// 一轮学习会话（ui_spec §6）：20 题常规轮 + 10 题默写，或错题本单题再练
@Observable
final class RoundSession: Identifiable {
    enum Mode: Hashable {
        case normal
        case retrain
    }

    let id = UUID()
    let mode: Mode
    private(set) var round: [Card]
    /// mastered 补位题 id（P2：此类题不计入状态流转）
    let fillIDs: Set<String>
    private(set) var recallIDs: [String] = []

    var currentIndex = 0
    var recallIndex = 0
    var wrongCardIDs: Set<String> = []
    /// cardID → 已洗牌的选项顺序（每轮进场时洗牌并缓存，答案页复现同一顺序）
    var shuffledOptions: [String: [String]] = [:]
    /// 默写草稿（切题恢复）
    var drafts: [String: String] = [:]
    /// 本轮默写判对数（小结用）
    var recallCorrectCount = 0

    init(mode: Mode, round: [Card], fillIDs: Set<String> = []) {
        self.mode = mode
        self.round = round
        self.fillIDs = fillIDs
    }

    var isFinished: Bool {
        mode == .normal ? currentIndex >= round.count : false
    }

    var currentCard: Card? {
        currentIndex < round.count ? round[currentIndex] : nil
    }

    func card(for id: String) -> Card? {
        round.first { $0.id == id }
    }

    /// 进入常规轮时锁定 20 题；答完第 20 题后生成默写抽样
    func prepareRecall() {
        guard recallIDs.isEmpty else { return }
        recallIDs = Scheduler.pickRecallIDs(round: round, wrongCardIDs: wrongCardIDs)
        recallIndex = 0
    }

    func options(for cardID: String) -> [String] {
        if let cached = shuffledOptions[cardID] { return cached }
        guard let quiz = quizProvider?(cardID) else { return [] }
        let shuffled = quiz.allOptionTexts.shuffled()
        shuffledOptions[cardID] = shuffled
        return shuffled
    }

    /// 由外部注入 quiz 查询（避免循环持有 Library）
    var quizProvider: ((String) -> QuizItem?)?
}

// MARK: - 词项定位（ui_spec §3.5 容错规则）

enum TermLocator {

    private static let punctuation: Set<Character> = ["、", "，", "。", "；", "：", "！", "？",
                                                       "「", "」", "（", "）", "『", "』",
                                                       ",", ".", ";", ":", "!", "?", "(", ")"]

    /// 返回 term 在 classical 中全部出现范围；先精确匹配，失败退化去标点匹配
    static func ranges(of term: String, in classical: String) -> [Range<String.Index>] {
        guard !term.isEmpty else { return [] }

        // 1. 原文精确匹配（含全部出现处，U5）
        var ranges: [Range<String.Index>] = []
        var searchStart = classical.startIndex
        while let r = classical.range(of: term, range: searchStart..<classical.endIndex) {
            ranges.append(r)
            searchStart = r.upperBound
        }
        if !ranges.isEmpty { return ranges }

        // 2. 去标点匹配：把原文与 term 同时剔除标点后求位置，再映射回原串
        var kept: [(Character, String.Index)] = []
        for i in classical.indices where !punctuation.contains(classical[i]) {
            kept.append((classical[i], i))
        }
        let strippedText = String(kept.map(\.0))
        let strippedTerm = String(term.filter { !punctuation.contains($0) })
        guard !strippedTerm.isEmpty,
              let strippedRange = strippedText.range(of: strippedTerm) else { return [] }

        // 映射：stripped 下标 → kept 下标 → 原串下标
        let lower = strippedText.distance(from: strippedText.startIndex, to: strippedRange.lowerBound)
        let upper = strippedText.distance(from: strippedText.startIndex, to: strippedRange.upperBound)
        guard lower < kept.count, upper <= kept.count, upper > lower else { return [] }
        let fromIdx = kept[lower].1
        let toIdx = classical.index(after: kept[upper - 1].1)
        return [fromIdx..<toIdx]
    }

    /// term_english 在 full_english 中的首个匹配范围（引擎保证为连续子串）
    static func firstRange(of fragment: String, in full: String) -> Range<String.Index>? {
        guard !fragment.isEmpty else { return nil }
        return full.range(of: fragment)
    }

    /// 长段级译文（>400 字符）按句切分（ui_spec §3.2，U6）
    static func splitLongEnglish(_ full: String) -> [String] {
        guard full.count > 400 else { return [full] }
        var parts: [String] = []
        var current = ""
        for ch in full {
            current.append(ch)
            if ".!?".contains(ch) {
                parts.append(current.trimmingCharacters(in: .whitespaces))
                current = ""
            }
        }
        if !current.trimmingCharacters(in: .whitespaces).isEmpty {
            parts.append(current.trimmingCharacters(in: .whitespaces))
        }
        return parts.filter { !$0.isEmpty }
    }
}

// MARK: - 词级差异对比（ui_spec §4.5：word-level LCS）

struct DiffToken: Identifiable {
    enum Kind { case matched, missing, extra }
    let id = UUID()
    let text: String
    let kind: Kind
}

enum DiffBuilder {

    /// 以正确答案为基准做 word-level LCS 对齐（ui_spec §4.5）：
    /// - answerTokens：matched（普通）/ missing（遗漏，accent 高亮 + 下划线）
    /// - inputTokens：matched（普通）/ extra（多写，删除线）
    static func diff(answer: String, input: String)
        -> (answerTokens: [DiffToken], inputTokens: [DiffToken]) {
        let answerWords = answer.split(separator: " ").map(String.init)
        let inputWords = input.split(separator: " ").map(String.init)
        let lower = { (w: String) in w.lowercased().trimmingCharacters(in: .punctuationCharacters) }

        // LCS 表
        let n = answerWords.count, m = inputWords.count
        var lcs = Array(repeating: Array(repeating: 0, count: m + 1), count: n + 1)
        for i in stride(from: n - 1, through: 0, by: -1) {
            for j in stride(from: m - 1, through: 0, by: -1) {
                if lower(answerWords[i]) == lower(inputWords[j]) {
                    lcs[i][j] = lcs[i + 1][j + 1] + 1
                } else {
                    lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])
                }
            }
        }

        var answerTokens: [DiffToken] = []
        var inputTokens: [DiffToken] = []
        var i = 0, j = 0
        while i < n && j < m {
            if lower(answerWords[i]) == lower(inputWords[j]) {
                answerTokens.append(DiffToken(text: answerWords[i], kind: .matched))
                inputTokens.append(DiffToken(text: inputWords[j], kind: .matched))
                i += 1; j += 1
            } else if lcs[i + 1][j] >= lcs[i][j + 1] {
                answerTokens.append(DiffToken(text: answerWords[i], kind: .missing))
                i += 1
            } else {
                inputTokens.append(DiffToken(text: inputWords[j], kind: .extra))
                j += 1
            }
        }
        while i < n {
            answerTokens.append(DiffToken(text: answerWords[i], kind: .missing))
            i += 1
        }
        while j < m {
            inputTokens.append(DiffToken(text: inputWords[j], kind: .extra))
            j += 1
        }
        return (answerTokens, inputTokens)
    }
}
