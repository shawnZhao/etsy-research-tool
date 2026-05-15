export interface Keyword {
  id: string;
  keyword: string;
  search_volume_est: number;
  competition_score: number;
  avg_price: number;
  listing_count: number;
  top_category: string;
  related_tags: TagCount[];
  trend_direction: "up" | "down" | "stable";
  trend_data: TrendPoint[];
  last_updated: string;
  created_at: string;
}

export interface Shop {
  id: string;
  shop_id: number;
  name: string;
  url: string;
  total_listings: number;
  total_reviews: number;
  avg_rating: number;
  tags_used: TagCount[];
  category_distribution: CategoryDist[];
  price_range: PriceRange;
  listing_frequency: FrequencyData;
  last_updated: string;
  created_at: string;
}

export interface Listing {
  id: string;
  listing_id: number;
  shop_id: number;
  title: string;
  description: string;
  tags: string[];
  price: number;
  currency: string;
  category: string;
  category_path: string[];
  url: string;
  images: string[];
  favorites: number;
  review_count: number;
  rating: number;
  views_est: number;
  last_updated: string;
  created_at: string;
}

export interface SEOAudit {
  id: string;
  listing_id: string;
  title_score: number;
  tag_score: number;
  description_score: number;
  overall_score: number;
  suggestions: SEOSuggestion[];
  benchmarks: Record<string, number>;
  created_at: string;
}

export interface RankingSnapshot {
  id: string;
  listing_id: string;
  keyword_id: string;
  position: number;
  total_results: number;
  captured_at: string;
}

export interface TagCount {
  tag: string;
  count: number;
}

export interface CategoryDist {
  category: string;
  count: number;
  pct: number;
}

export interface PriceRange {
  min: number;
  max: number;
  avg: number;
  median: number;
}

export interface FrequencyData {
  weekly: number;
  monthly: number;
  trend: number[];
}

export interface TrendPoint {
  date: string;
  volume: number;
}

export interface SEOSuggestion {
  type: "title" | "tags" | "description";
  severity: "high" | "medium" | "low";
  message: string;
  detail: string;
}

export interface TaskStatus {
  task_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: unknown;
  error?: string;
}
