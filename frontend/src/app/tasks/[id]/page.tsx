"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { ExtractedRow, Task, TaskStep, api } from "@/lib/api";
import { useTaskWebSocket } from "@/hooks/useTaskWebSocket";
import { ExecutionFeed } from "@/components/ExecutionFeed";
import { LiveBrowserPanel } from "@/components/LiveBrowserPanel";
import { ResultCard } from "@/components/ResultCard";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

const STATUS_BADGES: Record<string, { badge: string; label: string }> = {
    running: { badge: "badge-warning", label: "Running" },
    queued: { badge: "badge-chrome", label: "Starting" },
    completed: { badge: "badge-success", label: "Completed" },
    failed: { badge: "badge-danger", label: "Failed" },
    pending: { badge: "badge-chrome", label: "Pending" },
    cancelled: { badge: "badge-chrome", label: "Cancelled" },
};

type SortKey = "default" | "price" | "rating";

function numericPrice(row: ExtractedRow): number | null {
    const raw = row.price;
    const value = typeof raw === "string" ? Number(raw.replace(/[^0-9.]/g, "")) : raw;
    return value === null || value === undefined || Number.isNaN(value) ? null : value;
}

export default function TaskDetailPage() {
    const params = useParams();
    const taskId = params.id as string;

    const [task, setTask] = useState<Task | null>(null);
    const [savedLogs, setSavedLogs] = useState<any[]>([]);
    const [storedRows, setStoredRows] = useState<ExtractedRow[] | null>(null);
    const [showRawLogs, setShowRawLogs] = useState(false);
    const [sortBy, setSortBy] = useState<SortKey>("default");

    const {
        steps, uiEvents, status: wsStatus, connected,
        frame, captcha, controlState, approval, viewport, sendAction,
    } = useTaskWebSocket(taskId);

    const activeStatus = wsStatus || task?.status || "pending";
    const isTerminal = TERMINAL_STATUSES.includes(activeStatus);

    const loadOutcome = useCallback(async () => {
        const [logs, results] = await Promise.all([
            api.getTaskLogs(taskId).catch(() => []),
            api.getTaskResults(taskId).catch(() => []),
        ]);
        setSavedLogs(logs);
        setStoredRows(results.length > 0 ? results[0].data?.items ?? [] : []);
    }, [taskId]);

    useEffect(() => {
        api.getTask(taskId)
            .then((t) => {
                setTask(t);
                if (TERMINAL_STATUSES.includes(t.status)) return loadOutcome();
            })
            .catch(console.error);
    }, [taskId, loadOutcome]);

    // Once the socket reports a terminal state, pull the persisted outcome.
    useEffect(() => {
        if (TERMINAL_STATUSES.includes(wsStatus)) loadOutcome();
    }, [wsStatus, loadOutcome]);

    const displaySteps: TaskStep[] = useMemo(() => {
        if (steps.length > 0) return steps;
        return savedLogs.map((log) => ({
            step: log.step_number,
            action: log.action ?? "",
            description: log.details?.description || log.action || "",
            status: log.details?.status || "completed",
            details: log.details ?? {},
            timestamp: log.created_at,
        }));
    }, [steps, savedLogs]);

    const rows: ExtractedRow[] = useMemo(() => {
        if (storedRows && storedRows.length > 0) return storedRows;
        const fromStream = displaySteps.find((s) => s.action.startsWith("task_"))?.details?.results;
        return Array.isArray(fromStream) ? fromStream : (storedRows ?? []);
    }, [storedRows, displaySteps]);

    const sortedRows = useMemo(() => {
        const copy = [...rows];
        if (sortBy === "price") {
            return copy.sort((a, b) => (numericPrice(a) ?? Infinity) - (numericPrice(b) ?? Infinity));
        }
        if (sortBy === "rating") {
            return copy.sort((a, b) => Number(b.rating ?? 0) - Number(a.rating ?? 0));
        }
        return copy;
    }, [rows, sortBy]);

    const cheapestIndex = useMemo(() => {
        let best = -1;
        let bestPrice = Infinity;
        sortedRows.forEach((row, idx) => {
            const price = numericPrice(row);
            if (price !== null && price < bestPrice) {
                bestPrice = price;
                best = idx;
            }
        });
        return best;
    }, [sortedRows]);

    const hasPrices = sortedRows.some((r) => numericPrice(r) !== null);
    const hasRatings = sortedRows.some((r) => r.rating);
    const summary = displaySteps.find((s) => s.action.startsWith("task_"))?.details?.summary;

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

    const badge = STATUS_BADGES[activeStatus] ?? STATUS_BADGES.pending;

    return (
        <div className="h-full flex flex-col p-4 gap-3 overflow-hidden relative">
            {activeStatus === "running" && (
                <div className="ambient-glow w-64 h-64 bg-[rgba(198,198,198,0.02)] top-0 right-20" />
            )}

            {/* Header */}
            <div className="glass-card px-5 py-3 flex items-center justify-between gap-4 shrink-0 relative z-10 anim-fade-up">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                        <h1
                            className="text-base font-extrabold text-[#f9f9f9] truncate max-w-2xl tracking-tight"
                            title={task.goal}
                        >
                            {task.goal}
                        </h1>
                        <span className={`badge ${badge.badge}`}>
                            {activeStatus === "running" && (
                                <span className="w-1 h-1 rounded-full bg-[#fbbf24] pulse-dot" />
                            )}
                            {badge.label}
                        </span>
                        {!connected && !isTerminal && (
                            <span className="badge badge-danger">
                                <span className="w-1 h-1 rounded-full bg-[#ee7d77]" />
                                Disconnected
                            </span>
                        )}
                    </div>
                    <p className="text-[10px] text-[#888787] font-mono mt-0.5">{task.id}</p>
                    {isTerminal && (summary || task.error_message) && (
                        <p className="text-[11px] text-[#a8a7a6] mt-1 truncate">
                            {summary || task.error_message}
                        </p>
                    )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    {!isTerminal && (
                        <button
                            onClick={async () => {
                                try {
                                    await api.cancelTask(taskId);
                                } catch (e) {
                                    console.error(e);
                                }
                            }}
                            className="btn-ghost text-xs flex items-center gap-1 text-[#ee7d77] border-[rgba(238,125,119,0.2)] hover:bg-[rgba(238,125,119,0.08)]"
                        >
                            <span className="material-symbols-rounded text-sm">stop_circle</span>
                            Cancel
                        </button>
                    )}
                    {isTerminal && (
                        <button
                            onClick={async () => {
                                try {
                                    const next = await api.createTask(task.goal);
                                    await api.startTask(next.id);
                                    window.location.href = `/tasks/${next.id}`;
                                } catch (e) {
                                    console.error(e);
                                }
                            }}
                            className="btn-ghost text-xs flex items-center gap-1"
                        >
                            <span className="material-symbols-rounded text-sm">replay</span>
                            Run again
                        </button>
                    )}
                    {rows.length > 0 && (
                        <button
                            onClick={() => navigator.clipboard.writeText(JSON.stringify(rows, null, 2))}
                            className="btn-ghost text-xs flex items-center gap-1"
                        >
                            <span className="material-symbols-rounded text-sm">content_copy</span>
                            Copy JSON
                        </button>
                    )}
                    <button
                        onClick={() => setShowRawLogs(!showRawLogs)}
                        className="btn-ghost text-xs flex items-center gap-1"
                    >
                        <span className="material-symbols-rounded text-sm">
                            {showRawLogs ? "visibility_off" : "data_object"}
                        </span>
                        {showRawLogs ? "Hide" : "Raw log"}
                    </button>
                </div>
            </div>

            {/* Body */}
            <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-3 relative z-10">
                <div
                    className="w-full lg:w-[340px] xl:w-[380px] shrink-0 h-full anim-fade-up"
                    style={{ animationDelay: "0.1s" }}
                >
                    <ExecutionFeed
                        events={uiEvents}
                        steps={displaySteps.filter(
                            (s) => s.action !== "screencast_frame" && !s.action.startsWith("task_")
                        )}
                        status={activeStatus}
                    />
                </div>

                <div
                    className="flex-1 flex flex-col gap-3 min-h-0 min-w-0 relative anim-fade-up"
                    style={{ animationDelay: "0.2s" }}
                >
                    {showRawLogs && (
                        <div className="absolute inset-0 z-50 bg-[#0a0a0a] rounded-2xl border border-[rgba(72,72,72,0.1)] p-4 overflow-y-auto shadow-2xl">
                            <div className="flex items-center justify-between mb-4 border-b border-[rgba(72,72,72,0.1)] pb-2">
                                <h3 className="font-mono text-[#c6c6c6] font-bold text-xs flex items-center gap-2">
                                    <span className="material-symbols-rounded text-sm">data_object</span>
                                    RAW EVENT LOG
                                </h3>
                                <button
                                    onClick={() => setShowRawLogs(false)}
                                    className="text-[#888787] hover:text-[#c6c6c6] text-xs transition-colors"
                                >
                                    ✕
                                </button>
                            </div>
                            <pre className="text-[10px] text-[#4ade80] font-mono whitespace-pre-wrap break-all">
                                {displaySteps
                                    .map((s) => JSON.stringify({ step: s.step, action: s.action, ...s.details }, null, 2))
                                    .join("\n\n---\n\n")}
                            </pre>
                        </div>
                    )}

                    {(!isTerminal || frame) && (
                        <div
                            className={`transition-all duration-500 ${
                                isTerminal && rows.length > 0 ? "h-64 shrink-0" : "flex-1 min-h-0"
                            }`}
                        >
                            <LiveBrowserPanel
                                frame={frame}
                                captcha={captcha}
                                controlState={controlState}
                                approval={approval}
                                viewport={viewport}
                                onSendAction={sendAction}
                            />
                        </div>
                    )}

                    {rows.length > 0 && (
                        <div className="flex-1 min-h-0 flex flex-col">
                            <div className="flex items-center justify-between mb-3 shrink-0 px-1">
                                <h2 className="text-sm font-extrabold text-[#e7e5e4] flex items-center gap-2">
                                    <span className="material-symbols-rounded text-base text-[#888787]">
                                        inventory_2
                                    </span>
                                    Extracted data
                                    <span className="badge badge-chrome">{rows.length}</span>
                                </h2>

                                {(hasPrices || hasRatings) && (
                                    <div className="flex gap-0.5 bg-[#0a0a0a] rounded-xl p-0.5 border border-[rgba(72,72,72,0.08)]">
                                        {([
                                            ["default", "As found"],
                                            ...(hasPrices ? [["price", "Price"] as const] : []),
                                            ...(hasRatings ? [["rating", "Rating"] as const] : []),
                                        ] as [SortKey, string][]).map(([key, label]) => (
                                            <button
                                                key={key}
                                                onClick={() => setSortBy(key)}
                                                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${
                                                    sortBy === key
                                                        ? "bg-gradient-to-r from-[#c6c6c6] to-[#9b9ea3] text-[#0e0e0e]"
                                                        : "text-[#888787] hover:text-[#a8a7a6]"
                                                }`}
                                            >
                                                {label}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex-1 overflow-y-auto px-1 pb-2">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3 anim-stagger">
                                    {sortedRows.map((row, idx) => (
                                        <ResultCard
                                            key={idx}
                                            row={row}
                                            rank={idx + 1}
                                            isCheapest={hasPrices && idx === cheapestIndex}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {isTerminal && rows.length === 0 && (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center text-[#888787] max-w-md">
                                <span className="material-symbols-rounded text-5xl mb-3 block text-[#262626]">
                                    inventory_2
                                </span>
                                <p className="text-sm font-bold text-[#a8a7a6] mb-1">No data extracted</p>
                                <p className="text-xs text-[#888787]">
                                    {summary || task.error_message || "The agent finished without collecting structured data."}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
