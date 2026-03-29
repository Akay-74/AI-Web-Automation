import Link from "next/link";

export default function HomePage() {
    const exampleTasks = [
        "Find the cheapest RTX 4060 laptop on Amazon",
        "Collect ML internship listings from LinkedIn",
        "Extract top AI news headlines",
        "Compare prices of iPhone 15 across stores",
    ];

    return (
        <div className="max-w-4xl mx-auto">
            {/* Hero Section */}
            <div className="text-center py-16">
                <h1 className="text-5xl font-bold mb-4">
                    <span className="gradient-text">AI Web Automation</span>
                </h1>
                <p className="text-xl text-slate-400 mb-8 max-w-2xl mx-auto">
                    Tell the AI what you want. It opens a browser, navigates websites,
                    extracts data, and returns structured results — all autonomously.
                </p>
                <Link
                    href="/tasks/new"
                    className="inline-flex items-center gap-2 px-8 py-3 rounded-lg
                     bg-brand-600 hover:bg-brand-500 text-white font-semibold
                     transition-all duration-200 glow"
                >
                    ✨ Create New Task
                </Link>
            </div>

            {/* Example Tasks */}
            <div className="mb-12">
                <h2 className="text-lg font-semibold text-slate-300 mb-4">Try these examples</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {exampleTasks.map((task, i) => (
                        <Link
                            key={i}
                            href={`/tasks/new?goal=${encodeURIComponent(task)}`}
                            className="glass-card p-4 hover:border-brand-500/50 transition-all
                         duration-200 cursor-pointer group"
                        >
                            <p className="text-slate-300 group-hover:text-white transition-colors">
                                &ldquo;{task}&rdquo;
                            </p>
                        </Link>
                    ))}
                </div>
            </div>

            {/* How It Works */}
            <div className="glass-card p-8">
                <h2 className="text-2xl font-bold mb-6 gradient-text">How It Works</h2>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {[
                        { step: "1", title: "Describe", desc: "Tell the AI your goal in plain English" },
                        { step: "2", title: "Plan", desc: "AI creates a step-by-step browser action plan" },
                        { step: "3", title: "Execute", desc: "Agent controls a browser autonomously" },
                        { step: "4", title: "Results", desc: "Structured data returned to your dashboard" },
                    ].map((item) => (
                        <div key={item.step} className="text-center">
                            <div className="w-10 h-10 rounded-full bg-brand-600/20 text-brand-400
                              flex items-center justify-center text-lg font-bold mx-auto mb-3">
                                {item.step}
                            </div>
                            <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                            <p className="text-sm text-slate-400">{item.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
