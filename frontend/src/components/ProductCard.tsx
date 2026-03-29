"use client";

import { ProductResult } from "@/lib/api";

interface ProductCardProps {
    product: ProductResult;
    isCheapest?: boolean;
}

export function ProductCard({ product, isCheapest }: ProductCardProps) {
    const formatPrice = (price: number | null | undefined, currency: string = "USD") => {
        if (price === null || price === undefined) return "Unknown Price";
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: currency,
        }).format(price);
    };

    return (
        <div className={`relative flex flex-col p-5 bg-[#12121a] rounded-xl border transition-all hover:-translate-y-1 hover:shadow-lg ${isCheapest
            ? "border-brand-500 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
            : "border-slate-800 hover:border-slate-600"
            }`}>
            {isCheapest && (
                <div className="absolute -top-3 -right-3 bg-brand-500 text-white text-[10px] uppercase tracking-wider font-bold px-3 py-1 rounded-full shadow-md animate-bounce">
                    Cheapest Valid
                </div>
            )}

            {/* Header / Title */}
            <div className="mb-4 text-slate-100">
                <h3 className="font-semibold line-clamp-2 text-lg" title={product.name || product.title}>
                    {product.name || product.title || "Extracted Item"}
                </h3>
                {(product.company || product.source) && (
                    <div className="text-brand-400 text-sm font-medium mt-1">
                        {product.company || product.source}
                    </div>
                )}
            </div>

            {/* Price & Rating (Only if it's a product) */}
            {(product.price !== undefined || product.rating) && (
                <div className="flex items-end justify-between mb-4 pb-4 border-b border-slate-800/50">
                    <div>
                        {product.price !== undefined && product.price !== null ? (
                            <span className="text-2xl font-bold text-white tracking-tight">
                                {formatPrice(product.price, product.currency)}
                            </span>
                        ) : (
                            <span className="text-slate-500 font-medium">Price not listed</span>
                        )}
                    </div>
                    {product.rating && (
                        <div className="flex items-center gap-1 text-sm font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                            ★ {product.rating}
                        </div>
                    )}
                </div>
            )}

            {/* Content / Specs Grid */}
            <div className="flex-1 text-xs mb-4">
                {product.summary || product.content ? (
                    <p className="text-slate-400 leading-relaxed line-clamp-5 text-sm">
                        {product.summary || product.content}
                    </p>
                ) : (
                    <div className="grid grid-cols-2 gap-y-3 gap-x-2">
                        {product.gpu && (
                            <div className="col-span-2 flex items-start gap-2">
                                <span className="text-slate-500 w-12 shrink-0">GPU</span>
                                <span className="text-slate-300 font-medium">{product.gpu}</span>
                            </div>
                        )}
                        {product.cpu && (
                            <div className="col-span-2 flex items-start gap-2">
                                <span className="text-slate-500 w-12 shrink-0">CPU</span>
                                <span className="text-slate-300">{product.cpu}</span>
                            </div>
                        )}
                        {product.ram && (
                            <div className="flex items-start gap-2">
                                <span className="text-slate-500 w-10 shrink-0">RAM</span>
                                <span className="text-slate-300">{product.ram}</span>
                            </div>
                        )}
                        {product.storage && (
                            <div className="flex items-start gap-2">
                                <span className="text-slate-500 w-10 shrink-0">Disk</span>
                                <span className="text-slate-300">{product.storage}</span>
                            </div>
                        )}
                        {product.location && (
                            <div className="col-span-2 flex items-start gap-2 mt-2">
                                <span className="text-slate-500 w-12 shrink-0">Loc</span>
                                <span className="text-slate-300">{product.location}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Validation Reason (if rejected or warned) */}
            {product.validation_reason && product.validation_reason !== "Leave empty" && (
                <div className="mt-auto mb-4 bg-slate-900/50 rounded p-2 text-[10px] text-slate-400 leading-tight">
                    {product.validation_reason.split("; ").map((reason, i) => (
                        <div key={i} className={reason.startsWith("✗") ? "text-red-400" : reason.startsWith("⚠") ? "text-amber-400" : "text-green-400"}>
                            {reason}
                        </div>
                    ))}
                </div>
            )}

            {/* Action */}
            <div className="mt-auto pt-2">
                {product.url && product.url !== "No link" && !product.url.toLowerCase().includes("no featured offers") ? (
                    <a
                        href={product.url.startsWith("http") ? product.url : `https://${product.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="block w-full text-center py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition-colors"
                    >
                        View {product.title ? "Link" : "Product"} ↗
                    </a>
                ) : (
                    <button disabled className="w-full py-2.5 rounded-lg bg-slate-900 text-slate-600 text-sm font-medium cursor-not-allowed">
                        No Link Available
                    </button>
                )}
            </div>
        </div>
    );
}
