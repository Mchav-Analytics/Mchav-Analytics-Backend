type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorState({
  title = "No pudimos cargar los datos",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="ui-state ui-state--error" role="alert">
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="ui-button ui-button--secondary" onClick={onRetry}>
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
