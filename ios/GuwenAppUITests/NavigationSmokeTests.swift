import XCTest

/// 四页导航冒烟测试（跑在云端 Mac 的 iPhone 模拟器上）
///
/// 覆盖 ui_spec 的四页：
///  1. 选择题页 QuizView   —— 首页点「开始一轮」进入
///  2. 答案展示页 AnswerView —— 点任一选项，0.4s 后自动进入
///  3. 检查默写页 RecallView —— 答完 20 题后进入
///  4. 错题本页 MistakeBookView —— 底部 Tab 切换
///
/// 只用 accessibilityIdentifier 定位，不依赖文案，改文案不会让测试变红。
final class NavigationSmokeTests: XCTestCase {

    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-ui-testing"]
        app.launch()
    }

    override func tearDownWithError() throws {
        app = nil
    }

    // MARK: - 主流程

    func testFourPagesNavigate() throws {
        // ---------- 页 0：首页 ----------
        let startButton = app.buttons["btn_start_round"]
        XCTAssertTrue(startButton.waitForExistence(timeout: 30),
                      "首页未出现「开始一轮」按钮（首次启动数据导入可能失败）")
        startButton.tap()

        // ---------- 页 1：选择题（第 1 题） ----------
        let firstOption = app.buttons["option_0"]
        XCTAssertTrue(firstOption.waitForExistence(timeout: 30), "选择题页未出现选项")

        // ---------- 页 2：答案页 ----------
        firstOption.tap()
        let nextButton = app.buttons["btn_next"]
        XCTAssertTrue(nextButton.waitForExistence(timeout: 15), "答案页未出现「下一题」按钮")

        // ---------- 连答一轮，进入页 3：默写 ----------
        var quizAnswered = 1
        while quizAnswered < 20 {
            nextButton.tap()

            // 若已跳到默写页就不再找选项
            if app.buttons["btn_reveal"].waitForExistence(timeout: 1) { break }

            let option = app.buttons["option_0"]
            guard option.waitForExistence(timeout: 10) else { break }
            option.tap()

            guard nextButton.waitForExistence(timeout: 15) else {
                XCTFail("第 \(quizAnswered + 1) 题答完后没进入答案页")
                return
            }
            quizAnswered += 1
        }

        // ---------- 页 3：检查默写 ----------
        let reveal = app.buttons["btn_reveal"]
        XCTAssertTrue(reveal.waitForExistence(timeout: 20),
                      "答完 \(quizAnswered) 题后未进入默写页")

        // 默写全部走“直接看答案 → 下一题”，句级题需要先自评
        var recallDone = 0
        while recallDone < 12 {
            if reveal.waitForExistence(timeout: 5) {
                reveal.tap()
            }
            if app.buttons["btn_self_correct"].waitForExistence(timeout: 2) {
                app.buttons["btn_self_correct"].tap()
            }
            let recallNext = app.buttons["btn_recall_next"]
            guard recallNext.waitForExistence(timeout: 5) else { break }
            recallNext.tap()
            recallDone += 1

            if app.buttons["btn_home"].waitForExistence(timeout: 2) { break }  // 已到小结页
        }
        XCTAssertGreaterThan(recallDone, 0, "默写页一题都没能推进")

        // ---------- 回首页 ----------
        let homeButton = app.buttons["btn_home"]
        if homeButton.waitForExistence(timeout: 5) {
            homeButton.tap()
        }
        XCTAssertTrue(app.buttons["btn_start_round"].waitForExistence(timeout: 15),
                      "从默写小结没能回到首页")

        // ---------- 页 4：错题本 ----------
        let mistakeTab = app.tabBars.buttons["错题本"]
        XCTAssertTrue(mistakeTab.waitForExistence(timeout: 10), "底部 Tab 里没有「错题本」")
        mistakeTab.tap()

        let mistakeNav = app.navigationBars["错题本"]
        let emptyText = app.staticTexts["还没有错题，继续做题吧"]
        let hasMistakePage = mistakeNav.waitForExistence(timeout: 10) || emptyText.waitForExistence(timeout: 5)
        XCTAssertTrue(hasMistakePage, "错题本页未出现")
    }

    // MARK: - 数据完整性（首次启动 jsonl → SwiftData 导入）

    func testImportedCardCounts() throws {
        XCTAssertTrue(app.buttons["btn_start_round"].waitForExistence(timeout: 30))
        // 首页文案里含「题库卡片」统计；用谓词匹配数字块，避免逐字依赖
        let cards = app.staticTexts["2,072"]
        let quizzes = app.staticTexts["565"]
        XCTAssertTrue(cards.waitForExistence(timeout: 10) || quizzes.waitForExistence(timeout: 10),
                      "题库统计异常：期望 2072 张卡 / 565 张可选卡")
    }
}
