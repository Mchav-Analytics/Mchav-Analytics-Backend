export function Spinner({ label = "Cargando..." }: { label?: string }) {
  return (
    <div className="ui-spinner" role="status" aria-live="polite">
      <span className="ui-spinner__ring" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
