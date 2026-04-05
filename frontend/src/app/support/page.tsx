"use client";

import { useState } from "react";
import Link from "next/link";

const faqs = [
    {
        q: "How do I create a task?",
        a: "Navigate to Neural Flow (New Task) from the sidebar. Enter your automation goal in natural language — e.g. \"Find the cheapest RTX 4060 laptop on Amazon\". Hit Deploy Kinetic Agent and the AI will handle everything from browser navigation to data extraction."
    },
    {
        q: "What kind of tasks can the agent handle?",
        a: "The agent excels at: price comparison across e-commerce sites, lead/data extraction, form filling, web scraping structured data, job searching, and content aggregation. It uses a headless browser (Playwright) with AI-powered decision making."
    },
    {
        q: "How long does a task take?",
        a: "Most tasks complete within 60–180 seconds depending on complexity. You can monitor progress in real-time on the Task Monitor page, including live browser screenshots and step-by-step execution logs."
    },
    {
        q: "Why did my task fail?",
        a: "Common causes: the target website blocks automation, the page structure changed, or the task goal was ambiguous. Check the Terminal logs for detailed error messages. Try rephrasing your goal to be more specific."
    },
    {
        q: "How does the Value Score work?",
        a: "The Value Score is a 0–100 rating that shows how a result's price compares to all other results. 100 = cheapest, 0 = most expensive. The 'Top Match' badge is awarded to the cheapest verified result."
    },
    {
        q: "Can I export my results?",
        a: "Yes — on the Task Monitor page, click 'Raw Logs' to see the full JSON data. You can copy this data or view it in the Terminal page. The API also provides a GET /api/tasks/{id}/results endpoint."
    },
];

const systemInfo = [
    { label: "Engine", value: "Kinetic AI v4.2" },
    { label: "Model", value: "GPT-4o-mini" },
    { label: "Browser", value: "Playwright 1.40" },
    { label: "Backend", value: "FastAPI + SQLAlchemy" },
    { label: "Frontend", value: "Next.js 14" },
    { label: "Database", value: "SQLite (local) / PostgreSQL (prod)" },
];

const shortcuts = [
    { keys: "Ctrl + N", action: "New Task" },
    { keys: "Ctrl + H", action: "Task History" },
    { keys: "Ctrl + T", action: "Terminal" },
    { keys: "Ctrl + A", action: "Analytics" },
];

export default function SupportPage() {
    const [openFaq, setOpenFaq] = useState<number | null>(null);

    return (
        <div className="min-h-screen p-8 relative overflow-hidden">
            <div className="ambient-glow w-72 h-72 bg-[rgba(198,198,198,0.02)] top-20 right-10" />

            <div className="max-w-4xl mx-auto relative z-10">
                {/* Header */}
                <div className="mb-10 anim-fade-up">
                    <h1 className="text-3xl font-extrabold tracking-tight gradient-text mb-2">Support</h1>
                    <p className="text-sm text-[#a8a7a6]">Documentation, system information, and frequently asked questions</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-10 anim-stagger">
                    {/* Quick Actions */}
                    <Link href="/tasks/new" className="obsidian-card p-5 group cursor-pointer">
                        <span className="material-symbols-rounded text-2xl text-[#888787] group-hover:text-[#d4d4d4] transition-colors mb-3 block">bolt</span>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-1">Create New Task</h3>
                        <p className="text-[11px] text-[#888787]">Deploy a kinetic agent with a natural language objective</p>
                    </Link>
                    <Link href="/terminal" className="obsidian-card p-5 group cursor-pointer">
                        <span className="material-symbols-rounded text-2xl text-[#888787] group-hover:text-[#d4d4d4] transition-colors mb-3 block">terminal</span>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-1">Open Terminal</h3>
                        <p className="text-[11px] text-[#888787]">View live system logs and run diagnostic commands</p>
                    </Link>
                    <Link href="/analytics" className="obsidian-card p-5 group cursor-pointer">
                        <span className="material-symbols-rounded text-2xl text-[#888787] group-hover:text-[#d4d4d4] transition-colors mb-3 block">monitoring</span>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-1">View Analytics</h3>
                        <p className="text-[11px] text-[#888787]">Check performance metrics and activity charts</p>
                    </Link>
                </div>

                {/* FAQ */}
                <div className="mb-10 anim-fade-up" style={{ animationDelay: "0.1s" }}>
                    <h2 className="text-lg font-extrabold text-[#f0eeed] mb-4 flex items-center gap-2">
                        <span className="material-symbols-rounded text-lg text-[#888787]">quiz</span>
                        Frequently Asked Questions
                    </h2>
                    <div className="space-y-1.5">
                        {faqs.map((faq, i) => (
                            <div key={i} className="obsidian-card overflow-hidden">
                                <button
                                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                                    className="w-full flex items-center justify-between px-5 py-3.5 text-left"
                                >
                                    <span className="text-sm font-semibold text-[#d4d3d2]">{faq.q}</span>
                                    <span className="material-symbols-rounded text-[#888787] transition-transform text-lg"
                                        style={{ transform: openFaq === i ? "rotate(180deg)" : "" }}>
                                        expand_more
                                    </span>
                                </button>
                                {openFaq === i && (
                                    <div className="px-5 pb-4 anim-fade-up">
                                        <p className="text-[13px] text-[#a8a7a6] leading-relaxed">{faq.a}</p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {/* System Info */}
                    <div className="glass-card p-6 anim-fade-up" style={{ animationDelay: "0.15s" }}>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-4 flex items-center gap-2">
                            <span className="material-symbols-rounded text-base text-[#888787]">info</span>
                            System Information
                        </h3>
                        <div className="space-y-2.5">
                            {systemInfo.map(s => (
                                <div key={s.label} className="flex items-center justify-between">
                                    <span className="text-xs text-[#888787] font-semibold">{s.label}</span>
                                    <span className="text-xs text-[#d4d3d2] font-mono">{s.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* API Reference */}
                    <div className="glass-card p-6 anim-fade-up" style={{ animationDelay: "0.2s" }}>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-4 flex items-center gap-2">
                            <span className="material-symbols-rounded text-base text-[#888787]">api</span>
                            API Reference
                        </h3>
                        <div className="space-y-2 font-mono text-[11px]">
                            {[
                                { method: "POST", path: "/api/tasks", desc: "Create task" },
                                { method: "GET", path: "/api/tasks", desc: "List tasks" },
                                { method: "GET", path: "/api/tasks/:id", desc: "Get task" },
                                { method: "POST", path: "/api/tasks/:id/start", desc: "Start task" },
                                { method: "GET", path: "/api/tasks/:id/logs", desc: "Get logs" },
                                { method: "GET", path: "/api/tasks/:id/results", desc: "Get results" },
                                { method: "WS", path: "/ws/tasks/:id", desc: "Live stream" },
                            ].map(e => (
                                <div key={e.path + e.method} className="flex items-center gap-2">
                                    <span className={`shrink-0 w-10 text-[9px] font-bold uppercase tracking-wider ${e.method === "POST" ? "text-[#4ade80]" :
                                            e.method === "WS" ? "text-[#fbbf24]" : "text-[#60a5fa]"
                                        }`}>{e.method}</span>
                                    <span className="text-[#d4d3d2] flex-1">{e.path}</span>
                                    <span className="text-[#888787] text-[10px]">{e.desc}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
