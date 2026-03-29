/** API client and types. */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

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
    ui_event?: UiEvent;
    raw_event?: any;
}

export interface ProductResult {
    name: string;
    price?: number | null;
    currency?: string;
    rating?: number | string;
    url?: string;
    gpu?: string;
    cpu?: string;
    ram?: string;
    storage?: string;
    validation_reason?: string;
    [key: string]: any;
}

export const api = {
    async createTask(goal: string, priority: number = 0): Promise<Task> {
        const res = await fetch(`${API_BASE_URL}/tasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal, priority }),
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async startTask(taskId: string): Promise<Task> {
        const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/start`, {
            method: "POST",
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTask(taskId: string): Promise<Task> {
        const res = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTaskLogs(taskId: string): Promise<any[]> {
        const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/logs`);
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
        const res = await fetch(`${API_BASE_URL}/tasks?${params}`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },

    async getTaskResults(taskId: string): Promise<any[]> {
        const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/results`);
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        // Backend returns { results: [...] }
        return data.results ?? data;
    },
};

export function getWebSocketUrl(taskId: string): string {
    // If we're in the browser, dynamically determine the host to avoid localhost mapping issues
    if (typeof window !== "undefined") {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = process.env.NEXT_PUBLIC_WS_URL
            ? new URL(process.env.NEXT_PUBLIC_WS_URL).host
            : window.location.host.replace("3000", "8000"); // fallback local mapping

        return `${protocol}//${host}/ws/tasks/${taskId}`;
    }

    // SSR fallback
    return `${WS_BASE_URL}/ws/tasks/${taskId}`;
}
