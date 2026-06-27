/**
 * Shows what the LLM decided to add, what was already there, and what was skipped.
 * Source labels come from keyword_extractor: "Verified in your docs",
 * "Backed by your projects", "Inferred from your background".
 */

const SOURCE_REASON = {
  "Verified in your docs":         "Required by JD — found in your resume docs",
  "Backed by your projects":       "Required by JD — found in your project work",
  "Inferred from your background": "Required by JD — inferred from your background",
};

export default function ChangeLog({ changeLog, alreadyPresent, rejectedKeywords }) {
  const added    = changeLog?.added          || [];
  const alreadyAlso = changeLog?.already_present || [];
  const rejected = rejectedKeywords          || [];

  const allAlready = [
    ...new Set([...(alreadyPresent || []), ...alreadyAlso.map(i => i.skill || i)])
  ];

  // Group added by category
  const byCategory = {};
  for (const item of added) {
    const cat = item.category || "Other Technical Skills";
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(item);
  }

  return (
    <div className="space-y-5">

      {/* Added */}
      {added.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wide text-green-700 mb-2 flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
            Added to resume ({added.length} skills)
          </h4>
          <div className="space-y-3">
            {Object.entries(byCategory).map(([cat, items]) => (
              <div key={cat}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">{cat}</p>
                <div className="space-y-1">
                  {items.map((item) => (
                    <div key={item.skill} className="flex items-baseline gap-2 text-xs">
                      <span className="font-medium text-gray-800 shrink-0">{item.skill}</span>
                      <span className="text-gray-400">—</span>
                      <span className="text-gray-500">{SOURCE_REASON[item.source] || item.source}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Already present */}
      {allAlready.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wide text-blue-600 mb-2 flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400" />
            Already in your resume ({allAlready.length} skills)
          </h4>
          <div className="flex flex-wrap gap-1">
            {allAlready.map((sk) => (
              <span key={sk} className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded-full border border-blue-200">
                {sk}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-1">JD keywords already listed — not re-added.</p>
        </div>
      )}

      {/* Skipped */}
      {rejected.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2 flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-gray-300" />
            Not added ({rejected.length} skills)
          </h4>
          <div className="space-y-1">
            {rejected.map((item) => (
              <div key={item.skill} className="flex items-center gap-3 text-xs">
                <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full border border-gray-200 shrink-0">
                  {item.skill}
                </span>
                <span className="text-gray-400">{item.reason}</span>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-orange-600 mt-2 bg-orange-50 px-3 py-1.5 rounded-lg">
            Certifications, clearances, and soft skills are not added — they must be genuinely held, not claimed on a resume.
          </p>
        </div>
      )}

      {added.length === 0 && allAlready.length === 0 && rejected.length === 0 && (
        <p className="text-sm text-gray-400">No keyword data available.</p>
      )}
    </div>
  );
}
