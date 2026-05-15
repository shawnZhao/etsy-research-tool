"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getSEOAudit } from "../../../lib/api";
import type { SEOAudit } from "../../../lib/types";

function ScoreCircle({ label, score }: { label: string; score: number }) {
  const color =
    score >= 70
      ? "text-green-600"
      : score >= 40
        ? "text-yellow-600"
        : "text-red-600";
  const borderColor =
    score >= 70
      ? "border-green-300"
      : score >= 40
        ? "border-yellow-300"
        : "border-red-300";
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-20 h-20 rounded-full border-4 ${borderColor} flex items-center justify-center mb-2`}
      >
        <span className={`text-3xl font-bold ${color}`}>{score}</span>
      </div>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  );
}

export default function SEOAuditDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [audit, setAudit] = useState<SEOAudit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getSEOAudit(id)
      .then(setAudit)
      .catch((e) => setError("Failed to load audit: " + e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading)
    return <div className="text-center py-12 text-gray-500">Loading...</div>;

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 inline-block">
          {error}
        </div>
      </div>
    );
  }

  if (!audit)
    return (
      <div className="text-center py-12 text-gray-500">Audit not found.</div>
    );

  const severityColors: Record<string, string> = {
    high: "border-red-400 bg-red-50",
    medium: "border-yellow-400 bg-yellow-50",
    low: "border-blue-400 bg-blue-50",
  };

  const severityBadgeColors: Record<string, string> = {
    high: "bg-red-200 text-red-800",
    medium: "bg-yellow-200 text-yellow-800",
    low: "bg-blue-200 text-blue-800",
  };

  const typeLabels: Record<string, string> = {
    title: "Title",
    tags: "Tags",
    description: "Description",
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">SEO Audit Report</h1>
      <p className="text-gray-500 mb-8">
        Analyzed: {new Date(audit.created_at).toLocaleString()}
      </p>

      <div className="mb-8">
        <div className="text-5xl font-bold text-orange-600 mb-2">
          {audit.overall_score}
        </div>
        <span className="text-gray-500">Overall SEO Score</span>
      </div>

      <div className="flex gap-8 mb-8">
        <ScoreCircle label="Title" score={audit.title_score} />
        <ScoreCircle label="Tags" score={audit.tag_score} />
        <ScoreCircle label="Description" score={audit.description_score} />
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Improvement Suggestions</h2>
        {audit.suggestions.length === 0 ? (
          <p className="text-gray-500">
            No suggestions — your listing SEO looks great!
          </p>
        ) : (
          <div className="space-y-3">
            {audit.suggestions.map((s, i) => (
              <div
                key={i}
                className={`border-l-4 p-4 rounded-r-lg ${severityColors[s.severity]}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded ${severityBadgeColors[s.severity]}`}
                  >
                    {s.severity.toUpperCase()}
                  </span>
                  <span className="text-sm text-gray-500">
                    {typeLabels[s.type]}
                  </span>
                </div>
                <p className="font-medium">{s.message}</p>
                <p className="text-sm text-gray-600 mt-1">{s.detail}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
