import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
    title: "AI Web Automation Agent",
    description: "Give a goal in plain English. An AI agent browses the web to complete it.",
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
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="antialiased">
                <Providers>
                    <div className="flex h-screen">
                        <Sidebar />
                        <main className="flex-1 overflow-auto p-6">{children}</main>
                    </div>
                </Providers>
            </body>
        </html>
    );
}
