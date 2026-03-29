"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Task, ProductResult, TaskStep } from "@/lib/api";
import { useTaskWebSocket } from "@/hooks/useTaskWebSocket";
import { AgentChatPanel } from "@/components/AgentChatPanel";
import { LiveBrowserPanel } from "@/components/LiveBrowserPanel";
import { ActionTimeline } from "@/components/ActionTimeline";
import { ProductCard } from "@/components/ProductCard";

export default function TaskDetailPage() {
    const params = useParams();
    const taskId = params.id as string;

    const [task, setTask] = useState<Task | null>(null);
    const [savedLogs, setSavedLogs] = useState<any[]>([]);
    const [finalResults, setFinalResults] = useState<any>(null);
    const [showRawLogs, setShowRawLogs] = useState(false);

    // Live state via WebSocket
    const { steps, uiEvents, status: wsStatus, connected, screenshot } = useTaskWebSocket(taskId);

    // Initial load
    useEffect(() => {
        async function loadTask() {
            try {
                const t = await api.getTask(taskId);
                setTask(t);
                if (t.status === "completed" || t.status === "failed") {
                    const l = await api.getTaskLogs(taskId);
                    setSavedLogs(l);
                    const r = await api.getTaskResults(taskId);
                    if (r.length > 0) {
                        setFinalResults(r[0].data);
                    }
                }
            } catch (error) {
                console.error("Failed to load task:", error);
            }
        }
        loadTask();
    }, [taskId]);

    // Fetch results if task transitions to completed live via WebSocket
    useEffect(() => {
        if (wsStatus === "completed" && !finalResults) {
            api.getTaskResults(taskId).then(r => {
                if (r.length > 0) setFinalResults(r[0].data);
            }).catch(console.error);
        }
    }, [wsStatus, taskId, finalResults]);

    const activeStatus = wsStatus || task?.status || "pending";
    const isTerminal = ["completed", "failed", "cancelled"].includes(activeStatus);

    // Merge live steps and saved logs to display timeline properly if loaded from DB
    const displaySteps = isTerminal && steps.length === 0
        ? savedLogs.map(l => ({
            step: l.step_number,
            action: l.action,
            description: l.details?.description || l.action,
            status: "completed",
            details: l.details,
            timestamp: l.timestamp || new Date().toISOString()
        }))
        : steps;

    // Use results either from WS payload logic or DB
    const resultsData = finalResults?.items ||
        displaySteps.find(s => s.action === "task_completed")?.details?.results ||
        [];

    // Find the cheapest product safely
    let cheapestIdx = -1;
    if (resultsData.length > 0) {
        let minPrice = Infinity;
        resultsData.forEach((res: ProductResult, idx: number) => {
            if (res.price !== undefined && res.price !== null && res.price < minPrice) {
                minPrice = res.price;
                cheapestIdx = idx;
            }
        });
    }

    if (!task) {
        return <div className="p-8 text-center text-slate-500 animate-pulse">Loading task details...</div>;
    }

    return (
        <div className="max-w-7xl mx-auto h-[calc(100vh-3rem)] flex flex-col pt-4 pb-8 space-y-4">

            {/* Header Panel */}
            <div className="glass-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <h1 className="text-xl font-bold text-white tracking-tight leading-tight">
                            {task.goal}
                        </h1>
                        <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider
                            ${activeStatus === "running" ? "bg-brand-500/20 text-brand-400" :
                                activeStatus === "completed" ? "bg-green-500/20 text-green-400" :
                                    activeStatus === "failed" ? "bg-red-500/20 text-red-400" :
                                        "bg-slate-800 text-slate-400"}`}
                        >
                            {activeStatus}
                        </span>
                        {!connected && !isTerminal && (
                            <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-1 rounded">
                                <span className="w-2 h-2 rounded-full bg-red-400"></span>
                                Disconnected
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-slate-500 font-mono">ID: {task.id}</p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => setShowRawLogs(!showRawLogs)}
                        className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800 text-sm font-medium text-slate-300 transition-colors"
                    >
                        {showRawLogs ? "Hide Raw Logs" : "Show Raw Logs"}
                    </button>
                    {activeStatus === "pending" || activeStatus === "queued" ? (
                        <button disabled className="px-4 py-2 rounded-lg bg-slate-800 text-slate-500 text-sm font-semibold cursor-wait">
                            <span className="flex items-center gap-2">
                                <span className="w-3 h-3 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" />
                                Starting...
                            </span>
                        </button>
                    ) : null}
                </div>
            </div>

            {/* Split View: Chat + Timeline on left, Browser + Results on right */}
            <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">

                {/* Left Column: Communications */}
                <div className="w-full lg:w-[400px] xl:w-[450px] flex flex-col gap-4 shrink-0 h-full">
                    {/* Chat Panel - Takes up available space */}
                    <div className="flex-1 min-h-0">
                        <AgentChatPanel events={uiEvents} />
                    </div>

                    {/* Timeline Panel - Fixed max height or scrolling */}
                    <div className="h-1/3 min-h-[250px] max-h-[350px] bg-[#12121a] rounded-xl border border-slate-800 p-4 shadow-xl overflow-y-auto hidden md:block">
                        <ActionTimeline steps={displaySteps.filter(s => s.action !== "screenshot" && !s.action.startsWith("task_"))} />
                    </div>
                </div>

                {/* Right Column: Visualization & Results */}
                <div className="flex-1 flex flex-col gap-4 min-h-0 relative">

                    {/* Raw Logs Overlay */}
                    {showRawLogs && (
                        <div className="absolute inset-0 z-50 bg-[#0d0d14] rounded-xl border border-slate-700 p-4 overflow-y-auto shadow-2xl">
                            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
                                <h3 className="font-mono text-brand-400 font-bold">RAW JSON EVENT STREAM</h3>
                                <button onClick={() => setShowRawLogs(false)} className="text-slate-500 hover:text-white">✕ Close</button>
                            </div>
                            <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap break-all">
                                {(displaySteps as TaskStep[]).map((s: TaskStep) => JSON.stringify(s.raw_event || s, null, 2)).join("\n\n---\n\n")}
                            </pre>
                        </div>
                    )}

                    {/* Browser Panel - Only show while running or if we have a screenshot */}
                    {(!isTerminal || screenshot) && (
                        <div className={`transition-all duration-500 ${isTerminal && resultsData.length > 0 ? 'h-64 shrink-0' : 'flex-1'}`}>
                            <LiveBrowserPanel screenshotBase64={screenshot} />
                        </div>
                    )}

                    {/* Results Grid - Only show if we have results */}
                    {resultsData.length > 0 && (
                        <div className={`flex-1 min-h-0 flex flex-col ${!isTerminal ? 'mt-4 border-t border-slate-800 pt-4' : ''}`}>
                            <div className="flex items-center justify-between mb-4 shrink-0 px-2">
                                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                    <span className="text-2xl">📦</span>
                                    Extracted Results
                                    <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full ml-2">
                                        {resultsData.length} items
                                    </span>
                                </h2>
                            </div>

                            <div className="flex-1 overflow-y-auto px-2 pb-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                    {resultsData.map((res: ProductResult, idx: number) => (
                                        <ProductCard
                                            key={idx}
                                            product={res}
                                            isCheapest={idx === cheapestIdx}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Fallback empty state */}
                    {isTerminal && resultsData.length === 0 && (
                        <div className="flex-1 flex items-center justify-center bg-[#12121a] rounded-xl border border-slate-800 border-dashed">
                            <div className="text-center text-slate-500">
                                <span className="text-4xl block mb-2">🤷‍♂️</span>
                                <p>No results were extracted for this task.</p>
                                {activeStatus === "failed" && <p className="text-sm text-red-400 mt-2">The task failed to complete.</p>}
                            </div>
                        </div>
                    )}
                </div>
            </div>

        </div>
    );
}
