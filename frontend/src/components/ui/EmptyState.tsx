type EmptyStateProps = {
  title: string;
  message: string;
};

export function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <div className="ui-state ui-state--empty">
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}
