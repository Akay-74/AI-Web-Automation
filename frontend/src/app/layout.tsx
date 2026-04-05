import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
    title: "Kinetic AI — Web Automation Agent",
    description: "Precision-engineered AI agents that navigate the digital landscape with chrome-plated efficiency.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <head>
                <link
                    href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap"
                    rel="stylesheet"
                />
                <link
                    href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
                    rel="stylesheet"
                />
            </head>
            <body className="antialiased">
                <Providers>
                    <div className="flex h-screen overflow-hidden bg-[#0e0e0e]">
                        <Sidebar />
                        <main className="flex-1 overflow-auto">{children}</main>
                    </div>
                </Providers>
            </body>
        </html>
    );
}
