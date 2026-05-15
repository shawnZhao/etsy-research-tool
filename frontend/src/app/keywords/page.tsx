"use client";

import { useState, useEffect } from "react";
import { listKeywords, searchKeyword, getTaskStatus } from "../../lib/api";
import type { Keyword } from "../../lib/types";
import Link from "next/link";

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listKeywords()
      .then(setKeywords)
      .catch((e) => setError("Failed to load keywords: " + e.message));
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
          setError("Search failed: " + status.error);
        }
      } catch (e) {
        setTaskId(null);
        setError("Failed to check task status: " + (e as Error).message);
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
      setError("Search failed: " + (e as Error).message);
    }
    setSearchInput("");
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Keyword Research</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search a keyword on Etsy..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleSearch}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? "Analyzing..." : "Search"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {error}
          <button onClick={() => setError(null)} className="ml-3 underline">Dismiss</button>
        </div>
      )}

      {keywords.length === 0 && !taskId && !error && (
        <p className="text-gray-500 text-center py-12">
          No keywords analyzed yet. Search a keyword to get started.
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
              <span className={`text-sm px-2 py-1 rounded ${
                kw.trend_direction === "up" ? "bg-green-100 text-green-700" :
                kw.trend_direction === "down" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-600"
              }`}>
                {kw.trend_direction === "up" ? "Rising" :
                 kw.trend_direction === "down" ? "Falling" : "Stable"}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-3 text-sm text-gray-600">
              <div>Volume: <strong>{kw.search_volume_est.toLocaleString()}</strong></div>
              <div>Competition: <strong>{kw.competition_score}%</strong></div>
              <div>Avg Price: <strong>${Number(kw.avg_price).toFixed(2)}</strong></div>
              <div>Listings: <strong>{kw.listing_count.toLocaleString()}</strong></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
