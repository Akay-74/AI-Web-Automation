"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function NewTaskForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [goal, setGoal] = useState(searchParams.get("goal") || "");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!goal.trim()) return;

        setLoading(true);
        setError("");
        try {
            const task = await api.createTask(goal.trim());
            // Auto-start the task
            await api.startTask(task.id);
            router.push(`/tasks/${task.id}`);
        } catch (err: any) {
            setError(err.message || "Failed to create task");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto py-12">
            <h1 className="text-3xl font-bold mb-2 gradient-text">New Task</h1>
            <p className="text-slate-400 mb-8">
                Describe what you want the AI agent to do on the web.
            </p>

            <form onSubmit={handleSubmit}>
                <div className="glass-card p-6 mb-4">
                    <label htmlFor="goal" className="block text-sm font-medium text-slate-300 mb-2">
                        Your Goal
                    </label>
                    <textarea
                        id="goal"
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        placeholder='e.g., "Find the cheapest RTX 4060 laptop on Amazon"'
                        rows={4}
                        className="w-full bg-black/30 border border-slate-700 rounded-lg px-4 py-3
                       text-white placeholder-slate-500 focus:outline-none
                       focus:border-brand-500 focus:ring-1 focus:ring-brand-500
                       transition-all resize-none"
                    />
                </div>

                {error && (
                    <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                        {error}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading || !goal.trim()}
                    className="w-full py-3 rounded-lg bg-brand-600 hover:bg-brand-500
                     disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-semibold transition-all duration-200 glow"
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Creating...
                        </span>
                    ) : (
                        "🚀 Launch Agent"
                    )}
                </button>
            </form>
        </div>
    );
}

export default function NewTaskPage() {
    return (
        <Suspense fallback={
            <div className="max-w-2xl mx-auto py-12">
                <div className="w-8 h-8 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mx-auto" />
            </div>
        }>
            <NewTaskForm />
        </Suspense>
    );
}
