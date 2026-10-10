import { deriveClientPasswordHash } from "./crypto";

export interface AuthUser {
  id: string;
  username: string;
}

const STORAGE_KEY_USER = "traffic_auth_user";
const STORAGE_KEY_TOKEN = "traffic_auth_token";

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY_USER);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(STORAGE_KEY_TOKEN);
  } catch {
    return null;
  }
}

export async function loginWithCredentials(
  username: string,
  password: string
): Promise<AuthUser> {
  const cleanUsername = username.trim().toLowerCase();
  const clientHash = await deriveClientPasswordHash(cleanUsername, password);

  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: cleanUsername,
      client_hash: clientHash,
    }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Invalid username or password");
  }

  const data = await res.json();
  const user: AuthUser = data.user;
  const token: string = data.token;

  // Persist locally and in cookies
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
    if (token) {
      localStorage.setItem(STORAGE_KEY_TOKEN, token);
      document.cookie = `auth_token=${token}; path=/; max-age=604800; SameSite=Lax`;
    }
  }

  return user;
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch("/auth/logout", { method: "POST" });
  } catch {
    // Ignore network error during logout
  }

  if (typeof window !== "undefined") {
    localStorage.removeItem(STORAGE_KEY_USER);
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    document.cookie = "auth_token=; path=/; max-age=0; SameSite=Lax";
  }
}

export async function checkSession(): Promise<AuthUser | null> {
  const localUser = getStoredUser();
  const token = getStoredToken();
  const hasCookie =
    typeof document !== "undefined" && document.cookie.includes("auth_token=");

  if (!token && !hasCookie) {
    return null;
  }

  try {
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch("/auth/me", {
      headers,
      cache: "no-store",
    });

    if (res.ok) {
      const data = await res.json();
      if (data.user) {
        localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(data.user));
        return data.user;
      }
    }
  } catch {
    // Offline or network error: fallback to valid localStorage user if present
    if (localUser) return localUser;
  }

  // Session invalid
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORAGE_KEY_USER);
    localStorage.removeItem(STORAGE_KEY_TOKEN);
  }
  return null;
}
