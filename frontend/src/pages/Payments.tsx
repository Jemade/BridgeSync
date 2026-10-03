import { useState, useEffect, useRef, type FormEvent } from "react";
import { Upload, ArrowRight } from "lucide-react";
import { api, type Payment, type Page } from "../api";
import {
  Status,
  Empty,
  Pager,
  Dialog,
  Field,
  ErrorBox,
  money,
  message,
} from "../ui";

export default function Payments({
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
  const [data, setData] = useState<Page<Payment> | null>(null),
    [page, setPage] = useState(1),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [matching, setMatching] = useState<Payment | null>(null);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const c = new AbortController();
    api<Page<Payment>>("/payments?page=" + page, { signal: c.signal })
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(message(e));
      });
    return () => c.abort();
  }, [page, revision]);
  async function upload(f: File) {
    setError("");
    if (f.size > 1_000_000) {
      setError("CSV files must be smaller than 1 MB.");
      return;
    }
    setBusy(true);
    const form = new FormData();
    form.append("file", f);
    try {
      const r = await api<{ imported: number; duplicates: number }>(
        "/payments/import",
        { method: "POST", body: form },
      );
      notify(
        r.imported +
          " payments imported. " +
          r.duplicates +
          " duplicates skipped.",
      );
      refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
      if (file.current) file.current.value = "";
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Payments</h1>
          <p>Match payment records to orders and review exceptions.</p>
        </div>
        {write && (
          <button
            className="button primary"
            disabled={busy}
            onClick={() => file.current?.click()}
          >
            <Upload size={16} />
            {busy ? "Importing..." : "Import CSV"}
          </button>
        )}
        <input
          className="hidden"
          ref={file}
          type="file"
          accept=".csv,text/csv"
          aria-label="Payment CSV"
          onChange={(e) => {
            if (e.target.files?.[0]) upload(e.target.files[0]);
          }}
        />
      </div>
      <div className="notice">
        <div>
          <strong>CSV format</strong>
          <p>
            reference,order_reference,amount,currency. Up to 1000 rows; UTF-8.
          </p>
        </div>
        <a className="text-button" href="/sample-payments.csv" download>
          Download sample <ArrowRight size={15} />
        </a>
      </div>
      <ErrorBox text={error} />
      <section className="panel">
        {data?.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {["Payment", "Order", "Amount", "Result", ""].map((h, i) => (
                    <th scope="col" key={i}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id}>
                    <td className="strong">{p.reference}</td>
                    <td>{p.order_reference}</td>
                    <td className="numeric">
                      {money(p.amount_cents, p.currency)}
                    </td>
                    <td>
                      <Status value={p.status} />
                    </td>
                    <td>
                      {write && p.status !== "matched" && (
                        <button
                          className="text-button"
                          onClick={() => setMatching(p)}
                        >
                          Match order
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title={data ? "No payments imported" : "Loading payments"}
            detail="Import a CSV to compare payment amounts and currencies with your orders."
          />
        )}
        {data && (
          <Pager page={page} total={data.total} size={20} setPage={setPage} />
        )}
      </section>
      <p className="caption">
        An exact order reference, amount and currency produces a match. Invalid
        files are rejected together.
      </p>
      {matching && (
        <MatchDialog
          payment={matching}
          close={() => setMatching(null)}
          done={() => {
            setMatching(null);
            refresh();
            notify("Payment matched to the selected order.");
          }}
        />
      )}
    </>
  );
}
function MatchDialog({
  payment,
  close,
  done,
}: {
  payment: Payment;
  close: () => void;
  done: () => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/payments/" + payment.id + "/match", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))),
      });
      done();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog title={"Match " + payment.reference} close={close}>
      <p>
        The selected order must equal{" "}
        {money(payment.amount_cents, payment.currency)}.
      </p>
      <form onSubmit={submit}>
        <Field label="Order reference">
          <input
            name="order_reference"
            required
            maxLength={80}
            autoFocus
            defaultValue={payment.order_reference}
          />
        </Field>
        <ErrorBox text={error} />
        <div className="dialog-actions">
          <button className="button primary" disabled={busy}>
            {busy ? "Matching..." : "Match payment"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
