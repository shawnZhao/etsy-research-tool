"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getKeyword, getKeywordRelated, getKeywordTrend } from "../../../lib/api";
import type { Keyword, TagCount, TrendPoint } from "../../../lib/types";
import { useTranslation } from "../../../lib/i18n/context";
import { getFieldAnnotation } from "../../../lib/annotations";
import { InfoBadge } from "../../../components/InfoBadge";

export default function KeywordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const [keyword, setKeyword] = useState<Keyword | null>(null);
  const [related, setRelated] = useState<TagCount[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getKeyword(id).then(setKeyword),
      getKeywordRelated(id).then(setRelated),
      getKeywordTrend(id).then(setTrend),
    ])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-center py-12 text-gray-500">{t("common.loading")}</div>;

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 inline-block">
          {t("keywords.detail.errorPrefix") + error}
        </div>
      </div>
    );
  }

  if (!keyword) return <div className="text-center py-12 text-gray-500">{t("keywords.detail.notFound")}</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">{keyword.keyword}</h1>
      <p className="text-gray-500 mb-8">
        {t("keywords.detail.lastUpdated") + new Date(keyword.last_updated).toLocaleString()}
      </p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard
          label={t("keywords.detail.estSearchVolume")}
          value={keyword.search_volume_est.toLocaleString()}
          tooltipKey="search_volume_est"
          t={t}
        />
        <MetricCard
          label={t("keywords.detail.competition")}
          value={`${keyword.competition_score}%`}
          tooltipKey="competition_score"
          t={t}
        />
        <MetricCard
          label={t("keywords.detail.avgPrice")}
          value={`$${Number(keyword.avg_price).toFixed(2)}`}
          tooltipKey="avg_price"
          t={t}
        />
        <MetricCard
          label={t("keywords.detail.activeListings")}
          value={keyword.listing_count.toLocaleString()}
          tooltipKey="listing_count"
          t={t}
        />
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">{t("keywords.detail.relatedTags")}</h2>
          {related.length === 0 ? (
            <p className="text-gray-500">{t("keywords.detail.noRelatedTags")}</p>
          ) : (
            <div className="space-y-2">
              {related.map((rt) => (
                <div key={rt.tag} className="flex justify-between items-center border-b pb-2">
                  <span className="font-medium">{rt.tag}</span>
                  <span className="text-gray-500">
                    {t("keywords.detail.listingsCount", { count: rt.count })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">{t("keywords.detail.trendHistory")}</h2>
          {trend.length === 0 ? (
            <p className="text-gray-500">{t("keywords.detail.noTrendData")}</p>
          ) : (
            <div className="space-y-2">
              {trend.map((tp, i) => (
                <div key={i} className="flex justify-between items-center border-b pb-2">
                  <span className="text-gray-500">{new Date(tp.date).toLocaleDateString()}</span>
                  <span className="font-medium">{tp.volume.toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  tooltipKey,
  t,
}: {
  label: string;
  value: string;
  tooltipKey?: string;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const annotationKey = tooltipKey ? getFieldAnnotation(tooltipKey) : null;
  const tooltipText = annotationKey ? t(annotationKey) : null;

  return (
    <div className="border rounded-lg p-4 text-center">
      <div className="text-sm text-gray-500 mb-1">
        <InfoBadge label={label} tooltip={tooltipText} />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
