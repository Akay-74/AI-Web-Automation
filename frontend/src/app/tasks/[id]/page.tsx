"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Task, ProductResult, TaskStep } from "@/lib/api";
import { useTaskWebSocket } from "@/hooks/useTaskWebSocket";
import { ExecutionFeed } from "@/components/ExecutionFeed";
import { LiveBrowserPanel } from "@/components/LiveBrowserPanel";
import { ProductCard } from "@/components/ProductCard";

export default function TaskDetailPage() {
    const params = useParams();
    const taskId = params.id as string;

    const [task, setTask] = useState<Task | null>(null);
    const [savedLogs, setSavedLogs] = useState<any[]>([]);
    const [finalResults, setFinalResults] = useState<any>(null);
    const [showRawLogs, setShowRawLogs] = useState(false);
    const [sortBy, setSortBy] = useState<"price" | "rating" | "valid">("valid");

    const { steps, uiEvents, status: wsStatus, connected, screenshot, captchaDetected, captchaType, viewport, sendAction } = useTaskWebSocket(taskId);

    useEffect(() => {
        async function loadTask() {
            try {
                const t = await api.getTask(taskId);
                setTask(t);
                if (t.status === "completed" || t.status === "failed") {
                    const l = await api.getTaskLogs(taskId);
                    setSavedLogs(l);
                    const r = await api.getTaskResults(taskId);
                    if (r.length > 0) setFinalResults(r[0].data);
                }
            } catch (error) { console.error(error); }
        }
        loadTask();
    }, [taskId]);

    useEffect(() => {
        if (wsStatus === "completed" && !finalResults) {
            api.getTaskResults(taskId).then(r => {
                if (r.length > 0) setFinalResults(r[0].data);
            }).catch(console.error);
        }
    }, [wsStatus, taskId, finalResults]);

    const activeStatus = wsStatus || task?.status || "pending";
    const isTerminal = ["completed", "failed", "cancelled"].includes(activeStatus);

    const displaySteps = isTerminal && steps.length === 0
        ? savedLogs.map(l => ({
            step: l.step_number, action: l.action,
            description: l.details?.description || l.action,
            status: "completed", details: l.details,
            timestamp: l.timestamp || new Date().toISOString()
        }))
        : steps;

    const rawResultsData: ProductResult[] = finalResults?.items ||
        displaySteps.find(s => s.action === "task_completed")?.details?.results || [];

    const resultsData = [...rawResultsData].sort((a, b) => {
        if (sortBy === "price") return (a.price ?? Infinity) - (b.price ?? Infinity);
        if (sortBy === "rating") return Number(b.rating ?? 0) - Number(a.rating ?? 0);
        if ((a.is_valid !== false) !== (b.is_valid !== false)) return (a.is_valid !== false) ? -1 : 1;
        return (a.price ?? Infinity) - (b.price ?? Infinity);
    });

    const validResults = resultsData.filter(r => r.is_valid !== false && typeof r.price === "number");
    let cheapestIdx = -1;
    if (validResults.length > 0) {
        const cheapestItem = validResults.reduce((min, r) => ((r.price as number) < (min.price as number) ? r : min));
        cheapestIdx = resultsData.indexOf(cheapestItem);
    }
    const allPrices = resultsData.filter(r => typeof r.price === "number").map(r => r.price!);
    const validCount = rawResultsData.filter(r => r.is_valid !== false).length;
    const invalidCount = rawResultsData.length - validCount;

    if (!task) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-2 border-[#262626] border-t-[#c6c6c6] rounded-full animate-spin" />
                    <span className="text-xs text-[#888787]">Loading task...</span>
                </div>
            </div>
        );
    }

    const statusConfig: Record<string, { badge: string; label: string }> = {
        running: { badge: "badge-warning", label: "Active Cycle" },
        completed: { badge: "badge-success", label: "Verified" },
        failed: { badge: "badge-danger", label: "Critical Fault" },
        pending: { badge: "badge-chrome", label: "Queued" },
        cancelled: { badge: "badge-chrome", label: "Archived" },
    };
    const cfg = statusConfig[activeStatus] || statusConfig.pending;

    return (
        <div className="h-full flex flex-col p-4 gap-3 overflow-hidden relative">
            {/* Ambient glow */}
            {activeStatus === "running" && (
                <div className="ambient-glow w-64 h-64 bg-[rgba(198,198,198,0.02)] top-0 right-20" />
            )}

            {/* Header */}
            <div className="glass-card px-5 py-3 flex items-center justify-between gap-4 shrink-0 relative z-10 anim-fade-up">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                        <h1 className="text-base font-extrabold text-[#f9f9f9] truncate max-w-2xl tracking-tight" title={task.goal}>
                            {task.goal}
                        </h1>
                        <span className={`badge ${cfg.badge}`}>
                            {activeStatus === "running" && <span className="w-1 h-1 rounded-full bg-[#fbbf24] pulse-dot" />}
                            {cfg.label}
                        </span>
                        {!connected && !isTerminal && (
                            <span className="badge badge-danger"><span className="w-1 h-1 rounded-full bg-[#ee7d77]" />Disconnected</span>
                        )}
                    </div>
                    <p className="text-[10px] text-[#888787] font-mono mt-0.5">{task.id}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    {/* Cancel running task */}
                    {activeStatus === "running" && (
                        <button onClick={async () => { try { await api.cancelTask(taskId); window.location.reload(); } catch { } }}
                            className="btn-ghost text-xs flex items-center gap-1 text-[#ee7d77] border-[rgba(238,125,119,0.2)] hover:bg-[rgba(238,125,119,0.08)]">
                            <span className="material-symbols-rounded text-sm">stop_circle</span>
                            Cancel
                        </button>
                    )}
                    {/* Retry (re-create same task) */}
                    {isTerminal && (
                        <button onClick={async () => {
                            try {
                                const newTask = await api.createTask(task.goal);
                                await api.startTask(newTask.id);
                                window.location.href = `/tasks/${newTask.id}`;
                            } catch { }
                        }} className="btn-ghost text-xs flex items-center gap-1">
                            <span className="material-symbols-rounded text-sm">replay</span>
                            Retry
                        </button>
                    )}
                    {/* Export JSON */}
                    {resultsData.length > 0 && (
                        <button onClick={() => { navigator.clipboard.writeText(JSON.stringify(resultsData, null, 2)); }}
                            className="btn-ghost text-xs flex items-center gap-1">
                            <span className="material-symbols-rounded text-sm">content_copy</span>
                            Export
                        </button>
                    )}
                    {/* Raw Logs toggle */}
                    <button onClick={() => setShowRawLogs(!showRawLogs)} className="btn-ghost text-xs flex items-center gap-1">
                        <span className="material-symbols-rounded text-sm">{showRawLogs ? "visibility_off" : "data_object"}</span>
                        {showRawLogs ? "Hide" : "Raw Logs"}
                    </button>
                </div>
            </div>

            {/* Main layout */}
            <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-3 relative z-10">

                {/* Left: Execution Feed */}
                <div className="w-full lg:w-[340px] xl:w-[380px] shrink-0 h-full anim-fade-up" style={{ animationDelay: "0.1s" }}>
                    <ExecutionFeed
                        events={uiEvents}
                        steps={displaySteps.filter(s => s.action !== "screenshot" && s.action !== "screencast_frame" && !s.action.startsWith("task_"))}
                        status={activeStatus}
                    />
                </div>

                {/* Right: Browser + Results */}
                <div className="flex-1 flex flex-col gap-3 min-h-0 min-w-0 relative anim-fade-up" style={{ animationDelay: "0.2s" }}>

                    {/* Raw Logs Overlay */}
                    {showRawLogs && (
                        <div className="absolute inset-0 z-50 bg-[#0a0a0a] rounded-2xl border border-[rgba(72,72,72,0.1)] p-4 overflow-y-auto shadow-2xl">
                            <div className="flex items-center justify-between mb-4 border-b border-[rgba(72,72,72,0.1)] pb-2">
                                <h3 className="font-mono text-[#c6c6c6] font-bold text-xs flex items-center gap-2">
                                    <span className="material-symbols-rounded text-sm">data_object</span>
                                    RAW EVENT STREAM
                                </h3>
                                <button onClick={() => setShowRawLogs(false)} className="text-[#888787] hover:text-[#c6c6c6] text-xs transition-colors">✕</button>
                            </div>
                            <pre className="text-[10px] text-[#4ade80] font-mono whitespace-pre-wrap break-all">
                                {(displaySteps as TaskStep[]).map((s: TaskStep) => JSON.stringify(s.raw_event || s, null, 2)).join("\n\n---\n\n")}
                            </pre>
                        </div>
                    )}

                    {/* Live Browser */}
                    {(!isTerminal || screenshot) && (
                        <div className={`transition-all duration-500 ${isTerminal && resultsData.length > 0 ? "h-64 shrink-0" : "flex-1 min-h-0"}`}>
                            <LiveBrowserPanel
                                screenshotBase64={screenshot}
                                captchaDetected={captchaDetected}
                                captchaType={captchaType}
                                viewport={viewport}
                                onSendAction={sendAction}
                            />
                        </div>
                    )}

                    {/* Results */}
                    {resultsData.length > 0 && (
                        <div className="flex-1 min-h-0 flex flex-col">
                            <div className="flex items-center justify-between mb-3 shrink-0 px-1">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-sm font-extrabold text-[#e7e5e4] flex items-center gap-2">
                                        <span className="material-symbols-rounded text-base text-[#888787]">inventory_2</span>
                                        Liquid Assets
                                        <span className="badge badge-chrome">{resultsData.length}</span>
                                    </h2>
                                    <span className="badge badge-success">✓ {validCount}</span>
                                    {invalidCount > 0 && <span className="badge badge-danger">✗ {invalidCount}</span>}
                                </div>
                                <div className="flex gap-0.5 bg-[#0a0a0a] rounded-xl p-0.5 border border-[rgba(72,72,72,0.08)]">
                                    {(["valid", "price", "rating"] as const).map(opt => (
                                        <button key={opt} onClick={() => setSortBy(opt)}
                                            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${sortBy === opt
                                                ? "bg-gradient-to-r from-[#c6c6c6] to-[#9b9ea3] text-[#0e0e0e]"
                                                : "text-[#888787] hover:text-[#a8a7a6]"
                                                }`}>
                                            {opt === "valid" ? "Best" : opt === "price" ? "Price" : "Rating"}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="flex-1 overflow-y-auto px-1 pb-2">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3 anim-stagger">
                                    {resultsData.map((res, idx) => (
                                        <ProductCard key={idx} product={res} isCheapest={idx === cheapestIdx} rank={idx + 1} allPrices={allPrices} />
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {isTerminal && resultsData.length === 0 && (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center text-[#888787]">
                                <span className="material-symbols-rounded text-5xl mb-3 block text-[#262626]">inventory_2</span>
                                <p className="text-sm font-bold text-[#a8a7a6] mb-1">Empty Vault</p>
                                <p className="text-xs text-[#888787]">No structured data was extracted from this operation.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
