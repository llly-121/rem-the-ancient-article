import XCTest

/// ui_spec U1–U13 的自动化验收（跑在云端 Mac 的 iPhone 模拟器上）
///
/// README「六、验收清单」里原本有十项标注「需人眼判断」，对没有 Mac 的 Windows 用户等于永远
/// 无法验证。这些用例把那十项换成可重复执行的断言：
///
/// | 用例 | 对应条款 | 判据 |
/// |---|---|---|
/// | testU1ProgressBarFills          | U1      | 进度条 label「已完成 N / 20 题」的 N 随答题递增 |
/// | testU2RapidTapsOnlyFirstCounts  | U2      | 0.4s 延迟内连点两次选项，只推进一题 |
/// | testU4UnderlineEveryOccurrence  | U4      | term 在原句出现 2 次 → 下划线 2 处 |
/// | testU5HighlightOnlyFirstHit     | U5      | term_english 出现 2 次 → 只高亮 1 处 |
/// | testU6LongSentenceSplits        | U6      | 423 字符长译文 → 拆句且放进可滚动容器 |
/// | testU7RecallDiffMarks           | U7      | 默写全错 → 正确答案行标出缺词 |
/// | testU8HintButtonDisablesAfterUse| U8      | 用过提示 → 提示按钮置灰 |
/// | testU9RecallOnlyTouchesAttempts | U9      | 判分后 attempts +1，status / cc 不动 |
/// | testU10toU12MistakeBookFlow     | U10–U12 | 加入错题本 → 共 1 条 → 左滑删除 → 空状态 |
///
/// U13（无位图 / 断网）与「深色模式无硬编码色」由 `scripts/check_static_acceptance.py` 静态检查，
/// 因为这三项是「代码里不存在某类东西」，跑 UI 反而测不出来。
final class UAcceptanceTests: XCTestCase {

    private var app: XCUIApplication!

    /// 靶卡：必须与 data/*.jsonl 中的事实一致，数据若变动这里的期望值要同步复核
    /// - w0053「天下」：classical 出现 2 次、term_english "the world" 在译文出现 2 次
    /// - s0566《生于忧患》：full_english 423 字符，超过 400 的分句阈值
    private enum Target {
        static let multiOccurrenceWord = "w0053"
        static let longSentence = "s0566"
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
        app = nil
    }

    // MARK: - 启动与通用等待

    @discardableResult
    private func launch(card: String? = nil) -> XCUIApplication {
        let instance = XCUIApplication()
        instance.launchArguments = ["-ui-testing"]
        if let card {
            instance.launchArguments += ["-ui-testing-card", card]
        }
        instance.launch()
        app = instance
        return instance
    }

    @discardableResult
    private func waitUntilGone(_ element: XCUIElement, _ timeout: TimeInterval = 10) -> Bool {
        let exp = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == false"), object: element)
        return XCTWaiter.wait(for: [exp], timeout: timeout) == .completed
    }

