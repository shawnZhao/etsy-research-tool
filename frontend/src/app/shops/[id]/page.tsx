"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getShop, getShopTags, getShopListings } from "../../../lib/api";
import type { Shop, TagCount, Listing } from "../../../lib/types";

export default function ShopDetailPage() {
  const { id } = useParams<{ id: string }>();
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
      .catch((e) => setError("Failed to load shop data: " + e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 inline-block">
          {error}
        </div>
      </div>
    );
  }

  if (!shop) return <div className="text-center py-12 text-gray-500">Shop not found.</div>;

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
          View on Etsy &rarr;
        </a>
        {" · "}
        Last updated: {new Date(shop.last_updated).toLocaleString()}
      </p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <MetricCard label="Total Listings" value={(shop.total_listings || 0).toLocaleString()} />
        <MetricCard label="Total Reviews" value={(shop.total_reviews || 0).toLocaleString()} />
        <MetricCard label="Avg Rating" value={shop.avg_rating ? `★ ${Number(shop.avg_rating).toFixed(1)}` : "N/A"} />
        <MetricCard
          label="Price Range"
          value={`$${shop.price_range?.min ?? 0} - $${shop.price_range?.max ?? 0}`}
        />
      </div>

      <div className="grid grid-cols-2 gap-8 mb-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Top Tags Used</h2>
          {tags.length === 0 ? (
            <p className="text-gray-500">No tag data available.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {displayTags.map((t) => {
                const size = 12 + (t.count / maxTagCount) * 24;
                return (
                  <span
                    key={t.tag}
                    style={{ fontSize: `${size}px` }}
                    className="text-gray-700 px-2 py-1"
                  >
                    {t.tag}
                  </span>
                );
              })}
            </div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-4">Category Distribution</h2>
          {!shop.category_distribution || shop.category_distribution.length === 0 ? (
            <p className="text-gray-500">No category data available.</p>
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
        <h2 className="text-xl font-semibold mb-4">Recent Listings</h2>
        {displayListings.length === 0 ? (
          <p className="text-gray-500">No listings found.</p>
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
                      listing.favorites != null ? `${listing.favorites} favorites` : "",
                      listing.tags ? `${listing.tags.length} tags` : "",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
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
