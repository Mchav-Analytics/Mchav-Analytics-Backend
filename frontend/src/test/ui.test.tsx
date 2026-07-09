import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "../components/ui/EmptyState";
import { Spinner } from "../components/ui/Spinner";

describe("UI components", () => {
  it("renders spinner label", () => {
    render(<Spinner label="Cargando datos" />);
    expect(screen.getByText("Cargando datos")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(<EmptyState title="Sin datos" message="No hay registros" />);
    expect(screen.getByText("Sin datos")).toBeInTheDocument();
    expect(screen.getByText("No hay registros")).toBeInTheDocument();
  });
});
