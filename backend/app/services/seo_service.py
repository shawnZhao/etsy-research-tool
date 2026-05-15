import re


LONGTAIL_MODIFIERS = [
    "handmade", "custom", "personalized", "gift", "vintage",
    "boho", "minimalist", "modern", "rustic", "wedding",
    "gold", "silver",
]


def _word_matches(word: str, text: str) -> bool:
    """Check if word appears as a whole word in text (word-boundary match)."""
    return bool(re.search(r"\b" + re.escape(word) + r"\b", text))


def _word_count(word: str, text: str) -> int:
    """Count word-boundary occurrences of word in text."""
    return len(re.findall(r"\b" + re.escape(word) + r"\b", text))


class SEOService:
    def score_title(
        self, title: str, core_keywords: list[str]
    ) -> tuple[float, list[dict]]:
        """Score title 0-100. Returns (score, suggestions)."""
        score = 0.0
        suggestions: list[dict] = []

        # Length check: 40-60 ideal (+30), 20-80 partial (+15)
        title_len = len(title)
        if 40 <= title_len <= 60:
            score += 30
        elif 20 <= title_len <= 80:
            score += 15
            suggestions.append({
                "type": "title",
                "severity": "medium",
                "message": "Title length is outside the ideal 40-60 character range",
                "detail": "Your title is {} characters. Etsy titles perform best at 40-60 "
                         "characters. Consider trimming filler words or adding more "
                         "descriptive terms to reach the sweet spot.".format(title_len),
            })
        else:
            suggestions.append({
                "type": "title",
                "severity": "high",
                "message": "Title length is {} characters—far from the 40-60 ideal".format(title_len),
                "detail": "Etsy titles should be 40-60 characters for optimal visibility. "
                         "{} characters is too {}. Revise your title to hit that range "
                         "by {}.".format(
                             title_len,
                             "short" if title_len < 40 else "long",
                             "adding descriptive keywords"
                             if title_len < 40 else "removing unnecessary words",
                         ),
            })

        # Core keyword in first 40 characters
        first_40 = title[:40].lower()
        kw_in_first_40 = any(
            _word_matches(kw.lower(), first_40) for kw in core_keywords
        )
        if kw_in_first_40:
            score += 30
        else:
            suggestions.append({
                "type": "title",
                "severity": "high",
                "message": "Core keyword missing from the first 40 characters of the title",
                "detail": "Etsy search weights the beginning of titles more heavily. "
                         "Place your most important keyword ({}) within the first 40 "
                         "characters to improve ranking.".format(
                             core_keywords[0] if core_keywords else "your main keyword"
                         ),
            })

        # Capital letter ratio
        if title_len > 0:
            upper_count = sum(1 for ch in title if ch.isupper())
            cap_ratio = upper_count / title_len
        else:
            cap_ratio = 0
        if cap_ratio < 0.5:
            score += 20
        else:
            suggestions.append({
                "type": "title",
                "severity": "medium",
                "message": "Too many capital letters—{}% of the title is uppercase".format(
                    round(cap_ratio * 100)
                ),
                "detail": "ALL CAPS text can look spammy and may hurt click-through rate. "
                         "Use sentence case or title case instead. Only capitalize "
                         "proper nouns and the first letter of key words.",
            })

        # Longtail modifiers in title
        title_lower = title.lower()
        modifier_count = sum(
            1 for mod in LONGTAIL_MODIFIERS if _word_matches(mod, title_lower)
        )
        if modifier_count >= 2:
            score += 20
        else:
            suggestions.append({
                "type": "title",
                "severity": "low",
                "message": "Include 2+ buyer-friendly modifier words in your title",
                "detail": "Modifier words like 'handmade', 'custom', 'vintage', 'gift', "
                         "'minimalist', etc. help buyers find your item. Add at least 2 "
                         "from the Etsy longtail modifier list to attract more searches.",
            })

        return round(score, 1), suggestions

    def score_tags(
        self,
        tags: list[str],
        title: str,
        category_hot_tags: list[str],
    ) -> tuple[float, list[dict]]:
        """Score tags 0-100. Returns (score, suggestions)."""
        score = 0.0
        suggestions: list[dict] = []

        # All 13 tag slots used
        if len(tags) >= 13:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "high",
                "message": "Only {}/13 tag slots are used—fill all of them".format(len(tags)),
                "detail": "Etsy allows 13 tags per listing. Unused slots are missed "
                         "opportunities for search visibility. Add {} more tags using "
                         "longtail keywords and synonyms of your main terms.".format(
                             13 - len(tags)
                         ),
            })

        # 3+ multi-word (longtail) tags
        multi_word_count = sum(1 for t in tags if " " in t.strip())
        if multi_word_count >= 3:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "medium",
                "message": "Only {} multi-word (longtail) tags—add at least 3".format(
                    multi_word_count
                ),
                "detail": "Multi-word tags like 'boho wedding gift' or 'custom gold "
                         "necklace' capture more specific, high-intent searches. "
                         "Replace single-word tags with 2-3 word phrases where possible.",
            })

        # 8+ tags share words with title
        title_words = set(re.findall(r"\w+", title.lower()))
        tag_title_match_count = sum(
            1 for t in tags
            if any(word in title_words for word in t.lower().split())
        )
        if tag_title_match_count >= 8:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "medium",
                "message": "Only {}/13 tags align with title words—aim for 8+".format(
                    tag_title_match_count
                ),
                "detail": "Tags that share words with your title reinforce relevance "
                         "signals to Etsy search. Review your tags and align them "
                         "more closely with the language used in your title.",
            })

        # 3+ tags match category hot tags
        hot_tags_lower = {t.lower() for t in category_hot_tags}
        hot_tag_match_count = sum(
            1 for t in tags if t.lower() in hot_tags_lower
        )
        if hot_tag_match_count >= 3:
            score += 25
        else:
            suggestions.append({
                "type": "tags",
                "severity": "low",
                "message": "Only {} tags match current trending tags in your category".format(
                    hot_tag_match_count
                ),
                "detail": "Use trending tags from your category to boost visibility. "
                         "Trending tags: {}. Include at least 3 where relevant.".format(
                             ", ".join(category_hot_tags[:5])
                         ),
            })

        return round(score, 1), suggestions

    def score_description(
        self, description: str, core_keywords: list[str]
    ) -> tuple[float, list[dict]]:
        """Score description 0-100. Returns (score, suggestions)."""
        score = 0.0
        suggestions: list[dict] = []

        # Length >= 200 characters
        desc_len = len(description)
        if desc_len >= 200:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "medium",
                "message": "Description is only {} characters—expand to at least 200".format(
                    desc_len
                ),
                "detail": "Longer descriptions give Etsy more text to index and give "
                         "buyers more confidence. Describe materials, dimensions, "
                         "care instructions, and ideal use cases. Aim for 200+ characters.",
            })

        # Core keywords appear 2-5 times total
        desc_lower = description.lower()
        total_kw_mentions = sum(
            _word_count(kw.lower(), desc_lower) for kw in core_keywords
        )
        if 2 <= total_kw_mentions <= 5:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "medium",
                "message": "Core keywords appear only {} time(s)—mention them 2-5 times".format(
                    total_kw_mentions
                ),
                "detail": "Naturally weave your core keywords ({}) into the description "
                         "at least 2 times. Avoid keyword stuffing; 2-5 mentions is "
                         "the sweet spot for Etsy SEO.".format(
                             ", ".join(core_keywords) if core_keywords else "your keywords"
                         ),
            })

        # Structure check: newlines, bullets, or dashes
        has_structure = (
            "\n" in description
            or "•" in description
            or "- " in description
        )
        if has_structure:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "low",
                "message": "Description lacks formatting structure—add sections or bullets",
                "detail": "Use line breaks, bullet points (• or -), and short paragraphs "
                         "to make your description scannable. Buyers skim—structure "
                         "helps them find key details quickly.",
            })

        # 2+ longtail keyword phrases present
        longtail_count = sum(
            1 for mod in LONGTAIL_MODIFIERS if _word_matches(mod, desc_lower)
        )
        if longtail_count >= 2:
            score += 25
        else:
            suggestions.append({
                "type": "description",
                "severity": "low",
                "message": "Include 2+ longtail keyword phrases in your description",
                "detail": "Longtail modifier words like 'handmade', 'custom', 'vintage', "
                         "'gift', 'boho', etc. improve search relevance. Naturally "
                         "incorporate 2+ of these into your description text.",
            })

        return round(score, 1), suggestions

    def extract_core_keywords(
        self, title: str, tags: list[str]
    ) -> list[str]:
        """Extract likely core keywords from title and tags. Return max 5."""
        # First 5 words of title
        title_words = title.lower().split()[:5]
        # First 3 tags
        tag_words = [t.lower() for t in tags[:3]]

        # Union preserving order, max 5
        seen: set[str] = set()
        result: list[str] = []
        for word in title_words + tag_words:
            stripped = word.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                result.append(stripped)
                if len(result) >= 5:
                    break
        return result

    def compute_overall_score(
        self, title_score: float, tag_score: float, desc_score: float
    ) -> float:
        """Compute weighted overall score. Title 35%, Tags 40%, Description 25%."""
        return round(title_score * 0.35 + tag_score * 0.40 + desc_score * 0.25, 1)
