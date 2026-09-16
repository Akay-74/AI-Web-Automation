"use client";

import { useCallback, useState } from "react";
import { ApprovalRequest, ControlState } from "@/lib/api";

interface LiveBrowserPanelProps {
    frame: string | null;
    captcha?: string | null;
    controlState?: ControlState;
    approval?: ApprovalRequest | null;
    viewport?: { width: number; height: number };
    onSendAction?: (action: Record<string, unknown>) => void;
}

const SPECIAL_KEYS = new Set([
    "Enter", "Tab", "Escape", "Backspace", "Delete",
    "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
    "Home", "End", "PageUp", "PageDown",
]);

const CONTROL_LABELS: Record<ControlState, string> = {
    AI_ACTIVE: "Agent driving",
    AI_PAUSED: "Paused",
    HUMAN_ACTIVE: "You are driving",
    WAITING_FOR_APPROVAL: "Waiting for you",
    COMPLETED: "Finished",
    FAILED: "Failed",
};

/**
 * The live browser view: a CDP screencast you can click into.
 *
 * The stream is rendered at the browser's own aspect ratio and is not
 * transformed, so a click's position within the image maps straight onto a
 * viewport coordinate.
 */
export function LiveBrowserPanel({
    frame,
    captcha = null,
    controlState = "AI_ACTIVE",
    approval = null,
    viewport = { width: 1440, height: 900 },
    onSendAction,
}: LiveBrowserPanelProps) {
    const [isFullscreen, setIsFullscreen] = useState(false);

    const humanDriving = controlState === "HUMAN_ACTIVE";
    const interactive = humanDriving || Boolean(captcha);

    const send = useCallback(
        (action: Record<string, unknown>) => onSendAction?.(action),
        [onSendAction]
    );

    const handleClick = useCallback(
        (e: React.MouseEvent<HTMLImageElement>) => {
            if (!interactive) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * viewport.width;
            const y = ((e.clientY - rect.top) / rect.height) * viewport.height;
            send({
                user_action: "click",
                x: Math.max(0, Math.min(viewport.width, x)),
                y: Math.max(0, Math.min(viewport.height, y)),
            });
        },
        [interactive, viewport, send]
    );

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (!interactive) return;
            if (SPECIAL_KEYS.has(e.key)) {
                e.preventDefault();
                send({ user_action: "keypress", key: e.key });
            } else if (e.key.length === 1) {
                e.preventDefault();
                send({ user_action: "type", text: e.key });
            }
        },
        [interactive, send]
    );

    const handleWheel = useCallback(
        (e: React.WheelEvent) => {
            if (!interactive) return;
            send({ user_action: "scroll", deltaX: e.deltaX, deltaY: e.deltaY });
        },
        [interactive, send]
    );

    const viewportBody = (
        <div
            className={`relative flex-1 bg-[#131313] overflow-hidden flex items-center justify-center ${interactive ? "cursor-crosshair" : ""}`}
            tabIndex={0}
            onKeyDown={handleKeyDown}
            onWheel={handleWheel}
        >
            {approval && (
                <div className="absolute top-0 left-0 right-0 z-30 bg-[#1c1507] border-b border-[#fbbf24]/40 px-4 py-3 flex items-center justify-between gap-3 backdrop-blur-sm">
                    <div className="min-w-0">
                        <p className="text-xs font-bold text-[#fbbf24] uppercase tracking-wider">
                            Approval needed
                        </p>
                        <p className="text-[11px] text-[#e7e5e4] truncate">{approval.reason}</p>
                        <p className="text-[10px] text-[#888787] truncate">{approval.description}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <button
                            onClick={() => send({ user_action: "approve_action" })}
                            className="px-3 py-1.5 bg-[#4ade80] text-[#0a0a0a] text-xs font-bold rounded-lg hover:bg-[#22c55e] transition-colors"
                        >
                            Approve
                        </button>
                        <button
                            onClick={() => send({ user_action: "reject_action" })}
                            className="px-3 py-1.5 bg-[#2a2a2a] text-[#ee7d77] text-xs font-bold rounded-lg hover:bg-[#3a3a3a] transition-colors"
                        >
                            Decline
                        </button>
                    </div>
                </div>
            )}

            {captcha && !approval && (
                <div className="absolute top-0 left-0 right-0 z-20 bg-[#1c1507] border-b border-[#fbbf24]/40 px-4 py-3 flex items-center justify-between gap-3 backdrop-blur-sm">
                    <div>
                        <p className="text-xs font-bold text-[#fbbf24] uppercase tracking-wider">
                            {captcha} challenge
                        </p>
                        <p className="text-[10px] text-[#c6c6c6]">
                            Solve it in the view below, then tell the agent to carry on.
                        </p>
                    </div>
                    <button
                        onClick={() => send({ user_action: "captcha_resume" })}
                        className="px-4 py-1.5 bg-[#4ade80] text-[#0a0a0a] text-xs font-bold rounded-lg hover:bg-[#22c55e] transition-colors shrink-0"
                    >
                        I solved it
                    </button>
                </div>
            )}

            {frame ? (
                <img
                    src={`data:image/jpeg;base64,${frame}`}
                    alt="Agent browser view"
                    className={`w-full h-full object-contain ${interactive ? "select-none" : ""}`}
                    onClick={handleClick}
                    draggable={false}
                />
            ) : (
                <div className="text-center p-8">
                    <div className="w-10 h-10 border-2 border-[#262626] border-t-[#c6c6c6] rounded-full animate-spin mx-auto mb-3" />
                    <p className="text-xs text-[#888787] font-medium">Waiting for the browser stream...</p>
                </div>
            )}

            {interactive && (
                <div className="absolute bottom-2 left-2 bg-[#4ade80]/20 border border-[#4ade80]/40 rounded-lg px-2.5 py-1 flex items-center gap-1.5 pointer-events-none">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] pulse-dot" />
                    <span className="text-[9px] font-bold text-[#4ade80] uppercase tracking-wider">
                        Your input is live
                    </span>
                </div>
            )}
        </div>
    );

    const chrome = (
        <div className="bg-[#1a1a1a] border-b border-[rgba(72,72,72,0.2)] flex h-10 items-center gap-3 px-3 shrink-0">
            <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#28c940]/60" />
            </div>

            <span className="text-xs text-[#888787] font-mono">agent browser</span>

            <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                    humanDriving
                        ? "bg-[#4ade80]/15 text-[#4ade80]"
                        : controlState === "AI_ACTIVE"
                          ? "bg-[#c6c6c6]/10 text-[#c6c6c6]"
                          : "bg-[#fbbf24]/15 text-[#fbbf24]"
                }`}
            >
                {CONTROL_LABELS[controlState]}
            </span>

            <div className="flex-1" />

            <div className="flex items-center gap-1.5">
                {humanDriving ? (
                    <button
                        onClick={() => send({ user_action: "give_control_back" })}
                        className="btn-ghost text-[11px] px-2 py-1"
                        title="Hand the browser back to the agent"
                    >
                        Give back to agent
                    </button>
                ) : (
                    <button
                        onClick={() => send({ user_action: "take_control" })}
                        className="btn-ghost text-[11px] px-2 py-1"
                        title="Drive the browser yourself"
                    >
                        Take control
                    </button>
                )}

                {controlState === "AI_ACTIVE" && (
                    <button
                        onClick={() => send({ user_action: "pause" })}
                        className="btn-ghost text-[11px] px-2 py-1"
                        title="Pause the agent where it is"
                    >
                        Pause
                    </button>
                )}
                {controlState === "AI_PAUSED" && (
                    <button
                        onClick={() => send({ user_action: "resume" })}
                        className="btn-ghost text-[11px] px-2 py-1"
                        title="Let the agent carry on"
                    >
                        Resume
                    </button>
                )}

                <button
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="btn-ghost text-[11px] px-2 py-1"
                    title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
                >
                    {isFullscreen ? "Close" : "Expand"}
                </button>

                <span className="flex items-center gap-1.5 text-[10px] text-[#888787] pl-1">
                    <span
                        className={`w-1.5 h-1.5 rounded-full pulse-dot ${frame ? "bg-[#4ade80]" : "bg-[#ee7d77]"}`}
                    />
                    {frame ? "Streaming" : "No signal"}
                </span>
            </div>
        </div>
    );

    if (isFullscreen) {
        return (
            <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex flex-col">
                {chrome}
                {viewportBody}
            </div>
        );
    }

    return (
        <div className="rounded-2xl overflow-hidden border border-[rgba(72,72,72,0.1)] bg-[#0a0a0a] flex flex-col h-full">
            {chrome}
            {viewportBody}
        </div>
    );
}
