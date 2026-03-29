"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Task } from "@/lib/api";

export default function HistoryPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.listTasks(undefined, 50, 0)
            .then((res) => setTasks(res.tasks))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const statusColors: Record<string, string> = {
        pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
        queued: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        running: "bg-brand-500/10 text-brand-400 border-brand-500/20",
        completed: "bg-green-500/10 text-green-400 border-green-500/20",
        failed: "bg-red-500/10 text-red-400 border-red-500/20",
        cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    };

    return (
        <div className="max-w-4xl mx-auto py-8">
            <h1 className="text-3xl font-bold mb-8 gradient-text">Task History</h1>

            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="w-8 h-8 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
                </div>
            ) : tasks.length === 0 ? (
                <div className="glass-card p-12 text-center">
                    <p className="text-slate-400 mb-4">No tasks yet.</p>
                    <Link href="/tasks/new" className="text-brand-400 hover:text-brand-300 underline">
                        Create your first task
                    </Link>
                </div>
            ) : (
                <div className="space-y-3">
                    {tasks.map((task) => (
                        <Link key={task.id} href={`/tasks/${task.id}`}>
                            <div className="glass-card p-4 hover:border-brand-500/30 transition-all cursor-pointer">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1 min-w-0">
                                        <p className="text-white font-medium truncate">{task.goal}</p>
                                        <p className="text-xs text-slate-500 mt-1">
                                            {new Date(task.created_at).toLocaleString()}
                                        </p>
                                    </div>
                                    <span className={`ml-4 px-2.5 py-1 rounded-full text-xs font-medium border ${statusColors[task.status] || ""}`}>
                                        {task.status}
                                    </span>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
