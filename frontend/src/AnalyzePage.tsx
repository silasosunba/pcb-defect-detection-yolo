import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  FileImage,
  Image as ImageIcon,
  Link as LinkIcon,
  ScanLine,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import { label, type Inspection, type ModelStatus, type User } from "./api";
import { Alert, Spinner } from "./WorkspacePanels";
import { SiteLink, type Navigate } from "./SitePages";

const LIMIT = 20 * 1024 * 1024;
export function AnalyzePage({
  user,
  model,
  file,
  setFile,
  run,
  last,
  open,
  navigate,
}: {
  user: User | null;
  model: ModelStatus | null;
  file: File | null;
  setFile: (f: File | null) => void;
  run: (f: File, confidence: number) => Promise<void>;
  last: Inspection | null;
  open: (i: Inspection) => void;
  navigate: Navigate;
}) {

  const [mode, setMode] = useState<"upload" | "url">("upload");
  const [url, setUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [confidence, setConfidence] = useState(25);
  const input = useRef<HTMLInputElement>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {

    if (!file) {

      setPreview("");

      return;
    
}

    const value = URL.createObjectURL(file);
    setPreview(value);

    return () => URL.revokeObjectURL(value);
  
}, [file]);

  function choose(selected?: File) {

    setError("");

    if (!selected) {

      return;
    
}

    if (selected.size > LIMIT) {

      setError("Choose an image that is 20 MB or smaller.");

      return;
    
}

    if (
      !["image/png", "image/jpeg", "image/webp", "image/tiff"].includes(
        selected.type,
      ) &&
      !/\.(png|jpe?g|webp|tiff?)$/i.test(selected.name)
    ) {

      setError("Choose a JPG, PNG, TIFF or WebP image.");

      return;
    
}

    setFile(selected);
  
}

  async function loadUrl() {

    setError("");
    let parsed: URL;

    try {

      parsed = new URL(url);

      if (
        !["https:", "http:"].includes(parsed.protocol) ||
        parsed.username ||
        parsed.password
      ) {

        throw new Error();
      
}
    
} catch {

      setError("Enter a valid HTTP or HTTPS image URL without credentials.");

      return;
    
}

    controller.current?.abort();
    controller.current = new AbortController();
    const timeout = setTimeout(() => controller.current?.abort(), 15000);
    setFetching(true);

    try {

      const response = await fetch(parsed.href, {
        credentials: "omit",
        referrerPolicy: "no-referrer",
        signal: controller.current.signal,
      });

      if (!response.ok) {

        throw new Error("The image URL could not be loaded.");
      
}

      if (Number(response.headers.get("content-length")) > LIMIT) {

        throw new Error("The image exceeds 20 MB.");
      
}

      if (!response.body) {

        throw new Error("This URL returned no image.");
      
}

      const reader = response.body.getReader();
      let size = 0;
      const parts: ArrayBuffer[] = [];

      while (true) {

        const { value, done } = await reader.read();

        if (done) {

          break;
        
}

        size += value.byteLength;

        if (size > LIMIT) {

          await reader.cancel();

          throw new Error("The image exceeds 20 MB.");
        
}

        parts.push(value.slice().buffer as ArrayBuffer);
      
}

      const type = (response.headers.get("content-type") || "").split(";")[0];
      const suffix =
        type === "image/jpeg"
          ? "jpg"
          : type === "image/tiff"
            ? "tiff"
            : type === "image/webp"
              ? "webp"
              : "png";
      const name = parsed.pathname.split("/").pop() || `linked-board.${suffix}`;
      choose(new File(parts, name, { type }));
    
} catch (e) {

      setError(
        e instanceof TypeError
          ? "This host does not permit browser access to the image. Download it and use Upload Image."
          : e instanceof Error && e.name === "AbortError"
            ? "The image request timed out or was cancelled."
            : e instanceof Error
              ? e.message
              : "Could not load this image.",
      );
    
} finally {

      clearTimeout(timeout);
      setFetching(false);
    
}
  
}

  async function submit() {

    if (!file) {

      return;
    
}

    if (!user) {

      navigate("/auth/login?next=/analyze");

      return;
    
}

    setError("");
    setBusy(true);

    try {

      await run(file, confidence / 100);
    
} catch (e) {

      setError(
        e instanceof Error ? e.message : "Analysis failed. Please try again.",
      );
    
} finally {

      setBusy(false);
    
}
  
}

  const tiff =
    file && (/\.tiff?$/i.test(file.name) || file.type === "image/tiff");

  return (
    <div className="container page-container analysis-page">
      <div className="page-heading">
        <h1 className="cyan-text">PCB Image Analysis</h1>
        <p>
          Find surface defects with labeled bounding boxes and confidence
          scores.
        </p>
      </div>
      <section className="panel analysis-panel">
        <div className="input-tabs" role="tablist" aria-label="Image source">
          <button
            role="tab"
            aria-selected={mode === "upload"}
            className={mode === "upload" ? "selected" : ""}
            onClick={() => setMode("upload")}
          >
            <Upload size={17} />
            Upload Image
          </button>
          <button
            role="tab"
            aria-selected={mode === "url"}
            className={mode === "url" ? "selected" : ""}
            onClick={() => setMode("url")}
          >
            <LinkIcon size={17} />
            Image URL
          </button>
        </div>
        {mode === "url" && (
          <div className="url-section">
            <label htmlFor="image-url">Direct image URL</label>
            <div>
              <input
                id="image-url"
                type="url"
                placeholder="https://example.com/board.png"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={busy || fetching}
              />
              <button
                className="button primary"
                onClick={loadUrl}
                disabled={!url || fetching || busy}
              >
                {fetching ? <Spinner /> : "Load image"}
              </button>
            </div>
            <small>
              The image host must allow browser access. You can also download
              the image and upload it.
            </small>
          </div>
        )}
        <input
          hidden
          ref={input}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/tiff,.tif,.tiff"
          onChange={(e) => choose(e.target.files?.[0])}
          disabled={busy}
        />
        {file ? (
          <div className="image-preview">
            <div className="preview-toolbar">
              <span>
                <FileImage size={17} />
                {file.name}
              </span>
              <button
                className="icon-button"
                onClick={() => {

                  setFile(null);

                  if (input.current) {

                    input.current.value = "";
                  
}
                
}}
                aria-label="Remove image"
                disabled={busy}
              >
                <X size={18} />
              </button>
            </div>
            {tiff ? (
              <div className="tiff-preview">
                <FileImage size={60} />
                <p>TIFF image selected</p>
                <small>
                  The annotated image will be available after analysis.
                </small>
              </div>
            ) : (
              <img src={preview} alt="Selected circuit board to inspect" />
            )}
            <div className="preview-caption">
              <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              <button
                className="text-button"
                onClick={() => input.current?.click()}
                disabled={busy}
              >
                Choose another image
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`analysis-dropzone ${dragging ? "dragging" : ""}`}
            role="button"
            tabIndex={0}
            aria-label="Choose PCB image"
            onClick={() => input.current?.click()}
            onKeyDown={(e) => {

              if (e.key === "Enter" || e.key === " ") {

                e.preventDefault();
                input.current?.click();
              
}
            
}}
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
            <ImageIcon size={62} strokeWidth={1.8} />
            <h2>Upload PCB Image</h2>
            <p>Click to browse or drag and drop</p>
            <small>JPG, PNG, TIFF or WebP · up to 20 MB · 20 megapixels</small>
          </div>
        )}
        {error && <Alert>{error}</Alert>}
        {file && (
          <div className="analysis-controls">
            <div className="confidence-setting">
              <div>
                <label htmlFor="confidence">
                  <SlidersHorizontal size={17} /> Confidence threshold
                </label>
                <strong>{confidence}%</strong>
              </div>
              <input
                id="confidence"
                type="range"
                min={5}
                max={95}
                step={5}
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
                disabled={busy}
              />
              <div className="range-labels">
                <span>More sensitive</span>
                <span>More selective</span>
              </div>
            </div>
            <button
              className="button primary run-analysis"
              onClick={submit}
              disabled={busy || fetching || Boolean(user && !model?.available)}
            >
              {busy ? (
                <>
                  <Spinner /> Analyzing…
                </>
              ) : (
                <>
                  <ScanLine size={18} />
                  {user ? "Analyze PCB" : "Sign in to analyze"}
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </div>
        )}
        {user && !model?.available && (
          <div className="model-notice">
            <span className="status-dot" />
            <div>
              <strong>Awaiting trained model</strong>
              <p>
                Your workspace is ready. Install your Kaggle-trained weights to
                enable analysis.
              </p>
            </div>
            <SiteLink to="/model" navigate={navigate}>
              Model setup <ArrowRight size={15} />
            </SiteLink>
          </div>
        )}
        <div className="privacy-caption">
          <ShieldCheck size={14} />
          Saved images and results are accessible to you and workspace
          administrators.
        </div>
      </section>
      {last && (
        <section className="panel latest-result">
          <div className="panel-heading">
            <div>
              <ScanLine size={20} />
              <h2>Latest Analysis</h2>
            </div>
            <span
              className={`badge ${last.detections.length ? "amber" : "green"}`}
            >
              {last.detections.length} detections
            </span>
          </div>
          <div className="latest-result-content">
            <button onClick={() => open(last)} className="result-thumbnail">
              <img
                src={last.image_url}
                alt="Latest circuit board analysis with predicted bounding boxes"
              />
            </button>
            <div>
              <h2>{last.filename}</h2>
              <p>
                {last.detections.length
                  ? `${last.detections.length} predicted regions · ${[...new Set(last.detections.map((d) => label(d.label)))].join(", ")}`
                  : "No defects detected at the selected confidence threshold."}
              </p>
              <p className="muted">
                {last.duration_ms} ms inference ·{" "}
                {Math.round(last.confidence * 100)}% confidence threshold
              </p>
              <div className="result-actions">
                <button className="button primary" onClick={() => open(last)}>
                  Review detections <ArrowRight size={16} />
                </button>
                <a
                  className="button secondary"
                  href={last.image_url}
                  download={`${last.id}.png`}
                >
                  <ArrowDownToLine size={16} /> Image
                </a>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );

}
