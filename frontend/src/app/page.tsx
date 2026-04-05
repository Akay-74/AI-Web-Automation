"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Task } from "@/lib/api";

function AnimatedCounter({ target, suffix = "" }: { target: number; suffix?: string }) {
    const [count, setCount] = useState(0);
    useEffect(() => {
        let start = 0;
        const duration = 1200;
        const step = Math.ceil(target / (duration / 16));
        const timer = setInterval(() => {
            start += step;
            if (start >= target) { setCount(target); clearInterval(timer); }
            else setCount(start);
        }, 16);
        return () => clearInterval(timer);
    }, [target]);
    return <>{count.toLocaleString()}{suffix}</>;
}

export default function DashboardPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.listTasks().then(res => { setTasks(res.tasks); setLoading(false); }).catch(() => setLoading(false));
    }, []);

    const completed = tasks.filter(t => t.status === "completed").length;
    const running = tasks.filter(t => t.status === "running").length;

    const stats = [
        { label: "Cycles Executed", value: tasks.length, icon: "cycle" },
        { label: "Process Accuracy", value: tasks.length > 0 ? Math.round((completed / tasks.length) * 100) : 99, suffix: "%", icon: "verified" },
        { label: "Active Agents", value: running || 1, icon: "sensors" },
    ];

    const templates = [
        { title: "Market Arbitrage Scraper", desc: "Real-time valuation comparison across e-commerce", goal: "Find the cheapest RTX 4060 laptop on Amazon and compare prices" },
        { title: "Neural Lead Extraction", desc: "Automated B2B discovery & qualification", goal: "Find 10 AI startup founders on LinkedIn with their contact info" },
        { title: "Content Curation Engine", desc: "Aggregate & rank trending intelligence", goal: "Collect the top 10 AI news headlines from TechCrunch today" },
        { title: "Job Market Scanner", desc: "Filter remote positions by criteria", goal: "Find remote Python developer jobs under $150k on Indeed" },
    ];

    const flowSteps = [
        { step: "01", title: "Input", desc: "Define target objectives via natural language interface.", icon: "edit_note" },
        { step: "02", title: "Synthesis", desc: "Neural engine generates optimized navigation paths.", icon: "account_tree" },
        { step: "03", title: "Execution", desc: "Kinetic agents process live web data in real-time.", icon: "bolt" },
        { step: "04", title: "Output", desc: "Receive verified datasets and automated results.", icon: "inventory_2" },
    ];

    return (
        <div className="min-h-screen p-8 relative overflow-hidden">
            {/* Ambient glow orbs */}
            <div className="ambient-glow w-96 h-96 bg-[rgba(198,198,198,0.03)] -top-40 right-20" />
            <div className="ambient-glow w-64 h-64 bg-[rgba(198,198,198,0.02)] bottom-20 left-10" style={{ animationDelay: "3s" }} />

            <div className="max-w-6xl mx-auto relative z-10">
                {/* Hero */}
                <div className="mb-16 anim-fade-up">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-2 h-2 rounded-full bg-[#4ade80] pulse-dot" />
                        <span className="text-[11px] font-bold text-[#4ade80] uppercase tracking-[0.15em]">System Online</span>
                    </div>
                    <h1 className="text-5xl font-extrabold tracking-tight leading-[1.1] mb-4">
                        <span className="gradient-text">Liquid Intelligence</span>
                        <br />
                        <span className="text-[#d4d3d2]">Kinetic Web Automation</span>
                    </h1>
                    <p className="text-base text-[#a8a7a6] max-w-xl leading-relaxed">
                        Precision-engineered AI agents that navigate the digital landscape with chrome-plated efficiency. Complex workflows, simplified into silver streams of data.
                    </p>
                    <div className="mt-8 flex gap-3">
                        <Link href="/tasks/new" className="btn-chrome inline-flex items-center gap-2">
                            <span className="material-symbols-rounded text-lg">bolt</span>
                            Initialize New Task
                        </Link>
                        <Link href="/history" className="btn-ghost inline-flex items-center gap-2">
                            <span className="material-symbols-rounded text-lg" style={{ fontVariationSettings: "'FILL' 0" }}>database</span>
                            Access Vault
                        </Link>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-16 anim-stagger">
                    {stats.map((s) => (
                        <div key={s.label} className="obsidian-card p-6 group">
                            <div className="flex items-center justify-between mb-3">
                                <span className="material-symbols-rounded text-[#888787] text-xl group-hover:text-[#a8a7a6] transition-colors">{s.icon}</span>
                            </div>
                            <div className="text-3xl font-extrabold text-[#f9f9f9] tracking-tight mb-1">
                                {loading ? <div className="shimmer h-8 w-20 rounded-lg" /> : <AnimatedCounter target={s.value} suffix={s.suffix} />}
                            </div>
                            <p className="text-[11px] text-[#a8a7a6] font-semibold uppercase tracking-[0.1em]">{s.label}</p>
                        </div>
                    ))}
                </div>

                {/* Kinetic Templates */}
                <div className="mb-16">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h2 className="text-xl font-extrabold text-[#e7e5e4] tracking-tight">Kinetic Templates</h2>
                            <p className="text-xs text-[#a8a7a6] mt-1">Optimized blueprints for high-frequency automation</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 anim-stagger">
                        {templates.map((t) => (
                            <Link key={t.title} href={`/tasks/new?goal=${encodeURIComponent(t.goal)}`}
                                className="obsidian-card p-5 group cursor-pointer">
                                <h3 className="text-sm font-bold text-[#e7e5e4] mb-1 group-hover:text-[#f9f9f9] transition-colors">{t.title}</h3>
                                <p className="text-xs text-[#a8a7a6] leading-relaxed">{t.desc}</p>
                                <div className="mt-3 flex items-center gap-1 text-[10px] text-[#888787] group-hover:text-[#a8a7a6] transition-colors">
                                    <span className="material-symbols-rounded text-sm">arrow_forward</span>
                                    <span className="uppercase tracking-widest font-semibold">Deploy</span>
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>

                {/* Operational Flow */}
                <div className="mb-16">
                    <h2 className="text-xl font-extrabold text-[#e7e5e4] tracking-tight mb-6">Operational Flow</h2>
                    <div className="grid grid-cols-4 gap-3 anim-stagger">
                        {flowSteps.map((fs) => (
                            <div key={fs.step} className="relative p-5 group">
                                <div className="text-[40px] font-extrabold text-[rgba(198,198,198,0.06)] leading-none mb-3 select-none">{fs.step}</div>
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="material-symbols-rounded text-[#888787] text-lg group-hover:text-[#a8a7a6] transition-colors">{fs.icon}</span>
                                    <h3 className="text-sm font-bold text-[#e7e5e4]">{fs.title}</h3>
                                </div>
                                <p className="text-xs text-[#a8a7a6] leading-relaxed">{fs.desc}</p>
                                {fs.step !== "04" && (
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 text-[#262626]">
                                        <span className="material-symbols-rounded text-xl">chevron_right</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Neural Log Preview */}
                <div className="obsidian-card p-6 mb-8 anim-fade-up">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-bold text-[#e7e5e4] flex items-center gap-2">
                            <span className="material-symbols-rounded text-lg text-[#888787]">terminal</span>
                            Neural Log Activity
                        </h3>
                        <span className="badge badge-chrome">Live Feed</span>
                    </div>
                    <div className="bg-[#0a0a0a] rounded-lg p-4 font-mono text-xs space-y-2">
                        <div className="text-[#4ade80]"><span className="text-[#888787]">[SYS]</span> Agent core initialized. Model: GPT-4o-mini</div>
                        <div className="text-[#d4d3d2]"><span className="text-[#888787]">[NET]</span> Playwright browser pool ready — 3 contexts</div>
                        <div className="text-[#d4d3d2]"><span className="text-[#888787]">[API]</span> FastAPI server listening on :8000</div>
                        <div className="text-[#c6c6c6] cursor-blink"><span className="text-[#888787]">[RDY]</span> Awaiting neural input</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
