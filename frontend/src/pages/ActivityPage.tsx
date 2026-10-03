import { useState, useEffect } from "react";
import { api, type Audit, type Page } from "../api";
import { Empty, Pager, ErrorBox, date, message } from "../ui";

export default function ActivityPage({ revision }: { revision: number }) {
  const [data, setData] = useState<Page<Audit> | null>(null),
    [page, setPage] = useState(1),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    api<Page<Audit>>("/audit?page=" + page, { signal: c.signal })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(message(e));
      });
    return () => c.abort();
  }, [page, revision]);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Activity</h1>
          <p>A record of changes, deliveries and reconciliation actions.</p>
        </div>
      </div>
      <ErrorBox text={error} />
      <section className="panel">
        {data?.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {["Action", "Detail", "Actor", "When"].map((h) => (
                    <th key={h} scope="col">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id}>
                    <td className="strong">
                      {a.action.replaceAll(".", " / ")}
                    </td>
                    <td>{a.detail}</td>
                    <td>{a.actor}</td>
                    <td className="muted nowrap">{date(a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title={data ? "No activity recorded" : "Loading activity"}
            detail="Actions in this workspace appear here."
          />
        )}
        {data && (
          <Pager page={page} total={data.total} size={30} setPage={setPage} />
        )}
      </section>
    </>
  );
}
