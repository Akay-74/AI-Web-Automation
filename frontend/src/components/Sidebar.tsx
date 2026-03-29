"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/", label: "Home", icon: "🏠" },
    { href: "/tasks/new", label: "New Task", icon: "✨" },
    { href: "/history", label: "History", icon: "📋" },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-64 border-r border-slate-800 bg-[#0d0d14] flex flex-col">
            {/* Logo */}
            <div className="p-6 border-b border-slate-800">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
                        AI
                    </div>
                    <div>
                        <h1 className="text-sm font-bold text-white">Web Agent</h1>
                        <p className="text-[10px] text-slate-500">Automation Platform</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4">
                <ul className="space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <li key={item.href}>
                                <Link
                                    href={item.href}
                                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm
                    transition-all duration-200
                    ${isActive
                                            ? "bg-brand-600/10 text-brand-400 border border-brand-500/20"
                                            : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                                        }`}
                                >
                                    <span>{item.icon}</span>
                                    <span>{item.label}</span>
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-slate-800">
                <div className="text-xs text-slate-600 text-center">
                    Powered by GPT-4o-mini + Playwright
                </div>
            </div>
        </aside>
    );
}
