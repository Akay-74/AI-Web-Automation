"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Task } from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";

type FilterTab = "all" | "completed" | "running" | "failed" | "cancelled";

export default function HistoryPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<FilterTab>("all");
    const [search, setSearch] = useState("");
    const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        api.listTasks(undefined, 100
            
        ).then(res => { setTasks(res.tasks); setLoading(false); }).catch(() => setLoading(false));
    }, []);

    const filtered = (activeTab === "all" ? tasks : tasks.filter(t => t.status === activeTab))
        .filter(t => !search || t.goal.toLowerCase().includes(search.toLowerCase()));

    const stats = {
        total: tasks.length,
        completed: tasks.filter(t => t.status === "completed").length,
        failed: tasks.filter(t => t.status === "failed").length,
        running: tasks.filter(t => t.status === "running").length,
    };

    const tabs: { key: FilterTab; label: string }[] = [
        { key: "all", label: "All" },
        { key: "completed", label: "Verified" },
        { key: "running", label: "Active" },
        { key: "failed", label: "Faulted" },
        { key: "cancelled", label: "Archived" },
    ];

    const statusConfig: Record<string, { badge: string; dot: string; label: string }> = {
        completed: { badge: "badge-success", dot: "bg-[#4ade80]", label: "Verified" },
        running: { badge: "badge-warning", dot: "bg-[#fbbf24] pulse-dot", label: "Active Cycle" },
        failed: { badge: "badge-danger", dot: "bg-[#ee7d77]", label: "Critical Fault" },
        pending: { badge: "badge-chrome", dot: "bg-[#767575]", label: "Queued" },
        cancelled: { badge: "badge-chrome", dot: "bg-[#666666]", label: "Archived" },
    };

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 60) return `${mins}m lapsed`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h lapsed`;
        return `${Math.floor(hrs / 24)}d lapsed`;
    };

    return (
        <div className="min-h-screen p-8 relative overflow-hidden">
            <div className="ambient-glow w-72 h-72 bg-[rgba(198,198,198,0.02)] top-10 right-20" />

            <div className="max-w-5xl mx-auto relative z-10">
                {/* Header */}
                <div className="flex items-start justify-between mb-8 anim-fade-up">
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight gradient-text mb-1">Task History</h1>
                        <p className="text-xs text-[#a8a7a6]">Archive of all neural operations executed by the kinetic engine</p>
                    </div>
                    <Link href="/tasks/new" className="btn-chrome text-sm flex items-center gap-1.5">
                        <span className="material-symbols-rounded text-base">add</span>
                        New Task
                    </Link>
                </div>

                {/* Search */}
                <div className="mb-5 anim-fade-up" style={{ animationDelay: "0.05s" }}>
                    <div className="relative max-w-md">
                        <span className="material-symbols-rounded absolute left-3 top-1/2 -translate-y-1/2 text-[#666] text-lg">search</span>
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Search operations..."
                            className="input-obsidian pl-10 py-2.5 text-sm"
                        />
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-3 mb-8 anim-stagger">
                    {[
                        { label: "Total Operations", value: stats.total, color: "text-[#e7e5e4]" },
                        { label: "Verified Success", value: stats.completed, color: "text-[#4ade80]" },
                        { label: "Critical Faults", value: stats.failed, color: "text-[#ee7d77]" },
                        { label: "Active Cycles", value: stats.running, color: "text-[#fbbf24]" },
                    ].map(s => (
                        <div key={s.label} className="obsidian-card p-4">
                            <div className={`text-2xl font-extrabold ${s.color} tracking-tight`}>
                                {loading ? <div className="shimmer h-7 w-12 rounded" /> : s.value}
                            </div>
                            <p className="text-[10px] text-[#888787] font-semibold uppercase tracking-widest mt-1">{s.label}</p>
                        </div>
                    ))}
                </div>

                {/* Filter Tabs */}
                <div className="flex gap-1 mb-6 bg-[#0a0a0a] rounded-xl p-1 w-fit anim-fade-up" style={{ animationDelay: "0.15s" }}>
                    {tabs.map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300 ${activeTab === tab.key
                                ? "bg-gradient-to-r from-[#c6c6c6] to-[#9b9ea3] text-[#0e0e0e]"
                                : "text-[#a8a7a6] hover:text-[#d4d3d2] hover:bg-[#131313]"
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Task List */}
                {loading ? (
                    <div className="space-y-3">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="shimmer h-20 rounded-xl" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-24 text-center anim-fade-up">
                        <span className="material-symbols-rounded text-5xl text-[#262626] mb-4">inventory_2</span>
                        <h3 className="text-lg font-bold text-[#a8a7a6] mb-1">Empty Vault</h3>
                        <p className="text-xs text-[#888787] mb-6">No operations match the current filter.</p>
                        <Link href="/tasks/new" className="btn-chrome text-sm">Initialize First Task</Link>
                    </div>
                ) : (
                    <div className="space-y-2 anim-stagger">
                        {filtered.map((task) => {
                            const cfg = statusConfig[task.status] || statusConfig.pending;
                            return (
                                <div key={task.id} className="obsidian-card flex items-center p-4 gap-4 group">
                                    {/* Status dot */}
                                    <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />

                                    {/* Content — clickable */}
                                    <Link href={`/tasks/${task.id}`} className="flex-1 min-w-0">
                                        <h3 className="text-sm font-bold text-[#e7e5e4] truncate group-hover:text-[#f9f9f9] transition-colors">
                                            {task.goal}
                                        </h3>
                                        <p className="text-[10px] text-[#888787] font-mono mt-0.5">
                                            {task.id.slice(0, 8)} • {timeAgo(task.created_at)}
                                        </p>
                                    </Link>

                                    {/* Badge */}
                                    <span className={`badge ${cfg.badge} shrink-0`}>{cfg.label}</span>

                                    {/* Delete */}
                                    <button
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            setDeleteTarget(task);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 transition-opacity text-[#666] hover:text-[#ee7d77] shrink-0"
                                        title="Delete task"
                                    >
                                        <span className="material-symbols-rounded text-lg">delete</span>
                                    </button>

                                    {/* Arrow */}
                                    <Link href={`/tasks/${task.id}`} className="shrink-0">
                                        <span className="material-symbols-rounded text-[#262626] group-hover:text-[#a8a7a6] transition-colors text-lg">
                                            chevron_right
                                        </span>
                                    </Link>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Pagination */}
                {filtered.length > 0 && (
                    <div className="flex items-center justify-between mt-6 text-[10px] text-[#888787] uppercase tracking-widest font-semibold anim-fade-up">
                        <span>Archive Index 1-{filtered.length} of {tasks.length}</span>
                    </div>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            <ConfirmDialog
                open={!!deleteTarget}
                title="Delete Operation"
                message={deleteTarget ? `This will permanently remove "${deleteTarget.goal.length > 60 ? deleteTarget.goal.slice(0, 60) + '…' : deleteTarget.goal}" and all its logs and results. This cannot be undone.` : ""}
                confirmLabel={deleting ? "Deleting..." : "Delete"}
                variant="danger"
                onCancel={() => setDeleteTarget(null)}
                onConfirm={async () => {
                    if (!deleteTarget || deleting) return;
                    setDeleting(true);
                    try {
                        await api.deleteTask(deleteTarget.id);
                        setTasks(prev => prev.filter(t => t.id !== deleteTarget.id));
                    } catch { }
                    setDeleting(false);
                    setDeleteTarget(null);
                }}
            />
        </div>
    );
}
