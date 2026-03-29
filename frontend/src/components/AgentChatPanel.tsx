"use client";

import { useEffect, useRef } from "react";
import { UiEvent } from "@/lib/api";

interface AgentChatPanelProps {
    events: UiEvent[];
}

export function AgentChatPanel({ events }: AgentChatPanelProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new events arrive
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [events]);

    return (
        <div className="flex flex-col h-full bg-[#0d0d14] rounded-xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800 flex items-center gap-3 bg-black/40">
                <div className="w-8 h-8 rounded-full bg-brand-600/20 flex items-center justify-center">
                    <span className="text-xl">🤖</span>
                </div>
                <div>
                    <h2 className="font-semibold text-slate-100 leading-tight">Project Antigravity Agent</h2>
                    <p className="text-xs text-brand-400 opacity-80">Autonomous Browser AI</p>
                </div>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
                {events.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-slate-500 italic text-sm">
                        Waiting for agent to begin tasks...
                    </div>
                ) : (
                    events.map((evt, idx) => {
                        const isError = evt.type === "error";
                        const isSuccess = evt.type === "result";

                        return (
                            <div key={idx} className={`flex gap-3 max-w-[90%] ${isError ? "mr-auto" : ""}`}>
                                <div className="mt-1 opacity-80 shrink-0 text-sm">
                                    {evt.type === "error" ? "❌" :
                                        evt.type === "result" ? "✨" :
                                            evt.type === "action" ? "🖱️" : "💬"}
                                </div>
                                <div
                                    className={`p-3 rounded-2xl rounded-tl-sm text-sm shadow-sm transition-all animate-in fade-in slide-in-from-bottom-2 ${isError
                                            ? "bg-red-500/10 text-red-100 border border-red-500/20"
                                            : isSuccess
                                                ? "bg-green-500/10 text-green-100 border border-green-500/20"
                                                : "bg-[#1e1e2d] text-slate-200 border border-slate-700/50"
                                        }`}
                                >
                                    <span className="opacity-50 text-xs mr-2 font-mono hidden md:inline-block">
                                        [{new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]
                                    </span>
                                    {evt.message}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

        </div>
    );
}
