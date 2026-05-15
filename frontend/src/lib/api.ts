import type {
  Keyword,
  Shop,
  Listing,
  SEOAudit,
  TagCount,
  TrendPoint,
  FrequencyData,
  TaskStatus,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: customHeaders, ...restOptions } = options || {};
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...customHeaders,
    },
    ...restOptions,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.detail || err.message || "Request failed");
  }
  return res.json();
}

// Keywords
export const searchKeyword = (keyword: string) =>
  request<{ task_id: string }>("/keywords/search", {
    method: "POST",
    body: JSON.stringify({ keyword }),
  });

export const getKeyword = (id: string) =>
  request<Keyword>(`/keywords/${id}`);

export const listKeywords = (sort?: string, order?: string) =>
  request<Keyword[]>(`/keywords?sort=${sort || "last_updated"}&order=${order || "desc"}`);

export const getKeywordRelated = (id: string) =>
  request<TagCount[]>(`/keywords/${id}/related`);

export const compareKeywords = (ids: string[]) =>
  request<Keyword[]>(`/keywords/compare`, {
    method: "POST",
    body: JSON.stringify({ ids }),
  });

export const getKeywordTrend = (id: string) =>
  request<TrendPoint[]>(`/keywords/${id}/trend`);

// Shops
export const trackShop = (url: string) =>
  request<{ task_id: string }>("/shops/track", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

export const listShops = () =>
  request<Shop[]>("/shops");

export const getShop = (id: string) =>
  request<Shop>(`/shops/${id}`);

export const getShopTags = (id: string) =>
  request<TagCount[]>(`/shops/${id}/tags`);

export const getShopListings = (id: string, page = 1) =>
  request<{ items: Listing[]; total: number }>(`/shops/${id}/listings?page=${page}`);

export const getShopTrend = (id: string) =>
  request<FrequencyData>(`/shops/${id}/trend`);

export const compareShops = (ids: string[]) =>
  request<Shop[]>(`/shops/compare`, {
    method: "POST",
    body: JSON.stringify({ ids }),
  });

// SEO
export const auditListing = (listingUrl: string) =>
  request<{ task_id: string }>("/seo/audit", {
    method: "POST",
    body: JSON.stringify({ listing_url: listingUrl }),
  });

export const getSEOAudit = (id: string) =>
  request<SEOAudit>(`/seo/audits/${id}`);

export const listAudits = (listingId?: string) =>
  request<SEOAudit[]>(`/seo/audits${listingId ? `?listing_id=${listingId}` : ""}`);

export const getTaskStatus = (taskId: string) =>
  request<TaskStatus>(`/tasks/${taskId}`);
