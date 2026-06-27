import { useState } from "react";

export default function LatexViewer({ latex }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(latex);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!latex) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-500">LaTeX Source</h3>
        <button
          onClick={copy}
          className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="bg-gray-900 text-green-400 text-xs p-4 rounded overflow-auto max-h-96 font-mono whitespace-pre-wrap">
        {latex}
      </pre>
    </div>
  );
}
