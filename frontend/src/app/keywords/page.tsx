"use client";

import { useState, useEffect } from "react";
import { listKeywords, searchKeyword, getTaskStatus } from "../../lib/api";
import type { Keyword } from "../../lib/types";
import { useTranslation } from "../../lib/i18n/context";
import Link from "next/link";

function getTrendLabel(trend: string) {
  if (trend === "up") return "keywords.list.rising";
  if (trend === "down") return "keywords.list.falling";
  return "keywords.list.stable";
}

function getTrendStyle(trend: string) {
  if (trend === "up") return "bg-green-100 text-green-700";
  if (trend === "down") return "bg-red-100 text-red-700";
  return "bg-gray-100 text-gray-600";
}

export default function KeywordsPage() {
  const { t } = useTranslation();
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listKeywords()
      .then(setKeywords)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId);
        if (status.status === "SUCCESS") {
          setTaskId(null);
          const updated = await listKeywords();
          setKeywords(updated);
        } else if (status.status === "FAILURE") {
          setTaskId(null);
          setError("[TASK] " + (status.error || "Unknown"));
        }
      } catch (e) {
        setTaskId(null);
        setError("[TASK] " + (e as Error).message);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  const handleSearch = async () => {
    if (!searchInput.trim() || taskId) return;
    setError(null);
    try {
      const { task_id } = await searchKeyword(searchInput.trim());
      setTaskId(task_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setSearchInput("");
  };

  function renderError() {
    if (!error) return null;
    let prefix: string;
    if (error.startsWith("[TASK] ")) {
      prefix = t("keywords.list.searchFailed");
    } else {
      prefix = t(error.startsWith("Failed") ? "keywords.list.errorPrefix" : "keywords.list.searchFailed");
    }
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
        {prefix + (error.startsWith("[TASK] ") ? error.slice(7) : error)}
        <button onClick={() => setError(null)} className="ml-3 underline">{t("common.dismiss")}</button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t("keywords.list.title")}</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder={t("keywords.list.searchPlaceholder")}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleSearch}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? t("keywords.list.analyzing") : t("keywords.list.searchButton")}
        </button>
      </div>

      {renderError()}

      {keywords.length === 0 && !taskId && !error && (
        <p className="text-gray-500 text-center py-12">
          {t("keywords.list.empty")}
        </p>
      )}

      <div className="grid gap-4">
        {keywords.map((kw) => (
          <Link
            key={kw.id}
            href={`/keywords/${kw.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{kw.keyword}</span>
              <span className={`text-sm px-2 py-1 rounded ${getTrendStyle(kw.trend_direction)}`}>
                {t(getTrendLabel(kw.trend_direction))}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-3 text-sm text-gray-600">
              <div>{t("keywords.list.volume")} <strong>{kw.search_volume_est.toLocaleString()}</strong></div>
              <div>{t("keywords.list.competition")} <strong>{kw.competition_score}%</strong></div>
              <div>{t("keywords.list.avgPrice")} <strong>${Number(kw.avg_price).toFixed(2)}</strong></div>
              <div>{t("keywords.list.listings")} <strong>{kw.listing_count.toLocaleString()}</strong></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
