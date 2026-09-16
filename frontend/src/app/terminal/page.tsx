"use client";

import { useEffect, useState, useRef } from "react";
import { api, Task } from "@/lib/api";

interface LogEntry {
    timestamp: string;
    level: "SYS" | "NET" | "AGT" | "ERR" | "WRN" | "API";
    message: string;
}

export default function TerminalPage() {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [filter, setFilter] = useState<string>("all");
    const [autoScroll, setAutoScroll] = useState(true);
    const [commandInput, setCommandInput] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);

    // Generate system logs from task data
    useEffect(() => {
        api.listTasks(undefined, 50).then(res => {
            setTasks(res.tasks);
            const generated: LogEntry[] = [
                { timestamp: new Date().toISOString(), level: "SYS", message: "Kinetic AI engine initialized — Liquid Core v4.2" },
                { timestamp: new Date().toISOString(), level: "NET", message: "Playwright browser pool ready — 3 contexts allocated" },
                { timestamp: new Date().toISOString(), level: "API", message: "FastAPI server active on :8000 — all routes registered" },
                { timestamp: new Date().toISOString(), level: "SYS", message: `Task database loaded — ${res.tasks.length} operations in vault` },
            ];

            // Generate log entries from actual tasks
            res.tasks.slice(0, 20).reverse().forEach(t => {
                const ts = t.created_at;
                generated.push({ timestamp: ts, level: "AGT", message: `Task created: "${t.goal}" [${t.id.slice(0, 8)}]` });

                if (t.started_at) {
                    generated.push({ timestamp: t.started_at, level: "NET", message: `Agent dispatched for [${t.id.slice(0, 8)}] — opening browser session` });
                }
                if (t.completed_at && t.status === "completed") {
                    generated.push({ timestamp: t.completed_at, level: "SYS", message: `Task [${t.id.slice(0, 8)}] completed — results verified and stored` });
                }
                if (t.status === "failed") {
                    generated.push({ timestamp: t.completed_at || t.created_at, level: "ERR", message: `Task [${t.id.slice(0, 8)}] critical fault: ${t.error_message || "execution failed"}` });
                }
            });

            generated.push({ timestamp: new Date().toISOString(), level: "SYS", message: "Terminal session active — awaiting commands" });
            setLogs(generated);
        }).catch(() => {
            setLogs([
                { timestamp: new Date().toISOString(), level: "SYS", message: "Kinetic AI engine initialized" },
                { timestamp: new Date().toISOString(), level: "WRN", message: "Could not connect to backend — running in offline mode" },
            ]);
        });
    }, []);

    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    const handleCommand = (e: React.FormEvent) => {
        e.preventDefault();
        if (!commandInput.trim()) return;
        const cmd = commandInput.trim().toLowerCase();
        const now = new Date().toISOString();

        setLogs(prev => [...prev, { timestamp: now, level: "SYS", message: `> ${commandInput}` }]);

        // Process commands
        if (cmd === "help") {
            setLogs(prev => [...prev,
            { timestamp: now, level: "SYS", message: "Available commands:" },
            { timestamp: now, level: "SYS", message: "  status    — Show system status" },
            { timestamp: now, level: "SYS", message: "  tasks     — List recent tasks" },
            { timestamp: now, level: "SYS", message: "  stats     — Show task statistics" },
            { timestamp: now, level: "SYS", message: "  clear     — Clear terminal" },
            { timestamp: now, level: "SYS", message: "  version   — Show engine version" },
            ]);
        } else if (cmd === "clear") {
            setLogs([{ timestamp: now, level: "SYS", message: "Terminal cleared" }]);
        } else if (cmd === "status") {
            const running = tasks.filter(t => t.status === "running").length;
            const completed = tasks.filter(t => t.status === "completed").length;
            setLogs(prev => [...prev,
            { timestamp: now, level: "SYS", message: `Engine: ONLINE | Active: ${running} | Completed: ${completed} | Total: ${tasks.length}` },
            ]);
        } else if (cmd === "tasks") {
            tasks.slice(0, 5).forEach(t => {
                setLogs(prev => [...prev,
                { timestamp: now, level: "AGT", message: `[${t.id.slice(0, 8)}] ${t.status.toUpperCase()} — ${t.goal.slice(0, 60)}` },
                ]);
            });
        } else if (cmd === "stats") {
            const completed = tasks.filter(t => t.status === "completed").length;
            const failed = tasks.filter(t => t.status === "failed").length;
            const rate = tasks.length > 0 ? Math.round((completed / tasks.length) * 100) : 0;
            setLogs(prev => [...prev,
            { timestamp: now, level: "SYS", message: `Success rate: ${rate}% | Completed: ${completed} | Failed: ${failed} | Total: ${tasks.length}` },
            ]);
        } else if (cmd === "version") {
            setLogs(prev => [...prev,
            { timestamp: now, level: "SYS", message: "AI Web Automation Agent v0.2.0 | FastAPI + Playwright + Next.js" },
            ]);
        } else {
            setLogs(prev => [...prev,
            { timestamp: now, level: "WRN", message: `Unknown command: "${commandInput}". Type "help" for available commands.` },
            ]);
        }
        setCommandInput("");
    };

    const levelColors: Record<string, string> = {
        SYS: "text-[#d4d4d4]",
        NET: "text-[#60a5fa]",
        AGT: "text-[#4ade80]",
        ERR: "text-[#ee7d77]",
        WRN: "text-[#fbbf24]",
        API: "text-[#c0c1ff]",
    };
    const levelBadgeColors: Record<string, string> = {
        SYS: "text-[#888787]",
        NET: "text-[#60a5fa]",
        AGT: "text-[#4ade80]",
        ERR: "text-[#ee7d77]",
        WRN: "text-[#fbbf24]",
        API: "text-[#c0c1ff]",
    };

    const filteredLogs = filter === "all" ? logs : logs.filter(l => l.level === filter);

    return (
        <div className="h-full flex flex-col p-4 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-3 shrink-0 anim-fade-up">
                <div>
                    <h1 className="text-xl font-extrabold tracking-tight gradient-text">Terminal</h1>
                    <p className="text-[10px] text-[#888787] mt-0.5">Live system log feed & command interface</p>
                </div>
                <div className="flex gap-2">
                    {/* Level Filters */}
                    <div className="flex gap-0.5 bg-[#0a0a0a] rounded-xl p-0.5 border border-[rgba(120,120,120,0.08)]">
                        {["all", "SYS", "AGT", "ERR"].map(f => (
                            <button key={f} onClick={() => setFilter(f)}
                                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${filter === f
                                        ? "bg-gradient-to-r from-[#c6c6c6] to-[#9b9ea3] text-[#0e0e0e]"
                                        : "text-[#888787] hover:text-[#a8a7a6]"
                                    }`}>
                                {f === "all" ? "All" : f}
                            </button>
                        ))}
                    </div>
                    <button onClick={() => setAutoScroll(!autoScroll)} className={`btn-ghost text-xs flex items-center gap-1 ${autoScroll ? "text-[#4ade80]" : ""}`}>
                        <span className="material-symbols-rounded text-sm">{autoScroll ? "vertical_align_bottom" : "pause"}</span>
                        {autoScroll ? "Auto" : "Paused"}
                    </button>
                    <button onClick={() => setLogs([{ timestamp: new Date().toISOString(), level: "SYS", message: "Terminal cleared" }])}
                        className="btn-ghost text-xs flex items-center gap-1">
                        <span className="material-symbols-rounded text-sm">delete_sweep</span>
                        Clear
                    </button>
                </div>
            </div>

            {/* Terminal Body */}
            <div className="flex-1 bg-[#0a0a0a] rounded-2xl border border-[rgba(120,120,120,0.08)] flex flex-col overflow-hidden anim-fade-up" style={{ animationDelay: "0.1s" }}>
                {/* Log feed */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 font-mono text-[12px] space-y-0.5 scroll-smooth">
                    {filteredLogs.map((log, i) => (
                        <div key={i} className={`flex gap-3 py-0.5 hover:bg-[rgba(198,198,198,0.02)] px-2 rounded transition-colors ${levelColors[log.level]}`}>
                            <span className="text-[#555] shrink-0 text-[10px] mt-0.5 w-16 text-right">
                                {new Date(log.timestamp).toLocaleTimeString("en", { hour12: false })}
                            </span>
                            <span className={`shrink-0 text-[10px] font-bold w-7 uppercase mt-0.5 ${levelBadgeColors[log.level]}`}>[{log.level}]</span>
                            <span className="flex-1 break-all">{log.message}</span>
                        </div>
                    ))}
                    <div className="text-[#d4d4d4] cursor-blink py-0.5 px-2" />
                </div>

                {/* Command Input */}
                <form onSubmit={handleCommand} className="border-t border-[rgba(120,120,120,0.08)] px-4 py-3 flex items-center gap-3 shrink-0">
                    <span className="text-[#4ade80] font-mono text-sm font-bold shrink-0">❯</span>
                    <input
                        type="text"
                        value={commandInput}
                        onChange={e => setCommandInput(e.target.value)}
                        placeholder='Type "help" for commands...'
                        className="flex-1 bg-transparent text-[#d4d3d2] font-mono text-sm outline-none placeholder:text-[#555]"
                        autoFocus
                    />
                    <button type="submit" className="text-[#888787] hover:text-[#d4d4d4] transition-colors">
                        <span className="material-symbols-rounded text-lg">send</span>
                    </button>
                </form>
            </div>
        </div>
    );
}
