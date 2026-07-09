import type { ReactNode } from "react";

type CardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
};

export function Card({ title, subtitle, children, actions }: CardProps) {
  return (
    <section className="ui-card">
      <header className="ui-card__header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="ui-card__actions">{actions}</div> : null}
      </header>
      <div className="ui-card__body">{children}</div>
    </section>
  );
}
