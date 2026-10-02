const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_KEY = "interview-console-basic-auth";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function hasSessionCredentials() {
  return typeof window !== "undefined" && Boolean(sessionStorage.getItem(AUTH_KEY));
}

export function saveSessionCredentials(username: string, password: string) {
  sessionStorage.setItem(AUTH_KEY, `Basic ${btoa(`${username}:${password}`)}`);
}

export function clearSessionCredentials() {
  sessionStorage.removeItem(AUTH_KEY);
}

export async function request(path: string, options?: RequestInit) {
  const headers = new Headers(options?.headers);
  headers.set("Content-Type", "application/json");
  const credentials = typeof window !== "undefined" ? sessionStorage.getItem(AUTH_KEY) : null;
  if (credentials) headers.set("Authorization", credentials);
  const response = await fetch(API + path, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) clearSessionCredentials();
    throw new ApiError(response.status, await response.text());
  }
  return response.json();
}
