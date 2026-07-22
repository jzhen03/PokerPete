import createClient from "openapi-fetch";
import type { paths } from "./schema";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = createClient<paths>({ baseUrl: BASE_URL });

export class ApiError extends Error {}

/** Unwraps an openapi-fetch result, raising the FastAPI error detail on failure. */
export function unwrap<T>({ data, error }: { data?: T; error?: unknown }): T {
  if (error !== undefined) {
    const detail = (error as { detail?: unknown })?.detail;
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (data === undefined) {
    throw new ApiError("empty response");
  }
  return data;
}
