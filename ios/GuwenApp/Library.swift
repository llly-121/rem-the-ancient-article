import Foundation
import Observation
import SwiftData

/// 首次启动：把 bundle 内四个 jsonl 导入 SwiftData（幂等——非空且版本一致即跳过）
enum LibraryImporter {

    /// 数据版本号。题库 jsonl 一改就必须递增，否则老用户会一直用旧数据：
    /// 「非空即跳过」保证了幂等，但也挡住了内容更新。
    /// v2：干扰项归一化去重（消除 58 条只差冠词/大小写的假选项）＋ 诸侯/左右/兴 补人工干扰项。
    /// v3：句级干扰项重做——删除 191 条崩坏项（如「曰」被换成 "They would surely say" 导致
    ///     "His fellow villagers They would surely say:"），102 题改为人工手写，269 题全部可出题。
    private static let dataVersion = "4"
    private static let versionKey = "library.dataVersion"

    static func importIfNeeded(_ context: ModelContext) {
        let wordCount = (try? context.fetchCount(FetchDescriptor<WordCardEntity>())) ?? 0
        let sentenceCount = (try? context.fetchCount(FetchDescriptor<SentenceCardEntity>())) ?? 0
        let storedVersion = UserDefaults.standard.string(forKey: versionKey)

        if wordCount > 0, sentenceCount > 0, storedVersion == dataVersion { return }

        // 版本不一致 → 先清空再重导，否则会与旧记录主键冲突
        if wordCount > 0 || sentenceCount > 0 {
            try? context.delete(model: WordCardEntity.self)
            try? context.delete(model: SentenceCardEntity.self)
            try? context.delete(model: WordQuizEntity.self)
            try? context.delete(model: SentenceQuizEntity.self)
            try? context.save()
        }

        importWordCards(context)
        importSentenceCards(context)
        importWordQuiz(context)
        importSentenceQuiz(context)
        try? context.save()
        UserDefaults.standard.set(dataVersion, forKey: versionKey)
    }

    // MARK: - bundle 读取

    private static func loadLines(resource: String) -> [String] {
        guard let url = Bundle.main.url(forResource: resource, withExtension: "jsonl"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return [] }
        return raw.split(separator: "\n", omittingEmptySubsequences: true)
            .map { String($0).trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
    }

    private static func jsonString<T: Encodable>(_ value: T) -> String {
        guard let data = try? JSONEncoder().encode(value) else { return "[]" }
        return String(data: data, encoding: .utf8) ?? "[]"
    }

    // MARK: - 各文件导入

    private static func importWordCards(_ context: ModelContext) {
        for line in loadLines(resource: "word_cards") {
            guard let data = line.data(using: .utf8),
                  let raw = try? JSONDecoder().decode(RawWordCard.self, from: data) else { continue }
            context.insert(WordCardEntity(
                id: raw.id, term: raw.term, charCount: raw.char_count, termType: raw.term_type,
                meaning: raw.meaning_in_this_sentence,
                otherSensesJSON: jsonString(raw.other_senses ?? []),
                termEnglish: raw.term_english, fullEnglish: raw.full_english,
                classical: raw.classical_sentence, sourceWork: raw.source_work,
                prevSentence: raw.prev_sentence ?? "", nextSentence: raw.next_sentence ?? "",
                errorMode: raw.typical_error_mode, examFrequency: raw.exam_frequency))
        }
    }

    private static func importSentenceCards(_ context: ModelContext) {
        for line in loadLines(resource: "sentence_cards") {
            guard let data = line.data(using: .utf8),
                  let raw = try? JSONDecoder().decode(RawSentenceCard.self, from: data) else { continue }
            context.insert(SentenceCardEntity(
                id: raw.id, classical: raw.classical_sentence, fullEnglish: raw.full_english,
                sourceWork: raw.source_work, prevSentence: raw.prev_sentence ?? "",
                nextSentence: raw.next_sentence ?? "", sentenceType: raw.sentence_type,
                examFrequency: raw.exam_frequency))
        }
    }

    private static func importWordQuiz(_ context: ModelContext) {
        for line in loadLines(resource: "word_quiz") {
            guard let data = line.data(using: .utf8),
                  let raw = try? JSONDecoder().decode(RawWordQuiz.self, from: data) else { continue }
            context.insert(WordQuizEntity(
                cardID: raw.id, correct: raw.correct,
                distractorsJSON: jsonString(raw.distractors.map { Distractor(
                    text: $0.text, errorType: $0.error_type, explanation: $0.explanation) })))
        }
    }

    private static func importSentenceQuiz(_ context: ModelContext) {
        for line in loadLines(resource: "sentence_quiz") {
            guard let data = line.data(using: .utf8),
                  let raw = try? JSONDecoder().decode(RawSentenceQuiz.self, from: data) else { continue }
            context.insert(SentenceQuizEntity(
                cardID: raw.id, correct: raw.correct,
                distractorsJSON: jsonString(raw.distractors.map { Distractor(
                    text: $0.text, errorType: $0.error_type, explanation: $0.explanation) })))
        }
    }
}

/// 只读题库：启动时从 SwiftData 装入内存，供引擎与视图高速查询
@Observable
final class Library {
    private(set) var cards: [String: Card] = [:]
    private(set) var quizzes: [String: QuizItem] = [:]
    private(set) var cardCount = 0

