import { useEffect, useRef, type ReactNode } from "react";
import { FileText, ChevronLeft, ChevronRight, X } from "lucide-react";

export const money = (n: number, currency: string) =>
  new Intl.NumberFormat("en", { style: "currency", currency }).format(n / 100);
export const date = (n: number) =>
  new Date(n * 1000).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
export const message = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Try again.";
export const labels: Record<string, string> = {
  succeeded: "Synced",
  pending: "Pending",
  running: "Processing",
  retrying: "Retrying",
  failed: "Failed",
  matched: "Matched",
  mismatch: "Amount mismatch",
  unmatched: "Unmatched",
};
export function Logo() {
  return (
    <span className="brand">
      <svg viewBox="0 0 40 32" width="34" height="28" aria-hidden="true">
        <path
          d="M4 24Q20 0 36 24M4 24H36M20 5V27"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        />
        <circle cx="4" cy="24" r="3" fill="currentColor" />
        <circle cx="36" cy="24" r="3" fill="currentColor" />
      </svg>
      <span>BridgeSync</span>
    </span>
  );
}
export function Status({ value }: { value: string }) {
  return (
    <span className={"status status-" + value}>
      <span aria-hidden="true" className="dot" />
      {labels[value] || value}
    </span>
  );
}
export function Empty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty">
      <FileText size={26} />
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
export function Pager({
  page,
  total,
  size,
  setPage,
}: {
  page: number;
  total: number;
  size: number;
  setPage: (n: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total ? (page - 1) * size + 1 : 0}-{Math.min(page * size, total)} of{" "}
        {total}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={page * size >= total}
          onClick={() => setPage(page + 1)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
export function Dialog({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    d.showModal();
    return () => d.close();
  }, []);
  return (
    <dialog ref={ref} aria-labelledby="dialog-title" onCancel={close}>
      <div className="dialog-heading">
        <h2 id="dialog-title">{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function ErrorBox({ text }: { text: string }) {
  return text ? (
    <div className="error" role="alert">
      {text}
    </div>
  ) : null;
}
