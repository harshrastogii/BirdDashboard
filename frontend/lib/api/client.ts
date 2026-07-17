import { API_BASE } from "@/lib/config";
import type { Problem } from "./types";

export class ApiError extends Error {
  status: number;
  code: string | null;
  constructor(problem: Problem) {
    super(problem.detail || problem.title);
    this.status = problem.status;
    this.code = problem.code;
  }
}

/** Typed fetch against the Avian Observatory API, parsing Problem+JSON errors. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
  });

  if (!res.ok) {
    let problem: Problem;
    try {
      problem = (await res.json()) as Problem;
    } catch {
      problem = {
        type: "about:blank", title: res.statusText, status: res.status,
        detail: null, code: null, request_id: null,
      };
    }
    throw new ApiError(problem);
  }

  return (await res.json()) as T;
}

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
