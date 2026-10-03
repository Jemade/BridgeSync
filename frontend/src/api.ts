export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET")
    headers.set("X-BridgeSync-Request", "browser");
  const response = await fetch("/api" + path, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login")
      window.dispatchEvent(new Event("bridgesync:session-expired"));
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : "Check the supplied values and try again.";
    const rows = body.errors?.map((e: { row: number }) => e.row).join(", ");
    throw new ApiError(
      detail + (rows ? " Invalid rows: " + rows : ""),
      response.status,
    );
  }
  return body as T;
}
export type User = {
  id: string;
  name: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  organisation: string;
};
export type Order = {
  id: string;
  reference: string;
  customer: string;
  amount_cents: number;
  currency: string;
  created_at: number;
  job_id: string;
  status: string;
  attempts: number;
  last_error: string | null;
};
export type Payment = {
  id: string;
  reference: string;
  order_reference: string;
  amount_cents: number;
  currency: string;
  status: string;
  note: string;
  created_at: number;
};
export type Audit = {
  id: string;
  actor: string;
  action: string;
  detail: string;
  created_at: number;
};
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
