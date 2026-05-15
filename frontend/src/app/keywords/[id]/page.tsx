"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getKeyword, getKeywordRelated, getKeywordTrend } from "../../../lib/api";
import type { Keyword, TagCount, TrendPoint } from "../../../lib/types";

export default function KeywordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [keyword, setKeyword] = useState<Keyword | null>(null);
  const [related, setRelated] = useState<TagCount[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);

  useEffect(() => {
    if (!id) return;
    getKeyword(id).then(setKeyword).catch(console.error);
    getKeywordRelated(id).then(setRelated).catch(console.error);
    getKeywordTrend(id).then(setTrend).catch(console.error);
  }, [id]);

  if (!keyword) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">{keyword.keyword}</h1>
      <p className="text-gray-500 mb-8">Last updated: {new Date(keyword.last_updated).toLocaleString()}</p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard label="Est. Search Volume" value={keyword.search_volume_est.toLocaleString()} />
        <MetricCard label="Competition" value={`${keyword.competition_score}%`} />
        <MetricCard label="Avg Price" value={`$${Number(keyword.avg_price).toFixed(2)}`} />
        <MetricCard label="Active Listings" value={keyword.listing_count.toLocaleString()} />
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Related Tags</h2>
          {related.length === 0 ? (
            <p className="text-gray-500">No related tags found.</p>
          ) : (
            <div className="space-y-2">
              {related.map((rt) => (
                <div key={rt.tag} className="flex justify-between items-center border-b pb-2">
                  <span className="font-medium">{rt.tag}</span>
                  <span className="text-gray-500">{rt.count} listings</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Trend History</h2>
          {trend.length === 0 ? (
            <p className="text-gray-500">No trend data yet.</p>
          ) : (
            <div className="space-y-2">
              {trend.map((t, i) => (
                <div key={i} className="flex justify-between items-center border-b pb-2">
                  <span className="text-gray-500">{new Date(t.date).toLocaleDateString()}</span>
                  <span className="font-medium">{t.volume.toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border rounded-lg p-4 text-center">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
