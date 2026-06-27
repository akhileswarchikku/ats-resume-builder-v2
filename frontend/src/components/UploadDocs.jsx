import { useRef, useState } from "react";
import { uploadDocs } from "../api";

// Status → visual config
const RESUME_STATE = {
  null:       { border: "border-gray-300",  bg: "bg-gray-50  hover:border-blue-400 hover:bg-blue-50", icon: "↑",  iconBg: "bg-white border border-gray-200", textColor: "text-gray-700",  hint: ".docx or .pdf — click to upload" },
  uploading:  { border: "border-blue-300",  bg: "bg-blue-50",  icon: null, iconBg: "bg-blue-100",  textColor: "text-blue-700",   hint: "Uploading…" },
  verifying:  { border: "border-yellow-400",bg: "bg-yellow-50",icon: null, iconBg: "bg-yellow-100",textColor: "text-yellow-700", hint: "Agent verifying identity…" },
  granted:    { border: "border-green-400", bg: "bg-green-50", icon: "✓",  iconBg: "bg-green-100", textColor: "text-green-700",  hint: "" },
  denied:     { border: "border-red-400",   bg: "bg-red-50",   icon: "✕",  iconBg: "bg-red-100",   textColor: "text-red-700",    hint: "" },
  error:      { border: "border-red-400",   bg: "bg-red-50",   icon: "✕",  iconBg: "bg-red-100",   textColor: "text-red-700",    hint: "Upload failed — click to retry" },
};

function Spinner() {
  return <span className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin inline-block" />;
}

