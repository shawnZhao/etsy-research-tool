"use client";

import { useState, useEffect } from "react";
import { listShops, trackShop, getTaskStatus } from "../../lib/api";
import type { Shop } from "../../lib/types";
import { useTranslation } from "../../lib/i18n/context";
import Link from "next/link";

export default function ShopsPage() {
  const { t } = useTranslation();
  const [shops, setShops] = useState<Shop[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    listShops()
      .then(setShops)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId);
        if (status.status === "SUCCESS") {
          setTaskId(null);
          const updated = await listShops();
          setShops(updated);
        } else if (status.status === "FAILURE") {
          setTaskId(null);
          setError("[SYNC] " + (status.error || "Unknown"));
        }
      } catch (e) {
        setTaskId(null);
        setError("[SYNC] " + (e as Error).message);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  const handleTrack = async () => {
    if (!urlInput.trim()) return;
    setError(null);
    try {
      const { task_id } = await trackShop(urlInput.trim());
      setTaskId(task_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setUrlInput("");
  };

  function renderError() {
    if (!error) return null;
    const isSync = error.startsWith("[SYNC] ");
    const message = isSync ? error.slice(7) : error;
    const prefix = isSync ? t("shops.list.syncFailed") : t("shops.list.trackFailed");
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
        {prefix + message}
        <button onClick={() => setError(null)} className="ml-3 underline">{t("common.dismiss")}</button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t("shops.list.title")}</h1>
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTrack()}
          placeholder={t("shops.list.urlPlaceholder")}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-lg"
        />
        <button
          onClick={handleTrack}
          disabled={!!taskId}
          className="bg-orange-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50"
        >
          {taskId ? t("shops.list.syncing") : t("shops.list.trackButton")}
        </button>
      </div>

      {renderError()}

      {shops.length === 0 && !taskId && !error && (
        <p className="text-gray-500 text-center py-12">
          {t("shops.list.empty")}
        </p>
      )}

      <div className="grid gap-4">
        {shops.map((shop) => (
          <Link
            key={shop.id}
            href={`/shops/${shop.id}`}
            className="block border rounded-lg p-4 hover:border-orange-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{shop.name}</span>
              <span className="text-sm text-yellow-600">
                {shop.avg_rating ? `★ ${Number(shop.avg_rating).toFixed(1)}` : ""}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-3 text-sm text-gray-600">
              <div>{t("shops.list.listings")} <strong>{shop.total_listings?.toLocaleString() || "0"}</strong></div>
              <div>{t("shops.list.reviews")} <strong>{shop.total_reviews?.toLocaleString() || "0"}</strong></div>
              <div>{t("shops.list.tags")} <strong>{shop.tags_used?.length || 0}</strong></div>
              <div>{t("shops.list.updated")} <strong>{shop.last_updated ? new Date(shop.last_updated).toLocaleDateString() : t("common.na")}</strong></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
