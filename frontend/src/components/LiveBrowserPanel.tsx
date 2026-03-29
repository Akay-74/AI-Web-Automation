"use client";

interface LiveBrowserPanelProps {
    screenshotBase64: string | null;
}

export function LiveBrowserPanel({ screenshotBase64 }: LiveBrowserPanelProps) {
    return (
        <div className="rounded-xl overflow-hidden border border-slate-800 shadow-xl bg-black flex flex-col h-full">
            {/* Browser Chrome Context */}
            <div className="bg-slate-900 border-b border-slate-800 p-3 flex items-center gap-4 shrink-0 shadow-sm z-10">
                <div className="flex gap-2 shrink-0">
                    <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                </div>

                <div className="flex-1 bg-black/50 border border-slate-800 rounded px-4 py-1.5 text-xs text-slate-400 flex justify-between items-center max-w-lg mx-auto overflow-hidden">
                    <span className="truncate">agent-session-window</span>
                    <span className="flex items-center gap-2 text-[10px] font-bold tracking-wider text-red-400 shrink-0">
                        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                        LIVE
                    </span>
                </div>
                <div className="w-[52px]"></div> {/* Spacer for symmetry */}
            </div>

            {/* Browser Render Context */}
            <div className="relative flex-1 bg-[#12121a] overflow-hidden flex items-center justify-center">
                {screenshotBase64 ? (
                    <img
                        src={`data:image/png;base64,${screenshotBase64}`}
                        alt="Agent browser view"
                        className="w-full h-full object-contain object-top"
                    />
                ) : (
                    <div className="text-center p-8 text-slate-500">
                        <div className="w-12 h-12 border-4 border-slate-800 border-t-brand-500 rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-sm">Connecting to headless browser...</p>
                    </div>
                )}
            </div>
        </div>
    );
}
