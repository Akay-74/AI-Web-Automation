"use client";

import { useState, useRef, useCallback } from "react";

interface LiveBrowserPanelProps {
    screenshotBase64: string | null;
    captchaDetected?: boolean;
    captchaType?: string;
    viewport?: { width: number; height: number };
    onSendAction?: (action: Record<string, unknown>) => void;
}

/**
 * Interactive Live Browser Panel — displays a smooth screencast stream
 * and forwards user mouse/keyboard actions back to the agent's browser
 * via WebSocket.
 *
 * Features:
 * - Click-to-interact: click anywhere on the screencast → forwarded to Playwright
 * - Keyboard input: type while panel is focused → forwarded to Playwright
 * - Scroll forwarding: mouse wheel events → forwarded to Playwright
 * - CAPTCHA alert banner with "I solved it" resume button
 * - Pop-out fullscreen modal for better visibility
 */
export function LiveBrowserPanel({
    screenshotBase64,
    captchaDetected = false,
    captchaType = "",
    viewport = { width: 1920, height: 1080 },
    onSendAction,
}: LiveBrowserPanelProps) {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isInteractive, setIsInteractive] = useState(false);
    const imgRef = useRef<HTMLImageElement | null>(null);
    const fullscreenImgRef = useRef<HTMLImageElement | null>(null);

    /**
     * Convert a mouse event on the displayed image to browser viewport coordinates.
     * The image may be scaled down, so we calculate the ratio.
     */
    const getViewportCoords = useCallback(
        (e: React.MouseEvent<HTMLImageElement>) => {
            const img = e.currentTarget;
            const rect = img.getBoundingClientRect();
            // Calculate displayed image dimensions (accounting for object-contain)
            const imgAspect = viewport.width / viewport.height;
            const containerAspect = rect.width / rect.height;

            let displayW: number, displayH: number, offsetX: number, offsetY: number;
            if (imgAspect > containerAspect) {
                displayW = rect.width;
                displayH = rect.width / imgAspect;
                offsetX = 0;
                offsetY = (rect.height - displayH) / 2;
            } else {
                displayH = rect.height;
                displayW = rect.height * imgAspect;
                offsetX = (rect.width - displayW) / 2;
                offsetY = 0;
            }

            const relX = (e.clientX - rect.left - offsetX) / displayW;
            const relY = (e.clientY - rect.top - offsetY) / displayH;

            // Clamp to valid range
            const x = Math.max(0, Math.min(viewport.width, relX * viewport.width));
            const y = Math.max(0, Math.min(viewport.height, relY * viewport.height));
            return { x, y };
        },
        [viewport]
    );

    const handleClick = useCallback(
        (e: React.MouseEvent<HTMLImageElement>) => {
            if (!isInteractive || !onSendAction) return;
            const { x, y } = getViewportCoords(e);
            onSendAction({ user_action: "click", x, y });
        },
        [isInteractive, onSendAction, getViewportCoords]
    );

    // Throttle scroll events to prevent flooding the WebSocket
    const lastScrollRef = useRef<number>(0);
    const handleScroll = useCallback(
        (e: React.WheelEvent) => {
            if (!isInteractive || !onSendAction) return;
            e.preventDefault();
            const now = Date.now();
            if (now - lastScrollRef.current < 50) return; // max 20 events/sec
            lastScrollRef.current = now;
            onSendAction({ user_action: "scroll", deltaX: e.deltaX, deltaY: e.deltaY });
        },
        [isInteractive, onSendAction]
    );

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (!isInteractive || !onSendAction) return;
            e.preventDefault();
            // Special keys
            const specialKeys = [
                "Enter", "Tab", "Escape", "Backspace", "Delete",
                "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                "Home", "End", "PageUp", "PageDown",
            ];
            if (specialKeys.includes(e.key)) {
                onSendAction({ user_action: "keypress", key: e.key });
            } else if (e.key.length === 1) {
                onSendAction({ user_action: "type", text: e.key });
            }
        },
        [isInteractive, onSendAction]
    );

    const handleCaptchaResume = useCallback(() => {
        if (onSendAction) {
            onSendAction({ user_action: "captcha_resume" });
        }
    }, [onSendAction]);

    const renderViewport = (ref: React.RefObject<HTMLImageElement | null>, inModal: boolean) => (
        <div
            className={`relative flex-1 bg-[#131313] overflow-hidden flex items-center justify-center ${isInteractive ? "cursor-crosshair" : ""}`}
            tabIndex={0}
            onKeyDown={handleKeyDown}
            onWheel={handleScroll}
        >
            {/* CAPTCHA Alert Banner */}
            {captchaDetected && (
                <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-r from-[#ee7d77]/20 to-[#fbbf24]/20 border-b border-[#fbbf24]/30 px-4 py-3 flex items-center justify-between backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                        <span className="text-lg">⚠️</span>
                        <div>
                            <span className="text-xs font-bold text-[#fbbf24] uppercase tracking-wider">
                                {captchaType.toUpperCase()} Detected
                            </span>
                            <p className="text-[10px] text-[#c6c6c6]">
                                Solve the CAPTCHA below, then click &quot;I Solved It&quot;
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleCaptchaResume}
                        className="px-4 py-1.5 bg-[#4ade80] text-[#0a0a0a] text-xs font-bold rounded-lg hover:bg-[#22c55e] transition-colors flex items-center gap-1.5"
                    >
                        <span>✓</span> I Solved It
                    </button>
                </div>
            )}

            {screenshotBase64 ? (
                <img
                    ref={ref}
                    src={`data:image/jpeg;base64,${screenshotBase64}`}
                    alt="Agent browser view"
                    className={`w-full h-full object-contain object-top ${isInteractive ? "select-none" : ""}`}
                    style={{ willChange: "contents" }}
                    onClick={handleClick}
                    draggable={false}
                />
            ) : (
                <div className="text-center p-8">
                    <div className="w-10 h-10 border-2 border-[#262626] border-t-[#c6c6c6] rounded-full animate-spin mx-auto mb-3"></div>
                    <p className="text-xs text-[#888787] font-medium">Connecting to headless viewport...</p>
                </div>
            )}

            {/* Interactive mode overlay indicator */}
            {isInteractive && (
                <div className="absolute bottom-2 left-2 bg-[#4ade80]/20 border border-[#4ade80]/40 rounded-lg px-2.5 py-1 flex items-center gap-1.5 pointer-events-none">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] pulse-dot"></span>
                    <span className="text-[9px] font-bold text-[#4ade80] uppercase tracking-wider">Interactive</span>
                </div>
            )}
        </div>
    );

    return (
        <>
            {/* Inline panel */}
            <div className="rounded-2xl overflow-hidden border border-[rgba(72,72,72,0.1)] bg-[#0a0a0a] flex flex-col h-full">
                {/* Browser Chrome bar */}
                <div className="bg-[#0e0e0e] border-b border-[rgba(72,72,72,0.1)] px-4 py-2.5 flex items-center gap-3 shrink-0">
                    <div className="flex gap-1.5 shrink-0">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#ee7d77]/60"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-[#fbbf24]/60"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-[#4ade80]/60"></div>
                    </div>
                    <div className="flex-1 bg-[#000] rounded-lg px-4 py-1.5 text-[10px] text-[#888787] font-mono flex justify-between items-center max-w-md mx-auto border border-[rgba(72,72,72,0.08)]">
                        <span className="truncate">agent-kinetic-viewport</span>
                        <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-widest uppercase shrink-0">
                            {screenshotBase64 ? (
                                <span className="flex items-center gap-1.5 text-[#4ade80]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] pulse-dot"></span>
                                    Streaming
                                </span>
                            ) : (
                                <span className="flex items-center gap-1.5 text-[#ee7d77]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#ee7d77] pulse-dot"></span>
                                    Live
                                </span>
                            )}
                        </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        {/* Interactive toggle */}
                        <button
                            onClick={() => setIsInteractive(!isInteractive)}
                            className={`text-xs px-2.5 py-1 rounded-lg font-bold tracking-wider transition-all flex items-center gap-1.5 ${isInteractive
                                ? "bg-[#4ade80]/15 text-[#4ade80] border border-[#4ade80]/30"
                                : "text-[#888787] hover:text-[#c6c6c6] border border-transparent hover:border-[rgba(72,72,72,0.2)]"
                                }`}
                            title={isInteractive ? "Disable interaction" : "Enable interaction — click to control the browser"}
                        >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                            </svg>
                            <span className="text-[9px] uppercase">{isInteractive ? "On" : "Off"}</span>
                        </button>
                        {/* Pop-out button */}
                        <button
                            onClick={() => setIsFullscreen(true)}
                            className="text-[#888787] hover:text-[#c6c6c6] transition-colors p-1 rounded-lg hover:bg-[rgba(72,72,72,0.15)]"
                            title="Pop out fullscreen"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Viewport */}
                {renderViewport(imgRef, false)}
            </div>

            {/* Fullscreen Modal */}
            {isFullscreen && (
                <div
                    className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-sm flex flex-col"
                    onClick={(e) => { if (e.target === e.currentTarget) setIsFullscreen(false); }}
                >
                    {/* Modal header */}
                    <div className="flex items-center justify-between px-6 py-3 border-b border-[rgba(72,72,72,0.2)]">
                        <div className="flex items-center gap-3">
                            <div className="flex gap-1.5">
                                <div className="w-2.5 h-2.5 rounded-full bg-[#ee7d77]/60"></div>
                                <div className="w-2.5 h-2.5 rounded-full bg-[#fbbf24]/60"></div>
                                <div className="w-2.5 h-2.5 rounded-full bg-[#4ade80]/60"></div>
                            </div>
                            <span className="text-xs text-[#888787] font-mono">agent-kinetic-viewport</span>
                            <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-widest uppercase text-[#4ade80]">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#4ade80] pulse-dot"></span>
                                Streaming
                            </span>
                            {isInteractive && (
                                <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-widest uppercase text-[#fbbf24]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#fbbf24] pulse-dot"></span>
                                    Interactive
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsInteractive(!isInteractive)}
                                className={`text-xs px-3 py-1 rounded-lg font-bold transition-all ${isInteractive
                                    ? "bg-[#4ade80]/15 text-[#4ade80]"
                                    : "text-[#888787] hover:text-white"
                                    }`}
                            >
                                {isInteractive ? "🖱 Interactive ON" : "🖱 Enable Interaction"}
                            </button>
                            <button
                                onClick={() => setIsFullscreen(false)}
                                className="text-[#888787] hover:text-white transition-colors text-sm px-3 py-1 rounded-lg hover:bg-[rgba(72,72,72,0.2)] font-mono"
                            >
                                ESC ✕
                            </button>
                        </div>
                    </div>
                    {/* Modal body */}
                    <div className="flex-1 flex flex-col min-h-0">
                        {renderViewport(fullscreenImgRef, true)}
                    </div>
                </div>
            )}
        </>
    );
}
