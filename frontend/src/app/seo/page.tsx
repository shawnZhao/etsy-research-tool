"use client";

import { useState, useEffect } from "react";
import { listAudits, auditListing, getTaskStatus } from "../../lib/api";
import type { SEOAudit } from "../../lib/types";
import Link from "next/link";

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? "bg-green-100 text-green-700"
      : score >= 40
        ? "bg-yellow-100 text-yellow-700"
        : "bg-red-100 text-red-700";
  return (
    <span className={`px-3 py-1 rounded-full font-bold text-lg ${color}`}>
      {score}
    </span>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const barColor =
    score >= 70
      ? "bg-green-500"
      : score >= 40
        ? "bg-yellow-500"
        : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-16">{label}</span>
      <div className="w-24 bg-gray-200 rounded-full h-2">
        <div
          className={`${barColor} h-2 rounded-full`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
      <span className="text-xs text-gray-600">{score}%</span>
    </div>
  );
}

export default function SEOPage() {
  const [audits, setAudits] = useState<SEOAudit[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listAudits()
      .then(setAudits)
      .catch((e) => setError("Failed to load audits: " + e.message));
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId);
        if (status.status === "SUCCESS") {
          setTaskId(null);
          const updated = await listAudits();
          setAudits(updated);
        } else if (status.status === "FAILURE") {
          setTaskId(null);
          setError("Audit failed: " + status.error);
        }
      } catch (e) {
        setTaskId(null);
        setError("Failed to check task status: " + (e as Error).message);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  const handleAudit = async () => {
    if (!urlInput.trim() || taskId) return;
    setError(null);
    try {
      const { task_id } = await auditListing(urlInput.trim());
      setTaskId(task_id);
    } catch (e) {
      setError("Failed to start audit: " + (e as Error).message);
    }
    setUrlInput("");
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">SEO Audit</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAudit()}
          placeholder="Paste a listing URL to analyze its SEO..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleAudit}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? "Auditing..." : "Audit"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {error}
          <button onClick={() => setError(null)} className="ml-3 underline">
            Dismiss
          </button>
        </div>
      )}

      {audits.length === 0 && !taskId && !error && (
        <p className="text-gray-500 text-center py-12">
          No SEO audits yet. Paste a listing URL to analyze its SEO.
        </p>
      )}

      <div className="grid gap-4">
        {audits.map((audit) => (
          <Link
            key={audit.id}
            href={`/seo/${audit.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-lg font-semibold">Audit Report</span>
                <span className="text-sm text-gray-500 ml-3">
                  {new Date(audit.created_at).toLocaleString()}
                </span>
              </div>
              <ScoreBadge score={audit.overall_score} />
            </div>
            <div className="flex gap-6 mt-3">
              <ScoreBar label="Title" score={audit.title_score} />
              <ScoreBar label="Tags" score={audit.tag_score} />
              <ScoreBar label="Description" score={audit.description_score} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
