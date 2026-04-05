"use client";

import { useEffect, useRef } from "react";

interface ConfirmDialogProps {
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: "danger" | "chrome";
    onConfirm: () => void;
    onCancel: () => void;
}

export function ConfirmDialog({
    open, title, message,
    confirmLabel = "Delete",
    cancelLabel = "Cancel",
    variant = "danger",
    onConfirm, onCancel,
}: ConfirmDialogProps) {
    const overlayRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onCancel();
        };
        window.addEventListener("keydown", handleKey);
        return () => window.removeEventListener("keydown", handleKey);
    }, [open, onCancel]);

    if (!open) return null;

    const isDanger = variant === "danger";

    return (
        <div
            ref={overlayRef}
            onClick={(e) => { if (e.target === overlayRef.current) onCancel(); }}
            className="fixed inset-0 z-[999] flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
        >
            <div className="w-full max-w-sm anim-fade-up" style={{ animationDuration: "0.2s" }}>
                <div className="bg-[#131313] rounded-2xl border border-[rgba(120,120,120,0.12)] shadow-2xl overflow-hidden">
                    {/* Top accent line */}
                    <div className={`h-[2px] ${isDanger
                        ? "bg-gradient-to-r from-transparent via-[#ee7d77] to-transparent"
                        : "bg-gradient-to-r from-transparent via-[#c6c6c6] to-transparent"}`}
                    />

                    <div className="p-6">
                        {/* Icon */}
                        <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${isDanger ? "bg-[rgba(238,125,119,0.1)]" : "bg-[rgba(198,198,198,0.08)]"
                            }`}>
                            <span className={`material-symbols-rounded text-2xl ${isDanger ? "text-[#ee7d77]" : "text-[#c6c6c6]"
                                }`}>
                                {isDanger ? "delete_forever" : "help"}
                            </span>
                        </div>

                        {/* Title */}
                        <h3 className="text-base font-extrabold text-[#f9f9f9] tracking-tight mb-1.5">{title}</h3>
                        <p className="text-[13px] text-[#a8a7a6] leading-relaxed">{message}</p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2.5 px-6 pb-6">
                        <button
                            onClick={onCancel}
                            className="flex-1 py-2.5 rounded-xl text-sm font-bold text-[#a8a7a6] bg-[#1a1919] hover:bg-[#262626] border border-[rgba(120,120,120,0.1)] transition-all"
                        >
                            {cancelLabel}
                        </button>
                        <button
                            onClick={onConfirm}
                            className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-1.5 ${isDanger
                                    ? "bg-[#ee7d77] hover:bg-[#e96b64] text-[#0e0e0e]"
                                    : "btn-chrome"
                                }`}
                        >
                            <span className="material-symbols-rounded text-base">
                                {isDanger ? "delete" : "check"}
                            </span>
                            {confirmLabel}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
