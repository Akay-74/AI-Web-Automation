"use client";

import { ExtractedRow } from "@/lib/api";

interface ResultCardProps {
    row: ExtractedRow;
    rank?: number;
    isCheapest?: boolean;
}

// Rendered explicitly below; anything else falls into the extra-fields list.
const KNOWN_FIELDS = new Set([
    "name", "title", "company", "source", "price", "currency", "rating",
    "url", "summary", "content", "specs",
]);

function formatPrice(price: number | string | null | undefined, currency = "USD"): string | null {
    const value = typeof price === "string" ? Number(price.replace(/[^0-9.]/g, "")) : price;
    if (value === null || value === undefined || Number.isNaN(value)) return null;
    try {
        return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
    } catch {
        return `${currency} ${value}`;
    }
}

/** One extracted row. Shows whichever fields the schema actually produced. */
export function ResultCard({ row, rank, isCheapest }: ResultCardProps) {
    const heading = row.name || row.title || "Extracted item";
    const subtitle = row.company || row.source;
    const price = formatPrice(row.price, row.currency || "USD");
    const body = row.summary || row.content;
    const link = typeof row.url === "string" && row.url.startsWith("http") ? row.url : null;

    const extras = Object.entries(row)
        .filter(([key, value]) => !KNOWN_FIELDS.has(key) && value !== null && value !== "" && value !== undefined)
        .slice(0, 4);

    return (
        <div
            className={`relative flex flex-col rounded-2xl overflow-hidden transition-all duration-300 group ${
                isCheapest ? "bg-[#1a1919] glow-chrome" : "bg-[#131313] hover:bg-[#1a1919]"
            }`}
            style={{
                border: isCheapest
                    ? "1px solid rgba(198,198,198,0.15)"
                    : "1px solid rgba(72,72,72,0.1)",
            }}
        >
            {isCheapest && <div className="h-[2px] bg-gradient-to-r from-transparent via-[#c6c6c6] to-transparent" />}

            <div className="p-5 flex flex-col gap-3 flex-1">
                {(rank !== undefined || isCheapest) && (
                    <div className="flex items-center gap-2">
                        {rank !== undefined && (
                            <span className="text-[10px] font-mono text-[#888787]">#{rank}</span>
                        )}
                        {isCheapest && (
                            <span className="text-[10px] font-bold uppercase tracking-widest text-[#e7e5e4] bg-[rgba(198,198,198,0.1)] px-2.5 py-0.5 rounded-full">
                                Lowest price
                            </span>
                        )}
                    </div>
                )}

                <div>
                    <h3
                        className="text-sm font-bold text-[#e7e5e4] line-clamp-2 leading-snug group-hover:text-[#f9f9f9] transition-colors"
                        title={heading}
                    >
                        {heading}
                    </h3>
                    {subtitle && (
                        <p className="text-[11px] text-[#a8a7a6] mt-0.5 truncate font-medium">{subtitle}</p>
                    )}
                </div>

                {(price || row.rating) && (
                    <div className="flex items-end justify-between">
                        {price ? (
                            <span
                                className={`text-2xl font-extrabold tracking-tight ${isCheapest ? "gradient-text-chrome" : "text-[#f9f9f9]"}`}
                            >
                                {price}
                            </span>
                        ) : (
                            <span />
                        )}
                        {row.rating && <span className="badge badge-warning">★ {row.rating}</span>}
                    </div>
                )}

                {row.specs && (
                    <p className="text-[11px] text-[#d4d3d2] leading-relaxed line-clamp-2">{row.specs}</p>
                )}

                {body && (
                    <p className="text-[11px] text-[#a8a7a6] leading-relaxed line-clamp-3">{body}</p>
                )}

                {extras.length > 0 && (
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                        {extras.map(([key, value]) => (
                            <div key={key} className="flex gap-1.5 min-w-0">
                                <dt className="text-[#888787] shrink-0 font-semibold capitalize">
                                    {key.replace(/_/g, " ")}
                                </dt>
                                <dd className="text-[#d4d3d2] truncate">{String(value)}</dd>
                            </div>
                        ))}
                    </dl>
                )}
            </div>

            <div className="px-5 pb-5">
                {link ? (
                    <a
                        href={link}
                        target="_blank"
                        rel="noreferrer"
                        className={`flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl text-xs font-bold transition-all ${
                            isCheapest
                                ? "btn-chrome py-2.5"
                                : "bg-[#1a1919] hover:bg-[#262626] text-[#d4d3d2] hover:text-[#e7e5e4] border border-[rgba(72,72,72,0.1)]"
                        }`}
                    >
                        <span className="material-symbols-rounded text-sm">open_in_new</span>
                        Open source
                    </a>
                ) : (
                    <button
                        disabled
                        className="w-full py-2.5 rounded-xl bg-[#0e0e0e] text-[#3a3a3a] text-xs font-semibold cursor-not-allowed"
                    >
                        No link
                    </button>
                )}
            </div>
        </div>
    );
}
