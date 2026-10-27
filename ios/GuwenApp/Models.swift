import Foundation

// MARK: - 原始数据解码（jsonl 行级 Decodable）

struct RawDistractor: Codable, Hashable {
    let text: String
    let error_type: String
    let explanation: String
}

struct RawWordCard: Codable {
    let id: String
    let term: String
    let char_count: Int
    let term_type: String
    let meaning_in_this_sentence: String
    let other_senses: [String]?
    let term_english: String
    let full_english: String
    let classical_sentence: String
    let source_work: String
    let prev_sentence: String?
    let next_sentence: String?
    let typical_error_mode: String
    let exam_frequency: Int
}

struct RawSentenceCard: Codable {
    let id: String
    let classical_sentence: String
    let full_english: String
    let source_work: String
    let prev_sentence: String?
    let next_sentence: String?
    let sentence_type: String
    let exam_frequency: Int
}

struct RawWordQuiz: Codable {
    let id: String
    let term: String?
    let char_count: Int?
    let correct: String
    let distractors: [RawDistractor]
    let needs_manual: Bool?
    let note: String?
}

struct RawSentenceQuiz: Codable {
    let id: String
    let classical_sentence: String?
    let correct: String
    let distractors: [RawDistractor]
}

// MARK: - App 内统一卡模型

enum CardType: String, Codable, CaseIterable {
    case word
    case sentence
}

enum CardStatus: String, Codable {
    case new
    case learning
    case mastered
}

struct Distractor: Hashable, Identifiable {
    var id: String { text }
    let text: String
    let errorType: String
    let explanation: String
}

struct QuizItem: Hashable {
    let cardID: String
    let type: CardType
    let correct: String
    let distractors: [Distractor]
    var allOptionTexts: [String] { [correct] + distractors.map(\.text) }
}

/// 运行期统一卡片（词/句两型合一，字段按类型取值）
struct Card: Identifiable, Hashable {
    let id: String
    let type: CardType
    let term: String            // 词卡用；句卡为空串
    let charCount: Int
    let meaning: String         // 词卡 meaning_in_this_sentence；句卡为空串
    let otherSenses: [String]
    let termEnglish: String     // 词卡片段英译；句卡为空串
    let fullEnglish: String
    let classical: String
    let sourceWork: String
    let prevSentence: String?
    let nextSentence: String?
    let errorMode: String       // 词卡 typical_error_mode；句卡为空串
    let sentenceType: String    // 句卡 sentence_type；词卡为空串
    let examFrequency: Int

    /// 默写正确答案：词级 = term_english，句级 = full_english
    var recallAnswer: String { type == .word ? termEnglish : fullEnglish }

    /// 篇名（source_work 去掉括号部分）
    var workName: String {
        if let r = sourceWork.range(of: "（") {
            return String(sourceWork[sourceWork.startIndex..<r.lowerBound])
        }
        return sourceWork
    }
}

// MARK: - 学习状态（引擎 §1）

struct ProgressState {
    var status: CardStatus = .new
    var consecutiveCorrect = 0
    var totalAttempts = 0
    var totalCorrect = 0
    var lastSeenAt: Date? = nil
    var inMistakeBook = false

    /// error_rate（派生，引擎 §1.2）
    var errorRate: Double {
        totalAttempts > 0 ? Double(totalAttempts - totalCorrect) / Double(totalAttempts) : 0
    }

    /// learning 卡是否满足间隔（引擎 §2.4）
    func isDue(now: Date) -> Bool {
        guard status == .learning, let last = lastSeenAt else { return false }
        return now >= last + Self.interval(for: consecutiveCorrect)
    }

    /// MVP 简化阶梯 [10min, 1d, 3d]（引擎 P3）
    static func interval(for consecutiveCorrect: Int) -> TimeInterval {
        switch consecutiveCorrect {
        case 0: return 10 * 60
        case 1: return 1 * 86_400
        default: return 3 * 86_400
        }
    }
}

// MARK: - 错题本条目

struct MistakeEntry: Identifiable, Hashable {
    let cardID: String
    let addedAt: Date
    var id: String { cardID }
}
