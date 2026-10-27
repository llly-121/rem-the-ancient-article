import Foundation
import SwiftData

// MARK: - SwiftData 实体（首次启动由 bundle 内 jsonl 导入）

@Model
final class WordCardEntity {
    @Attribute(.unique) var id: String
    var term: String
    var charCount: Int
    var termType: String
    var meaning: String
    var otherSensesJSON: String   // [String] 的 JSON
    var termEnglish: String
    var fullEnglish: String
    var classical: String
    var sourceWork: String
    var prevSentence: String
    var nextSentence: String
    var errorMode: String
    var examFrequency: Int

    init(id: String, term: String, charCount: Int, termType: String, meaning: String,
         otherSensesJSON: String, termEnglish: String, fullEnglish: String, classical: String,
         sourceWork: String, prevSentence: String, nextSentence: String, errorMode: String,
         examFrequency: Int) {
        self.id = id
        self.term = term
        self.charCount = charCount
        self.termType = termType
        self.meaning = meaning
        self.otherSensesJSON = otherSensesJSON
        self.termEnglish = termEnglish
        self.fullEnglish = fullEnglish
        self.classical = classical
        self.sourceWork = sourceWork
        self.prevSentence = prevSentence
        self.nextSentence = nextSentence
        self.errorMode = errorMode
        self.examFrequency = examFrequency
    }
}

@Model
final class SentenceCardEntity {
    @Attribute(.unique) var id: String
    var classical: String
    var fullEnglish: String
    var sourceWork: String
    var prevSentence: String
    var nextSentence: String
    var sentenceType: String
    var examFrequency: Int

    init(id: String, classical: String, fullEnglish: String, sourceWork: String,
         prevSentence: String, nextSentence: String, sentenceType: String, examFrequency: Int) {
        self.id = id
        self.classical = classical
        self.fullEnglish = fullEnglish
        self.sourceWork = sourceWork
        self.prevSentence = prevSentence
        self.nextSentence = nextSentence
        self.sentenceType = sentenceType
        self.examFrequency = examFrequency
    }
}

@Model
final class WordQuizEntity {
    @Attribute(.unique) var cardID: String
    var correct: String
    var distractorsJSON: String   // [Distractor] 的 JSON

    init(cardID: String, correct: String, distractorsJSON: String) {
        self.cardID = cardID
        self.correct = correct
        self.distractorsJSON = distractorsJSON
    }
}

@Model
final class SentenceQuizEntity {
    @Attribute(.unique) var cardID: String
    var correct: String
    var distractorsJSON: String

    init(cardID: String, correct: String, distractorsJSON: String) {
        self.cardID = cardID
        self.correct = correct
        self.distractorsJSON = distractorsJSON
    }
}

// MARK: - 学习状态与错题本（独立持久化，与只读题库解耦）

@Model
final class ProgressRecord {
    @Attribute(.unique) var id: String
    var typeRaw: String
    var statusRaw: String
    var consecutiveCorrect: Int
    var totalAttempts: Int
    var totalCorrect: Int
    var lastSeenAt: Date?
    var inMistakeBook: Bool

    init(id: String, typeRaw: String, statusRaw: String, consecutiveCorrect: Int,
         totalAttempts: Int, totalCorrect: Int, lastSeenAt: Date?, inMistakeBook: Bool) {
        self.id = id
        self.typeRaw = typeRaw
        self.statusRaw = statusRaw
        self.consecutiveCorrect = consecutiveCorrect
        self.totalAttempts = totalAttempts
        self.totalCorrect = totalCorrect
        self.lastSeenAt = lastSeenAt
        self.inMistakeBook = inMistakeBook
    }
}

@Model
final class MistakeRecord {
    @Attribute(.unique) var cardID: String
    var addedAt: Date

    init(cardID: String, addedAt: Date) {
        self.cardID = cardID
        self.addedAt = addedAt
    }
}

/// SwiftData 容器注册的全部模型
enum AppSchema {
    static var models: [any PersistentModel.Type] {
        [WordCardEntity.self, SentenceCardEntity.self,
         WordQuizEntity.self, SentenceQuizEntity.self,
         ProgressRecord.self, MistakeRecord.self]
    }
}
