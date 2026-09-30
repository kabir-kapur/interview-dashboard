const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function request(path: string, options?: RequestInit) {
  const response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json" } });
  if (!response.ok) throw Error(await response.text());
  return response.json();
}
