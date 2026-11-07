import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  CircuitBoard,
  Clock3,
  FileImage,
  Layers,
  Lightbulb,
  LogOut,
  Menu,
  ScanLine,
  Search,
  ShieldCheck,
  TriangleAlert,
  Upload,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import {
  api,
  date,
  label,
  type DashboardData,
  type Inspection,
  type User,
} from "./api";
import { Alert, Empty, InspectionTable, Spinner } from "./WorkspacePanels";

export type Navigate = (path: string) => void;
export function SiteLink({
  to,
  navigate,
  children,
  className = "",
  onClick,
}: {
  to: string;
  navigate: Navigate;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {

  return (
    <a
      href={to}
      className={className}
      onClick={(event) => {

        if (
          event.button === 0 &&
          !event.metaKey &&
          !event.ctrlKey &&
          !event.shiftKey &&
          !event.altKey
        ) {

          event.preventDefault();
          navigate(to);
          onClick?.();
        
}
      
}}
    >
      {children}
    </a>
  );

}
export function Brand({
  navigate,
  compact = false,
}: {
  navigate: Navigate;
  compact?: boolean;
}) {

  return (
    <SiteLink to="/" navigate={navigate} className="brand">
      <CircuitBoard size={30} />
      {compact ? (
        <span>
          PCB<span className="purple-text">Detect</span>
        </span>
      ) : (
        <span>
          PCB <span className="cyan-text">Defect Detector</span>
        </span>
      )}
    </SiteLink>
  );

}
export function Header({
  user,
  navigate,
  path,
  logout,
}: {
  user: User | null;
  navigate: Navigate;
  path: string;
  logout: () => void;
}) {

  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  const links = [
    { to: "/dashboard", name: "Dashboard" },
    { to: "/analyze", name: "Analyze" },
    { to: "/history", name: "History" },
    { to: "/model", name: "Detection model" },
    ...(user?.role === "admin"
      ? [{ to: "/admin", name: "Administration" }]
      : []),
  ];

  return (
    <header className="site-header">
      <div className="container header-inner">
        <Brand navigate={navigate} />
        <nav className="desktop-nav" aria-label="Main navigation">
          {user ? (
            <>
              {links.map((link) => (
                <SiteLink
                  key={link.to}
                  to={link.to}
                  navigate={navigate}
                  className={path === link.to ? "nav-active" : ""}
                >
                  {link.name}
                </SiteLink>
              ))}
              <SiteLink to="/account" navigate={navigate} className="avatar">
                <span className="sr-only">Your account</span>
                {user.name[0].toUpperCase()}
              </SiteLink>
            </>
          ) : (
            <SiteLink
              to="/auth/login"
              navigate={navigate}
              className="button primary"
            >
              Sign In
            </SiteLink>
          )}
        </nav>
        <button
          className="mobile-menu-button icon-button"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open && (
        <nav
          className="mobile-nav"
          aria-label="Mobile navigation"
          onClick={() => setOpen(false)}
        >
          {user ? (
            <>
              {links.map((link) => (
                <SiteLink key={link.to} to={link.to} navigate={navigate}>
                  {link.name}
                </SiteLink>
              ))}
              <SiteLink to="/account" navigate={navigate}>
                Your account
              </SiteLink>
              <button onClick={logout}>
                <LogOut size={16} /> Sign out
              </button>
            </>
          ) : (
            <>
              <SiteLink to="/analyze" navigate={navigate}>
                Analyze a board
              </SiteLink>
              <SiteLink to="/auth/login" navigate={navigate}>
                Sign In
              </SiteLink>
              <SiteLink to="/auth/register" navigate={navigate}>
                Create account
              </SiteLink>
            </>
          )}
        </nav>
      )}
    </header>
  );

}
export function Footer({ navigate }: { navigate: Navigate }) {

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <Brand navigate={navigate} compact />
            <p>
              AI-assisted circuit board inspection.
              <br />
              Locate defects. Review the details.
            </p>
            <div className="footer-icons">
              <CircuitBoard size={18} />
              <ScanLine size={18} />
              <ShieldCheck size={18} />
            </div>
          </div>
          <div>
            <h3>Product</h3>
            <SiteLink to="/#features" navigate={navigate}>
              Features
            </SiteLink>
            <SiteLink to="/analyze" navigate={navigate}>
              Image analysis
            </SiteLink>
            <SiteLink to="/dashboard" navigate={navigate}>
              Dashboard
            </SiteLink>
            <SiteLink to="/history" navigate={navigate}>
              Inspection history
            </SiteLink>
          </div>
          <div>
            <h3>Resources</h3>
            <SiteLink to="/guide" navigate={navigate}>
              Defect guide
            </SiteLink>
            <SiteLink to="/guide#workflow" navigate={navigate}>
              How it works
            </SiteLink>
            <SiteLink to="/model" navigate={navigate}>
              Model setup
            </SiteLink>
            <SiteLink to="/privacy" navigate={navigate}>
              Privacy & access
            </SiteLink>
          </div>
          <div>
            <h3>Workspace</h3>
            <SiteLink to="/auth/login" navigate={navigate}>
              Sign in
            </SiteLink>
            <SiteLink to="/auth/register" navigate={navigate}>
              Create account
            </SiteLink>
            <SiteLink to="/account" navigate={navigate}>
              Your account
            </SiteLink>
            <p>
              AI-assisted.
              <br />
              Human-reviewed.
            </p>
          </div>
        </div>
        <div className="footer-bottom">
          © {new Date().getFullYear()} PCB Detect. Built for a closer look.
        </div>
      </div>
    </footer>
  );

}
const features = [
  {
    icon: Search,
    title: "Precise Detection",
    text: "Locate PCB surface defects with labeled bounding boxes and a confidence score for each prediction.",
  },
  {
    icon: TriangleAlert,
    title: "Multi-Stage Assessment",
    text: "Prioritize review with transparent class-based guidance for open circuits, shorts and other surface defects.",
  },
  {
    icon: Lightbulb,
    title: "Explainable Results",
    text: "See the predicted region, defect type and confidence, with a plain-language explanation of what to inspect.",
  },
  {
    icon: Zap,
    title: "Image Analysis",
    text: "Upload a board image, adjust the confidence threshold and compare the original with the annotated result.",
  },
  {
    icon: BarChart3,
    title: "Detailed Reports",
    text: "Track your inspections, review defect distributions and export annotated images and detection coordinates.",
  },
  {
    icon: Wrench,
    title: "Repair Guidance",
    text: "Read practical review suggestions for each predicted defect before a qualified technician decides on rework.",
  },
];
export function Home({
  navigate,
  onFile,
}: {
  navigate: Navigate;
  onFile: (file: File) => void;
}) {

  const [dragging, setDragging] = useState(false);

  function choose(file?: File) {

    if (file) {

      onFile(file);
      navigate("/analyze");
    
}
  
}

  return (
    <>
      <section className="hero">
        <div className="hero-glow cyan-glow" />
        <div className="hero-glow purple-glow" />
        <div className="container hero-content">
          <h1>PCB Defect Detector</h1>
          <p>
            Detect and analyze circuit board defects with AI. Find the affected
            regions, understand the predictions, and review practical repair
            guidance in one workspace.
          </p>
          <div className="hero-actions">
            <SiteLink
              to="/analyze"
              navigate={navigate}
              className="button primary large"
            >
              Start Analyzing
            </SiteLink>
            <SiteLink
              to="/dashboard"
              navigate={navigate}
              className="button outline-purple large"
            >
              View Dashboard
            </SiteLink>
          </div>
        </div>
      </section>
      <section id="features" className="features-section container">
        <div className="section-heading">
          <h2>
            Advanced <span className="purple-text">Features</span>
          </h2>
          <p>
            Computer vision and practical tools for a closer look at every
            circuit board.
          </p>
        </div>
        <div className="features-grid">
          {features.map(({ icon: Icon, title, text }, i) => (
            <article className="feature-card" key={title}>
              <Icon
                className={i % 2 ? "purple-text" : "cyan-text"}
                size={38}
                strokeWidth={1.8}
              />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="home-upload container">
        <div className="section-heading">
          <h2>
            Upload Your <span className="cyan-text">PCB Image</span>
          </h2>
          <p>Choose a clear, high-resolution image to begin your inspection.</p>
        </div>
        <label
          className={`home-dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(e) => {

            e.preventDefault();
            setDragging(true);
          
}}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {

            e.preventDefault();
            setDragging(false);
            choose(e.dataTransfer.files[0]);
          
}}
        >
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/tiff,.tif,.tiff"
            onChange={(e) => choose(e.target.files?.[0])}
          />
          <Upload size={58} strokeWidth={1.7} />
          <strong>Drag & Drop PCB Image</strong>
          <span>or click to browse files</span>
          <small>JPG, PNG, TIFF or WebP · up to 20 MB</small>
        </label>
      </section>
    </>
  );

}

export function AuthPage({
  register,
  navigate,
  onAuth,
}: {
  register: boolean;
  navigate: Navigate;
  onAuth: (user: User) => void;
}) {

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setError(""), [register]);

  async function submit(e: FormEvent<HTMLFormElement>) {

    e.preventDefault();
    setError("");
    const form = new FormData(e.currentTarget);

    if (register && form.get("password") !== form.get("confirm")) {

      setError("The passwords do not match.");

      return;
    
}

    setBusy(true);
    const body = {
      email: form.get("email"),
      password: form.get("password"),
      ...(register
        ? { name: form.get("name") }
        : { remember_me: form.get("remember_me") === "on" }),
    };

    try {

      onAuth(
        await api<User>(`/auth/${register ? "register" : "login"}`, {
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
    
} catch (e) {

      setError(e instanceof Error ? e.message : "Could not sign in.");
    
} finally {

      setBusy(false);
    
}
  
}

  return (
    <main className="auth-shell">
      <aside className="auth-story">
        <Brand navigate={navigate} compact />
        <div className="auth-glow" />
        <div className="auth-story-bottom">
          <div className="auth-story-icon">
            <CircuitBoard size={52} />
          </div>
          <h2>
            See the defect.
            <br />
            <span className="cyan-text">Understand the detail.</span>
          </h2>
          <p>
            A dedicated workspace for visual PCB inspection, traceable results
            and informed review.
          </p>
          <span>
            <ShieldCheck size={16} /> Your boards. Your inspection history.
          </span>
        </div>
      </aside>
      <section className="auth-main">
        <div className="auth-content">
          <CircuitBoard className="auth-mark" size={45} />
          <h1>{register ? "Create your account" : "Welcome to PCB Detect"}</h1>
          <p>
            {register
              ? "Start your PCB inspection workspace."
              : "Enter your credentials to sign in to your account."}
          </p>
          <form className="auth-card" onSubmit={submit}>
            {register && (
              <label htmlFor="full-name">
                Full name
                <input
                  id="full-name"
                  name="name"
                  autoComplete="name"
                  minLength={2}
                  maxLength={80}
                  placeholder="Your full name"
                  required
                />
              </label>
            )}
            <label htmlFor="email">
              Email
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                required
              />
            </label>
            <label htmlFor="password">
              Password
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={12}
                maxLength={128}
                aria-describedby="password-hint"
                required
              />
            </label>
            {register && (
              <label htmlFor="confirm-password">
                Confirm password
                <input
                  id="confirm-password"
                  name="confirm"
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={128}
                  required
                />
              </label>
            )}
            <small id="password-hint">Use 12–128 characters.</small>
            {!register && (
              <label className="checkbox-label">
                <input type="checkbox" name="remember_me" /> Remember me for 30
                days
              </label>
            )}
            {error && <Alert>{error}</Alert>}
            <button className="button primary" disabled={busy}>
              {busy ? <Spinner /> : register ? "Create account" : "Sign In"}
            </button>
            <div className="auth-access-note">
              <ShieldCheck size={16} />
              <span>Protected sign-in for users and administrators.</span>
            </div>
          </form>
          <p className="auth-switch">
            {register ? "Already have an account?" : "Don't have an account?"}{" "}
            <SiteLink
              to={register ? "/auth/login" : "/auth/register"}
              navigate={navigate}
            >
              {register ? "Sign in" : "Sign up"}
            </SiteLink>
          </p>
          <SiteLink to="/" navigate={navigate} className="back-home">
            ← Back to home
          </SiteLink>
        </div>
      </section>
    </main>
  );

}

export function Dashboard({
  user,
  navigate,
  open,
}: {
  user: User;
  navigate: Navigate;
  open: (i: Inspection) => void;
}) {

  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {

    let current = true;
    api<DashboardData>("/dashboard")
      .then((d) => {

        if (current) {

          setData(d);
        
}
      
})
      .catch((e) => {

        if (current) {

          setError(e.message);
        
}
      
});

    return () => {

      current = false;
    
};
  
}, [user.id]);

  if (error) {

    return (
      <div className="container page-container">
        <Alert>{error}</Alert>
      </div>
    );
  
}

  if (!data) {

    return (
      <div className="loading-page">
        <Spinner /> Loading dashboard…
      </div>
    );
  
}

  const max = Math.max(1, ...data.trend.map((t) => t.total));
  const classMax = Math.max(1, ...Object.values(data.class_counts));

  return (
    <div className="container page-container">
      <div className="page-heading with-action">
        <div>
          <div className="eyebrow">YOUR INSPECTION WORKSPACE</div>
          <h1>Dashboard</h1>
          <p>
            Welcome back, {user.name.split(" ")[0]}. Here is your inspection
            activity.
          </p>
        </div>
        <SiteLink to="/analyze" navigate={navigate} className="button primary">
          <ScanLine size={17} /> New Analysis
        </SiteLink>
      </div>
      <div className="stat-grid">
        {[
          {
            name: "Total inspections",
            value: data.inspections,
            icon: ScanLine,
            detail: "Saved board analyses",
          },
          {
            name: "Detected defects",
            value: data.defects,
            icon: TriangleAlert,
            detail: "Predicted regions for review",
          },
          {
            name: "No detections",
            value: data.no_detections,
            icon: CheckCircle2,
            detail: "Review before a quality decision",
          },
          {
            name: "Avg. inference",
            value: `${data.average_duration_ms} ms`,
            icon: Clock3,
            detail: "Excludes initial model loading",
          },
        ].map((s) => (
          <section className="panel stat" key={s.name}>
            <div>
              {s.name}
              <s.icon size={20} />
            </div>
            <strong>{s.value}</strong>
            <small>{s.detail}</small>
          </section>
        ))}
      </div>
      <div className="dashboard-charts">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <h2>Inspection Activity</h2>
            <span className="muted">Last 7 days · UTC</span>
          </div>
          {data.trend.some((t) => t.total) ? (
            <div
              className="activity-chart"
              role="img"
              aria-label={data.trend
                .map((t) => `${t.day}: ${t.total} inspections`)
                .join(", ")}
            >
              {data.trend.map((t) => (
                <div className="chart-column" key={t.day}>
                  <span>{t.total}</span>
                  <div className="chart-track">
                    <div
                      className="chart-bar"
                      style={{ height: `${(t.total / max) * 100}%` }}
                    />
                  </div>
                  <small>
                    {new Date(`${t.day}T12:00:00Z`).toLocaleDateString(
                      undefined,
                      { weekday: "short", timeZone: "UTC" },
                    )}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="Your activity starts here">
              Run your first analysis to begin tracking inspections.
            </Empty>
          )}
        </section>
        <section className="panel chart-panel">
          <div className="panel-heading">
            <h2>Defect Distribution</h2>
            <Layers size={18} />
          </div>
          {Object.keys(data.class_counts).length ? (
            <div className="distribution">
              {Object.entries(data.class_counts).map(([name, count]) => (
                <div key={name}>
                  <div>
                    <span>{label(name)}</span>
                    <strong>{count}</strong>
                  </div>
                  <div className="distribution-track">
                    <span style={{ width: `${(count / classMax) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="No detections recorded">
              Defect classes will appear after you save an analysis.
            </Empty>
          )}
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <FileImage size={19} />
            <h2>Recent Analyses</h2>
          </div>
          <SiteLink to="/history" navigate={navigate} className="text-button">
            View all <ArrowRight size={15} />
          </SiteLink>
        </div>
        {data.recent_inspections.length ? (
          <InspectionTable items={data.recent_inspections} open={open} />
        ) : (
          <Empty title="No analyses yet">
            Upload your first board image to build your inspection history.
          </Empty>
        )}
      </section>
    </div>
  );

}
export function AccountPage({
  user,
  logout,
}: {
  user: User;
  logout: () => void;
}) {

  return (
    <div className="container page-container">
      <div className="page-heading">
        <h1>Your account</h1>
        <p>Your identity and workspace access.</p>
      </div>
      <section className="panel account-panel">
        <span className="avatar large">{user.name[0].toUpperCase()}</span>
        <h2>{user.name}</h2>
        <p>{user.email}</p>
        <span className="badge green">{label(user.role)}</span>
        <dl className="result-meta">
          <div>
            <dt>Member since</dt>
            <dd>{date(user.created_at)}</dd>
          </div>
          <div>
            <dt>Access</dt>
            <dd>
              {user.role === "admin"
                ? "Workspace administration and all inspections"
                : "Personal inspections and history"}
            </dd>
          </div>
        </dl>
        <button className="button secondary" onClick={logout}>
          <LogOut size={17} />
          Sign out
        </button>
      </section>
    </div>
  );

}
export function Guide({ privacy = false }: { privacy?: boolean }) {

  const classes = [
    ["Missing hole", "An expected hole appears absent or obstructed."],
    ["Mouse bite", "A notch in the edge of a conductive trace or pad."],
    ["Open circuit", "A gap in a conductor that may interrupt continuity."],
    ["Short", "A connection between conductors that should be separate."],
    ["Spur", "An extra copper projection from a trace or pad."],
    [
      "Spurious copper",
      "A copper fragment outside the intended conductor pattern.",
    ],
    [
      "Pin hole · DeepPCB",
      "A small void within a copper region, distinct from a missing hole.",
    ],
  ];

  return (
    <div className="container page-container guide-page">
      <div className="page-heading">
        <div className="eyebrow">
          {privacy ? "YOUR DATA & WORKSPACE" : "A CLOSER LOOK"}
        </div>
        <h1>{privacy ? "Privacy & access" : "Understanding PCB defects"}</h1>
        <p>
          {privacy
            ? "How account and inspection information is handled."
            : "A guide to the surface defects recognized by the supported datasets."}
        </p>
      </div>
      {privacy ? (
        <div className="panel prose">
          <ShieldCheck size={32} className="cyan-text" />
          <h2>Private inspection history</h2>
          <p>
            Your images and results are accessible to you and workspace
            administrators. Other registered users cannot view them.
            Administrators can also see account names, email addresses, roles,
            status and inspection activity.
          </p>
          <h2>Account protection</h2>
          <p>
            Passwords are stored as hashes. Browser sign-in uses an HttpOnly
            session cookie. Disabling an account or changing its role revokes
            its sessions.
          </p>
          <h2>What is stored</h2>
          <p>
            Accounts and inspection records are stored in PostgreSQL. Original
            and annotated images are stored by the application. Contact your
            workspace administrator for data retention, export or deletion
            requests.
          </p>
          <h2>Image links</h2>
          <p>
            If you load an image by URL, your browser requests it directly from
            that host. The application then receives the selected image when you
            run an analysis.
          </p>
        </div>
      ) : (
        <>
          <div className="guide-grid">
            {classes.map(([name, text], i) => (
              <article className="panel guide-item" key={name}>
                <span className="class-number">0{i + 1}</span>
                <h2>{name}</h2>
                <p>{text}</p>
              </article>
            ))}
          </div>
          <section id="workflow" className="panel prose">
            <h2>From image to inspection result</h2>
            <ol>
              <li>
                Upload a clear board image or load an accessible image URL.
              </li>
              <li>
                Choose a confidence threshold and run the trained YOLO detection
                model.
              </li>
              <li>
                Review numbered bounding boxes, confidence scores and box
                coordinates.
              </li>
              <li>
                Compare the original, read class-based guidance, and export the
                result.
              </li>
            </ol>
            <h2>Interpreting the result</h2>
            <p>
              A confidence score measures the model's confidence in a
              prediction. It does not measure the electrical impact of a defect.
              Review priority and repair guidance are class-based rules, not
              predictions from a trained severity model. No detections does not
              certify a defect-free board.
            </p>
            <p>
              Actual impact depends on the board layout, manufacturing
              tolerances and electrical checks. Review all predictions before
              making a quality decision.
            </p>
          </section>
        </>
      )}
    </div>
  );

}
