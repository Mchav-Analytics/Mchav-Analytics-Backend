export type ApiResponse<T> = {
  status: string;
  data: T;
};

export type PaginatedResponse<T> = {
  status: string;
  data: T[];
  meta: {
    total: number;
    page: number;
    page_size: number;
  };
};

export type Project = {
  id_project: number;
  jira_project_id: string;
  project_key: string;
  project_name: string;
  status: string | null;
  created_at: string | null;
};

export type Sprint = {
  id_sprint: number;
  jira_sprint_id: string;
  name: string;
  start_date: string | null;
  end_date: string | null;
  state: string;
  id_board: number;
};

export type Issue = {
  id_issue: number;
  jira_issue_id: string;
  issue_key: string;
  summary: string;
  status: string;
  assignee: string | null;
  story_points: number | null;
  created_at: string;
  started_at: string | null;
  resolved_at: string | null;
  id_sprint: number | null;
};

export type KpiValue = {
  kpi_type: string;
  unit: string;
  metric_value: number;
  calc_date: string | null;
};

export type SprintKpis = {
  id_sprint: number;
  sprint_name: string;
  kpis: KpiValue[];
};
