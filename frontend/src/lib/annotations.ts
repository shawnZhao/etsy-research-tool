const FIELD_DESCRIPTIONS: Record<string, string> = {
  search_volume_est: "annotation.searchVolumeEst",
  competition_score: "annotation.competitionScore",
  avg_price: "annotation.avgPrice",
  listing_count: "annotation.listingCount",
  trend_direction: "annotation.trendDirection",
  total_listings: "annotation.totalListings",
  total_reviews: "annotation.totalReviews",
  avg_rating: "annotation.avgRating",
  price_range: "annotation.priceRange",
  overall_score: "annotation.overallScore",
  title_score: "annotation.titleScore",
  tag_score: "annotation.tagScore",
  description_score: "annotation.descriptionScore",
};

export function getFieldAnnotation(field: string): string | null {
  return FIELD_DESCRIPTIONS[field] || null;
}