    init(context: ModelContext) {
        load(context: context)
    }

    func load(context: ModelContext) {
        var result: [String: Card] = [:]

        let wordDesc = FetchDescriptor<WordCardEntity>()
        if let words = try? context.fetch(wordDesc) {
            for e in words {
                let senses: [String] = decodeJSON(e.otherSensesJSON) ?? []
                result[e.id] = Card(
                    id: e.id, type: .word, term: e.term, charCount: e.charCount,
                    meaning: e.meaning, otherSenses: senses,
                    termEnglish: e.termEnglish, fullEnglish: e.fullEnglish,
                    classical: e.classical, sourceWork: e.sourceWork,
                    prevSentence: e.prevSentence.isEmpty ? nil : e.prevSentence,
                    nextSentence: e.nextSentence.isEmpty ? nil : e.nextSentence,
                    errorMode: e.errorMode, sentenceType: "", examFrequency: e.examFrequency)
            }
        }

        let sentDesc = FetchDescriptor<SentenceCardEntity>()
        if let sentences = try? context.fetch(sentDesc) {
            for e in sentences {
                result[e.id] = Card(
                    id: e.id, type: .sentence, term: "", charCount: 0,
                    meaning: "", otherSenses: [],
                    termEnglish: "", fullEnglish: e.fullEnglish,
                    classical: e.classical, sourceWork: e.sourceWork,
                    prevSentence: e.prevSentence.isEmpty ? nil : e.prevSentence,
                    nextSentence: e.nextSentence.isEmpty ? nil : e.nextSentence,
                    errorMode: "", sentenceType: e.sentenceType, examFrequency: e.examFrequency)
            }
        }
        cards = result
        cardCount = result.count

        // 只有凑满 3 个干扰项的题才能进抽题池：UI 是固定「正确答案 + 3 个干扰项」四选项，
        // 少一项就会破版。句级 69 句特殊句式（判断/疑问/状语后置）的干扰项需要人工补写，
        // 在补上前不让它们出题——宁可少出题，也不出残题。
        var quiz: [String: QuizItem] = [:]
        let wq = FetchDescriptor<WordQuizEntity>()
        if let wordQuiz = try? context.fetch(wq) {
            for e in wordQuiz {
                let ds: [Distractor] = decodeJSON(e.distractorsJSON) ?? []
                guard ds.count >= 3 else { continue }
                quiz[e.cardID] = QuizItem(cardID: e.cardID, type: .word,
                                          correct: e.correct, distractors: ds)
            }
        }
        let sq = FetchDescriptor<SentenceQuizEntity>()
        if let sentenceQuiz = try? context.fetch(sq) {
            for e in sentenceQuiz {
                let ds: [Distractor] = decodeJSON(e.distractorsJSON) ?? []
                guard ds.count >= 3 else { continue }
                quiz[e.cardID] = QuizItem(cardID: e.cardID, type: .sentence,
                                          correct: e.correct, distractors: ds)
            }
        }
        quizzes = quiz
    }

    private func decodeJSON<T: Decodable>(_ string: String) -> T? {
        guard let data = string.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }
}
