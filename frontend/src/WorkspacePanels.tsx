import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type RefObject,
  type ReactNode,
} from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Box,
  CheckCircle2,
  Cpu,
  FileImage,
  FlaskConical,
  History,
  LoaderCircle,
  ScanLine,
  Search,
  Settings2,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import {
  api,
  date,
  label,
  type Inspection,
  type ModelStatus,
  type Overview,
  type Page,
  type User,
} from "./api";
const errorMessage = (e: unknown) =>
  e instanceof Error ? e.message : "The request could not be completed.";
export function Alert({ children }: { children: ReactNode }) {

  return (
    <div className="alert" role="alert">
      {children}
    </div>
  );

}
export function Spinner() {

  return <LoaderCircle size={18} className="spin" aria-label="Loading" />;

}

function useDialog(active: boolean, onClose: () => void) {

  const dialog = useRef<HTMLElement | null>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {

    if (!active) {

      return;
    
}

    const previousFocus = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      Array.from(
        dialog.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), [tabindex='0']",
        ) || [],
      );
    focusable()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {

      if (event.key === "Escape") {

        close.current();
      
}

      if (event.key !== "Tab") {

        return;
      
}

      const elements = focusable();
      const first = elements[0];
      const last = elements[elements.length - 1];

      if (event.shiftKey && document.activeElement === first) {

        event.preventDefault();
        last?.focus();
      
} else if (!event.shiftKey && document.activeElement === last) {

        event.preventDefault();
        first?.focus();
      
}
    
};
    document.addEventListener("keydown", keydown);

    return () => {

      document.removeEventListener("keydown", keydown);
      document.body.style.overflow = overflow;
      previousFocus?.focus();
    
};
  
}, [active]);

  return dialog;

}

export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {

  return (
    <div className="empty">
      <div className="empty-icon">
        <ScanLine size={27} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );

}

export function Result({
  inspection,
  onClose,
}: {
  inspection: Inspection;
  onClose: () => void;
}) {

  const [original, setOriginal] = useState(false);
  const dialog = useDialog(true, onClose);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        ref={dialog}
        className="result-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="result-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <div>
            <div className="section-kicker">INSPECTION RESULT</div>
            <h2 id="result-title">{inspection.filename}</h2>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close result"
            autoFocus
          >
            <X size={21} />
          </button>
        </header>
        <div className="result-layout">
          <div className="result-image">
            <img
              src={original ? inspection.original_url : inspection.image_url}
              alt={
                original
                  ? "Original circuit board"
                  : "Circuit board with predicted defect bounding boxes"
              }
            />
            <button
              className="button secondary"
              onClick={() => setOriginal(!original)}
            >
              {original ? "Show detections" : "Show original"}
            </button>
          </div>
          <aside>
            <span
              className={`badge ${inspection.detections.length ? "amber" : "green"}`}
            >
              {inspection.detections.length
                ? `${inspection.detections.length} detections`
                : "No defects detected"}
            </span>
            <p className="muted">
              Review predictions before making a quality decision.
            </p>
            <dl className="result-meta">
              <div>
                <dt>Inspected</dt>
                <dd>{date(inspection.created_at)}</dd>
              </div>
              <div>
                <dt>Image size</dt>
                <dd>
                  {inspection.width} × {inspection.height}
                </dd>
              </div>
              <div>
                <dt>Confidence threshold</dt>
                <dd>{Math.round(inspection.confidence * 100)}%</dd>
              </div>
              <div>
                <dt>Inference time</dt>
                <dd>{inspection.duration_ms} ms</dd>
              </div>
            </dl>
            <div className="detections">
              {inspection.detections.map((d, i) => (
                <details className="detection" key={i} open={i === 0}>
                  <summary>
                    <span className="detection-number">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span>{label(d.label)}</span>
                    <strong>{Math.round(d.confidence * 100)}%</strong>
                  </summary>
                  <div className="detection-details">
                    <span
                      className={`badge ${d.review_priority === "critical" ? "critical" : "amber"}`}
                    >
                      {label(d.review_priority)} review priority
                    </span>
                    <p>{d.explanation}</p>
                    <p>
                      <strong>Suggested review:</strong> {d.recommendation}
                    </p>
                    <small className="mono">
                      Box (pixels): [{d.box.join(", ")}]
                    </small>
                  </div>
                </details>
              ))}
            </div>
            <p className="guidance-note">
              Review priorities and repair suggestions are class-based guidance,
              not predictions of electrical severity.
            </p>
            <a
              className="button primary"
              href={inspection.image_url}
              download={`${inspection.id}-annotated.png`}
            >
              <ArrowDownToLine size={16} /> Download image
            </a>
            <button
              className="button secondary"
              onClick={() => {

                const a = document.createElement("a");
                a.href = URL.createObjectURL(
                  new Blob([JSON.stringify(inspection, null, 2)], {
                    type: "application/json",
                  }),
                );
                a.download = `${inspection.id}.json`;
                a.click();
                setTimeout(() => URL.revokeObjectURL(a.href), 1000);
              
}}
            >
              <ArrowDownToLine size={16} /> Export JSON
            </button>
            <small className="model-hash">
              MODEL {inspection.model_sha256.slice(0, 12)}
            </small>
          </aside>
        </div>
      </section>
    </div>
  );

}

