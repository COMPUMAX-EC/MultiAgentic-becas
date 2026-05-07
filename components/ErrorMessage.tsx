import { ReactNode } from "react";

type ErrorMessageProps = {
  title: string;
  message: string;
  type?: "error" | "warning" | "info";
  children?: ReactNode;
};

export function ErrorMessage({
  title,
  message,
  type = "error",
  children,
}: ErrorMessageProps) {
  return (
    <section className={`message-panel message-panel-${type}`} role="status">
      <div>
        <p className="card-label">{title}</p>
        <p>{message}</p>
      </div>
      {children ? <div className="message-action-area">{children}</div> : null}
    </section>
  );
}
