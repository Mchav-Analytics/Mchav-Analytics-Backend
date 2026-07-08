const TOKEN_KEY = "mchav_access_token";

export function saveAccessToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}
