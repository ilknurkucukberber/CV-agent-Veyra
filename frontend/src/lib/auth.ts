import { apiFetch, clearToken, setToken } from "./api";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export async function login(email: string, password: string): Promise<void> {
  const data = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
}

export async function register(
  email: string,
  password: string,
  fullName?: string,
): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName || null }),
  });
}

export function getCurrentUser(): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me");
}

export function requestPasswordReset(email: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function confirmEmailVerification(token: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function resendVerificationEmail(email: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function logout(): void {
  clearToken();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}
