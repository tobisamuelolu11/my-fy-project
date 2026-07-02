"""
semantic_scholar.py  –  Fetch real papers from the Semantic Scholar API
Docs: https://api.semanticscholar.org/api-docs/

No API key required for basic usage (100 requests / 5 min limit).
Get a free key at https://www.semanticscholar.org/product/api to raise
the limit to 1 request/second — pass it as a CLI argument (see bottom).

This module is a drop-in companion to arxiv_fetch.py — both write into the
same `articles` table (title, authors, journal, year, keywords, abstract,
content, url) and de-duplicate by title, so you can run either one, or
both back-to-back, to build up your dataset.

    python semantic_scholar.py                 # public rate limit
    python semantic_scholar.py YOUR_API_KEY     # faster, with a key
    python semantic_scholar.py --clear          # wipe articles table first
    python semantic_scholar.py --topics "topic one, topic two"
"""

import requests
import time
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'scholorfind.db')

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS   = "title,authors,year,abstract,venue,externalIds,openAccessPdf,tldr,url"

# ── Topics — mirrors the broad academic spread used in arxiv_fetch.py ──────
DEFAULT_TOPICS = [
    # Computer Science & AI
    "machine learning",
    "deep learning neural networks",
    "natural language processing",
    "computer vision",
    "cybersecurity",
    "blockchain",
    "cloud computing",
    "recommender systems",

    # Medicine & Health Sciences
    "cancer treatment clinical trials",
    "infectious disease epidemiology",
    "mental health depression anxiety",
    "cardiovascular disease prevention",
    "vaccine immunology",
    "drug discovery pharmacology",
    "medical imaging diagnosis",
    "public health nutrition",

    # Biology & Life Sciences
    "genomics gene expression",
    "CRISPR gene editing",
    "protein structure folding",
    "ecology biodiversity conservation",
    "neuroscience brain cognitive",
    "cell biology molecular mechanisms",
    "evolutionary biology genetics",
    "microbiology microbiome",

    # Physics & Engineering
    "quantum computing physics",
    "renewable energy solar wind",
    "materials science nanotechnology",
    "robotics autonomous systems",
    "fluid dynamics thermodynamics",
    "semiconductor electronics",
    "structural engineering mechanics",
    "signal processing communications",

    # Mathematics & Statistics
    "optimization algorithms mathematics",
    "graph theory combinatorics",
    "probability statistics inference",
    "numerical methods simulation",
    "cryptography number theory",

    # Social Sciences
    "economics financial markets",
    "political science governance policy",
    "sociology social inequality",
    "psychology behavior cognition",
    "education learning outcomes",
    "urban planning smart cities",

    # Environmental Science
    "climate change global warming",
    "environmental pollution remediation",
    "water resources hydrology",
    "sustainable agriculture food security",

    # Humanities & Arts
    "linguistics language evolution",
    "history archaeology ancient civilizations",
    "philosophy ethics artificial intelligence",

    # Business & Management
    "supply chain management logistics",
    "entrepreneurship innovation startup",
    "organizational behavior leadership",
    "marketing consumer behavior",
]


# ─────────────────────────────────────────────
# Core fetch function
# ─────────────────────────────────────────────
def fetch_papers(query: str, limit: int = 20, api_key: str = None) -> list[dict]:
    """
    Search Semantic Scholar for papers matching a query.
    Returns a list of cleaned article dicts ready for DB insertion
    (same shape as arxiv_fetch.fetch_papers: title, authors, journal,
    year, keywords, abstract, content, url).
    """
    url     = f"{BASE_URL}/paper/search"
    params  = {"query": query, "limit": limit, "fields": FIELDS}
    headers = {"x-api-key": api_key} if api_key else {}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"  [!] Timeout while fetching '{query}'")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  [!] HTTP error for '{query}': {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"  [!] Request failed for '{query}': {e}")
        return []

    data   = response.json()
    papers = data.get("data", [])
    result = []

    for paper in papers:
        title    = paper.get("title") or ""
        abstract = paper.get("abstract") or ""
        year     = paper.get("year") or 0
        venue    = paper.get("venue") or "Semantic Scholar"

        raw_authors = paper.get("authors") or []
        authors = "; ".join(a.get("name", "") for a in raw_authors[:4]) or "Unknown Authors"

        # Fall back to the AI-generated TLDR if no abstract is available
        tldr = paper.get("tldr") or {}
        if not abstract and tldr.get("text"):
            abstract = tldr["text"]

        if not title or not abstract:
            continue   # skip papers with no useful content to index

        # Real paper URL: prefer Semantic Scholar's own permalink,
        # fall back to an open-access PDF, then to a DOI/arXiv link if present
        paper_url = paper.get("url") or ""
        if not paper_url:
            oa = paper.get("openAccessPdf") or {}
            paper_url = oa.get("url", "")
        if not paper_url:
            ext = paper.get("externalIds") or {}
            if ext.get("DOI"):
                paper_url = f"https://doi.org/{ext['DOI']}"
            elif ext.get("ArXiv"):
                paper_url = f"https://arxiv.org/abs/{ext['ArXiv']}"

        keywords = _extract_keywords(title)
        content  = f"{title} {keywords} {abstract}"

        result.append({
            "title":    title,
            "authors":  authors,
            "journal":  venue,
            "year":     int(year) if year else 0,
            "keywords": keywords,
            "abstract": abstract[:1000],
            "content":  content,
            "url":      paper_url,
        })

    return result