export default function UploadDocs({ onResumeReady }) {
  const resumeRef   = useRef(null);
  const projectsRef = useRef(null);

  const [resumeFile,   setResumeFile]   = useState(null);
  const [projectsFile, setProjectsFile] = useState(null);

  // Resume card state
  const [resumeStatus,  setResumeStatus]  = useState(null);  // null | uploading | verifying | granted | denied | error
  const [resumeMsg,     setResumeMsg]     = useState("");     // agent message
  const [verifyDetails, setVerifyDetails] = useState(null);  // full verification result

  // Projects card state
  const [projStatus, setProjStatus] = useState(null);

  // ── Resume upload ──────────────────────────────────────────────────────────
  const handleResumeChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResumeFile(file);
    setResumeMsg("");
    setVerifyDetails(null);
    e.target.value = "";

    setResumeStatus("uploading");
    let data;
    try {
      setResumeStatus("verifying");
      data = await uploadDocs(file, null);
    } catch (err) {
      // Parse the 403 detail from the API
      let detail = null;
      try {
        const body = JSON.parse(err.message);
        detail = body.detail ?? body;
      } catch { detail = { message: err.message }; }

      if (detail?.error === "identity_mismatch") {
        setResumeStatus("denied");
        setResumeMsg(detail.message || "Identity does not match the authorized user.");
        setVerifyDetails(detail);
      } else {
        setResumeStatus("error");
        setResumeMsg(detail?.message || err.message);
      }
      return;
    }

    setResumeStatus("granted");
    setResumeMsg(data?.verification?.message || "Identity verified — resume updated.");
    setVerifyDetails(data?.verification ?? null);
    onResumeReady?.();
  };

  // ── Projects upload ────────────────────────────────────────────────────────
  const handleProjectsChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setProjectsFile(file);
    setProjStatus("uploading");
    e.target.value = "";
    try {
      await uploadDocs(null, file);
      setProjStatus("done");
    } catch {
      setProjStatus("error");
    }
  };

  const rs = RESUME_STATE[resumeStatus] ?? RESUME_STATE[null];
  const isVerifying  = resumeStatus === "verifying";
  const isUploading  = resumeStatus === "uploading";
  const isGranted    = resumeStatus === "granted";
  const isDenied     = resumeStatus === "denied";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500">Your Documents</h3>
        <p className="text-xs text-gray-400">
          Resume upload is identity-verified by AI agent
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">

        {/* ── Resume card ─────────────────────────────────────────────────── */}
        <div
          onClick={() => resumeRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed cursor-pointer transition select-none ${rs.border} ${rs.bg}`}
        >
          <input ref={resumeRef} type="file" accept=".docx,.doc,.pdf" className="hidden" onChange={handleResumeChange} />

          {/* Icon */}
          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${rs.iconBg}`}>
            {isUploading || isVerifying ? <Spinner /> : <span className={rs.textColor}>{rs.icon ?? "↑"}</span>}
          </div>

          {/* Title */}
          <p className={`text-sm font-semibold ${rs.textColor}`}>Resume</p>

          {/* Status line */}
          <p className={`text-xs text-center ${rs.textColor}`}>
            {isVerifying  ? "Agent verifying identity…"
             : isGranted  ? resumeFile?.name
             : isDenied   ? "Access denied"
             : resumeFile ? resumeFile.name
             : rs.hint}
          </p>

          {/* Replace hint */}
          {(isGranted || isDenied) && (
            <span className="text-[11px] underline underline-offset-2 opacity-60">click to try again</span>
          )}
        </div>

        {/* ── Verification result panel ────────────────────────────────────── */}
        {resumeMsg && (
          <div className={`col-span-2 -mt-2 rounded-lg px-4 py-3 text-xs space-y-1
            ${isGranted ? "bg-green-50 border border-green-200 text-green-800"
                        : "bg-red-50   border border-red-200   text-red-800"}
          `}>
            <p className="font-semibold">{isGranted ? "✓ Access granted" : "✕ Access denied"}</p>
            <p>{resumeMsg}</p>
            {verifyDetails && (
              <div className="flex flex-wrap gap-3 mt-1 text-[11px] opacity-80">
                {verifyDetails.authorized_name && <span>Authorized: <strong>{verifyDetails.authorized_name}</strong></span>}
                {verifyDetails.uploaded_name   && <span>Uploaded: <strong>{verifyDetails.uploaded_name}</strong></span>}
                {verifyDetails.matched_fields?.length > 0 && (
                  <span>Matched: {verifyDetails.matched_fields.join(", ")}</span>
                )}
                {verifyDetails.mismatched_fields?.length > 0 && (
                  <span>Mismatch: {verifyDetails.mismatched_fields.join(", ")}</span>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Projects card ────────────────────────────────────────────────── */}
        <div
          onClick={() => projectsRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed cursor-pointer transition select-none
            ${projStatus === "done"  ? "border-green-400 bg-green-50"
            : projStatus === "error" ? "border-red-400   bg-red-50"
            : projStatus === "uploading" ? "border-blue-300 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"}
          `}
        >
          <input ref={projectsRef} type="file" accept=".docx,.doc,.pdf" className="hidden" onChange={handleProjectsChange} />

          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl
            ${projStatus === "done"      ? "bg-green-100 text-green-700"
            : projStatus === "error"    ? "bg-red-100   text-red-700"
            : projStatus === "uploading"? "bg-blue-100  text-blue-700"
            : "bg-white border border-gray-200 text-gray-500"}
          `}>
            {projStatus === "uploading" ? <Spinner /> : projStatus === "done" ? "✓" : projStatus === "error" ? "✕" : "↑"}
          </div>

          <p className={`text-sm font-semibold
            ${projStatus === "done"  ? "text-green-700"
            : projStatus === "error" ? "text-red-700"
            : "text-gray-700"}
          `}>Projects / Portfolio</p>

          <p className={`text-xs text-center
            ${projStatus === "done"  ? "text-green-600"
            : projStatus === "error" ? "text-red-500"
            : "text-gray-400"}
          `}>
            {projStatus === "done" ? projectsFile?.name : ".docx or .pdf — click to upload (optional)"}
          </p>

          {projStatus === "done"  && <span className="text-[11px] text-green-600 underline underline-offset-2">click to replace</span>}
          {projStatus === "error" && <span className="text-[11px] text-red-500">upload failed — click to retry</span>}
        </div>

      </div>
    </div>
  );
}
