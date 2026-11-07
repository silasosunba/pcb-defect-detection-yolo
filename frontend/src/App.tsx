import { useCallback, useEffect, useState } from "react";
import { ArrowRight, History } from "lucide-react";
import {
  api,
  type Inspection,
  type ModelStatus,
  type Page,
  type User,
} from "./api";
import {
  Admin,
  Alert,
  Empty,
  InspectionTable,
  ModelPage,
  Pagination,
  Result,
  Spinner,
} from "./WorkspacePanels";
import {
  AccountPage,
  AuthPage,
  Dashboard,
  Footer,
  Guide,
  Header,
  Home,
  SiteLink,
} from "./SitePages";
import { AnalyzePage } from "./AnalyzePage";

const privatePaths = new Set([
  "/dashboard",
  "/history",
  "/model",
  "/admin",
  "/account",
]);
const validPaths = new Set([
  "/",
  "/analyze",
  "/dashboard",
  "/history",
  "/model",
  "/admin",
  "/account",
  "/guide",
  "/privacy",
  "/auth/login",
  "/auth/register",
]);
const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "The request could not be completed.";

function HistoryPage({
  open,
  navigate,
}: {
  open: (i: Inspection) => void;
  navigate: (path: string) => void;
}) {

  const [records, setRecords] = useState<Page<Inspection>>({
    items: [],
    total: 0,
  });
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {

    let active = true;
    setBusy(true);
    setError("");
    api<Page<Inspection>>(`/inspections?offset=${offset}`)
      .then((data) => {

        if (active) {

          setRecords(data);
        
}
      
})
      .catch((e) => {

        if (active) {

          setError(errorMessage(e));
        
}
      
})
      .finally(() => {

        if (active) {

          setBusy(false);
        
}
      
});

    return () => {

      active = false;
    
};
  
}, [offset]);

  return (
    <div className="container page-container">
      <div className="page-heading with-action">
        <div>
          <h1>Inspection History</h1>
          <p>Revisit your board images, predictions and exported results.</p>
        </div>
        <SiteLink to="/analyze" navigate={navigate} className="button primary">
          New Analysis <ArrowRight size={16} />
        </SiteLink>
      </div>
      {error && <Alert>{error}</Alert>}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <History size={20} />
            <h2>All Analyses</h2>
            <span className="count-pill">{records.total}</span>
          </div>
        </div>
        {busy ? (
          <div className="loading-page">
            <Spinner /> Loading inspections…
          </div>
        ) : records.items.length ? (
          <InspectionTable items={records.items} open={open} />
        ) : (
          <Empty title="No analyses yet">
            Your saved analyses will appear here.
          </Empty>
        )}
        <Pagination
          total={records.total}
          offset={offset}
          setOffset={setOffset}
        />
      </section>
    </div>
  );

}

