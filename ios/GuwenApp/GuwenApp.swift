import SwiftUI
import SwiftData

@main
struct GuwenApp: App {
    private let container: ModelContainer
    @State private var library: Library
    @State private var store: ProgressStore
    @State private var flow = AppFlow()

    init() {
        do {
            container = try ModelContainer(for: AppSchema.models)
        } catch {
            fatalError("无法创建 SwiftData 容器: \(error)")
        }
        let context = ModelContext(container)
        context.autosaveEnabled = true
        LibraryImporter.importIfNeeded(context)          // 首次启动：bundle jsonl → SwiftData
        let lib = Library(context: context)
        let progressStore = ProgressStore(context: context)
        progressStore.libraryRef = lib
        _library = State(initialValue: lib)
        _store = State(initialValue: progressStore)
    }

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environment(library)
                .environment(store)
                .environment(flow)
                .modelContainer(container)
                .tint(Theme.accent)
                .background(Theme.bg)
        }
    }
}

// MARK: - 全局流程（ui_spec §6：RoundFlow 独立于 Tab）

@Observable
final class AppFlow {
    var session: RoundSession?

    /// 开始一轮常规 20 题
    func startRound(library: Library, store: ProgressStore, wordRatio: Double) {
        let plan = Scheduler.pickRound(now: Date(), wordRatio: wordRatio,
                                       library: library, store: store)
        let session = RoundSession(mode: .normal, round: plan.round, fillIDs: plan.fillIDs)
        session.quizProvider = { [weak library] id in library?.quizzes[id] }
        self.session = session
    }

    /// 错题本「再练一次」：单题小测（P8：计 attempts/correct，不动 cc/status）
    func startRetrain(card: Card, library: Library) {
        let session = RoundSession(mode: .retrain, round: [card])
        session.quizProvider = { [weak library] id in library?.quizzes[id] }
        self.session = session
    }

    func endSession() {
        session = nil
    }
}

struct RootTabView: View {
    @Environment(AppFlow.self) private var flow

    var body: some View {
        TabView {
            HomeView()
                .tabItem { Label("今日", systemImage: "text.book.closed") }
            MistakeBookView()
                .tabItem { Label("错题本", systemImage: "rectangle.stack") }
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { flow.session != nil },
                set: { if !$0 { flow.session = nil } }
            )
        ) {
            if let session = flow.session {
                RoundFlow(session: session)
            }
        }
    }
}