    private func attachScene(_ name: String) {
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)

        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "\(name)-层级"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
    }

    /// 按 identifier 精确定位（不限定元素类型：SwiftUI 会把同一 identifier 挂到
    /// otherElements / staticTexts / scrollViews 等不同类型的节点上）
    private func element(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    /// 按 identifier 前缀定位，返回该元素与其标识串去掉前缀后的部分
    private func element(prefix: String) -> (element: XCUIElement, suffix: String) {
        let query = app.descendants(matching: .any)
            .matching(NSPredicate(format: "identifier BEGINSWITH %@", prefix))
        let first = query.firstMatch
        let matched = query.allElementsBoundByIndex.map(\.identifier).first ?? ""
        return (first, String(matched.dropFirst(prefix.count)))
    }

    /// 解析「已完成 3 / 20 题」→ (3, 20)
    private func progress(_ element: XCUIElement) -> (completed: Int, total: Int) {
        let numbers = element.label
            .split(whereSeparator: { !$0.isNumber })
            .compactMap { Int($0) }
        guard numbers.count >= 2 else { return (-1, -1) }
        return (numbers[0], numbers[1])
    }

    /// 从 "missing3_extra1" 这类串里取出某个键后面的整数
    private func number(after key: String, in text: String) -> Int? {
        guard let range = text.range(of: key) else { return nil }
        let tail = text[range.upperBound...]
        let digits = tail.prefix { $0.isNumber }
        return Int(digits)
    }

    // MARK: - 流程辅助

    private func startRound() {
        let start = app.buttons["btn_start_round"]
        XCTAssertTrue(start.waitForExistence(timeout: 40),
                      "首页未出现「开始一轮」（首次启动导入题库可能失败）")
        start.tap()
    }

    /// 在当前选择题页选第一个选项，进答案页后点「下一题」回到下一题的选择页
    private func answerAndAdvance() {
        let option = app.buttons["option_0"]
        XCTAssertTrue(option.waitForExistence(timeout: 20), "选择题页未出现选项")
        option.tap()

        let next = app.buttons["btn_next"]
        XCTAssertTrue(next.waitForExistence(timeout: 20), "点选项后未进入答案页")
        next.tap()
        _ = waitUntilGone(next, 10)
    }

    /// 在单题靶卡轮里：答完唯一一题并进入默写页
    private func enterRecallOnTargetCard() {
        let option = app.buttons["option_0"]
        XCTAssertTrue(option.waitForExistence(timeout: 30), "靶卡未进入选择题页")
        option.tap()

        let next = app.buttons["btn_next"]
        XCTAssertTrue(next.waitForExistence(timeout: 20), "靶卡未进入答案页")
        next.tap()

        XCTAssertTrue(app.buttons["btn_reveal"].waitForExistence(timeout: 20),
                      "单题轮答完后未进入默写页")
    }

    // MARK: - U1 进度条 20 段随答题填充

    func testU1ProgressBarFills() throws {
        launch()
        startRound()

        let bar = element("progress_bar")
        XCTAssertTrue(bar.waitForExistence(timeout: 30), "选择题页没有进度条")
        XCTAssertEqual(progress(bar).completed, 0, "第 1 题时进度条不应有已填充段")
        XCTAssertEqual(progress(bar).total, 20, "进度条总段数应为 20")
        attachScene("U1-第1题进度条")

        for expected in 1...3 {
            answerAndAdvance()
            let current = element("progress_bar")
            XCTAssertTrue(current.waitForExistence(timeout: 20),
                          "答完第 \(expected) 题后进度条消失")
            XCTAssertEqual(progress(current).completed, expected,
                           "答完 \(expected) 题后进度条应填充 \(expected) 段")
            XCTAssertEqual(progress(current).total, 20)
        }
        attachScene("U1-答完3题进度条")
    }

    // MARK: - U2 连点两个选项只有第一个生效

    func testU2RapidTapsOnlyFirstCounts() throws {
        launch()
        startRound()

        let header = element("quiz_header")
        XCTAssertTrue(header.waitForExistence(timeout: 30), "选择题页没有题号")
        XCTAssertEqual(header.label, "第 1/20 题")

        let first = app.buttons["option_0"]
        let second = app.buttons["option_1"]
        XCTAssertTrue(first.waitForExistence(timeout: 20))
        XCTAssertTrue(second.exists, "四选项未齐，无法验证连点")

        // 第一次正常点；第二次用坐标点击绕过 XCUITest 的可点击性检查，
        // 模拟真实手指在 0.4s 延迟窗口内连点第二个选项
        first.tap()
        second.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()

        let next = app.buttons["btn_next"]
        XCTAssertTrue(next.waitForExistence(timeout: 20), "连点后未进入答案页")
        attachScene("U2-连点后答案页")
        next.tap()

        let after = element("quiz_header")
        XCTAssertTrue(after.waitForExistence(timeout: 20), "连点后未回到选择题页")
        XCTAssertEqual(after.label, "第 2/20 题",
                       "连点两次不应跳题（应停在第 2 题，而不是第 3 题）")
    }

    // MARK: - U4 词项下划线（多出现处全标）

    func testU4UnderlineEveryOccurrence() throws {
        launch(card: Target.multiOccurrenceWord)

        let stem = element(prefix: "stem_underline_")
        guard stem.element.waitForExistence(timeout: 40) else {
            attachScene("U4-题面未出现下划线锚点")
            XCTFail("靶卡 w0053 的题面没拿到 stem_underline_* 锚点，"
                    + "说明 term 定位失败或该卡不是词级题；层级见附件")
            return
        }
        XCTAssertEqual(stem.suffix, "2",
                       "「天下」在原句出现 2 次，题面应标 2 处下划线（而非只标首处）")
        attachScene("U4-选择题页下划线")

        app.buttons["option_0"].tap()

        let answerStem = element(prefix: "answer_stem_underline_")
        XCTAssertTrue(answerStem.element.waitForExistence(timeout: 20),
                      "答案页古文区没有下划线锚点")
        XCTAssertEqual(answerStem.suffix, "2",
                       "答案页应与选择题页同口径：出现 2 次就标 2 处")
        attachScene("U4-答案页下划线")
    }

    // MARK: - U5 term_english 只高亮首处

    func testU5HighlightOnlyFirstHit() throws {
        launch(card: Target.multiOccurrenceWord)
        answerOnlyToAnswerPage()

        let highlight = element(prefix: "answer_hl_")
        guard highlight.element.waitForExistence(timeout: 25) else {
            attachScene("U5-英译区未出现高亮锚点")
            XCTFail("答案页英译区没拿到 answer_hl_* 锚点，层级见附件")
            return
        }
        // 格式 answer_hl_{高亮处数}_occ_{片段在原句出现次数}
        XCTAssertEqual(highlight.suffix, "1_occ_2",
                       "「the world」在译文中出现 2 次，应只高亮首处（1），不是全标（2）")
        attachScene("U5-答案页高亮")
    }

    /// 只答到答案页，不继续推进
    private func answerOnlyToAnswerPage() {
        let option = app.buttons["option_0"]
        XCTAssertTrue(option.waitForExistence(timeout: 40), "靶卡未进入选择题页")
        option.tap()
        XCTAssertTrue(app.buttons["btn_next"].waitForExistence(timeout: 20),
                      "靶卡未进入答案页")
    }

    // MARK: - U6 长段级译文分句滚动显示

    func testU6LongSentenceSplits() throws {
        launch(card: Target.longSentence)
        answerOnlyToAnswerPage()

        let scroll = element(prefix: "answer_english_scroll_")
        guard scroll.element.waitForExistence(timeout: 25) else {
            attachScene("U6-英译区未出现分句锚点")
            XCTFail("靶卡 s0566 的英译区没拿到 answer_english_scroll_* 锚点，层级见附件")
            return
        }
        let lineCount = Int(scroll.suffix) ?? 0
        XCTAssertGreaterThanOrEqual(lineCount, 2,
                                    "423 字符的译文超过 400 阈值，应拆成多句滚动显示，实际 \(lineCount) 段")
        attachScene("U6-答案页分句滚动")
    }

    // MARK: - U7 默写对比的删除线/高亮 + U8 提示按钮置灰

    func testU7RecallDiffMarks() throws {
        launch(card: Target.multiOccurrenceWord)
        enterRecallOnTargetCard()

        let editor = app.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 20), "默写页没有输入框")
        editor.tap()
        editor.typeText("zzz qqq")

        app.buttons["btn_reveal"].tap()

        // 正确答案行：默写全错 → 整句都是缺词（标 highlight + 下划线）
        let answerDiff = element(prefix: "diff_answer_")
        guard answerDiff.element.waitForExistence(timeout: 20) else {
            attachScene("U7-未出现正确答案对比行")
            XCTFail("默写对比态没出现 diff_answer_* 锚点，层级见附件")
            return
        }
        let missing = number(after: "missing", in: answerDiff.suffix) ?? 0
        let extra = number(after: "extra", in: answerDiff.suffix) ?? 0
        XCTAssertGreaterThan(missing, 0,
                             "默写全错时正确答案行应标出缺词（高亮+下划线），实际 missing=\(missing)")
        XCTAssertEqual(extra, 0, "正确答案行只会有缺词，不应出现多写词")

        // 你的默写行：多写的词要打删除线
        let inputDiff = element(prefix: "diff_input_")
        XCTAssertTrue(inputDiff.element.waitForExistence(timeout: 10),
                      "默写对比态没出现 diff_input_* 锚点")
        XCTAssertGreaterThan(number(after: "extra", in: inputDiff.suffix) ?? 0, 0,
                             "「你的默写」里多写的词应打删除线")
        attachScene("U7-默写对比")
    }

    func testU8HintButtonDisablesAfterUse() throws {
        launch(card: Target.multiOccurrenceWord)
        enterRecallOnTargetCard()

        let hint = app.buttons["btn_hint"]
        XCTAssertTrue(hint.waitForExistence(timeout: 20), "默写页没有提示按钮")
        XCTAssertTrue(hint.isEnabled, "提示按钮初始应可点")

        hint.tap()

        XCTAssertFalse(hint.isEnabled, "用过提示后按钮应置灰，不能重复使用")
        attachScene("U8-提示已置灰")
    }

    // MARK: - U9 默写 10 题只动 total_attempts / total_correct

    func testU9RecallOnlyTouchesAttempts() throws {
        launch(card: Target.multiOccurrenceWord)
        enterRecallOnTargetCard()

        let probeBefore = readProbe()
        XCTAssertNotNil(probeBefore, "没读到 recall_probe（-ui-testing 探针未生效）")

        // 不做任何输入直接看答案 → 词级必判错，只应写 total_attempts
        app.buttons["btn_reveal"].tap()

        let probeAfter = readProbe()
        XCTAssertNotNil(probeAfter, "判分后探针消失")

        guard let before = probeBefore, let after = probeAfter else { return }
        XCTAssertEqual(after.status, before.status,
                       "默写不应改变卡片状态（应始终 learning）")
        XCTAssertEqual(after.consecutiveCorrect, before.consecutiveCorrect,
                       "默写不应改变 consecutive_correct（否则会把卡推向 mastered）")
        XCTAssertEqual(after.attempts, before.attempts + 1,
                       "默写判分应让 total_attempts 恰好 +1")
        attachScene("U9-默写判分后")
    }

    private func readProbe()
        -> (status: String, consecutiveCorrect: Int, attempts: Int, correct: Int)? {
        // identifier 形如 recall_header_statuslearning_cc1_att2_ok1
        let header = element(prefix: "recall_header")
        guard header.element.exists else { return nil }
        let tokens = header.suffix.components(separatedBy: "_").filter { !$0.isEmpty }
        guard tokens.count >= 4 else { return nil }

        func value(_ prefix: String) -> Int {
            guard let token = tokens.first(where: { $0.hasPrefix(prefix) }) else { return -1 }
            return Int(token.dropFirst(prefix.count)) ?? -1
        }
        let statusToken = tokens.first { $0.hasPrefix("status") } ?? ""
        return (String(statusToken.dropFirst("status".count)),
                value("cc"), value("att"), value("ok"))
    }

    // MARK: - U10–U12 错题本：加入 / 计数 / 筛选入口 / 左滑删除

    func testU10toU12MistakeBookFlow() throws {
        launch()
        startRound()

        // U10：答案页把当前题加入错题本
        let option = app.buttons["option_0"]
        XCTAssertTrue(option.waitForExistence(timeout: 30), "选择题页未出现选项")
        option.tap()

        let add = app.buttons["btn_add_mistake"]
        XCTAssertTrue(add.waitForExistence(timeout: 20), "答案页没有「加入错题本」按钮")
        add.tap()

        XCTAssertTrue(app.staticTexts["已加入错题本"].waitForExistence(timeout: 5),
                      "加入错题本后没出现 Toast 反馈")
        XCTAssertFalse(add.isEnabled, "已加入后按钮应置灰，避免重复加入")
        attachScene("U10-已加入错题本")

        // 退出本轮，回首页（第 2 题页面的「退出」→ 确认）
        let next = app.buttons["btn_next"]
        XCTAssertTrue(next.waitForExistence(timeout: 20))
        next.tap()
        _ = waitUntilGone(next, 10)

        let exitButton = app.buttons["退出"]
        XCTAssertTrue(exitButton.waitForExistence(timeout: 20), "选择题页没有「退出」按钮")
        exitButton.tap()
        let confirmExit = app.alerts.buttons["退出"]
        XCTAssertTrue(confirmExit.waitForExistence(timeout: 10), "退出确认弹窗未出现")
        confirmExit.tap()

        XCTAssertTrue(app.buttons["btn_start_round"].waitForExistence(timeout: 25),
                      "退出后没回到首页")

        // U11 / U12：错题本计数与筛选入口
        let mistakeTab = app.tabBars.buttons["错题本"]
        XCTAssertTrue(mistakeTab.waitForExistence(timeout: 15), "底部 Tab 里没有「错题本」")
        mistakeTab.tap()

        XCTAssertTrue(app.staticTexts["共 1 条"].waitForExistence(timeout: 15),
                      "加入一道错题后应显示「共 1 条」")
        XCTAssertTrue(app.buttons["全部"].exists || app.staticTexts["全部"].exists,
                      "错题本缺少筛选入口（默认「全部」）")
        attachScene("U11-错题本1条")

        // 左滑删除 → 回到空状态
        let firstCell = app.cells.firstMatch
        XCTAssertTrue(firstCell.waitForExistence(timeout: 10), "错题本列表没有单元格")
        firstCell.swipeLeft()

        let deleteButton = app.buttons["删除"]
        XCTAssertTrue(deleteButton.waitForExistence(timeout: 10), "左滑没有出现删除按钮")
        deleteButton.tap()

        XCTAssertTrue(app.staticTexts["还没有错题，继续做题吧"].waitForExistence(timeout: 15),
                      "删除后应回到错题本空状态")
        attachScene("U12-错题本已清空")
    }
}
