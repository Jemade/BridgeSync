import { useState, useEffect } from "react";
import { Link2, ArrowRight } from "lucide-react";
import { api } from "../api";
import { Field, ErrorBox, message } from "../ui";

export default function Integrations({
  admin,
  notify,
}: {
  admin: boolean;
  notify: (s: string) => void;
}) {
  const [mode, setMode] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<{ mode: string }>("/connector")
      .then((r) => setMode(r.mode))
      .catch((e) => setError(message(e)));
  }, []);
  async function change(value: string) {
    setBusy(true);
    try {
      await api("/connector", {
        method: "PUT",
        body: JSON.stringify({ mode: value }),
      });
      setMode(value);
      notify("Test connector updated.");
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Integrations</h1>
          <p>Manage the destination for your order deliveries.</p>
        </div>
      </div>
      <ErrorBox text={error} />
      <section className="panel connector-card">
        <div className="connector-title">
          <span className="connector-icon">
            <Link2 size={24} />
          </span>
          <div>
            <h2>Test business system</h2>
            <p>
              A working HTTP connector with a persistent, idempotent receiver.
            </p>
          </div>
          <span className="tag">Simulation</span>
        </div>
        <div className="connector-body">
          <h3>Connection behaviour</h3>
          <p>
            Use these modes to demonstrate delivery, temporary failures and
            permanent rejections. This connector does not connect to a
            commercial ERP.
          </p>
          <Field label="Test mode">
            <select
              value={mode}
              disabled={!admin || busy}
              onChange={(e) => change(e.target.value)}
            >
              <option value="" disabled>
                Loading...
              </option>
              <option value="available">Available: accept orders</option>
              <option value="outage">Temporary outage: return HTTP 503</option>
              <option value="reject">
                Permanent rejection: return HTTP 422
              </option>
            </select>
          </Field>
          <p className="muted">
            Transient failures retry automatically. Terminal failures require a
            manual retry.
          </p>
        </div>
      </section>
      <section className="panel compact">
        <h2>Receive orders from another application</h2>
        <p>
          Create an integration key in Settings, then send an authenticated
          request to:
        </p>
        <code>POST /api/webhooks/orders</code>
        <p>
          Repeated event IDs with the same payload return the original order. A
          conflicting payload is rejected.
        </p>
        <a
          className="text-button"
          href="/docs"
          target="_blank"
          rel="noreferrer"
        >
          Open API reference <ArrowRight size={15} />
        </a>
      </section>
    </>
  );
}
