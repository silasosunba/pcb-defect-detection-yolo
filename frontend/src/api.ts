export type User = {
  id: string;
  name: string;
  email: string;
  role: "admin" | "user";
  active: boolean;
  created_at: number;
  last_login: number | null;
  inspection_count?: number;
};
export type Detection = {
  label: string;
  confidence: number;
  box: number[];
  review_priority: string;
  explanation: string;
  recommendation: string;
};
export type DashboardData = {
  inspections: number;
  defects: number;
  no_detections: number;
  average_duration_ms: number;
  class_counts: Record<string, number>;
  trend: { day: string; total: number }[];
  recent_inspections: Inspection[];
};
export type Inspection = {
  id: string;
  filename: string;
  created_at: number;
  confidence: number;
  width: number;
  height: number;
  detections: Detection[];
  duration_ms: number;
  image_url: string;
  original_url: string;
  model_sha256: string;
  user_name?: string;
};
export type ModelStatus = {
  available: boolean;
  state: string;
  message: string;
  image_size: number;
  manifest: {
    names: string[];
    architecture: string;
    metrics?: Record<string, number>;
    dataset: string;
    sha256: string;
  } | null;
};
export type Page<T> = { items: T[]; total: number };
export type Overview = {
  users: number;
  active_users: number;
  admins: number;
  inspections: number;
  defects: number;
  average_duration_ms: number;
  class_counts: Record<string, number>;
  recent_inspections: Inspection[];
  audit: {
    id: number;
    action: string;
    target: string;
    created_at: number;
    actor_name: string | null;
  }[];
};

export class ApiError extends Error {

  constructor(
    public status: number,
    message: string,
  ) {

    super(message);
  
}

}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {

  const headers = new Headers(options.headers);
  headers.set("X-PCB-Request", "1");

  if (options.body && !(options.body instanceof FormData)) {

    headers.set("Content-Type", "application/json");
  
}

  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {

    const body = await response.json().catch(() => ({}));
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? body.detail.map((e: { msg: string }) => e.msg).join(". ")
          : "The request could not be completed.";

    if (response.status === 401 && !path.startsWith("/auth/")) {

      window.dispatchEvent(new Event("session-expired"));
    
}

    throw new ApiError(response.status, detail);
  
}

  return response.status === 204 ? (undefined as T) : response.json();

}

export const date = (value: number) =>
  new Date(value * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
export const label = (value: string) =>
  value.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
