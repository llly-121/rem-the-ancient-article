import SwiftUI

/// 轮次流程（ui_spec §6）：
/// QuizView(1…20) ──select→ AnswerView ──下一题→ QuizView / RecallView(1…10) → RecallSummary → 关闭
enum FlowStep: Hashable {
    case answer
    case recall
    case summary
}

struct RoundFlow: View {
    @Environment(Library.self) private var library
    @Environment(ProgressStore.self) private var store
    @Environment(AppFlow.self) private var flow

    let session: RoundSession
    @State private var path: [FlowStep] = []

    var body: some View {
        // 必须用 NavigationStack(path:) 绑定 path，否则 path.append 不会真的 push 页面
        NavigationStack(path: $path) {
            QuizView(session: session, path: $path)
                .navigationDestination(for: FlowStep.self) { step in
                    switch step {
                    case .answer:
                        AnswerView(session: session, path: $path)
                    case .recall:
                        RecallView(session: session, path: $path)
                    case .summary:
                        RecallSummaryView(session: session, path: $path)
                    }
                }
        }
        .background(Theme.bg.ignoresSafeArea())
    }
}
