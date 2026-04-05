"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

const quickGoals = [
    { label: "E-Commerce Arbitrage", goal: "Find the cheapest RTX 4060 laptop on Amazon" },
    { label: "Lead Generation", goal: "Find 10 AI startup founders on LinkedIn with contact info" },
    { label: "News Intelligence", goal: "Collect top 10 AI headlines from TechCrunch today" },
    { label: "Job Scanner", goal: "Find remote Python developer jobs under $150k on Indeed" },
];

export default function NewTaskPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [goal, setGoal] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [maxSteps, setMaxSteps] = useState(15);

    useEffect(() => {
        const prefill = searchParams.get("goal");
        if (prefill) setGoal(prefill);
    }, [searchParams]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!goal.trim()) return;
        setSubmitting(true);
        try {
            const task = await api.createTask(goal);
            await api.startTask(task.id);
            router.push(`/tasks/${task.id}`);
        } catch (err) {
            console.error(err);
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen p-8 flex items-start justify-center relative overflow-hidden">
            {/* Ambient glow */}
            <div className="ambient-glow w-80 h-80 bg-[rgba(198,198,198,0.03)] top-20 right-10" />

            <div className="w-full max-w-2xl relative z-10 mt-8">
                {/* Header */}
                <div className="mb-10 anim-fade-up">
                    <h1 className="text-3xl font-extrabold tracking-tight gradient-text mb-2">Initialize Task</h1>
                    <p className="text-sm text-[#a8a7a6] leading-relaxed">
                        Define your neural objective. The kinetic engine will execute multi-step operations across the digital plane.
                    </p>
                </div>

                {/* Task Form */}
                <form onSubmit={handleSubmit} className="space-y-6 anim-fade-up" style={{ animationDelay: "0.1s" }}>

                    {/* Objective Input */}
                    <div className="glass-card p-6">
                        <label className="block text-[11px] font-bold text-[#a8a7a6] uppercase tracking-[0.15em] mb-3">
                            Neural Objective
                        </label>
                        <textarea
                            value={goal}
                            onChange={(e) => setGoal(e.target.value)}
                            placeholder="Describe your automation target in natural language..."
                            rows={4}
                            className="input-obsidian resize-none"
                        />

                        {/* Quick fill chips */}
                        <div className="mt-4">
                            <p className="text-[10px] text-[#888787] uppercase tracking-widest font-semibold mb-2">Quick Deploy Templates</p>
                            <div className="flex flex-wrap gap-2">
                                {quickGoals.map((q) => (
                                    <button
                                        key={q.label}
                                        type="button"
                                        onClick={() => setGoal(q.goal)}
                                        className="text-[11px] px-3 py-1.5 rounded-lg bg-[#1a1919] text-[#d4d3d2] hover:bg-[#262626] hover:text-[#e7e5e4] transition-all border border-[rgba(72,72,72,0.1)] hover:border-[rgba(72,72,72,0.3)] font-medium"
                                    >
                                        {q.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Advanced Options */}
                    <div className="obsidian-card overflow-hidden">
                        <button
                            type="button"
                            onClick={() => setShowAdvanced(!showAdvanced)}
                            className="w-full flex items-center justify-between p-4 text-sm text-[#a8a7a6] hover:text-[#d4d3d2] transition-colors"
                        >
                            <span className="flex items-center gap-2 font-semibold">
                                <span className="material-symbols-rounded text-lg">tune</span>
                                Advanced Configuration
                            </span>
                            <span className="material-symbols-rounded text-lg transition-transform" style={{ transform: showAdvanced ? "rotate(180deg)" : "" }}>
                                expand_more
                            </span>
                        </button>
                        {showAdvanced && (
                            <div className="px-4 pb-4 pt-0 anim-fade-up">
                                <label className="block text-[10px] font-bold text-[#888787] uppercase tracking-widest mb-2">
                                    Max Execution Steps
                                </label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range"
                                        min={5}
                                        max={50}
                                        value={maxSteps}
                                        onChange={(e) => setMaxSteps(Number(e.target.value))}
                                        className="flex-1 accent-[#c6c6c6] h-1"
                                    />
                                    <span className="text-sm font-bold text-[#e7e5e4] font-mono w-8 text-right">{maxSteps}</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Submit */}
                    <button
                        type="submit"
                        disabled={!goal.trim() || submitting}
                        className={`btn-chrome w-full flex items-center justify-center gap-2 py-4 text-base ${!goal.trim() || submitting ? "opacity-40 cursor-not-allowed" : ""
                            }`}
                    >
                        {submitting ? (
                            <>
                                <div className="w-4 h-4 border-2 border-[#0e0e0e] border-t-transparent rounded-full animate-spin" />
                                Initializing Neural Agent...
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-rounded">bolt</span>
                                Deploy Kinetic Agent
                            </>
                        )}
                    </button>

                    {/* Flow indicator */}
                    <div className="flex items-center justify-center gap-6 text-[10px] text-[#888787] uppercase tracking-widest font-semibold">
                        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#c6c6c6]" /> Input</span>
                        <span className="text-[#262626]">→</span>
                        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#666666]" /> Synthesis</span>
                        <span className="text-[#262626]">→</span>
                        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#666666]" /> Execution</span>
                        <span className="text-[#262626]">→</span>
                        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#666666]" /> Output</span>
                    </div>
                </form>
            </div>
        </div>
    );
}
