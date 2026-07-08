export type LoginResponse = {
  auth_url: string;
};

export async function requestJiraLogin(): Promise<LoginResponse> {
  const response = await fetch("/api/auth/login", {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("No fue posible iniciar el login con Jira.");
  }

  return response.json() as Promise<LoginResponse>;
}
