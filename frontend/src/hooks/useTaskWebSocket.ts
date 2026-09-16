"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
    ApprovalRequest,
    ControlState,
    TaskStep,
    UiEvent,
    getWebSocketUrl,
} from "@/lib/api";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];
const RECONNECT_DELAY_MS = 3000;

/**
 * Subscribes to a task's live event stream and sends user input back.
 *
 * Every message from the backend has the same envelope:
 *   { task_id, step, action, raw_event, ui_event?, timestamp }
 * so there is one place that reads it, here.
 */
export function useTaskWebSocket(taskId: string) {
    const [steps, setSteps] = useState<TaskStep[]>([]);
    const [uiEvents, setUiEvents] = useState<UiEvent[]>([]);
    const [status, setStatus] = useState<string>("");
    const [connected, setConnected] = useState(false);
    const [frame, setFrame] = useState<string | null>(null);
    const [captcha, setCaptcha] = useState<string | null>(null);
    const [controlState, setControlState] = useState<ControlState>("AI_ACTIVE");
    const [approval, setApproval] = useState<ApprovalRequest | null>(null);
    const [viewport, setViewport] = useState({ width: 1440, height: 900 });

    const wsRef = useRef<WebSocket | null>(null);
    const statusRef = useRef(status);

    useEffect(() => {
        statusRef.current = status;
    }, [status]);

    const sendAction = useCallback((action: Record<string, unknown>) => {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(action));
        }
    }, []);

    useEffect(() => {
        if (!taskId) return;

        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
        let unmounted = false;

        function handleMessage(raw: MessageEvent) {
            let data: any;
            try {
                data = JSON.parse(raw.data);
            } catch {
                return;
            }

            const action: string = data.action ?? "";
            const event = data.raw_event ?? {};

            // Screencast frames are high-frequency and never belong in the feed.
            if (action === "screencast_frame") {
                if (event.image) setFrame(event.image);
                return;
            }

            if (data.status) {
                setStatus(data.status);
                statusRef.current = data.status;
            }

            switch (action) {
                case "browser_launched":
                    if (event.viewport) setViewport(event.viewport);
                    break;
                case "captcha_detected":
                    setCaptcha(event.captcha_type ?? "unknown");
                    break;
                case "captcha_solved":
                case "captcha_timeout":
                    setCaptcha(null);
                    break;
                case "control_state_changed":
                    if (event.current_state) setControlState(event.current_state);
                    break;
                case "approval_requested":
                    setApproval({
                        action: event.action ?? "",
                        description: event.description ?? "",
                        reason: event.reason ?? "",
                        riskLevel: event.risk_level ?? "high",
                        timeoutSeconds: event.timeout_seconds ?? 0,
                    });
                    break;
                case "approval_granted":
                case "approval_denied":
                    setApproval(null);
                    break;
            }

            if (data.ui_event) {
                setUiEvents((prev) => [...prev, data.ui_event]);
            }

            // The timeline shows real steps only, not lifecycle chatter.
            if (typeof data.step === "number" && data.step > 0) {
                const step: TaskStep = {
                    step: data.step,
                    action,
                    description: event.description ?? action,
                    status: event.status ?? "completed",
                    details: event,
                    timestamp: data.timestamp,
                };

                setSteps((prev) => {
                    const idx = prev.findIndex(
                        (p) => p.step === step.step && p.action === step.action
                    );
                    if (idx < 0) return [...prev, step];
                    const next = [...prev];
                    next[idx] = step;
                    return next;
                });
            }

            if (TERMINAL_STATUSES.includes(data.status)) {
                setApproval(null);
                setCaptcha(null);
            }
        }

        function connect() {
            if (unmounted) return;

            const ws = new WebSocket(getWebSocketUrl(taskId));
            wsRef.current = ws;

            ws.onopen = () => {
                if (!unmounted) setConnected(true);
            };
            ws.onmessage = handleMessage;
            ws.onerror = () => {
                if (!unmounted) setConnected(false);
            };
            ws.onclose = () => {
                if (unmounted) return;
                setConnected(false);
                // Only chase the connection while the task could still be running.
                if (!TERMINAL_STATUSES.includes(statusRef.current)) {
                    reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
                }
            };
        }

        connect();

        return () => {
            unmounted = true;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            const ws = wsRef.current;
            if (ws) {
                ws.onclose = null;
                ws.close();
            }
        };
    }, [taskId]);

    return {
        steps,
        uiEvents,
        status,
        connected,
        frame,
        captcha,
        controlState,
        approval,
        viewport,
        sendAction,
    };
}
