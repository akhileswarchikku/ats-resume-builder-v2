import { useRef, useState } from "react";
import { uploadDocs } from "../api";

export default function UploadDocs({ onResumeReady, highlight }) {
  const projectsRef = useRef(null);
  const [projectsFile, setProjectsFile] = useState(null);
  const [status, setStatus] = useState(null); // null | "uploading" | "done" | "error"

  const handleChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setProjectsFile(file);
    setStatus("uploading");
    try {
      await uploadDocs(null, file);
      setStatus("done");
    } catch {
      setStatus("error");
    }
    e.target.value = "";
  };

  const isUploading = status === "uploading";
  const isDone      = status === "done";
  const isError     = status === "error";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500">Your Documents</h3>
        <p className="text-xs text-gray-400">Resume is pre-loaded — update projects anytime</p>
      </div>

      <div className="grid grid-cols-2 gap-4">

        {/* ── Resume — locked / pre-loaded ──────────────────────────────── */}
        <div className="flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-green-300 bg-green-50 select-none">
          <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-xl text-green-700">
            ✓
          </div>
          <p className="text-sm font-semibold text-green-800">Resume</p>
          <p className="text-xs text-green-700 text-center">Akhileswar's resume — pre-loaded</p>
          <span className="text-[11px] px-2 py-0.5 bg-green-200 text-green-800 rounded-full font-medium">
            locked
          </span>
        </div>

        {/* ── Projects / Portfolio — uploadable ─────────────────────────── */}
        <div
          onClick={() => projectsRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed cursor-pointer transition select-none
            ${isDone  ? "border-green-400 bg-green-50"  : ""}
            ${isError ? "border-red-400   bg-red-50"    : ""}
            ${!isDone && !isError ? "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50" : ""}
          `}
        >
          <input
            ref={projectsRef}
            type="file"
            accept=".docx,.doc,.pdf"
            className="hidden"
            onChange={handleChange}
          />

          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl
            ${isDone  ? "bg-green-100" : ""}
            ${isError ? "bg-red-100"   : ""}
            ${!isDone && !isError ? "bg-white border border-gray-200" : ""}
          `}>
            {isUploading
              ? <span className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" />
              : isDone ? "✓" : isError ? "✕" : "↑"}
          </div>

          <p className={`text-sm font-semibold
            ${isDone  ? "text-green-700" : isError ? "text-red-700" : "text-gray-700"}
          `}>
            Projects / Portfolio
          </p>

          <p className={`text-xs text-center
            ${isDone  ? "text-green-600" : isError ? "text-red-500" : "text-gray-400"}
          `}>
            {isDone ? projectsFile?.name : isError ? "upload failed" : ".docx or .pdf — click to upload"}
          </p>

          {isDone  && <span className="text-[11px] text-green-600 underline underline-offset-2">click to replace</span>}
          {isError && <span className="text-[11px] text-red-500">click to retry</span>}
        </div>
      </div>
    </div>
  );
}
