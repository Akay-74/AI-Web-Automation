"use client";

import { useEffect, useRef, useState } from "react";
import { getWebSocketUrl, TaskStep, UiEvent } from "@/lib/api";

/**
 * Hook for subscribing to real-time task execution updates via WebSocket.
 *
 * Upgraded to support:
 * - Bidirectional communication (send user actions back to backend)
 * - Screencast frame handling (JPEG stream)
 * - CAPTCHA detection events
 * - Viewport dimension tracking
 */
export function useTaskWebSocket(taskId: string) {
    const [steps, setSteps] = useState<TaskStep[]>([]);
    const [uiEvents, setUiEvents] = useState<UiEvent[]>([]);
    const [status, setStatus] = useState<string>("");
    const [connected, setConnected] = useState(false);
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const [captchaDetected, setCaptchaDetected] = useState(false);
    const [captchaType, setCaptchaType] = useState<string>("");
    const [viewport, setViewport] = useState<{ width: number; height: number }>({
        width: 1920,
        height: 1080,
    });
    const wsRef = useRef<WebSocket | null>(null);
    const statusRef = useRef(status);

    // Keep statusRef in sync without re-triggering effects
    useEffect(() => {
        statusRef.current = status;
    }, [status]);

    /**
     * Send a user action to the backend via WebSocket.
     * Used for interactive browser control and CAPTCHA resume.
     */
    const sendAction = (action: Record<string, unknown>) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(action));
        }
    };

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

                    // Handle base64 Screenshot (legacy PNG) or Screencast Frame (live JPEG)
                    if (data.action === "screenshot" || data.action === "screencast_frame"
                        || data.raw_event?.action === "screenshot" || data.raw_event?.action === "screencast_frame") {
                        const img = data.details?.image || data.raw_event?.details?.image;
                        if (img) setScreenshot(img);
                        return;
                    }

                    // Handle CAPTCHA events
                    if (data.action === "captcha_detected") {
                        setCaptchaDetected(true);
                        setCaptchaType(data.raw_event?.captcha_type || data.details?.captcha_type || "unknown");
                    }
                    if (data.action === "captcha_solved") {
                        setCaptchaDetected(false);
                        setCaptchaType("");
                    }

                    // Track viewport dimensions from browser_launched
                    if (data.action === "browser_launched" && data.raw_event?.viewport) {
                        setViewport(data.raw_event.viewport);
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

    return {
        steps,
        uiEvents,
        status,
        connected,
        screenshot,
        captchaDetected,
        captchaType,
        viewport,
        sendAction,
    };
}
