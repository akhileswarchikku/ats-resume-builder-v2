import { useRef, useState } from "react";
import { uploadDocs } from "../api";

function UploadCard({ label, hint, accept, file, status, inputRef, onChange, required, highlight }) {
  const isUploading = status === "uploading";
  const isDone      = status === "done";
  const isError     = status === "error";
  const needsAction = highlight && !isDone;

  return (
    <div
      onClick={() => inputRef.current?.click()}
      className={`relative flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed cursor-pointer transition select-none
        ${isDone      ? "border-green-400 bg-green-50" : ""}
        ${isError     ? "border-red-400   bg-red-50"   : ""}
        ${needsAction ? "border-orange-400 bg-orange-50 animate-pulse" : ""}
        ${!isDone && !isError && !needsAction ? "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50" : ""}
      `}
    >
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={onChange} />

      {/* Icon */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl
        ${isDone      ? "bg-green-100"  : ""}
        ${isError     ? "bg-red-100"    : ""}
        ${needsAction ? "bg-orange-100" : ""}
        ${!isDone && !isError && !needsAction ? "bg-white border border-gray-200" : ""}
      `}>
        {isUploading
          ? <span className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" />
          : isDone ? "✓" : isError ? "✕" : needsAction ? "!" : "↑"}
      </div>

      {/* Label */}
      <p className={`text-sm font-semibold
        ${isDone      ? "text-green-700"  : ""}
        ${isError     ? "text-red-700"    : ""}
        ${needsAction ? "text-orange-700" : ""}
        ${!isDone && !isError && !needsAction ? "text-gray-700" : ""}
      `}>
        {label}
        {required && !isDone && <span className="text-red-500 ml-0.5">*</span>}
      </p>

      {/* Hint / filename */}
      <p className={`text-xs text-center
        ${isDone      ? "text-green-600"  : ""}
        ${isError     ? "text-red-500"    : ""}
        ${needsAction ? "text-orange-600" : ""}
        ${!isDone && !isError && !needsAction ? "text-gray-400" : ""}
      `}>
        {isDone ? file?.name : needsAction ? "Required — click to upload" : file ? file.name : hint}
      </p>

      {isDone      && <span className="text-[11px] text-green-600 underline underline-offset-2">click to replace</span>}
      {isError     && <span className="text-[11px] text-red-500">upload failed — click to retry</span>}
    </div>
  );
}

export default function UploadDocs({ onResumeReady, highlight }) {
  const resumeRef   = useRef(null);
  const projectsRef = useRef(null);

  const [resumeFile,   setResumeFile]   = useState(null);
  const [projectsFile, setProjectsFile] = useState(null);
  const [status, setStatus] = useState({ resume: null, projects: null });

  const upload = async (type, file) => {
    setStatus(s => ({ ...s, [type]: "uploading" }));
    try {
      await uploadDocs(
        type === "resume"   ? file : null,
        type === "projects" ? file : null,
      );
      setStatus(s => ({ ...s, [type]: "done" }));
      if (type === "resume") onResumeReady?.();
    } catch {
      setStatus(s => ({ ...s, [type]: "error" }));
    }
  };

  const handleChange = (type, e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (type === "resume")  setResumeFile(file);
    else                    setProjectsFile(file);
    upload(type, file);
    e.target.value = "";
  };

  return (
    <div className={`bg-white rounded-xl border p-5 transition ${
      highlight && status.resume !== "done"
        ? "border-orange-300 shadow-orange-100 shadow-md"
        : "border-gray-200"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500">Your Documents</h3>
          {highlight && status.resume !== "done" && (
            <p className="text-xs text-orange-600 mt-0.5 font-medium">
              Upload your Resume first, then generate.
            </p>
          )}
        </div>
        <p className="text-xs text-gray-400">Upload once — stays loaded until server restarts</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <UploadCard
          label="Resume"
          hint=".docx or .pdf — click to upload"
          accept=".docx,.doc,.pdf"
          file={resumeFile}
          status={status.resume}
          inputRef={resumeRef}
          onChange={(e) => handleChange("resume", e)}
          required
          highlight={highlight}
        />
        <UploadCard
          label="Projects / Portfolio"
          hint=".docx or .pdf — click to upload (optional)"
          accept=".docx,.doc,.pdf"
          file={projectsFile}
          status={status.projects}
          inputRef={projectsRef}
          onChange={(e) => handleChange("projects", e)}
        />
      </div>
    </div>
  );
}
