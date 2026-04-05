"use client";

import { useEffect, useState } from "react";
import { api, Task } from "@/lib/api";

export default function AnalyticsPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.listTasks(undefined, 100).then(res => { setTasks(res.tasks); setLoading(false); }).catch(() => setLoading(false));
    }, []);

    const completed = tasks.filter(t => t.status === "completed");
    const failed = tasks.filter(t => t.status === "failed");
    const running = tasks.filter(t => t.status === "running");

    const successRate = tasks.length > 0 ? Math.round((completed.length / tasks.length) * 100) : 0;
    const failRate = tasks.length > 0 ? Math.round((failed.length / tasks.length) * 100) : 0;

    // Average duration for completed tasks
    const durations = completed
        .filter(t => t.started_at && t.completed_at)
        .map(t => (new Date(t.completed_at!).getTime() - new Date(t.started_at!).getTime()) / 1000);
    const avgDuration = durations.length > 0 ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : 0;
    const maxDuration = durations.length > 0 ? Math.round(Math.max(...durations)) : 0;
    const minDuration = durations.length > 0 ? Math.round(Math.min(...durations)) : 0;

    // Tasks per day (last 7 days)
    const now = Date.now();
    const last7 = Array.from({ length: 7 }, (_, i) => {
        const dayStart = new Date(now - (6 - i) * 86400000);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(dayStart.getTime() + 86400000);
        const count = tasks.filter(t => {
            const d = new Date(t.created_at).getTime();
            return d >= dayStart.getTime() && d < dayEnd.getTime();
        }).length;
        return { label: dayStart.toLocaleDateString("en", { weekday: "short" }), count };
    });
    const maxDay = Math.max(...last7.map(d => d.count), 1);

    // Status distribution
    const statusDist = [
        { label: "Completed", count: completed.length, color: "#4ade80", bg: "rgba(74,222,128,0.12)" },
        { label: "Running", count: running.length, color: "#fbbf24", bg: "rgba(251,191,36,0.12)" },
        { label: "Failed", count: failed.length, color: "#ee7d77", bg: "rgba(238,125,119,0.12)" },
        { label: "Other", count: tasks.length - completed.length - running.length - failed.length, color: "#888787", bg: "rgba(136,135,135,0.1)" },
    ].filter(s => s.count > 0);

    return (
        <div className="min-h-screen p-8 relative overflow-hidden">
            <div className="ambient-glow w-72 h-72 bg-[rgba(198,198,198,0.02)] top-10 left-40" />

            <div className="max-w-6xl mx-auto relative z-10">
                {/* Header */}
                <div className="mb-10 anim-fade-up">
                    <h1 className="text-3xl font-extrabold tracking-tight gradient-text mb-2">Analytics</h1>
                    <p className="text-sm text-[#a8a7a6]">Performance metrics and operational intelligence for the kinetic engine</p>
                </div>

                {/* Top stats */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-10 anim-stagger">
                    {[
                        { label: "Success Rate", value: `${successRate}%`, icon: "verified", glow: successRate > 80 ? "glow-success" : "" },
                        { label: "Avg Duration", value: `${avgDuration}s`, icon: "timer" },
                        { label: "Total Cycles", value: tasks.length.toString(), icon: "cycle" },
                        { label: "Failure Rate", value: `${failRate}%`, icon: "error_outline", glow: failRate > 20 ? "glow-danger" : "" },
                    ].map(s => (
                        <div key={s.label} className={`obsidian-card p-5 ${s.glow || ""}`}>
                            <div className="flex items-center justify-between mb-2">
                                <span className="material-symbols-rounded text-[#888787] text-lg">{s.icon}</span>
                            </div>
                            <div className="text-3xl font-extrabold text-[#f9f9f9] tracking-tight mb-0.5">
                                {loading ? <div className="shimmer h-8 w-16 rounded" /> : s.value}
                            </div>
                            <p className="text-[10px] text-[#888787] font-semibold uppercase tracking-widest">{s.label}</p>
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-10">
                    {/* 7-Day Activity Bar Chart */}
                    <div className="glass-card p-6 anim-fade-up" style={{ animationDelay: "0.1s" }}>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-1 flex items-center gap-2">
                            <span className="material-symbols-rounded text-[#888787] text-base">bar_chart</span>
                            7-Day Activity
                        </h3>
                        <p className="text-[10px] text-[#888787] mb-5">Tasks created per day</p>
                        {loading ? (
                            <div className="shimmer h-40 rounded-xl" />
                        ) : (
                            <div className="flex items-end gap-2 h-40">
                                {last7.map((day, i) => (
                                    <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                                        <span className="text-[10px] font-bold text-[#a8a7a6]">{day.count}</span>
                                        <div className="w-full rounded-t-lg transition-all duration-700 relative group"
                                            style={{
                                                height: `${Math.max(4, (day.count / maxDay) * 100)}%`,
                                                background: day.count > 0
                                                    ? "linear-gradient(180deg, rgba(198,198,198,0.5) 0%, rgba(198,198,198,0.15) 100%)"
                                                    : "rgba(198,198,198,0.05)"
                                            }}>
                                            <div className="absolute inset-0 rounded-t-lg opacity-0 group-hover:opacity-100 transition-opacity"
                                                style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.15) 0%, transparent 100%)" }} />
                                        </div>
                                        <span className="text-[9px] text-[#888787] font-semibold">{day.label}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Status Distribution */}
                    <div className="glass-card p-6 anim-fade-up" style={{ animationDelay: "0.15s" }}>
                        <h3 className="text-sm font-bold text-[#f0eeed] mb-1 flex items-center gap-2">
                            <span className="material-symbols-rounded text-[#888787] text-base">donut_small</span>
                            Status Distribution
                        </h3>
                        <p className="text-[10px] text-[#888787] mb-5">Breakdown of task outcomes</p>
                        {loading ? (
                            <div className="shimmer h-40 rounded-xl" />
                        ) : tasks.length === 0 ? (
                            <div className="h-40 flex items-center justify-center text-[#666] text-xs">No data yet</div>
                        ) : (
                            <div className="space-y-3">
                                {statusDist.map(s => (
                                    <div key={s.label}>
                                        <div className="flex items-center justify-between mb-1.5">
                                            <span className="text-xs font-semibold" style={{ color: s.color }}>{s.label}</span>
                                            <span className="text-xs font-bold text-[#d4d3d2]">{s.count} <span className="text-[#888787] font-normal">({Math.round((s.count / tasks.length) * 100)}%)</span></span>
                                        </div>
                                        <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(198,198,198,0.06)" }}>
                                            <div className="h-full rounded-full transition-all duration-1000"
                                                style={{ width: `${(s.count / tasks.length) * 100}%`, background: s.color }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Performance Details */}
                <div className="glass-card p-6 anim-fade-up" style={{ animationDelay: "0.2s" }}>
                    <h3 className="text-sm font-bold text-[#f0eeed] mb-5 flex items-center gap-2">
                        <span className="material-symbols-rounded text-[#888787] text-base">speed</span>
                        Performance Metrics
                    </h3>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[
                            { label: "Fastest Cycle", value: minDuration > 0 ? `${minDuration}s` : "—", icon: "bolt", color: "#4ade80" },
                            { label: "Slowest Cycle", value: maxDuration > 0 ? `${maxDuration}s` : "—", icon: "hourglass_top", color: "#fbbf24" },
                            { label: "Mean Cycle", value: avgDuration > 0 ? `${avgDuration}s` : "—", icon: "avg_pace", color: "#d4d4d4" },
                            { label: "Throughput", value: last7.reduce((a, b) => a + b.count, 0) > 0 ? `${(last7.reduce((a, b) => a + b.count, 0) / 7).toFixed(1)}/day` : "—", icon: "trending_up", color: "#60a5fa" },
                        ].map(m => (
                            <div key={m.label} className="bg-[#131313] rounded-xl p-4">
                                <span className="material-symbols-rounded text-xl mb-2 block" style={{ color: m.color }}>{m.icon}</span>
                                <div className="text-xl font-extrabold text-[#f9f9f9] tracking-tight">{loading ? <div className="shimmer h-6 w-12 rounded" /> : m.value}</div>
                                <p className="text-[9px] text-[#888787] font-semibold uppercase tracking-widest mt-1">{m.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
