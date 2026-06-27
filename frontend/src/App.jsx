import { useState } from "react";
import { generateResume, saveApplication } from "./api";
import MetricsTable from "./components/MetricsTable";
import ChangeLog from "./components/ChangeLog";

export default function App() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedPath, setSavedPath] = useState("");
  const [sessionStats, setSessionStats] = useState({ session_cost_usd: 0, applications: 0, llm_calls: 0 });

  const handleGenerate = async () => {
    if (!jd.trim()) { setError("Paste a job description first."); return; }
    setError("");
    setLoading(true);
    setResult(null);
    setSavedPath("");
    try {
      const data = await generateResume(jd);
      setResult(data);
      if (data.session_stats) setSessionStats(data.session_stats);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.pdf_b64) return;
    const bytes = atob(result.pdf_b64);
    const buf = new Uint8Array(bytes.length).map((_, i) => bytes.charCodeAt(i));
    const blob = new Blob([buf], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Resume_${result.company}_${result.job_title}.pdf`.replace(/\s+/g, "_");
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSave = async () => {
    if (!result) return;
    setSaving(true);
    try {
      const res = await saveApplication(result.company, result.job_title, jd, result.pdf_b64);
      setSavedPath(res.saved_to);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
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

        {/* JD Input */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Paste Job Description</label>
            <p className="text-xs text-gray-400 mb-3">Your resume from <span className="font-mono">docs/resume.docx</span> is loaded automatically — just paste the JD and generate.</p>
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

        {/* Results */}
        {result && (
          <>
            {/* Company / Role + action buttons */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-6 flex-wrap">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Company</p>
                <p className="font-semibold text-gray-900">{result.company}</p>
              </div>
              <div className="w-px h-8 bg-gray-200" />
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Role</p>
                <p className="font-semibold text-gray-900">{result.job_title}</p>
              </div>
              <div className="ml-auto flex gap-3">
                <button onClick={handleDownload}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition">
                  Download PDF
                </button>
                <button onClick={handleSave} disabled={saving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white rounded-lg text-sm font-medium transition">
                  {saving ? "Saving..." : "Save to My_Applications"}
                </button>
              </div>
              {result.generation_cost_usd !== undefined && (
                <p className="w-full text-xs text-gray-500 mt-1">
                  This generation cost: <span className="font-mono font-medium text-gray-700">${result.generation_cost_usd.toFixed(4)}</span>
                </p>
              )}
              {savedPath && (
                <p className="w-full text-xs text-green-700 bg-green-50 px-3 py-2 rounded-lg mt-1">
                  Saved: <span className="font-mono">{savedPath}</span>
                </p>
              )}
            </div>

            {/* Resume Changes Panel */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 mb-4">Resume Changes</h3>
              <ChangeLog changeLog={result.change_log} alreadyPresent={result.already_present} rejectedKeywords={result.rejected_keywords} />
            </div>

            {/* ATS Metrics: Before vs After */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 mb-4">ATS Score: Before vs After</h3>
              <div className="flex gap-8">
                <MetricsTable label="Before (Original Resume)" metrics={result.before_metrics} />
                <div className="w-px bg-gray-200" />
                <MetricsTable label="After (Keywords Added)" metrics={result.after_metrics} />
              </div>
            </div>

          </>
        )}
      </div>
    </div>
  );
}
