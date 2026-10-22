export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const TOKEN_KEY = "token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * Tüm backend çağrıları için tek giriş noktası: /api/v1 prefix'ini ve
 * Authorization header'ını otomatik ekler, 401'de oturumu temizleyip
 * /login'e yönlendirir.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const isFormData = options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (error) {
    if (error && typeof error === "object" && "name" in error && error.name === "AbortError") throw error;
    throw new ApiError(0, "Sunucuya bağlanılamadı. Bağlantını kontrol edip tekrar dene.");
  }

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Oturum süresi doldu, lütfen tekrar giriş yapın.");
  }

  if (!res.ok) {
    let detail = res.status >= 500
      ? "Sunucu şu anda isteği tamamlayamıyor. Lütfen biraz sonra tekrar dene."
      : `İstek başarısız oldu (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string" && data.detail) {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        const messages = data.detail.map((item: { loc?: unknown[]; msg?: unknown }) => {
          const field = item.loc?.slice(1).join(".");
          const message = typeof item.msg === "string" ? item.msg : "Geçersiz değer";
          return field ? `${field}: ${message}` : message;
        });
        if (messages.length) detail = messages.join("; ");
      }
    } catch {
      // yanıt JSON değilse varsayılan mesaj kullanılır
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
