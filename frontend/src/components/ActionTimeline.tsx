"use client";

import { TaskStep } from "@/lib/api";

interface ActionTimelineProps {
    steps: TaskStep[];
}

export function ActionTimeline({ steps }: ActionTimelineProps) {
    if (!steps || steps.length === 0) return null;

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 px-2">Task Execution Plan</h3>
            <div className="space-y-3 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-800 before:to-transparent">
                {steps.map((s, idx) => {
                    const statusColor =
                        s.status === "executing" || s.status === "running" ? "bg-brand-500/20 text-brand-400 border-brand-500/30" :
                            s.status === "completed" ? "bg-green-500/10 text-green-400 border-green-500/20" :
                                s.status === "failed" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                                    "bg-slate-800 text-slate-400 border-slate-700";

                    const badgeText = s.status === "executing" ? "In Progress" : s.status;

                    return (
                        <div key={`${s.step}-${idx}`} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group animate-in fade-in slide-in-from-bottom-2">
                            {/* Icon / Node */}
                            <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 border-[#0a0a0f] shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm ${s.status === 'executing' ? 'bg-brand-600 animate-pulse' : 'bg-slate-800'}`}>
                                <span className="text-xs font-bold text-white">{s.step}</span>
                            </div>

                            {/* Card Content */}
                            <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-slate-800 bg-[#12121a] hover:bg-[#181824] transition-colors shadow-sm">
                                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                                    <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded border ${statusColor}`}>
                                        {badgeText}
                                    </span>
                                </div>
                                <h4 className="font-semibold text-slate-200 text-sm">{s.description}</h4>
                                {s.details?.error && (
                                    <p className="text-xs text-red-400 mt-2 p-2 bg-red-500/10 rounded">{s.details.error}</p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
