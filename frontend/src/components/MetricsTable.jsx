export default function MetricsTable({ label, metrics }) {
  if (!metrics) return null;

  const chance = metrics.interview_chance;   // "Yes" | "No" | undefined
  const isYes  = chance === "Yes";

  const rows = [
    { name: "Overall ATS Match",   value: metrics.overall,                       pct: true  },
    { name: "Skills Match",        value: metrics.skills_match,                  pct: true  },
    { name: "Experience Match",    value: metrics.experience_match,              pct: true  },
    { name: "Education Match",     value: metrics.education_match,               pct: true  },
    { name: "Humanization Score",  value: metrics.humanization,                  pct: true  },
    { name: "Skills in Resume",    value: metrics.resume_skills?.length ?? 0,    pct: false },
    { name: "JD Skills Required",  value: metrics.jd_skills?.length ?? 0,        pct: false },
    { name: "Matched",             value: metrics.keywords_matched?.length ?? 0, pct: false },
    { name: "Missing",             value: metrics.keywords_missing?.length ?? 0, pct: false },
  ];

  const color = (r) => {
    if (!r.pct) {
      if (r.name === "Matched") return "text-green-600 font-semibold";
      if (r.name === "Missing") return "text-red-500 font-semibold";
      return "text-gray-700 font-medium";
    }
    if (r.value >= 75) return "text-green-600 font-semibold";
    if (r.value >= 50) return "text-yellow-600 font-semibold";
    return "text-red-600 font-semibold";
  };

  return (
    <div className="flex-1 min-w-0">
      <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500 mb-2">{label}</h3>

      {/* Interview Verdict Card */}
      {chance && (
        <div className={`mb-3 rounded-lg border overflow-hidden ${
          isYes ? "border-green-200" : "border-red-200"
        }`}>
          {/* Header */}
          <div className={`flex items-center gap-2 px-4 py-2 ${
            isYes ? "bg-green-600" : "bg-red-600"
          }`}>
            <span className="text-xs font-bold uppercase tracking-wider text-white opacity-80">
              Interview Chance
            </span>
            <span className="text-sm font-bold text-white">{chance}</span>
          </div>

          {/* Body */}
          <div className={`px-4 py-3 space-y-2 ${isYes ? "bg-green-50" : "bg-red-50"}`}>
            {/* Strength */}
            {metrics.interview_strength && (
              <div className="flex gap-2">
                <span className="text-green-600 font-bold text-xs mt-0.5 shrink-0">+</span>
                <p className="text-xs text-gray-700 leading-snug">{metrics.interview_strength}</p>
              </div>
            )}
            {/* Concern */}
            {metrics.interview_concern && (
              <div className="flex gap-2">
                <span className="text-orange-500 font-bold text-xs mt-0.5 shrink-0">!</span>
                <p className="text-xs text-gray-700 leading-snug">{metrics.interview_concern}</p>
              </div>
            )}
            {/* Summary */}
            {metrics.interview_summary && (
              <p className={`text-xs leading-snug pt-1 border-t ${
                isYes ? "border-green-200 text-green-900" : "border-red-200 text-red-900"
              }`}>
                {metrics.interview_summary}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Metrics Table */}
      <table className="w-full text-sm border border-gray-200 rounded overflow-hidden">
        <tbody>
          {rows.map((r) => (
            <tr key={r.name} className="border-b border-gray-100 last:border-0">
              <td className="px-3 py-2 text-gray-600">{r.name}</td>
              <td className={`px-3 py-2 text-right ${color(r)}`}>
                {r.value}{r.pct ? "%" : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Missing Skills */}
      {metrics.keywords_missing?.length > 0 && (
        <div className="mt-3">
          <p className="text-[11px] font-bold uppercase tracking-wide text-red-500 mb-1.5">
            Missing Skills ({metrics.keywords_missing.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {metrics.keywords_missing.map((sk) => (
              <span key={sk} className="px-2 py-0.5 text-xs rounded-full bg-red-50 text-red-600 border border-red-200">
                {sk}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
