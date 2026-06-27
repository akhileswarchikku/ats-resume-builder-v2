import { useState } from "react";
import { generateResume } from "./api";
import MetricsTable  from "./components/MetricsTable";
import ChangeLog     from "./components/ChangeLog";
import UploadDocs    from "./components/UploadDocs";

// ── File System Access API save (Chrome / Edge) ───────────────────────────────
async function saveToFolder(dirHandle, folderName, jdText, pdfB64) {
  const sub = await dirHandle.getDirectoryHandle(folderName, { create: true });

  // JD.txt
  const jdFile = await sub.getFileHandle("JD.txt", { create: true });
  const jdW    = await jdFile.createWritable();
  await jdW.write(jdText);
  await jdW.close();

  // Resume.pdf
  const bytes  = atob(pdfB64);
  const buf    = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
  const pdfFile = await sub.getFileHandle(`Resume_${folderName}.pdf`, { create: true });
  const pdfW   = await pdfFile.createWritable();
  await pdfW.write(buf);
  await pdfW.close();

  return `${dirHandle.name}/${folderName}/`;
}

// ── Browser download fallback ─────────────────────────────────────────────────
function browserDownload(pdfB64, filename) {
  const bytes = atob(pdfB64);
  const buf   = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
  const blob  = new Blob([buf], { type: "application/pdf" });
  const url   = URL.createObjectURL(blob);
  const a     = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

const fsa = () => typeof window !== "undefined" && "showDirectoryPicker" in window;

export default function App() {
  const [jd,          setJd]          = useState("");
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");
  const [result,      setResult]      = useState(null);
  const [sessionStats, setSessionStats] = useState({ session_cost_usd: 0, applications: 0, llm_calls: 0 });

  // Save folder (File System Access API)
  const [saveDir,       setSaveDir]       = useState(null);
  const [saveStatus,    setSaveStatus]    = useState("");
  const [resumeReady,   setResumeReady]   = useState(false);
  const [highlightUpload, setHighlightUpload] = useState(false);

  const handleGenerate = async () => {
    if (!jd.trim()) { setError("Paste a job description first."); return; }
    setError(""); setLoading(true); setResult(null); setSaveStatus("");
    try {
      const data = await generateResume(jd);
      setResult(data);
      setHighlightUpload(false);
      if (data.session_stats) setSessionStats(data.session_stats);
    } catch (e) {
      // Detect "no resume uploaded" error and highlight the upload panel
      const msg = e.message || "";
      const isNoResume = msg.includes("resume.docx not found") || msg.includes("resume.pdf not found");
      if (isNoResume) {
        setHighlightUpload(true);
        setError("Upload your Resume first using the panel above, then generate.");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const pickFolder = async () => {
    try {
      const handle = await window.showDirectoryPicker({ mode: "readwrite" });
      setSaveDir(handle);
      setSaveStatus("");
    } catch { /* user cancelled */ }
  };

  const handleSave = async () => {
    if (!result) return;
    const safe = (s) => s.replace(/[^\w\-]/g, "_").slice(0, 40);
    const folderName = `${safe(result.company)}_${safe(result.job_title)}`;

    setSaveStatus("saving");
    try {
      if (saveDir) {
        // Save directly to the user's chosen folder via File System Access API
        const path = await saveToFolder(saveDir, folderName, jd, result.pdf_b64);
        setSaveStatus(path);
      } else if (fsa()) {
        // No folder picked yet — prompt now
        const handle = await window.showDirectoryPicker({ mode: "readwrite" });
        setSaveDir(handle);
        const path = await saveToFolder(handle, folderName, jd, result.pdf_b64);
        setSaveStatus(path);
      } else {
        // Fallback: browser download
        browserDownload(result.pdf_b64, `Resume_${folderName}.pdf`);
        setSaveStatus("Downloaded to your browser's download folder.");
      }
    } catch (e) {
      setSaveStatus("error");
      setError(e.message);
    }
  };

  const handleDownload = () => {
    if (!result?.pdf_b64) return;
    const safe = (s) => s.replace(/[^\w\-]/g, "_").slice(0, 40);
    browserDownload(result.pdf_b64, `Resume_${safe(result.company)}_${safe(result.job_title)}.pdf`);
  };

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">A</div>
        <h1 className="text-lg font-semibold text-gray-900">ATS Resume Builder</h1>
        <div className="ml-auto flex items-center gap-4">
          <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-lg px-4 py-1.5 text-xs">
            <span className="text-gray-400">Session cost</span>
            <span className="font-mono font-semibold text-gray-900">${sessionStats.session_cost_usd.toFixed(4)}</span>
            <span className="w-px h-4 bg-gray-200" />
            <span className="text-gray-400">Applications</span>
            <span className="font-mono font-semibold text-gray-900">{sessionStats.applications}</span>
            <span className="w-px h-4 bg-gray-200" />
            <span className="text-gray-400">LLM calls</span>
            <span className="font-mono font-semibold text-gray-900">{sessionStats.llm_calls}</span>
          </div>
          <span className="text-xs text-gray-400">Gemini 2.5 Flash</span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">

        {/* ── Upload Docs ─────────────────────────────────────────────────── */}
        <UploadDocs
          highlight={highlightUpload}
          onResumeReady={() => { setResumeReady(true); setHighlightUpload(false); setError(""); }}
        />

        {/* ── JD Input ────────────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Paste Job Description</label>
            <p className="text-xs text-gray-400 mb-3">
              Upload your Resume + Projects above, then paste the JD and generate.
            </p>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description here..."
              rows={12}
              className="w-full border border-gray-300 rounded-lg p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleGenerate}
              disabled={loading || !jd.trim()}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" /> Generating...</>
              ) : "Generate Tailored Resume"}
            </button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </div>

        {/* ── Results ─────────────────────────────────────────────────────── */}
        {result && (
          <>
            {/* Company / Role + action bar */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center gap-6 flex-wrap">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Company</p>
                  <p className="font-semibold text-gray-900">{result.company}</p>
                </div>
                <div className="w-px h-8 bg-gray-200" />
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Role</p>
                  <p className="font-semibold text-gray-900">{result.job_title}</p>
                </div>

                {/* Action buttons */}
                <div className="ml-auto flex items-center gap-3 flex-wrap">
                  {/* Download PDF — always available */}
                  <button onClick={handleDownload}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition">
                    Download PDF
                  </button>

                  {/* Save folder picker */}
                  {fsa() && (
                    <button onClick={pickFolder}
                      className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition flex items-center gap-1.5 border border-gray-300">
                      <span>📁</span>
                      <span>{saveDir ? saveDir.name : "Pick Save Folder"}</span>
                    </button>
                  )}

                  {/* Save to folder */}
                  <button onClick={handleSave} disabled={saveStatus === "saving"}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white rounded-lg text-sm font-medium transition">
                    {saveStatus === "saving" ? "Saving…" : saveDir ? "Save Here" : "Save"}
                  </button>
                </div>
              </div>

              {/* Status messages */}
              {result.generation_cost_usd !== undefined && (
                <p className="text-xs text-gray-500 mt-3">
                  Generation cost: <span className="font-mono font-medium text-gray-700">${result.generation_cost_usd.toFixed(4)}</span>
                </p>
              )}
              {saveStatus && saveStatus !== "saving" && saveStatus !== "error" && (
                <p className="text-xs text-green-700 bg-green-50 px-3 py-2 rounded-lg mt-2">
                  Saved to: <span className="font-mono">{saveStatus}</span>
                  {!fsa() && <span className="ml-2 text-gray-400">(Tip: use Chrome/Edge for direct folder saves)</span>}
                </p>
              )}
            </div>

            {/* Resume Changes */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 mb-4">Resume Changes</h3>
              <ChangeLog
                changeLog={result.change_log}
                alreadyPresent={result.already_present}
                rejectedKeywords={result.rejected_keywords}
              />
            </div>

            {/* ATS Metrics */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 mb-4">ATS Score: Before vs After</h3>
              <div className="flex gap-8">
                <MetricsTable label="Before (Original Resume)" metrics={result.before_metrics} />
                <div className="w-px bg-gray-200" />
                <MetricsTable label="After (Keywords Added)"  metrics={result.after_metrics} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