export default function App() {

  const [route, setRoute] = useState(
    window.location.pathname + window.location.search + window.location.hash,
  );
  const path = new URL(route, window.location.origin).pathname;
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selected, setSelected] = useState<Inspection | null>(null);
  const [last, setLast] = useState<Inspection | null>(null);
  const navigate = useCallback((target: string) => {

    const url = new URL(target, window.location.origin);

    if (url.origin !== window.location.origin) {

      return;
    
}

    window.history.pushState({}, "", url.pathname + url.search + url.hash);
    setRoute(url.pathname + url.search + url.hash);
    setError("");
    window.scrollTo(0, 0);

    if (url.hash) {

      setTimeout(
        () => document.getElementById(url.hash.slice(1))?.scrollIntoView(),
        50,
      );
    
}
  
}, []);
  useEffect(() => {

    const update = () =>
      setRoute(
        window.location.pathname +
          window.location.search +
          window.location.hash,
      );
    window.addEventListener("popstate", update);

    return () => window.removeEventListener("popstate", update);
  
}, []);
  useEffect(() => {

    let active = true;
    api<User>("/auth/me")
      .then((value) => {

        if (active) {

          setUser(value);
        
}
      
})
      .catch(() => {})
      .finally(() => {

        if (active) {

          setChecking(false);
        
}
      
});

    return () => {

      active = false;
    
};
  
}, []);
  useEffect(() => {

    const expired = () => {

      setUser(null);
      setModel(null);
      setSelected(null);
      setLast(null);
      navigate(`/auth/login?next=${encodeURIComponent(path)}`);
    
};
    window.addEventListener("session-expired", expired);

    return () => window.removeEventListener("session-expired", expired);
  
}, [navigate, path]);
  const refreshModel = useCallback(async () => {

    try {

      setModel(await api<ModelStatus>("/model"));
    
} catch (e) {

      setError(errorMessage(e));
    
}
  
}, []);
  useEffect(() => {

    setModel(null);

    if (user) {

      void refreshModel();
    
}
  
}, [user, refreshModel]);
  const authRoute = path.startsWith("/auth/");
  const next = new URL(route, window.location.origin).searchParams.get("next");
  const returnTo =
    next && validPaths.has(next) && !next.startsWith("/auth/")
      ? next
      : privatePaths.has(path)
        ? path
        : "/dashboard";
  useEffect(() => {

    if (user && authRoute) {

      navigate(returnTo);
    
}
  
}, [user, authRoute, navigate, returnTo]);
  useEffect(() => {

    document.title = `${({ "/": "PCB Defect Detector", "/analyze": "Image Analysis", "/dashboard": "Dashboard", "/admin": "Administration", "/history": "Inspection History", "/model": "Detection Model", "/account": "Your Account", "/auth/login": "Sign In", "/auth/register": "Create Account", "/guide": "Defect Guide", "/privacy": "Privacy & Access" } as Record<string, string>)[path] || "Page not found"} · PCB Detect`;
  
}, [path]);

  async function logout() {

    try {

      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setModel(null);
      setSelected(null);
      setLast(null);
      setFile(null);
      navigate("/auth/login");
    
} catch (e) {

      setError(errorMessage(e));
    
}
  
}

  async function run(selectedFile: File, confidence: number) {

    const form = new FormData();
    form.append("file", selectedFile);
    form.append("confidence", String(confidence));
    const result = await api<Inspection>("/inspections", {
      method: "POST",
      body: form,
    });
    setLast(result);
    setSelected(result);
    await refreshModel();
  
}

  if (checking && (authRoute || privatePaths.has(path))) {

    return (
      <div className="boot">
        <Spinner />
        <span>Opening your workspace…</span>
      </div>
    );
  
}

  if ((authRoute || privatePaths.has(path)) && !user) {

    return (
      <AuthPage
        register={path === "/auth/register"}
        navigate={navigate}
        onAuth={(value) => {

          setUser(value);
          navigate(returnTo);
        
}}
      />
    );
  
}

  return (
    <div className="site-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <Header
        user={user}
        navigate={navigate}
        path={path}
        logout={() => void logout()}
      />
      <main id="main-content">
        {error && (
          <div className="container global-alert">
            <Alert>{error}</Alert>
          </div>
        )}
        {path === "/" && <Home navigate={navigate} onFile={setFile} />}{" "}
        {path === "/analyze" && (
          <AnalyzePage
            user={user}
            model={model}
            file={file}
            setFile={setFile}
            run={run}
            last={last}
            open={setSelected}
            navigate={navigate}
          />
        )}{" "}
        {path === "/dashboard" && user && (
          <Dashboard user={user} navigate={navigate} open={setSelected} />
        )}{" "}
        {path === "/history" && user && (
          <HistoryPage navigate={navigate} open={setSelected} />
        )}{" "}
        {path === "/model" && user && (
          <div className="container page-container">
            <ModelPage model={model} refresh={() => void refreshModel()} />
          </div>
        )}{" "}
        {path === "/admin" &&
          user &&
          (user.role === "admin" ? (
            <div className="container page-container">
              <Admin currentUser={user} open={setSelected} />
            </div>
          ) : (
            <div className="container page-container">
              <Alert>Administrator access is required to view this page.</Alert>
              <SiteLink
                to="/dashboard"
                navigate={navigate}
                className="button secondary"
              >
                Return to dashboard
              </SiteLink>
            </div>
          ))}{" "}
        {path === "/account" && user && (
          <AccountPage user={user} logout={() => void logout()} />
        )}{" "}
        {(path === "/guide" || path === "/privacy") && (
          <Guide privacy={path === "/privacy"} />
        )}{" "}
        {!validPaths.has(path) && (
          <div className="container page-container not-found">
            <h1>Page not found</h1>
            <p>This page is not part of your workspace.</p>
            <SiteLink to="/" navigate={navigate} className="button primary">
              Return home
            </SiteLink>
          </div>
        )}
      </main>
      <Footer navigate={navigate} />
      {selected && (
        <Result
          key={selected.id}
          inspection={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );

}
