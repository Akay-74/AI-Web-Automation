"use client";

import { useEffect, useRef } from "react";
import { UiEvent, TaskStep } from "@/lib/api";

interface ExecutionFeedProps {
    events: UiEvent[];
    steps: TaskStep[];
    totalSteps?: number;
    status: string;
}

function getStepIcon(action: string) {
    const map: Record<string, { icon: string; color: string }> = {
        navigate: { icon: "language", color: "text-[#60a5fa]" },
        type: { icon: "keyboard", color: "text-[#c6c6c6]" },
        click: { icon: "touch_app", color: "text-[#c6c6c6]" },
        scroll: { icon: "swap_vert", color: "text-[#a8a7a6]" },
        extract: { icon: "data_object", color: "text-[#fbbf24]" },
        validate: { icon: "verified", color: "text-[#4ade80]" },
        evaluate: { icon: "psychology", color: "text-[#c0c1ff]" },
        wait: { icon: "hourglass_empty", color: "text-[#888787]" },
        replan: { icon: "refresh", color: "text-[#ee7d77]" },
    };
    const key = Object.keys(map).find(k => action?.toLowerCase().startsWith(k));
    return key ? map[key] : { icon: "terminal", color: "text-[#a8a7a6]" };
}

export function ExecutionFeed({ events, steps, status }: ExecutionFeedProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [events, steps]);

    const completedSteps = steps.filter(s => s.status === "completed").length;
    const total = Math.max(steps.length, 1);
    const progress = Math.min(100, Math.round((completedSteps / total) * 100));
    const isRunning = status === "running";
    const isCompleted = status === "completed";
    const isFailed = status === "failed";

    return (
        <div className="flex flex-col h-full bg-[#0a0a0a] rounded-2xl border border-[rgba(72,72,72,0.1)] overflow-hidden">

            {/* Header */}
            <div className="px-4 py-3 border-b border-[rgba(72,72,72,0.1)] shrink-0">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-rounded text-[#888787] text-lg">terminal</span>
                        <span className="text-xs font-bold text-[#e7e5e4]">Execution Sequence</span>
                        {isRunning && <span className="badge badge-warning"><span className="w-1 h-1 rounded-full bg-[#fbbf24] pulse-dot" />Active</span>}
                        {isCompleted && <span className="badge badge-success">Complete</span>}
                        {isFailed && <span className="badge badge-danger">Fault</span>}
                    </div>
                    <span className="text-[10px] text-[#888787] font-mono">{completedSteps}/{total}</span>
                </div>

                {/* Liquid silver progress */}
                <div className="h-[2px] bg-[#131313] rounded-full overflow-hidden">
                    <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${isRunning ? "liquid-progress" : ""
                            }`}
                        style={{
                            width: `${isCompleted ? 100 : progress}%`,
                            background: isRunning ? undefined :
                                isFailed ? "#ee7d77" :
                                    isCompleted ? "linear-gradient(90deg, #4ade80, #22c55e)" :
                                        "#484848"
                        }}
                    />
                </div>
            </div>

            {/* Feed */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-1 scroll-smooth">
                {events.length === 0 && steps.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-[#888787] gap-3">
                        <div className="w-8 h-8 border-2 border-[#262626] border-t-[#c6c6c6] rounded-full animate-spin" />
                        <span className="text-xs font-medium">Awaiting neural input...</span>
                    </div>
                ) : (
                    <>
                        {steps
                            .filter(s => s.action !== "screenshot" && !s.action.startsWith("task_"))
                            .map((s, idx) => {
                                const { icon, color } = getStepIcon(s.action);
                                const isActive = s.status === "executing" || s.status === "running";
                                const isDone = s.status === "completed";
                                const isFail = s.status === "failed";

                                return (
                                    <div key={`step-${s.step}-${idx}`}
                                        className={`flex items-start gap-2.5 px-3 py-2 rounded-xl transition-all duration-300 anim-fade-up ${isActive ? "bg-[rgba(198,198,198,0.04)] glow" :
                                                isFail ? "bg-[rgba(238,125,119,0.04)]" :
                                                    "hover:bg-[rgba(198,198,198,0.02)]"
                                            }`}
                                        style={{ animationDelay: `${idx * 0.05}s` }}>

                                        <div className={`mt-0.5 w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${isDone ? "bg-[rgba(74,222,128,0.1)]" :
                                                isActive ? "bg-[rgba(198,198,198,0.08)] glow" :
                                                    isFail ? "bg-[rgba(238,125,119,0.1)]" :
                                                        "bg-[#131313]"
                                            }`}>
                                            {isDone ? (
                                                <span className="material-symbols-rounded text-xs text-[#4ade80]">check</span>
                                            ) : isFail ? (
                                                <span className="material-symbols-rounded text-xs text-[#ee7d77]">close</span>
                                            ) : isActive ? (
                                                <div className="w-2 h-2 bg-[#c6c6c6] rounded-full pulse-dot" />
                                            ) : (
                                                <span className={`material-symbols-rounded text-xs ${color}`}>{icon}</span>
                                            )}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <span className={`text-[10px] uppercase tracking-wider font-bold ${color}`}>
                                                {s.action}
                                            </span>
                                            <p className="text-[11px] text-[#d4d3d2] leading-relaxed mt-0.5 truncate" title={s.description}>
                                                {s.description}
                                            </p>
                                            {s.details?.error && (
                                                <p className="text-[10px] text-[#ee7d77] mt-1 bg-[rgba(238,125,119,0.08)] px-2 py-1 rounded-lg">{s.details.error}</p>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}

                        {events
                            .filter(e => e.type === "error" || e.type === "result" || e.type === "info")
                            .map((evt, idx) => (
                                <div key={`evt-${idx}`}
                                    className={`flex items-start gap-2.5 px-3 py-2 rounded-xl text-[11px] anim-fade-up ${evt.type === "error" ? "bg-[rgba(238,125,119,0.06)] text-[#ee7d77]" :
                                            evt.type === "result" ? "bg-[rgba(74,222,128,0.06)] text-[#4ade80]" :
                                                "text-[#d4d3d2]"
                                        }`}>
                                    <span className="material-symbols-rounded text-sm mt-0.5 shrink-0">
                                        {evt.type === "error" ? "error" : evt.type === "result" ? "auto_awesome" : "info"}
                                    </span>
                                    <span className="flex-1 leading-relaxed">{evt.message}</span>
                                </div>
                            ))}
                    </>
                )}
            </div>

            {/* Footer */}
            {isCompleted && steps.length > 0 && (
                <div className="px-4 py-2 border-t border-[rgba(72,72,72,0.1)] bg-[rgba(74,222,128,0.03)] shrink-0">
                    <p className="text-[10px] text-[#4ade80] font-bold uppercase tracking-widest flex items-center gap-1">
                        <span className="material-symbols-rounded text-xs">check_circle</span>
                        Sequence Complete — {completedSteps} steps verified
                    </p>
                </div>
            )}
            {isFailed && (
                <div className="px-4 py-2 border-t border-[rgba(72,72,72,0.1)] bg-[rgba(238,125,119,0.03)] shrink-0">
                    <p className="text-[10px] text-[#ee7d77] font-bold uppercase tracking-widest flex items-center gap-1">
                        <span className="material-symbols-rounded text-xs">error</span>
                        Critical fault — review logs
                    </p>
                </div>
            )}
        </div>
    );
}
