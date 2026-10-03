import { useState, useEffect } from "react";
import { Upload, ArrowRight } from "lucide-react";
import { api, type Order, type Page } from "../api";
import { Empty, ErrorBox, money, message } from "../ui";
import { OrderTable } from "./Orders";
import type { Tab } from "../App";

type Summary = {
  orders: number;
  synced: number;
  pending: number;
  failed: number;
  payment_exceptions: number;
  totals: { currency: string; amount_cents: number }[];
};
export default function Overview({
  revision,
  go,
}: {
  revision: number;
  go: (t: Tab) => void;
}) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 5000);
    return () => clearInterval(t);
  }, []);
  const [summary, setSummary] = useState<Summary | null>(null),
    [rows, setRows] = useState<Order[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<Summary>("/overview", { signal: controller.signal }),
      api<Page<Order>>("/orders", { signal: controller.signal }),
    ])
      .then(([s, r]) => {
        setSummary(s);
        setRows(r.items.slice(0, 6));
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(message(e));
      });
    return () => controller.abort();
  }, [revision, tick]);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Operations overview</h1>
          <p>A clear view of order delivery and payment exceptions.</p>
        </div>
        <button className="button secondary" onClick={() => go("payments")}>
          <Upload size={16} />
          Import payments
        </button>
      </div>
      <ErrorBox text={error} />
      <div className="metrics">
        {[
          ["Orders received", summary?.orders, ""],
          ["Orders synced", summary?.synced, "good"],
          ["Awaiting delivery", summary?.pending, ""],
          ["Delivery failures", summary?.failed, "bad"],
        ].map(([label, value, cls]) => (
          <div className="metric" key={String(label)}>
            <span>{label}</span>
            <strong className={String(cls)}>{value ?? "—"}</strong>
            <small>
              {label === "Delivery failures"
                ? "Requires review"
                : "Current workspace"}
            </small>
          </div>
        ))}
      </div>
      {summary && summary.payment_exceptions > 0 && (
        <div className="notice">
          <div>
            <strong>
              {summary.payment_exceptions} payment exceptions need review
            </strong>
            <p>Some imported payments do not match an order or its amount.</p>
          </div>
          <button className="text-button" onClick={() => go("payments")}>
            Review payments <ArrowRight size={16} />
          </button>
        </div>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Recent orders</h2>
          <button className="text-button" onClick={() => go("orders")}>
            View all orders <ArrowRight size={15} />
          </button>
        </div>
        {rows.length ? (
          <OrderTable rows={rows} onSelect={() => go("orders")} />
        ) : (
          <Empty
            title={summary ? "No orders yet" : "Loading orders"}
            detail="Orders received by your workspace appear here."
          />
        )}
      </section>
      <div className="overview-bottom">
        <section className="panel compact">
          <h2>Order value by currency</h2>
          {summary?.totals.length ? (
            summary.totals.map((t) => (
              <div className="value-row" key={t.currency}>
                <span>{t.currency}</span>
                <strong>{money(t.amount_cents, t.currency)}</strong>
              </div>
            ))
          ) : (
            <p>No order value recorded.</p>
          )}
          <p className="muted">
            Currencies are kept separate. No exchange rate is assumed.
          </p>
        </section>
        <section className="panel compact">
          <h2>Delivery you can inspect</h2>
          <p>
            Every accepted order has a durable delivery job. Open an order to
            inspect attempts and review failures.
          </p>
          <button className="text-button" onClick={() => go("integrations")}>
            Manage the test connector <ArrowRight size={15} />
          </button>
        </section>
      </div>
    </>
  );
}
