import { useRef, useState } from "react";
import { uploadDocs } from "../api";

function UploadCard({ label, hint, accept, file, status, inputRef, onChange }) {
  const isUploading = status === "uploading";
  const isDone      = status === "done";
  const isError     = status === "error";

  return (
    <div
      onClick={() => inputRef.current?.click()}
      className={`relative flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed cursor-pointer transition select-none
        ${isDone  ? "border-green-400 bg-green-50"  : ""}
        ${isError ? "border-red-400   bg-red-50"    : ""}
        ${!isDone && !isError ? "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={onChange}
      />

      {/* Icon */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl
        ${isDone  ? "bg-green-100" : ""}
        ${isError ? "bg-red-100"  : ""}
        ${!isDone && !isError ? "bg-white border border-gray-200" : ""}
      `}>
        {isUploading ? (
          <span className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" />
        ) : isDone ? "✓" : isError ? "✕" : "↑"}
      </div>

      {/* Label */}
      <p className={`text-sm font-semibold ${isDone ? "text-green-700" : isError ? "text-red-700" : "text-gray-700"}`}>
        {label}
      </p>

      {/* File name or hint */}
      <p className={`text-xs text-center ${isDone ? "text-green-600" : isError ? "text-red-500" : "text-gray-400"}`}>
        {file ? file.name : hint}
      </p>

      {/* Replace link when done */}
      {isDone && (
        <span className="text-[11px] text-green-600 underline underline-offset-2">
          click to replace
        </span>
      )}
      {isError && (
        <span className="text-[11px] text-red-500">upload failed — click to retry</span>
      )}
    </div>
  );
}

export default function UploadDocs({ onUploaded }) {
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
      onUploaded?.();
    } catch {
      setStatus(s => ({ ...s, [type]: "error" }));
    }
  };

  const handleChange = (type, e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (type === "resume")   setResumeFile(file);
    else                     setProjectsFile(file);
    upload(type, file);
    e.target.value = "";   // allow re-selecting same file
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500">Your Documents</h3>
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
        />
        <UploadCard
          label="Projects / Portfolio"
          hint=".docx or .pdf — click to upload"
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