def _extract_keywords(title: str) -> str:
    """Extract meaningful words from the title as pseudo-keywords."""
    stop = {"a","an","the","of","in","for","on","with","and","or","to","by",
            "from","using","based","via","towards","approach","study","analysis"}
    words = [w.strip(".,()[]") for w in title.lower().split()]
    return "; ".join(w for w in words if w and w not in stop and len(w) > 2)


# ─────────────────────────────────────────────
# Database helpers (shared shape with arxiv_fetch.py)
# ─────────────────────────────────────────────
def insert_articles(articles: list[dict]) -> int:
    """Insert articles, skipping exact title duplicates. Returns insert count."""
    if not articles:
        return 0

    conn     = sqlite3.connect(DB_PATH)
    cursor   = conn.cursor()
    inserted = 0

    for a in articles:
        exists = cursor.execute(
            "SELECT 1 FROM articles WHERE title = ?", (a["title"],)
        ).fetchone()

        if not exists:
            cursor.execute(
                """INSERT INTO articles (title, authors, journal, year, keywords, abstract, content, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (a["title"], a["authors"], a["journal"], a["year"],
                 a["keywords"], a["abstract"], a["content"], a.get("url", ""))
            )
            inserted += 1

    conn.commit()
    conn.close()
    return inserted


def clear_articles():
    """Remove all articles from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM articles")
    conn.commit()
    conn.close()
    print("✔ Cleared existing articles.")


# ─────────────────────────────────────────────
# Main seeding function
# ─────────────────────────────────────────────
def seed_from_semantic_scholar(topics: list[str] = None, papers_per_topic: int = 20,
                                api_key: str = None, clear_first: bool = False):
    """
    Fetch papers from Semantic Scholar for each topic and insert into the DB.

    Args:
        topics           : list of search topics (uses DEFAULT_TOPICS if None)
        papers_per_topic : how many papers to fetch per topic
        api_key           : optional Semantic Scholar API key (raises rate limit)
        clear_first       : if True, wipe existing articles before seeding
    """
    if topics is None:
        topics = DEFAULT_TOPICS

    if clear_first:
        clear_articles()

    print(f"\n{'='*55}")
    print(f"  Seeding from Semantic Scholar API")
    print(f"  Topics: {len(topics)}  |  Papers/topic: {papers_per_topic}")
    print(f"{'='*55}\n")

    total_inserted = 0

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] Fetching: '{topic}'")
        papers = fetch_papers(topic, limit=papers_per_topic, api_key=api_key)
        n = insert_articles(papers)
        total_inserted += n
        print(f"        → Fetched {len(papers)}, inserted {n} new\n")

        # Respect rate limit: 100 requests / 5 min without a key (~3.5s gap is safe)
        if i < len(topics):
            time.sleep(1.2 if api_key else 3.5)

    print(f"✔ Done. Total new articles inserted: {total_inserted}")

    conn  = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()
    print(f"  Total articles now in DB: {total}")
    print(f"  Database: {DB_PATH}\n")
    return total_inserted


# ─────────────────────────────────────────────
# Run directly to seed the DB
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    clear   = "--clear" in sys.argv
    topics  = None
    api_key = None

    if "--topics" in sys.argv:
        idx    = sys.argv.index("--topics")
        topics = [t.strip() for t in sys.argv[idx + 1].split(",")]
        print(f"Custom topics: {topics}")

    # First plain (non-flag) argument is treated as the API key
    plain_args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in (topics or [])]
    if plain_args:
        api_key = plain_args[0]
        print(f"Using API key: {api_key[:8]}…")
    else:
        print("No API key provided. Using public rate limit (slower).")
        print("Get a free key at: https://www.semanticscholar.org/product/api\n")

    seed_from_semantic_scholar(topics=topics, papers_per_topic=20, api_key=api_key, clear_first=clear)
