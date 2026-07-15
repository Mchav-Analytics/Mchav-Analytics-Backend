import { clearAccessToken } from "./authStorage";

export type LoginResponse = {
  status: string;
  data: {
    auth_url: string;
  };
};

export async function requestJiraLogin(): Promise<string> {
  const response = await fetch("/api/auth/login", {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("No fue posible iniciar el login con Jira.");
  }

  const body = (await response.json()) as LoginResponse;
  return body.data.auth_url;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  clearAccessToken();
}
