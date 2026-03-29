"use client";

import { useEffect, useRef, useState } from "react";
import { getWebSocketUrl, TaskStep, UiEvent } from "@/lib/api";

/**
 * Hook for subscribing to real-time task execution updates via WebSocket.
 *
 * Fixed: previously had `status` in useCallback deps which caused
 * infinite reconnect loops (connect recreated → effect cleanup → reconnect).
 * Now uses a ref for status to avoid stale closures without re-triggering effects.
 */
export function useTaskWebSocket(taskId: string) {
    const [steps, setSteps] = useState<TaskStep[]>([]);
    const [uiEvents, setUiEvents] = useState<UiEvent[]>([]);
    const [status, setStatus] = useState<string>("");
    const [connected, setConnected] = useState(false);
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const statusRef = useRef(status);

    // Keep statusRef in sync without re-triggering effects
    useEffect(() => {
        statusRef.current = status;
    }, [status]);

    useEffect(() => {
        if (!taskId) return;

        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
        let unmounted = false;

        function connect() {
            if (unmounted) return;

            const ws = new WebSocket(getWebSocketUrl(taskId));
            wsRef.current = ws;

            ws.onopen = () => {
                if (!unmounted) setConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // Update status
                    if (data.status) {
                        setStatus(data.status);
                        statusRef.current = data.status;
                    }

                    // Handle base64 Screenshot
                    if (data.action === "screenshot" || data.raw_event?.action === "screenshot") {
                        const img = data.details?.image || data.raw_event?.details?.image;
                        if (img) setScreenshot(img);
                        return;
                    }

                    // Append UI Chat Events
                    if (data.ui_event) {
                        setUiEvents((prev) => [...prev, data.ui_event]);
                    }

                    // Add or Update step timeline
                    if (data.step !== undefined) {
                        const action = data.action || data.raw_event?.action || "unknown";
                        const stepStatus = data.raw_event?.status || data.details?.status || "completed";
                        const rawDetails = data.raw_event || data.details || {};
                        const description = rawDetails.description || action;

                        const newStep: TaskStep = {
                            step: data.step,
                            action,
                            description,
                            status: stepStatus,
                            details: rawDetails,
                            timestamp: data.timestamp,
                            ui_event: data.ui_event,
                            raw_event: rawDetails,
                        };

                        setSteps((prev) => {
                            const existingIdx = prev.findIndex(
                                (p) => p.step === newStep.step && p.action === newStep.action
                            );
                            if (existingIdx >= 0) {
                                const updated = [...prev];
                                updated[existingIdx] = newStep;
                                return updated;
                            }
                            return [...prev, newStep];
                        });
                    }

                    // Auto-close on terminal states
                    if (["completed", "failed", "cancelled"].includes(data.status)) {
                        ws.close();
                    }
                } catch (e) {
                    console.error("WebSocket parse error:", e);
                }
            };

            ws.onclose = () => {
                if (unmounted) return;
                setConnected(false);

                // Only reconnect if still in a non-terminal state
                const currentStatus = statusRef.current;
                if (currentStatus === "running" || currentStatus === "queued" || currentStatus === "") {
                    reconnectTimer = setTimeout(() => {
                        if (!unmounted) connect();
                    }, 3000);
                }
            };

            ws.onerror = () => {
                if (!unmounted) setConnected(false);
            };
        }

        connect();

        return () => {
            unmounted = true;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.close();
            }
        };
    }, [taskId]); // Only re-run when taskId changes, NOT status

    return { steps, uiEvents, status, connected, screenshot };
}
