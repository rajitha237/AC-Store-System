import type { UserResponse } from "@/types/auth";

const TOKEN_KEY = "ac_store_access_token";
const USER_KEY = "ac_store_user";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(
  token: string,
): void {
  window.sessionStorage.setItem(
    TOKEN_KEY,
    token,
  );
}

export function removeAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function getStoredUser(): UserResponse | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.sessionStorage.getItem(
    USER_KEY,
  );

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserResponse;
  } catch {
    window.sessionStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setStoredUser(
  user: UserResponse,
): void {
  window.sessionStorage.setItem(
    USER_KEY,
    JSON.stringify(user),
  );
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(USER_KEY);
}
