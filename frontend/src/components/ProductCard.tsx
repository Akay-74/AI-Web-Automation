"use client";

import { ProductResult } from "@/lib/api";

interface ProductCardProps {
    product: ProductResult;
    isCheapest?: boolean;
    rank?: number;
    allPrices?: number[];
}

export function ProductCard({ product, isCheapest, rank, allPrices = [] }: ProductCardProps) {
    const formatPrice = (price: number | null | undefined, currency: string = "USD") => {
        if (price === null || price === undefined) return "—";
        return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(price);
    };

    const isValid = product.is_valid !== false;
    const hasPrice = typeof product.price === "number";

    let priceScore: number | null = null;
    if (hasPrice && allPrices.length > 1) {
        const sorted = [...allPrices].sort((a, b) => a - b);
        const idx = sorted.indexOf(product.price!);
        priceScore = Math.round(100 - (idx / (sorted.length - 1)) * 100);
    }

    return (
        <div className={`relative flex flex-col rounded-2xl overflow-hidden transition-all duration-300 group ${isCheapest
                ? "bg-[#1a1919] glow-chrome"
                : isValid
                    ? "bg-[#131313] hover:bg-[#1a1919]"
                    : "bg-[#131313] opacity-60"
            }`} style={{ border: isCheapest ? "1px solid rgba(198,198,198,0.15)" : "1px solid rgba(72,72,72,0.1)" }}>

            {/* Chrome top bar for best match */}
            {isCheapest && (
                <div className="h-[2px] bg-gradient-to-r from-transparent via-[#c6c6c6] to-transparent" />
            )}

            <div className="p-5 flex flex-col gap-3 flex-1">
                {/* Rank + validity */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {rank !== undefined && <span className="text-[10px] font-mono text-[#888787]">#{rank}</span>}
                        {isCheapest && (
                            <span className="text-[10px] font-bold uppercase tracking-widest text-[#e7e5e4] bg-gradient-to-r from-[rgba(198,198,198,0.12)] to-[rgba(198,198,198,0.04)] px-2.5 py-0.5 rounded-full flex items-center gap-1">
                                <span className="material-symbols-rounded text-xs">stars</span>
                                Top Match
                            </span>
                        )}
                    </div>
                    <span className={`badge ${isValid ? "badge-success" : "badge-danger"}`}>
                        {isValid ? "Verified" : "Invalid"}
                    </span>
                </div>

                {/* Title */}
                <div>
                    <h3 className="text-sm font-bold text-[#e7e5e4] line-clamp-2 leading-snug group-hover:text-[#f9f9f9] transition-colors"
                        title={product.name || product.title}>
                        {product.name || product.title || "Extracted Item"}
                    </h3>
                    {(product.company || product.source) && (
                        <p className="text-[11px] text-[#a8a7a6] mt-0.5 truncate font-medium">{product.company || product.source}</p>
                    )}
                </div>

                {/* Price + rating */}
                {(hasPrice || product.rating) && (
                    <div className="flex items-end justify-between">
                        {hasPrice ? (
                            <span className={`text-2xl font-extrabold tracking-tight ${isCheapest ? "gradient-text-chrome" : "text-[#f9f9f9]"}`}>
                                {formatPrice(product.price, product.currency)}
                            </span>
                        ) : (
                            <span className="text-[#888787] text-sm">—</span>
                        )}
                        {product.rating && (
                            <span className="badge badge-warning">★ {product.rating}</span>
                        )}
                    </div>
                )}

                {/* Value score bar */}
                {priceScore !== null && (
                    <div>
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-[9px] text-[#888787] uppercase tracking-widest font-semibold">Value Index</span>
                            <span className={`text-[9px] font-bold ${priceScore >= 80 ? "text-[#4ade80]" : priceScore >= 50 ? "text-[#fbbf24]" : "text-[#ee7d77]"
                                }`}>{priceScore}/100</span>
                        </div>
                        <div className="h-[2px] bg-[#1a1919] rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700"
                                style={{
                                    width: `${priceScore}%`,
                                    background: priceScore >= 80 ? "linear-gradient(90deg,#4ade80,#22c55e)"
                                        : priceScore >= 50 ? "linear-gradient(90deg,#fbbf24,#f59e0b)"
                                            : "linear-gradient(90deg,#ee7d77,#ef4444)"
                                }} />
                        </div>
                    </div>
                )}

                {/* Specs */}
                {!product.summary && !product.content && (
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                        {[["GPU", product.gpu], ["CPU", product.cpu], ["RAM", product.ram], ["Disk", product.storage]].filter(([, v]) => v).map(([label, val]) => (
                            <div key={label} className={`flex gap-1.5 ${label === "GPU" ? "col-span-2" : ""}`}>
                                <span className="text-[#888787] w-7 shrink-0 font-semibold">{label}</span>
                                <span className="text-[#d4d3d2] truncate">{val}</span>
                            </div>
                        ))}
                    </div>
                )}

                {(product.summary || product.content) && (
                    <p className="text-[11px] text-[#a8a7a6] leading-relaxed line-clamp-3">{product.summary || product.content}</p>
                )}
            </div>

            {/* Action */}
            <div className="px-5 pb-5">
                {product.url && product.url !== "No link" && !product.url.toLowerCase().includes("no featured") ? (
                    <a href={product.url.startsWith("http") ? product.url : `https://${product.url}`}
                        target="_blank" rel="noreferrer"
                        className={`flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl text-xs font-bold transition-all ${isCheapest
                                ? "btn-chrome py-2.5"
                                : "bg-[#1a1919] hover:bg-[#262626] text-[#d4d3d2] hover:text-[#e7e5e4] border border-[rgba(72,72,72,0.1)]"
                            }`}>
                        <span className="material-symbols-rounded text-sm">open_in_new</span>
                        View Source
                    </a>
                ) : (
                    <button disabled className="w-full py-2.5 rounded-xl bg-[#0e0e0e] text-[#262626] text-xs font-semibold cursor-not-allowed">
                        No Link Available
                    </button>
                )}
            </div>
        </div>
    );
}
