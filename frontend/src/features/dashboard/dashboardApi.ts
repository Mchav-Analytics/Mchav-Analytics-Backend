import { apiRequest } from "../../lib/apiClient";
import type {
  ApiResponse,
  Issue,
  PaginatedResponse,
  Project,
  Sprint,
  SprintKpis,
} from "../../types/api";

export async function fetchProjects(): Promise<Project[]> {
  const response = await apiRequest<PaginatedResponse<Project>>("/api/projects?page=1&page_size=50");
  return response.data;
}

export async function fetchProjectSprints(projectId: number): Promise<Sprint[]> {
  const response = await apiRequest<ApiResponse<Sprint[]>>(`/api/projects/${projectId}/sprints`);
  return response.data;
}

export async function fetchSprintIssues(sprintId: number): Promise<Issue[]> {
  const response = await apiRequest<ApiResponse<Issue[]>>(`/api/projects/sprints/${sprintId}/issues`);
  return response.data;
}

export async function fetchSprintKpis(sprintId: number): Promise<SprintKpis> {
  const response = await apiRequest<ApiResponse<SprintKpis>>(`/api/kpis/sprints/${sprintId}`);
  return response.data;
}

export async function computeSprintKpis(sprintId: number): Promise<SprintKpis> {
  const response = await apiRequest<ApiResponse<SprintKpis>>(`/api/kpis/sprints/${sprintId}/compute`, {
    method: "POST",
  });
  return response.data;
}

export function exportIssuesCsv(issues: Issue[]): void {
  const headers = ["issue_key", "summary", "status", "assignee", "story_points"];
  const lines = issues.map((issue) =>
    [
      issue.issue_key,
      `"${issue.summary.replace(/"/g, '""')}"`,
      issue.status,
      issue.assignee ?? "",
      issue.story_points ?? "",
    ].join(","),
  );
  const csv = [headers.join(","), ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mchav-issues.csv";
  link.click();
  URL.revokeObjectURL(url);
}
