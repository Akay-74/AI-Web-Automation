/** API client and types. */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

/**
 * Must match the backend's API_KEY when that is set. NEXT_PUBLIC_ values ship in
 * the client bundle, so this gates a personal deployment against strangers; it
 * is not per-user auth.
 */
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers);
    if (API_KEY) headers.set("X-API-Key", API_KEY);
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
}

export interface Task {
    id: string;
    goal: string;
    status: "pending" | "queued" | "running" | "completed" | "failed" | "cancelled";
    priority: number;
    error_message?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
}

export interface UiEvent {
    type: "info" | "action" | "result" | "error";
    message: string;
    step: number;
    timestamp: string;
}

export interface TaskStep {
    step: number;
    action: string;
    description: string;
    status: string;
    details: any;
    timestamp: string;
}

export type ControlState =
    | "AI_ACTIVE"
    | "AI_PAUSED"
    | "HUMAN_ACTIVE"
    | "WAITING_FOR_APPROVAL"
    | "COMPLETED"
    | "FAILED";

export interface ApprovalRequest {
    action: string;
    description: string;
    reason: string;
    riskLevel: string;
    timeoutSeconds: number;
}

/** One extracted row. Fields depend on the schema the agent used. */
export interface ExtractedRow {
    name?: string;
    title?: string;
    price?: number | string | null;
    currency?: string;
    rating?: number | string;
    url?: string;
    specs?: string;
    [key: string]: any;
}

export const api = {
    async createTask(goal: string, priority: number = 0): Promise<Task> {
        const res = await apiFetch(`/tasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal, priority }),
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async startTask(taskId: string): Promise<Task> {
        const res = await apiFetch(`/tasks/${taskId}/start`, {
            method: "POST",
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTask(taskId: string): Promise<Task> {
        const res = await apiFetch(`/tasks/${taskId}`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTaskLogs(taskId: string): Promise<any[]> {
        const res = await apiFetch(`/tasks/${taskId}/logs`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async listTasks(
        status?: string,
        limit: number = 20,
        offset: number = 0
    ): Promise<{ tasks: Task[]; total: number }> {
        const params = new URLSearchParams();
        if (status) params.set("status", status);
        params.set("limit", String(limit));
        params.set("offset", String(offset));
        const res = await apiFetch(`/tasks?${params}`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTaskResults(taskId: string): Promise<any[]> {
        const res = await apiFetch(`/tasks/${taskId}/results`);
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        // Backend returns { results: [...] }
        return data.results ?? data;
    },

    async cancelTask(taskId: string): Promise<Task> {
        const res = await apiFetch(`/tasks/${taskId}/cancel`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async deleteTask(taskId: string): Promise<void> {
        const res = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
        if (!res.ok) throw new Error(await res.text());
    },
};

export function getWebSocketUrl(taskId: string): string {
    // If we're in the browser, dynamically determine the host to avoid localhost mapping issues
    if (typeof window !== "undefined") {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = process.env.NEXT_PUBLIC_WS_URL
            ? new URL(process.env.NEXT_PUBLIC_WS_URL).host
            : window.location.host.replace("3000", "8000"); // fallback local mapping

        return `${protocol}//${host}/ws/tasks/${taskId}${wsAuthQuery()}`;
    }

    // SSR fallback
    return `${WS_BASE_URL}/ws/tasks/${taskId}${wsAuthQuery()}`;
}

/** Browsers cannot set headers on a WebSocket handshake, so the key rides in the query. */
function wsAuthQuery(): string {
    return API_KEY ? `?api_key=${encodeURIComponent(API_KEY)}` : "";
}
