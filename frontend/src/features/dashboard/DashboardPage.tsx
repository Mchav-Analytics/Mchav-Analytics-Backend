import { useCallback, useEffect, useMemo, useState } from "react";

import { BarChartCard, LineChartCard, PieChartCard } from "../../components/charts/MetricCharts";
import { Card } from "../../components/ui/Card";
import { DataTable, type Column } from "../../components/ui/DataTable";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { Spinner } from "../../components/ui/Spinner";
import type { Issue, KpiValue, Project, Sprint } from "../../types/api";
import {
  computeSprintKpis,
  exportIssuesCsv,
  fetchProjectSprints,
  fetchProjects,
  fetchSprintIssues,
  fetchSprintKpis,
} from "./dashboardApi";

type LoadState = "idle" | "loading" | "success" | "error";

export function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [kpis, setKpis] = useState<KpiValue[]>([]);

  const [selectedProjectId, setSelectedProjectId] = useState<number | "">("");
  const [selectedSprintId, setSelectedSprintId] = useState<number | "">("");
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const projectRows = await fetchProjects();
      setProjects(projectRows);
      setLoadState("success");
    } catch (err) {
      setLoadState("error");
      setError(err instanceof Error ? err.message : "No se pudieron cargar los proyectos");
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedProjectId) {
      setSprints([]);
      setSelectedSprintId("");
      return;
    }

    async function loadSprints() {
      setLoadState("loading");
      setError(null);
      try {
        const sprintRows = await fetchProjectSprints(Number(selectedProjectId));
        setSprints(sprintRows);
        setSelectedSprintId(sprintRows[0]?.id_sprint ?? "");
        setLoadState("success");
      } catch (err) {
        setLoadState("error");
        setError(err instanceof Error ? err.message : "No se pudieron cargar los sprints");
      }
    }

    void loadSprints();
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedSprintId) {
      setIssues([]);
      setKpis([]);
      return;
    }

    async function loadSprintData() {
      setLoadState("loading");
      setError(null);
      try {
        const [issueRows, kpiRows] = await Promise.all([
          fetchSprintIssues(Number(selectedSprintId)),
          fetchSprintKpis(Number(selectedSprintId)),
        ]);
        setIssues(issueRows);
        setKpis(kpiRows.kpis);
        setLoadState("success");
      } catch (err) {
        setLoadState("error");
        setError(err instanceof Error ? err.message : "No se pudieron cargar los datos del sprint");
      }
    }

    void loadSprintData();
  }, [selectedSprintId]);

  const filteredIssues = useMemo(() => {
    return issues.filter((issue) => {
      const matchesSearch =
        searchTerm.trim() === "" ||
        issue.issue_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        issue.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (issue.assignee ?? "").toLowerCase().includes(searchTerm.toLowerCase());

      const createdAt = new Date(issue.created_at).getTime();
      const fromOk = !dateFrom || createdAt >= new Date(dateFrom).getTime();
      const toOk = !dateTo || createdAt <= new Date(`${dateTo}T23:59:59`).getTime();

      return matchesSearch && fromOk && toOk;
    });
  }, [dateFrom, dateTo, issues, searchTerm]);

  const kpiCards = useMemo(
    () =>
      kpis.map((kpi) => ({
        label: kpi.kpi_type,
        value: kpi.metric_value,
        unit: kpi.unit,
      })),
    [kpis],
  );

  const issueColumns: Column<Issue>[] = [
    { key: "key", label: "Key", sortable: true, sortValue: (row) => row.issue_key, render: (row) => row.issue_key },
    { key: "summary", label: "Resumen", sortable: true, sortValue: (row) => row.summary, render: (row) => row.summary },
    { key: "status", label: "Estado", sortable: true, sortValue: (row) => row.status, render: (row) => row.status },
    {
      key: "assignee",
      label: "Asignado",
      sortable: true,
      sortValue: (row) => row.assignee ?? "",
      render: (row) => row.assignee ?? "—",
    },
    {
      key: "points",
      label: "Pts",
      sortable: true,
      sortValue: (row) => row.story_points ?? 0,
      render: (row) => row.story_points ?? "—",
    },
  ];

  async function handleComputeKpis() {
    if (!selectedSprintId) return;
    setLoadState("loading");
    setError(null);
    try {
      const result = await computeSprintKpis(selectedSprintId);
      setKpis(result.kpis);
      setLoadState("success");
    } catch (err) {
      setLoadState("error");
      setError(err instanceof Error ? err.message : "No se pudieron calcular los KPIs");
    }
  }

  if (loadState === "loading" && projects.length === 0) {
    return <Spinner label="Cargando dashboard..." />;
  }

  if (loadState === "error" && projects.length === 0) {
    return <ErrorState message={error ?? "Error desconocido"} onRetry={loadDashboard} />;
  }

  return (
    <div className="dashboard-page">
      <Card
        title="Filtros"
        subtitle="Proyecto, sprint, fechas y búsqueda"
        actions={
          <button type="button" className="ui-button" onClick={() => exportIssuesCsv(filteredIssues)}>
            Exportar CSV
          </button>
        }
      >
        <div className="dashboard-filters">
          <label>
            Proyecto
            <select
              value={selectedProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value ? Number(event.target.value) : "")}
            >
              <option value="">Selecciona un proyecto</option>
              {projects.map((project) => (
                <option key={project.id_project} value={project.id_project}>
                  {project.project_name} ({project.project_key})
                </option>
              ))}
            </select>
          </label>

          <label>
            Sprint
            <select
              value={selectedSprintId}
              onChange={(event) => setSelectedSprintId(event.target.value ? Number(event.target.value) : "")}
              disabled={!selectedProjectId}
            >
              <option value="">Selecciona un sprint</option>
              {sprints.map((sprint) => (
                <option key={sprint.id_sprint} value={sprint.id_sprint}>
                  {sprint.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Desde
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>

          <label>
            Hasta
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>

          <label className="dashboard-filters__search">
            Buscar
            <input
              type="search"
              placeholder="Key, resumen o asignado"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
        </div>
      </Card>

      {projects.length === 0 ? (
        <EmptyState
          title="Sin proyectos sincronizados"
          message="Sincroniza un proyecto desde el backend para ver métricas aquí."
        />
      ) : null}

      {loadState === "loading" && selectedSprintId ? <Spinner label="Cargando métricas del sprint..." /> : null}
      {loadState === "error" && error ? <ErrorState message={error} onRetry={loadDashboard} /> : null}

      {selectedSprintId ? (
        <>
          <section className="dashboard-kpis">
            {kpiCards.map((kpi) => (
              <article key={kpi.label} className="kpi-card">
                <span>{kpi.label}</span>
                <strong>
                  {kpi.value} {kpi.unit}
                </strong>
              </article>
            ))}
            <button type="button" className="ui-button ui-button--ghost" onClick={handleComputeKpis}>
              Recalcular KPIs
            </button>
          </section>

          <section className="dashboard-charts">
            <BarChartCard title="KPIs del sprint" data={kpiCards.map((item) => ({ label: item.label, value: item.value }))} />
            <LineChartCard
              title="Tendencia de story points"
              data={filteredIssues.map((issue) => ({
                label: issue.issue_key,
                value: issue.story_points ?? 0,
              }))}
            />
            <PieChartCard
              title="Distribución por estado"
              data={Object.entries(
                filteredIssues.reduce<Record<string, number>>((acc, issue) => {
                  acc[issue.status] = (acc[issue.status] ?? 0) + 1;
                  return acc;
                }, {}),
              ).map(([label, value]) => ({ label, value }))}
            />
          </section>

          <Card title="Issues del sprint" subtitle={`${filteredIssues.length} registros visibles`}>
            <DataTable columns={issueColumns} rows={filteredIssues} emptyLabel="No hay issues para los filtros actuales" />
          </Card>
        </>
      ) : null}
    </div>
  );
}
