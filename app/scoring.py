"""Transparent 0-100 scoring per the project spec. Every point is explained
in score_reasons so the weekly email can say *why* something scored well -
no opaque model judgement.
"""
from __future__ import annotations

from app.models import MatchCategory, Vacancy

SPORT_TERMS = ["sport", "rowing", "football", "formula 1", "f1 ", "olympic",
               "performance analysis", "performance analytics", "sports analytics",
               "sports technology", "sports science"]
CRIME_TERMS = ["crime", "cyber crime", "cybercrime", "forensic", "criminal investigation",
               "intelligence", "national security", "police"]
TRANSPORT_TERMS = ["transport", "travel", "aviation", "airline", "airport", "rail",
                    "logistics", "route optimisation", "route optimization"]
CS_SOFTWARE_TERMS = ["computer science", "software engineer", "software development",
                      "software developer", "digital and technology solutions",
                      "digital & technology solutions"]
PROGRAMMING_TERMS = ["programming", "software development", "developer", "coding", "python", "java", "c#"]
DATA_AI_CYBER_TERMS = ["data science", "data engineer", "artificial intelligence", "machine learning",
                        "cyber security", "cybersecurity"]
ALGO_TERMS = ["algorithm", "optimisation", "optimization", "graph theory", "operational research"]
MATH_MODEL_TERMS = ["mathematical modelling", "mathematical modeling", "quantitative", "statistics"]
WEAK_IT_TERMS = ["it support", "service desk", "helpdesk", "help desk", "desktop support"]
BUSINESS_TERMS = ["business administration", "hr apprentice", "human resources", "marketing apprentice",
                   "sales apprentice"]
FINANCE_TERMS = ["accounting", "accountancy", "investment banking", "finance apprentice", "audit apprentice"]

DEGREE_LEVEL_KEYWORDS_STRONG = ["software", "computer science", "computing", "data", "cyber", "digital"]