export function InspectionTable({
  items,
  open,
}: {
  items: Inspection[];
  open: (item: Inspection) => void;
}) {

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>BOARD / FILE</th>
            <th>INSPECTED</th>
            <th>RESULT</th>
            <th>INFERENCE</th>
            <th>
              <span className="sr-only">Open result</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <button className="file-button" onClick={() => open(item)}>
                  <span className="file-icon">
                    <FileImage size={18} />
                  </span>
                  <span>
                    {item.filename}
                    <small>
                      {item.user_name || `${item.width} × ${item.height} px`}
                    </small>
                  </span>
                </button>
              </td>
              <td>{date(item.created_at)}</td>
              <td>
                <span
                  className={`badge ${item.detections.length ? "amber" : "green"}`}
                >
                  {item.detections.length
                    ? `${item.detections.length} detections`
                    : "No detections"}
                </span>
              </td>
              <td className="mono">{item.duration_ms} ms</td>
              <td>
                <button
                  className="icon-button"
                  onClick={() => open(item)}
                  aria-label={`View ${item.filename}`}
                >
                  <ArrowRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

}

export function ModelPage({
  model,
  refresh,
}: {
  model: ModelStatus | null;
  refresh: () => void;
}) {

  const names = model?.manifest?.names || [
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    "short",
    "spur",
    "spurious_copper",
  ];

  return (
    <>
      <div className="page-title">
        <div className="section-kicker">FROM TRAINING TO INSPECTION</div>
        <h1>Your detection engine.</h1>
        <p>
          Train in Kaggle. Bring the best checkpoint back to your workspace.
        </p>
      </div>
      <section className="panel model-status">
        <div>
          <Cpu size={28} />
          <div>
            <h2>{model?.manifest?.architecture || "PCB model setup"}</h2>
            <p>{model?.message || "Loading model status…"}</p>
          </div>
        </div>
        <button className="button secondary" onClick={refresh}>
          Refresh status
        </button>
      </section>
      <div className="model-steps">
        {[
          {
            icon: FlaskConical,
            title: "Train in Kaggle",
            text: "Upload notebooks/pcb_yolo_kaggle.ipynb. Add the PCB Defects dataset, select a GPU and run the notebook.",
          },
          {
            icon: ArrowDownToLine,
            title: "Download the artifacts",
            text: "Download best.pt and model-manifest.json from the notebook output. Keep them together from the same training run.",
          },
          {
            icon: Cpu,
            title: "Connect your model",
            text: "Install the inference extra, place both files in models/ and restart the API. We verify the checksum and class order before inference.",
          },
        ].map((s, i) => (
          <section className="panel model-step" key={s.title}>
            <div className="model-step-number">0{i + 1}</div>
            <s.icon size={24} />
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </section>
        ))}
      </div>
      <section className="panel taxonomy">
        <div className="panel-heading">
          <div>
            <Box size={19} />
            <h2>
              {model?.manifest
                ? "Installed model classes"
                : "Default training classes"}
            </h2>
          </div>
          <span className="subtle-label">CLASS ORDER IS VERIFIED</span>
        </div>
        <div className="class-grid">
          {names.map((name, i) => (
            <div key={name}>
              <span className="mono">0{i}</span>
              <span>{label(name)}</span>
              <CheckCircle2 size={17} />
            </div>
          ))}
        </div>
        <p className="panel-footnote">
          DeepPCB uses pin hole in place of missing hole. Train these datasets
          separately using the notebook’s dataset setting.
        </p>
      </section>
      {model?.manifest && (
        <section className="panel manifest">
          <h2>Training provenance</h2>
          <p>Dataset: {model.manifest.dataset}</p>
          <p className="mono">SHA-256: {model.manifest.sha256}</p>
          {model.manifest.metrics && (
            <div className="metric-grid">
              {Object.entries(model.manifest.metrics).map(([key, value]) => (
                <div key={key}>
                  <small>{key}</small>
                  <strong>
                    {typeof value === "number"
                      ? value.toFixed(4)
                      : String(value)}
                  </strong>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
      <div className="info-note">
        <Activity size={19} />
        <p>
          Model scores are measured on the notebook’s held-out dataset. Validate
          on boards from your own camera before relying on results in
          production.
        </p>
      </div>
    </>
  );

}

export function Admin({
  currentUser,
  open,
}: {
  currentUser: User;
  open: (item: Inspection) => void;
}) {

  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<Page<User>>({ items: [], total: 0 });
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const dialog = useDialog(Boolean(editing), () => {

    if (!busy) {

      setEditing(null);
    
}
  
});
  const load = useCallback(async () => {

    setError("");
    setLoading(true);

    try {

      const [o, u] = await Promise.all([
        api<Overview>("/admin/overview"),
        api<Page<User>>(
          `/admin/users?q=${encodeURIComponent(query)}&offset=${offset}`,
        ),
      ]);
      setOverview(o);
      setUsers(u);
    
} catch (e) {

      setError(errorMessage(e));
    
} finally {

      setLoading(false);
    
}
  
}, [query, offset]);
  useEffect(() => {

    let active = true;
    const timer = setTimeout(() => {

      if (active) {

        void load();
      
}
    
}, 250);

    return () => {

      active = false;
      clearTimeout(timer);
    
};
  
}, [load]);

  async function save(e: FormEvent) {

    e.preventDefault();

    if (!editing) {

      return;
    
}

    setBusy(true);
    setError("");

    try {

      await api(`/admin/users/${editing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          role: editing.role,
          active: Boolean(editing.active),
        }),
      });
      setEditing(null);
      await load();
    
} catch (e) {

      setError(errorMessage(e));
    
} finally {

      setBusy(false);
    
}
  
}

  return (
    <>
      <div className="page-title">
        <div className="section-kicker">WORKSPACE ADMINISTRATION</div>
        <h1>The whole picture.</h1>
        <p>
          Manage access and follow inspection activity across your workspace.
        </p>
      </div>
      {error && <Alert>{error}</Alert>}
      {overview ? (
        <>
          <div className="stat-grid">
            {[
              {
                title: "Registered users",
                value: overview.users,
                detail: `${overview.active_users} active accounts`,
                icon: Users,
              },
              {
                title: "Total inspections",
                value: overview.inspections,
                detail: "Across all accounts",
                icon: ScanLine,
              },
              {
                title: "Detected defects",
                value: overview.defects,
                detail: "All saved predictions",
                icon: Activity,
              },
              {
                title: "Administrators",
                value: overview.admins,
                detail: "Workspace access managers",
                icon: ShieldCheck,
              },
            ].map((s) => (
              <section className="panel stat" key={s.title}>
                <div>
                  {s.title}
                  <s.icon size={18} />
                </div>
                <strong>{s.value}</strong>
                <small>{s.detail}</small>
              </section>
            ))}
          </div>
          <section className="panel users-panel">
            <div className="panel-heading">
              <div>
                <Users size={19} />
                <h2>User directory</h2>
                <span className="count-pill">{users.total}</span>
              </div>
              <label className="search-field">
                <Search size={16} />
                <input
                  aria-label="Search users"
                  placeholder="Search name or email"
                  value={query}
                  onChange={(e) => {

                    setQuery(e.target.value);
                    setOffset(0);
                  
}}
                />
              </label>
            </div>
            <div className="table-scroll">
              <table aria-busy={loading}>
                <thead>
                  <tr>
                    <th>USER</th>
                    <th>ROLE</th>
                    <th>STATUS</th>
                    <th>INSPECTIONS</th>
                    <th>LAST SIGN IN</th>
                    <th>ACCESS</th>
                  </tr>
                </thead>
                <tbody>
                  {users.items.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div className="directory-user">
                          <span className="avatar">
                            {u.name.slice(0, 1).toUpperCase()}
                          </span>
                          <span>
                            {u.name}
                            <small>{u.email}</small>
                          </span>
                        </div>
                      </td>
                      <td>{label(u.role)}</td>
                      <td>
                        <span
                          className={`badge ${u.active ? "green" : "neutral"}`}
                        >
                          {u.active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td>{u.inspection_count}</td>
                      <td>{u.last_login ? date(u.last_login) : "Never"}</td>
                      <td>
                        <button
                          className="text-button"
                          disabled={u.id === currentUser.id}
                          onClick={() => {

                            setError("");
                            setEditing({ ...u });
                          
}}
                        >
                          {u.id === currentUser.id ? "You" : "Manage"}
                          {u.id !== currentUser.id && <Settings2 size={15} />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!users.items.length && (
              <Empty title="No matching users">
                Try another name or email address.
              </Empty>
            )}
            <Pagination
              total={users.total}
              offset={offset}
              setOffset={setOffset}
            />
          </section>
          <section className="panel recent-panel">
            <div className="panel-heading">
              <div>
                <History size={18} />
                <h2>Workspace inspections</h2>
              </div>
              <span className="subtle-label">LATEST 10</span>
            </div>
            {overview.recent_inspections.length ? (
              <InspectionTable
                items={overview.recent_inspections}
                open={open}
              />
            ) : (
              <Empty title="No inspections yet">
                Activity appears when a user runs an inspection.
              </Empty>
            )}
          </section>
          <section className="panel audit-panel">
            <div className="panel-heading">
              <div>
                <ShieldCheck size={18} />
                <h2>Access & activity log</h2>
              </div>
              <span className="subtle-label">LATEST 30 EVENTS</span>
            </div>
            {overview.audit.map((a) => (
              <div className="audit-event" key={a.id}>
                <span className="audit-dot" />
                <div>
                  <strong>{a.actor_name || "System"}</strong>
                  <p>
                    {a.action.replaceAll(".", " · ")}
                    <small>Target: {a.target}</small>
                  </p>
                </div>
                <time>{date(a.created_at)}</time>
              </div>
            ))}
          </section>
        </>
      ) : (
        <div className="loading-page">
          <Spinner /> Loading workspace…
        </div>
      )}
      {editing && (
        <div className="modal-backdrop">
          <form
            ref={dialog as RefObject<HTMLFormElement | null>}
            className="edit-modal"
            onSubmit={save}
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-title"
          >
            <header>
              <h2 id="edit-title">Manage access</h2>
              <button
                type="button"
                className="icon-button"
                onClick={() => setEditing(null)}
                aria-label="Close user settings"
              >
                <X size={20} />
              </button>
            </header>
            <p>
              {editing.name}
              <small>{editing.email}</small>
            </p>
            <label>
              Account role
              <select
                autoFocus
                value={editing.role}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    role: e.target.value as User["role"],
                  })
                }
              >
                <option value="user">User — own inspections</option>
                <option value="admin">
                  Administrator — all workspace data
                </option>
              </select>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={Boolean(editing.active)}
                onChange={(e) =>
                  setEditing({ ...editing, active: e.target.checked })
                }
              />{" "}
              Account enabled
            </label>
            <p className="muted">
              Disabling an account or changing its role signs it out
              immediately.
            </p>
            {error && <Alert>{error}</Alert>}
            <button className="button primary" disabled={busy}>
              {busy ? <Spinner /> : "Save access settings"}
            </button>
          </form>
        </div>
      )}
    </>
  );

}

export function Pagination({
  total,
  offset,
  setOffset,
}: {
  total: number;
  offset: number;
  setOffset: (n: number) => void;
}) {

  return (
    <div className="pagination">
      <span>
        {total
          ? `${offset + 1}–${Math.min(offset + 20, total)} of ${total}`
          : "0 records"}
      </span>
      <button
        className="icon-button"
        aria-label="Previous page"
        disabled={offset === 0}
        onClick={() => setOffset(Math.max(0, offset - 20))}
      >
        <ArrowLeft size={16} />
      </button>
      <button
        className="icon-button"
        aria-label="Next page"
        disabled={offset + 20 >= total}
        onClick={() => setOffset(offset + 20)}
      >
        <ArrowRight size={16} />
      </button>
    </div>
  );

}
