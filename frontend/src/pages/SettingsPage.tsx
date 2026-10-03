import { useState, useEffect, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { api, type User } from "../api";
import { Dialog, Field, ErrorBox, date, message } from "../ui";

type Member = {
  id: string;
  name: string;
  email: string;
  role: string;
  active: boolean;
};
type Key = { id: string; name: string; created_at: number; revoked: boolean };
export default function SettingsPage({
  user,
  notify,
}: {
  user: User;
  notify: (s: string) => void;
}) {
  const [members, setMembers] = useState<Member[]>([]),
    [keys, setKeys] = useState<Key[]>([]),
    [error, setError] = useState(""),
    [token, setToken] = useState(""),
    [newMember, setNewMember] = useState(false),
    [busy, setBusy] = useState(false);
  const load = () =>
    Promise.all([api<Member[]>("/members"), api<Key[]>("/keys")])
      .then(([m, k]) => {
        setMembers(m);
        setKeys(k);
      })
      .catch((e) => setError(message(e)));
  useEffect(() => {
    load();
  }, []);
  async function createKey(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const form = e.currentTarget;
    try {
      const r = await api<{ token: string }>("/keys", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(form))),
      });
      setToken(r.token);
      form.reset();
      load();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  async function revoke(k: Key) {
    if (
      !confirm(
        "Revoke " + k.name + "? Applications using this key will stop working.",
      )
    )
      return;
    try {
      await api("/keys/" + k.id, { method: "DELETE" });
      load();
      notify("Integration key revoked.");
    } catch (e) {
      setError(message(e));
    }
  }
  async function disable(m: Member) {
    if (!confirm("Disable access for " + m.name + "?")) return;
    try {
      await api("/members/" + m.id, { method: "DELETE" });
      load();
      notify("Member access disabled.");
    } catch (e) {
      setError(message(e));
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Settings</h1>
          <p>Control access to {user.organisation}.</p>
        </div>
      </div>
      <ErrorBox text={error} />
      <section className="panel">
        <div className="panel-heading">
          <h2>Workspace members</h2>
          <button
            className="button secondary"
            onClick={() => setNewMember(true)}
          >
            <Plus size={15} />
            Add member
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {["Member", "Role", "Access", ""].map((h, i) => (
                  <th scope="col" key={i}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td>
                    <strong>{m.name}</strong>
                    <small className="cell-note">{m.email}</small>
                  </td>
                  <td>{m.role}</td>
                  <td>{m.active ? "Active" : "Disabled"}</td>
                  <td>
                    {m.id !== user.id && m.active && (
                      <button
                        className="text-button danger"
                        onClick={() => disable(m)}
                      >
                        Disable
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel compact">
        <h2>Integration keys</h2>
        <p>
          Keys can submit orders to this organisation. They cannot read
          workspace data. A new secret is displayed once.
        </p>
        <form className="inline-form" onSubmit={createKey}>
          <label className="sr-only" htmlFor="key-name">
            Key name
          </label>
          <input
            id="key-name"
            name="name"
            required
            maxLength={80}
            placeholder="Key name, e.g. Storefront"
          />
          <button className="button primary" disabled={busy}>
            Create key
          </button>
        </form>
        {token && (
          <div className="secret">
            <strong>Copy this key now</strong>
            <code>{token}</code>
            <button
              className="text-button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(token);
                  notify("Key copied.");
                } catch {
                  setError(
                    "Clipboard unavailable. Select and copy the displayed key.",
                  );
                }
              }}
            >
              Copy key
            </button>
          </div>
        )}
        <div className="key-list">
          {keys.map((k) => (
            <div key={k.id}>
              <span>
                <strong>{k.name}</strong>
                <small>
                  {k.revoked ? "Revoked" : "Active"} / Created{" "}
                  {date(k.created_at)}
                </small>
              </span>
              {!k.revoked && (
                <button
                  className="text-button danger"
                  onClick={() => revoke(k)}
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
      {newMember && (
        <MemberDialog
          close={() => setNewMember(false)}
          done={() => {
            setNewMember(false);
            load();
            notify("Member created. Share their access details securely.");
          }}
        />
      )}
    </>
  );
}
function MemberDialog({
  close,
  done,
}: {
  close: () => void;
  done: () => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/members", {
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
    <Dialog title="Add workspace member" close={close}>
      <form onSubmit={submit}>
        <Field label="Full name">
          <input name="name" required maxLength={120} autoFocus />
        </Field>
        <Field label="Email">
          <input type="email" name="email" required maxLength={254} />
        </Field>
        <Field label="Password">
          <input
            name="password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete="new-password"
          />
        </Field>
        <p className="caption">
          At least 12 characters. Share credentials through a secure channel.
        </p>
        <Field label="Role">
          <select name="role">
            <option value="viewer">Viewer: read workspace records</option>
            <option value="operator">
              Operator: create orders and reconcile
            </option>
            <option value="admin">Administrator: manage access and keys</option>
          </select>
        </Field>
        <ErrorBox text={error} />
        <div className="dialog-actions">
          <button className="button primary" disabled={busy}>
            {busy ? "Creating..." : "Create member"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
