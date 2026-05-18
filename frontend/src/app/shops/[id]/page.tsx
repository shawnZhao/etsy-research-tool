"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getShop, getShopTags, getShopListings } from "../../../lib/api";
import type { Shop, TagCount, Listing } from "../../../lib/types";
import { useTranslation } from "../../../lib/i18n/context";
import { getFieldAnnotation } from "../../../lib/annotations";
import { InfoBadge } from "../../../components/InfoBadge";

export default function ShopDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const [shop, setShop] = useState<Shop | null>(null);
  const [tags, setTags] = useState<TagCount[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getShop(id).then(setShop),
      getShopTags(id).then(setTags),
      getShopListings(id).then((res) => setListings(res.items || [])),
    ])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-center py-12 text-gray-500">{t("common.loading")}</div>;

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 inline-block">
          {t("shops.detail.errorPrefix") + error}
        </div>
      </div>
    );
  }

  if (!shop) return <div className="text-center py-12 text-gray-500">{t("shops.detail.notFound")}</div>;

  const maxTagCount = Math.max(1, ...tags.map((t) => t.count));
  const displayTags = tags.slice(0, 30);
  const displayListings = listings.slice(0, 10);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">{shop.name}</h1>
      <p className="text-gray-500 mb-8">
        <a
          href={shop.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-orange-600 hover:underline"
        >
          {t("shops.detail.viewOnEtsy")}
        </a>
        {" · "}
        {t("shops.detail.lastUpdated") + new Date(shop.last_updated).toLocaleString()}
      </p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard
          label={t("shops.detail.totalListings")}
          value={(shop.total_listings || 0).toLocaleString()}
          tooltipKey="total_listings"
          t={t}
        />
        <MetricCard
          label={t("shops.detail.totalReviews")}
          value={(shop.total_reviews || 0).toLocaleString()}
          tooltipKey="total_reviews"
          t={t}
        />
        <MetricCard
          label={t("shops.detail.avgRating")}
          value={shop.avg_rating ? `★ ${Number(shop.avg_rating).toFixed(1)}` : t("common.na")}
          tooltipKey="avg_rating"
          t={t}
        />
        <MetricCard
          label={t("shops.detail.priceRange")}
          value={`$${shop.price_range?.min ?? 0} - $${shop.price_range?.max ?? 0}`}
          tooltipKey="price_range"
          t={t}
        />
      </div>

      <div className="grid grid-cols-2 gap-8 mb-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">{t("shops.detail.topTags")}</h2>
          {tags.length === 0 ? (
            <p className="text-gray-500">{t("shops.detail.noTagData")}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {displayTags.map((tag) => {
                const size = 12 + (tag.count / maxTagCount) * 24;
                return (
                  <span
                    key={tag.tag}
                    style={{ fontSize: `${size}px` }}
                    className="text-gray-700 px-2 py-1"
                  >
                    {tag.tag}
                  </span>
                );
              })}
            </div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">{t("shops.detail.categoryDistribution")}</h2>
          {!shop.category_distribution || shop.category_distribution.length === 0 ? (
            <p className="text-gray-500">{t("shops.detail.noCategoryData")}</p>
          ) : (
            <div className="space-y-3">
              {(shop.category_distribution || []).map((cd) => (
                <div key={cd.category}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{cd.category}</span>
                    <span className="text-gray-500">{cd.pct}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-orange-500 h-2 rounded-full"
                      style={{ width: `${cd.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">{t("shops.detail.recentListings")}</h2>
        {displayListings.length === 0 ? (
          <p className="text-gray-500">{t("shops.detail.noListings")}</p>
        ) : (
          <div className="grid gap-4">
            {displayListings.map((listing) => (
              <div
                key={listing.id}
                className="border rounded-lg p-4 flex gap-4"
              >
                {listing.images && listing.images.length > 0 && (
                  <img
                    src={listing.images[0]}
                    alt={listing.title}
                    className="w-20 h-20 object-cover rounded"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{listing.title}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {[
                      listing.price !== undefined && listing.price !== null
                        ? `$${Number(listing.price).toFixed(2)}${listing.currency ? ` ${listing.currency}` : ""}`
                        : "",
                      listing.favorites != null
                        ? t("shops.detail.favorites", { count: listing.favorites })
                        : "",
                      listing.tags
                        ? t("shops.detail.tagsCount", { count: listing.tags.length })
                        : "",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <Link
                  href={`/seo?url=${encodeURIComponent(listing.url || "")}`}
                  className="self-center shrink-0 bg-orange-600 text-white text-sm px-4 py-2 rounded-lg font-medium hover:bg-orange-700 transition-colors"
                >
                  {t("shops.detail.auditSeo")}
                </Link>
              </div>
            ))}
          </div>
        )}
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
