"use client";

import { useEffect, useState } from "react";
import { listKeywords, listShops, listAudits } from "../lib/api";
import type { Keyword, Shop, SEOAudit } from "../lib/types";
import { useTranslation } from "../lib/i18n/context";
import Link from "next/link";

export default function DashboardPage() {
  const { t } = useTranslation();
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [shops, setShops] = useState<Shop[]>([]);
  const [audits, setAudits] = useState<SEOAudit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      listKeywords().then(setKeywords),
      listShops().then(setShops),
      listAudits().then(setAudits),
    ])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-12 text-gray-500">{t("dashboard.loading")}</div>;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 inline-block">
          {t("dashboard.errorPrefix") + error}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">{t("dashboard.title")}</h1>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <Link
          href="/keywords"
          className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all"
        >
          <div className="text-3xl mb-2">🔍</div>
          <div className="text-3xl font-bold text-orange-600">{keywords.length}</div>
          <div className="text-gray-500 mt-1">{t("dashboard.keywordsAnalyzed")}</div>
        </Link>
        <Link
          href="/shops"
          className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all"
        >
          <div className="text-3xl mb-2">🏪</div>
          <div className="text-3xl font-bold text-orange-600">{shops.length}</div>
          <div className="text-gray-500 mt-1">{t("dashboard.shopsTracked")}</div>
        </Link>
        <Link
          href="/seo"
          className="block border rounded-xl p-6 hover:border-orange-300 hover:shadow-sm transition-all"
        >
          <div className="text-3xl mb-2">📊</div>
          <div className="text-3xl font-bold text-orange-600">{audits.length}</div>
          <div className="text-gray-500 mt-1">{t("dashboard.seoAudits")}</div>
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">{t("dashboard.recentKeywords")}</h2>
            <Link href="/keywords" className="text-orange-600 text-sm hover:underline">
              {t("dashboard.viewAll")}
            </Link>
          </div>
          {keywords.length === 0 ? (
            <p className="text-gray-500">{t("dashboard.noKeywords")}</p>
          ) : (
            <div className="space-y-2">
              {keywords.slice(0, 5).map((kw) => (
                <Link
                  key={kw.id}
                  href={`/keywords/${kw.id}`}
                  className="flex justify-between items-center border rounded-lg p-3 hover:border-orange-200"
                >
                  <span className="font-medium">{kw.keyword}</span>
                  <span className="text-sm text-gray-500">
                    {t("dashboard.vol")} {kw.search_volume_est.toLocaleString()}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">{t("dashboard.trackedShops")}</h2>
            <Link href="/shops" className="text-orange-600 text-sm hover:underline">
              {t("dashboard.viewAll")}
            </Link>
          </div>
          {shops.length === 0 ? (
            <p className="text-gray-500">{t("dashboard.noShops")}</p>
          ) : (
            <div className="space-y-2">
              {shops.slice(0, 5).map((shop) => (
                <Link
                  key={shop.id}
                  href={`/shops/${shop.id}`}
                  className="flex justify-between items-center border rounded-lg p-3 hover:border-orange-200"
                >
                  <span className="font-medium">{shop.name}</span>
                  <span className="text-sm text-gray-500">
                    ★ {Number(shop.avg_rating).toFixed(1)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
