"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";


const navSections = [
    {
        items: [
            { href: "/", label: "Orchestrator", icon: "memory" },
            { href: "/tasks/new", label: "Neural Flow", icon: "account_tree" },
            { href: "/history", label: "Vault", icon: "database" },
            { href: "/analytics", label: "Analytics", icon: "monitoring" },
        ]
    },
    {
        items: [
            { href: "/terminal", label: "Terminal", icon: "terminal" },
            { href: "/support", label: "Support", icon: "help" },
        ]
    }
];

export function Sidebar() {
    const pathname = usePathname();
    const isTaskDetail = pathname.startsWith("/tasks/") && pathname !== "/tasks/new";
    const [open, setOpen] = useState(true);
    const [isWorkingMode, setIsWorkingMode] = useState(false);
    const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Auto-collapse when a task is running (task detail page), expand everywhere else
    useEffect(() => {
        if (!isTaskDetail) {
            setIsWorkingMode(false);
            setOpen(true);
            return;
        }

        // Extract task ID from /tasks/[id]
        const taskId = pathname.split('/').pop();
        if (!taskId) return;

        let active = true;

        // Fetch real task status
        api.getTask(taskId).then(task => {
            if (!active) return;
            // Only collapse if the task is actively running or queued
            if (task.status === "running" || task.status === "queued") {
                setIsWorkingMode(true);
                setOpen(false);
            } else {
                setIsWorkingMode(false);
                setOpen(true);
            }
        }).catch(err => {
            console.error("Failed to fetch task status for sidebar:", err);
            // Default to open on error
            if (active) {
                setIsWorkingMode(false);
                setOpen(true);
            }
        });

        return () => { active = false; };
    }, [pathname, isTaskDetail]);

    const handleMouseEnter = () => {
        if (!isWorkingMode) return;
        if (closeTimer.current) clearTimeout(closeTimer.current);
        setOpen(true);
    };

    const handleMouseLeave = () => {
        if (!isWorkingMode) return;
        closeTimer.current = setTimeout(() => setOpen(false), 200);
    };

    return (
        <>
            {/* Spacer for static mode so content isn't covered (layout.tsx uses flex row) */}
            {!isWorkingMode && (
                <div className="w-[220px] shrink-0 hidden md:block" />
            )}

            {/* Tab handle — only visible when sidebar is closed in working mode */}
            {isWorkingMode && (
                <div
                    className={`fixed left-0 top-1/2 -translate-y-1/2 z-40 transition-all duration-300 ${open ? "opacity-0 pointer-events-none -translate-x-2" : "opacity-100"}`}
                    onMouseEnter={handleMouseEnter}
                >
                    <div className="
                    flex items-center justify-center
                    w-6 h-16 ml-0
                    bg-[#131313] border border-l-0 border-[rgba(120,120,120,0.15)]
                    rounded-r-xl cursor-pointer
                    hover:bg-[rgba(198,198,198,0.06)] hover:border-[rgba(198,198,198,0.2)]
                    transition-all duration-300
                    group
                ">
                        <span className="
                        material-symbols-rounded text-[14px] text-[#666]
                        group-hover:text-[#c6c6c6] transition-colors duration-200
                        select-none
                    " style={{ fontVariationSettings: "'FILL' 0, 'wght' 300" }}>
                            chevron_right
                        </span>
                    </div>
                </div>
            )}

            {/* Overlay backdrop (subtle) */}
            <div
                className={`fixed inset-0 z-30 transition-opacity duration-300 ${(open && isWorkingMode) ? "opacity-100" : "opacity-0 pointer-events-none"}`}
                onMouseEnter={handleMouseLeave}
            />

            {/* Sidebar panel */}
            <aside
                className={`
                    fixed left-0 top-0 h-full z-40
                    w-[220px] flex flex-col
                    bg-[#0a0a0a]/95 backdrop-blur-xl
                    border-r border-[rgba(120,120,120,0.12)]
                    shadow-[4px_0_32px_rgba(0,0,0,0.6)]
                    transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]
                    ${open ? "translate-x-0" : "-translate-x-full"}
                    overflow-hidden
                `}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                {/* Ambient glow orb */}
                <div className="ambient-glow w-32 h-32 bg-[rgba(198,198,198,0.04)] top-10 -left-10" />

                {/* Logo */}
                <div className="px-5 pt-6 pb-5 relative z-10">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#e2e2e2] to-[#9b9ea3] flex items-center justify-center transition-all group-hover:shadow-[0_0_20px_rgba(198,198,198,0.25)]">
                            <span className="text-[#0e0e0e] font-extrabold text-[10px] tracking-wider">AI</span>
                        </div>
                        <div>
                            <h1 className="text-sm font-extrabold text-[#f9f9f9] tracking-tight leading-none">Kinetic AI</h1>
                            <p className="text-[10px] text-[#888787] font-medium tracking-wider mt-0.5">PRECISION ENGINE</p>
                        </div>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-3 mt-1 relative z-10 space-y-4">
                    {navSections.map((section, sIdx) => (
                        <div key={sIdx}>
                            <ul className="space-y-0.5 anim-stagger">
                                {section.items.map((item) => {
                                    const isActive = pathname === item.href || (item.href === "/" && isTaskDetail);
                                    return (
                                        <li key={item.href}>
                                            <Link
                                                href={item.href}
                                                onClick={() => setOpen(false)}
                                                className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-semibold
                                                    transition-all duration-300
                                                    ${isActive
                                                        ? "text-[#f9f9f9] bg-[rgba(198,198,198,0.08)]"
                                                        : "text-[#888787] hover:text-[#d4d3d2] hover:bg-[rgba(198,198,198,0.04)]"
                                                    }`}
                                            >
                                                {isActive && (
                                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-gradient-to-b from-[#e2e2e2] to-[#9b9ea3] nav-indicator" />
                                                )}
                                                <span className="material-symbols-rounded text-lg opacity-80" style={{ fontVariationSettings: "'FILL' 0, 'wght' 400" }}>
                                                    {item.icon}
                                                </span>
                                                <span>{item.label}</span>
                                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                            {sIdx < navSections.length - 1 && (
                                <div className="my-3 mx-3 h-px bg-[rgba(120,120,120,0.08)]" />
                            )}
                        </div>
                    ))}
                </nav>

                {/* System Status */}
                <div className="px-4 py-3 border-t border-[rgba(120,120,120,0.08)] relative z-10">
                    <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#4ade80] pulse-dot" />
                        <span className="text-[10px] font-bold text-[#4ade80] uppercase tracking-widest">Active System</span>
                    </div>
                    <p className="text-[10px] text-[#666] font-medium">Liquid Core v4.2</p>
                </div>

                {/* User Profile */}
                <div className="px-4 py-3 border-t border-[rgba(120,120,120,0.08)] relative z-10">
                    <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#c6c6c6] to-[#484848] flex items-center justify-center text-[9px] font-extrabold text-[#0e0e0e]">K</div>
                        <div>
                            <p className="text-[11px] font-bold text-[#d4d3d2] leading-none">K. Architect</p>
                            <p className="text-[9px] text-[#888787] mt-0.5">Master Auth</p>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    );
}