def _any_term(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def score_vacancy(v: Vacancy, config: dict) -> Vacancy:
    """Mutates and returns v with score, match_category, score_reasons, tags set."""
    reasons: list[str] = []
    tags: set[str] = set()
    score = 0

    haystack = " ".join(filter(None, [
        v.title, v.subject, v.degree, v.description, v.qualification, v.entry_requirements,
    ])).lower()
    location = (v.location or "").lower()

    # ---- hard exclusions (spec: "Do not allow positive scores to override hard exclusions") ----
    is_degree_apprenticeship = bool(v.level and v.level >= 6) or "degree apprenticeship" in haystack
    if v.level is not None and v.level < 6:
        score -= 100
        reasons.append(f"Excluded: apprenticeship level {v.level} is below the Level 6 degree threshold.")
    elif not is_degree_apprenticeship and v.level is None:
        # level unknown - don't nuke it, but don't reward either; handled by level bonus below (0)
        reasons.append("Level could not be confirmed from source data.")

    london_terms = config.get("location", {}).get("london_terms", ["london"])
    is_london = bool(location) and any(t in location for t in london_terms)
    if location and not is_london:
        score -= 100
        reasons.append(f"Excluded: location '{v.location}' is not realistically London-based.")
    elif not location:
        reasons.append("Location could not be confirmed from source data.")

    start_year = None
    for token in (v.start_date or "").replace("/", " ").split():
        if token.isdigit() and len(token) == 4:
            start_year = int(token)
            break
    primary_year = config.get("entry_year", {}).get("primary", 2027)
    if start_year and start_year != primary_year:
        score -= 50
        reasons.append(f"Start date {start_year} is not {primary_year}; scored down.")

    if _any_term(haystack, WEAK_IT_TERMS):
        score -= 30
        reasons.append("Primarily IT support content - penalised.")
    if _any_term(haystack, BUSINESS_TERMS):
        score -= 30
        reasons.append("Primarily business/HR/marketing content - penalised.")
    if _any_term(haystack, FINANCE_TERMS) and not _any_term(haystack, CS_SOFTWARE_TERMS + DATA_AI_CYBER_TERMS):
        score -= 30
        reasons.append("Primarily finance/accounting content with no technical software/data role - penalised.")

    # ---- positive weights ----
    if is_london:
        score += 25
        reasons.append("London-based (+25).")

    if v.level and v.level >= 6:
        score += 20
        reasons.append("Level 6 degree apprenticeship (+20).")

    if start_year == primary_year:
        score += 15
        reasons.append(f"Starts {primary_year} (+15).")

    if _any_term(haystack, CS_SOFTWARE_TERMS):
        score += 15
        reasons.append("Computer Science / Software Engineering subject (+15).")
        tags.add("CS")
        tags.add("SOFTWARE")

    if _any_term(haystack, PROGRAMMING_TERMS):
        score += 10
        reasons.append("Programming/software development content (+10).")
        tags.add("SOFTWARE")

    if _any_term(haystack, DATA_AI_CYBER_TERMS):
        score += 10
        reasons.append("Data science/AI/cyber security content (+10).")
        if "data" in haystack:
            tags.add("DATA")
        if "artificial intelligence" in haystack or "machine learning" in haystack:
            tags.add("AI")
            tags.add("MACHINE_LEARNING")
        if "cyber" in haystack:
            tags.add("CYBER")

    if _any_term(haystack, ALGO_TERMS):
        score += 8
        reasons.append("Algorithms/optimisation content (+8).")
        tags.add("ALGORITHMS")
        if "graph theory" in haystack:
            tags.add("NETWORKS")
        if "optimisation" in haystack or "optimization" in haystack:
            tags.add("OPTIMISATION")

    # interest combinations - only tag/score if there's real technical content alongside the interest
    has_technical_core = _any_term(haystack, CS_SOFTWARE_TERMS + PROGRAMMING_TERMS + DATA_AI_CYBER_TERMS)

    if _any_term(haystack, SPORT_TERMS):
        if has_technical_core:
            score += 8
            reasons.append("Combines technical (CS/software/data) work with sport - a strong personal-interest match (+8).")
            tags.add("SPORT")
            tags.add("SPORTS_ANALYTICS")
        else:
            reasons.append("Mentions sport but lacks confirmed technical content - not scored as a CS+sport match.")

    if _any_term(haystack, CRIME_TERMS):
        if has_technical_core:
            score += 8
            reasons.append("Combines technical work with crime/security/intelligence content (+8).")
            tags.add("CRIME")
            tags.add("SECURITY")
            if "intelligence" in haystack:
                tags.add("INTELLIGENCE")
        else:
            reasons.append("Mentions crime/security but lacks confirmed technical content.")

    if _any_term(haystack, TRANSPORT_TERMS):
        if has_technical_core:
            score += 8
            reasons.append("Combines technical work with transport/travel/aviation content (+8).")
            tags.add("TRANSPORT")
            if "aviation" in haystack or "airline" in haystack or "airport" in haystack:
                tags.add("AVIATION")
            if "travel" in haystack:
                tags.add("TRAVEL")
        else:
            reasons.append("Mentions transport/travel but lacks confirmed technical content.")

    if _any_term(haystack, MATH_MODEL_TERMS):
        score += 5
        reasons.append("Mathematical modelling content (+5).")
        tags.add("MATHEMATICS")

    if "python" in haystack:
        score += 5
        reasons.append("Python/software engineering explicitly mentioned (+5).")

    if _any_term(haystack, ["degree in computer science", "bsc computer science", "beng", "bsc (hons)", "bsc hons"]):
        score += 5
        reasons.append("Strong technical degree content (+5).")

    if "government" in haystack or _any_term(haystack, ["gchq", "ncsc", "home office", "ministry of defence",
                                                          "ministry of justice", "national crime agency",
                                                          "metropolitan police"]):
        tags.add("GOVERNMENT")
    if "robotic" in haystack:
        tags.add("ROBOTICS")
    if "cloud" in haystack:
        tags.add("CLOUD")

    v.score = max(-100, min(100, score))
    v.score_reasons = reasons
    v.tags = sorted(tags)

    hard_excluded = (v.level is not None and v.level < 6) or (bool(location) and not is_london)
    if hard_excluded:
        v.match_category = MatchCategory.EXCLUDED
    elif v.score >= 85:
        v.match_category = MatchCategory.EXCEPTIONAL_MATCH
    elif v.score >= 70:
        v.match_category = MatchCategory.STRONG_MATCH
    elif v.score >= 50:
        v.match_category = MatchCategory.GOOD_MATCH
    elif v.score >= 25:
        v.match_category = MatchCategory.POSSIBLE_MATCH
    else:
        v.match_category = MatchCategory.LOW_MATCH

    return v


def explain_match(v: Vacancy) -> str:
    """One personalised sentence for the emails, built only from confirmed facts."""
    parts = []
    if v.location and "london" in v.location.lower():
        parts.append("a London")
    if v.level and v.level >= 6:
        parts.append("Level 6 degree apprenticeship")
    else:
        parts.append("apprenticeship")
    if v.subject:
        parts.append(f"in {v.subject}")
    base = " ".join(parts)
    sentence = f"This is a {v.match_category.value.replace('_', ' ').lower()} because it is {base}"
    if "SPORT" in v.tags:
        sentence += ", and the technical work connects to your interest in sport/sports analytics"
    elif "CRIME" in v.tags or "SECURITY" in v.tags:
        sentence += ", and the technical work connects to your interest in crime-solving/security"
    elif "TRANSPORT" in v.tags or "TRAVEL" in v.tags or "AVIATION" in v.tags:
        sentence += ", and the technical work connects to your interest in transport/travel technology"
    elif "ALGORITHMS" in v.tags:
        sentence += ", directly matching your interest in algorithms (e.g. your A* search NEA project)"
    sentence += "."
    return sentence
