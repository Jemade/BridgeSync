import { useState, useEffect, type FormEvent } from "react";
import { Plus, Search, RefreshCw, ChevronRight } from "lucide-react";
import { api, type Order, type Page } from "../api";
import {
  Status,
  Empty,
  Pager,
  Dialog,
  Field,
  ErrorBox,
  money,
  date,
  message,
  labels,
} from "../ui";

export function OrderTable({
  rows,
  onSelect,
}: {
  rows: Order[];
  onSelect: (o: Order) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {["Order", "Customer", "Amount", "Delivery", "Received", ""].map(
              (h, i) => (
                <th scope="col" key={i}>
                  {h}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>
                <button className="row-link" onClick={() => onSelect(o)}>
                  {o.reference}
                </button>
              </td>
              <td>{o.customer}</td>
              <td className="numeric">{money(o.amount_cents, o.currency)}</td>
              <td>
                <Status value={o.status} />
              </td>
              <td className="muted nowrap">{date(o.created_at)}</td>
              <td>
                <button
                  className="icon-button"
                  aria-label={"Inspect " + o.reference}
                  onClick={() => onSelect(o)}
                >
                  <ChevronRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export default function Orders({
  revision,
  refresh,
  write,
  notify,
}: {
  revision: number;
  refresh: () => void;
  write: boolean;
  notify: (s: string) => void;
}) {
  const [data, setData] = useState<Page<Order> | null>(null),
    [q, setQ] = useState(""),
    [status, setStatus] = useState(""),
    [page, setPage] = useState(1),
    [error, setError] = useState(""),
    [creating, setCreating] = useState(false),
    [selected, setSelected] = useState<Order | null>(null);
  useEffect(() => {
    const c = new AbortController();
    const t = setTimeout(
      () =>
        api<Page<Order>>(
          "/orders?q=" +
            encodeURIComponent(q) +
            "&status=" +
            status +
            "&page=" +
            page,
          { signal: c.signal },
        )
          .then((d) => {
            setData(d);
            setError("");
          })
          .catch((e) => {
            if (e.name !== "AbortError") setError(message(e));
          }),
      200,
    );
    return () => {
      clearTimeout(t);
      c.abort();
    };
  }, [q, status, page, revision]);
  useEffect(() => {
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Orders</h1>
          <p>Track delivery from acceptance to the destination system.</p>
        </div>
        {write && (
          <button className="button primary" onClick={() => setCreating(true)}>
            <Plus size={16} />
            New order
          </button>
        )}
      </div>
      <ErrorBox text={error} />
      <section className="panel">
        <div className="toolbar">
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Search orders"
              placeholder="Search order or customer"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <select
            aria-label="Filter delivery status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All delivery states</option>
            {["pending", "running", "retrying", "succeeded", "failed"].map(
              (s) => (
                <option key={s} value={s}>
                  {labels[s]}
                </option>
              ),
            )}
          </select>
          <button
            className="icon-button"
            aria-label="Refresh orders"
            onClick={refresh}
          >
            <RefreshCw size={17} />
          </button>
        </div>
        {data?.items.length ? (
          <OrderTable rows={data.items} onSelect={setSelected} />
        ) : (
          <Empty
            title={data ? "No matching orders" : "Loading orders"}
            detail="Create an order or adjust your search."
          />
        )}
        {data && (
          <Pager page={page} total={data.total} size={20} setPage={setPage} />
        )}
      </section>
      <p className="caption">Delivery states refresh every 5 seconds.</p>
      {creating && (
        <NewOrder
          close={() => setCreating(false)}
          done={() => {
            setCreating(false);
            refresh();
            notify("Order accepted. Its delivery job is queued.");
          }}
        />
      )}
      {selected && (
        <JobDetail
          order={selected}
          close={() => setSelected(null)}
          write={write}
          refresh={refresh}
          notify={notify}
        />
      )}
    </>
  );
}
function NewOrder({ close, done }: { close: () => void; done: () => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const f = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await api("/orders", {
        method: "POST",
        body: JSON.stringify({ ...f, event_id: crypto.randomUUID() }),
      });
      done();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title="New order" close={close}>
      <p className="muted">
        Acceptance saves the order and delivery job together.
      </p>
      <form onSubmit={submit}>
        <Field label="Order reference">
          <input
            name="reference"
            required
            maxLength={80}
            placeholder="ORD-1007"
            autoFocus
          />
        </Field>
        <Field label="Customer">
          <input name="customer" required maxLength={120} />
        </Field>
        <div className="form-grid">
          <Field label="Amount">
            <input name="amount" type="number" min=".01" step=".01" required />
          </Field>
          <Field label="Currency">
            <select name="currency">
              <option>USD</option>
              <option>ZAR</option>
              <option>EUR</option>
              <option>GBP</option>
            </select>
          </Field>
        </div>
        <ErrorBox text={error} />
        <div className="dialog-actions">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Saving..." : "Accept order"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
type Job = {
  id: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  next_attempt_at: number;
};
type Attempt = {
  id: string;
  number: number;
  outcome: string;
  detail: string;
  duration_ms: number;
  created_at: number;
};
function JobDetail({
  order,
  close,
  write,
  refresh,
  notify,
}: {
  order: Order;
  close: () => void;
  write: boolean;
  refresh: () => void;
  notify: (s: string) => void;
}) {
  const [data, setData] = useState<{ job: Job; attempts: Attempt[] } | null>(
      null,
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<{ job: Job; attempts: Attempt[] }>("/jobs/" + order.job_id)
      .then(setData)
      .catch((e) => setError(message(e)));
  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [order.job_id]);
  async function retry() {
    setBusy(true);
    try {
      await api("/jobs/" + order.job_id + "/retry", { method: "POST" });
      await load();
      refresh();
      notify("Retry scheduled. The worker will collect this job.");
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title={order.reference} close={close}>
      <p>
        {order.customer} <span className="muted">/</span>{" "}
        {money(order.amount_cents, order.currency)}
      </p>
      <ErrorBox text={error} />
      {data && (
        <>
          <div
            className="job-summary"
            role="group"
            aria-label="Delivery summary"
          >
            <Status value={data.job.status} />
            <span>{data.job.attempts} attempts recorded</span>
          </div>
          {data.job.last_error && (
            <div className="error">{data.job.last_error}</div>
          )}
          {data.job.status === "retrying" && (
            <p className="muted">
              Next attempt: {date(data.job.next_attempt_at)}
            </p>
          )}
          <h3>Delivery attempts</h3>
          {data.attempts.length ? (
            <ol className="attempts">
              {data.attempts.map((a) => (
                <li key={a.id}>
                  <div>
                    <Status value={a.outcome} />
                    <small>
                      {date(a.created_at)} / {a.duration_ms} ms
                    </small>
                  </div>
                  <p>{a.detail}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted">
              The worker has not completed an attempt yet.
            </p>
          )}
          {write && data.job.status === "failed" && (
            <div className="dialog-actions">
              <button
                className="button primary"
                disabled={busy}
                onClick={retry}
              >
                <RefreshCw size={15} />
                {busy ? "Scheduling..." : "Retry delivery"}
              </button>
            </div>
          )}
        </>
      )}
    </Dialog>
  );
}
