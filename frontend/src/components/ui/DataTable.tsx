import type { ReactNode } from "react";
import { useMemo, useState } from "react";

export type Column<T> = {
  key: string;
  label: string;
  sortable?: boolean;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  emptyLabel?: string;
};

export function DataTable<T>({ columns, rows, emptyLabel = "Sin datos" }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const column = columns.find((item) => item.key === sortKey);
    if (!column?.sortValue) return rows;

    return [...rows].sort((a, b) => {
      const left = column.sortValue!(a);
      const right = column.sortValue!(b);
      if (left < right) return sortDir === "asc" ? -1 : 1;
      if (left > right) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [columns, rows, sortDir, sortKey]);

  function toggleSort(key: string, sortable?: boolean) {
    if (!sortable) return;
    if (sortKey === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir("asc");
  }

  if (rows.length === 0) {
    return <p className="ui-table__empty">{emptyLabel}</p>;
  }

  return (
    <div className="ui-table-wrap">
      <table className="ui-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>
                <button
                  type="button"
                  className={column.sortable ? "ui-table__sort" : "ui-table__label"}
                  onClick={() => toggleSort(column.key, column.sortable)}
                >
                  {column.label}
                  {sortKey === column.key ? (sortDir === "asc" ? " ↑" : " ↓") : null}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
