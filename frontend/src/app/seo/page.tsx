"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { listAudits, auditListing, getTaskStatus } from "../../lib/api";
import type { SEOAudit } from "../../lib/types";
import { useTranslation } from "../../lib/i18n/context";
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

function SEOPage() {
  const searchParams = useSearchParams();
  const { t } = useTranslation();
  const [audits, setAudits] = useState<SEOAudit[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    const urlParam = searchParams.get("url");
    if (urlParam) {
      setUrlInput(urlParam);
    }
  }, [searchParams]);

  useEffect(() => {
    listAudits()
      .then(setAudits)
      .catch((e) => setError(e.message));
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
          setError("[AUDIT] " + (status.error || "Unknown"));
        }
      } catch (e) {
        setTaskId(null);
        setError("[AUDIT] " + (e as Error).message);
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
      setError(e instanceof Error ? e.message : String(e));
    }
    setUrlInput("");
  };

  function renderError() {
    if (!error) return null;
    const isAudit = error.startsWith("[AUDIT] ");
    const message = isAudit ? error.slice(8) : error;
    const prefix = isAudit ? t("seo.list.auditFailed") : t("seo.list.startFailed");
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
        {prefix + message}
        <button onClick={() => setError(null)} className="ml-3 underline">{t("common.dismiss")}</button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t("seo.list.title")}</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAudit()}
          placeholder={t("seo.list.urlPlaceholder")}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleAudit}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? t("seo.list.auditing") : t("seo.list.auditButton")}
        </button>
      </div>

      {renderError()}

      {audits.length === 0 && !taskId && !error && (
        <p className="text-gray-500 text-center py-12">
          {t("seo.list.empty")}
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
                <span className="text-lg font-semibold">
                  {audit.listing?.title || t("seo.list.auditReport")}
                </span>
                <span className="text-sm text-gray-500 ml-3">
                  {new Date(audit.created_at).toLocaleString()}
                </span>
              </div>
              <ScoreBadge score={audit.overall_score} />
            </div>
            <div className="flex gap-6 mt-3">
              <ScoreBar label={t("seo.list.scoreTitle")} score={audit.title_score} />
              <ScoreBar label={t("seo.list.scoreTags")} score={audit.tag_score} />
              <ScoreBar label={t("seo.list.scoreDescription")} score={audit.description_score} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function SEOPageWrapper() {
  return (
    <Suspense>
      <SEOPage />
    </Suspense>
  );
}
