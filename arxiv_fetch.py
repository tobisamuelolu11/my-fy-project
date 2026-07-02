"""
arxiv_fetch.py  –  Fetch real papers from the arXiv API
Docs: https://info.arxiv.org/help/api/index.html

No API key required. Free and open.
Rate limit: max 1 request every 3 seconds (politely enforced below).
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sqlite3
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'scholorfind.db')

ARXIV_API = "http://export.arxiv.org/api/query"
NS        = {"atom": "http://www.w3.org/2005/Atom",
             "arxiv": "http://arxiv.org/schemas/atom"}

# ── Topics to seed the database ─────────────────────────────────────────────
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
def fetch_papers(query: str, max_results: int = 20) -> list[dict]:
    """
    Query the arXiv API and return a list of cleaned article dicts.

    Args:
        query       : search term e.g. "deep learning NLP"
        max_results : how many papers to fetch (max 100 recommended)

    Returns:
        list of dicts with keys: title, authors, journal, year, keywords, abstract, content
    """
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start":        0,
        "max_results":  max_results,
        "sortBy":       "relevance",
        "sortOrder":    "descending",
    })
    url = f"{ARXIV_API}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Academia/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            xml_data = response.read().decode("utf-8")
    except Exception as e:
        print(f"  [!] Failed to fetch '{query}': {e}")
        return []

    return _parse_arxiv_xml(xml_data)


def _parse_arxiv_xml(xml_data: str) -> list[dict]:
    """Parse arXiv Atom XML and return list of article dicts."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"  [!] XML parse error: {e}")
        return []

    results = []

    for entry in root.findall("atom:entry", NS):
        # Title
        title_el = entry.find("atom:title", NS)
        title    = title_el.text.strip().replace("\n", " ") if title_el is not None else ""

        # Abstract
        summary_el = entry.find("atom:summary", NS)
        abstract   = summary_el.text.strip().replace("\n", " ") if summary_el is not None else ""

        # Authors (up to 4)
        author_els = entry.findall("atom:author", NS)
        authors    = "; ".join(
            a.find("atom:name", NS).text.strip()
            for a in author_els[:4]
            if a.find("atom:name", NS) is not None
        ) or "Unknown Authors"

        # Published year
        published_el = entry.find("atom:published", NS)
        year = 0
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except ValueError:
                year = 0

        # Journal / category (arXiv uses subject categories as venue)
        category_el = entry.find("arxiv:primary_category", NS)
        if category_el is not None:
            journal = _category_label(category_el.attrib.get("term", "arXiv"))
        else:
            journal = "arXiv Preprint"

        # Article URL — arXiv's <id> field is the abstract page link (e.g. http://arxiv.org/abs/2101.00001v1)
        id_el = entry.find("atom:id", NS)
        url   = id_el.text.strip() if id_el is not None and id_el.text else ""

        # Skip entries missing key content
        if not title or not abstract:
            continue

        keywords = _extract_keywords(title)
        content  = f"{title} {keywords} {abstract}"

        results.append({
            "title":    title,
            "authors":  authors,
            "journal":  journal,
            "year":     year,
            "keywords": keywords,
            "abstract": abstract[:1000],   # cap at 1000 chars
            "content":  content,
            "url":      url,
        })

    return results


def _category_label(term: str) -> str:
    """Map arXiv category codes to readable journal/field names."""
    mapping = {
        # Computer Science
        "cs.LG":  "Machine Learning",
        "cs.AI":  "Artificial Intelligence",
        "cs.CV":  "Computer Vision",
        "cs.CL":  "Computation & Language",
        "cs.CR":  "Cryptography & Security",
        "cs.DB":  "Databases",
        "cs.DC":  "Distributed Computing",
        "cs.IR":  "Information Retrieval",
        "cs.NE":  "Neural & Evolutionary Computing",
        "cs.SE":  "Software Engineering",
        "cs.RO":  "Robotics",
        "cs.HC":  "Human-Computer Interaction",
        # Physics
        "quant-ph": "Quantum Physics",
        "physics.med-ph": "Medical Physics",
        "physics.ao-ph": "Atmospheric & Oceanic Physics",
        "cond-mat.mtrl-sci": "Materials Science",
        "physics.flu-dyn": "Fluid Dynamics",
        # Mathematics
        "math.OC":  "Optimization & Control",
        "math.CO":  "Combinatorics",
        "math.ST":  "Statistics Theory",
        "math.NT":  "Number Theory",
        "math.NA":  "Numerical Analysis",
        # Biology & Life Sciences
        "q-bio.GN": "Genomics",
        "q-bio.NC": "Neurons & Cognition",
        "q-bio.PE": "Populations & Evolution",
        "q-bio.BM": "Biomolecules",
        "q-bio.CB": "Cell Behavior",
        # Statistics & ML
        "stat.ML": "Statistics - Machine Learning",
        "stat.AP": "Statistics - Applications",
        "stat.ME": "Statistics - Methodology",
        # Economics & Social Sciences
        "econ.GN": "Economics",
        "econ.EM": "Econometrics",
        "econ.TH": "Economic Theory",
        # Electrical Engineering
        "eess.SP": "Signal Processing",
        "eess.SY": "Systems & Control",
        "eess.IV": "Image & Video Processing",
        # Environmental & Earth Sciences
        "physics.geo-ph": "Geophysics",
        "physics.atm-clus": "Atmospheric Science",
    }
    return mapping.get(term, f"arXiv — {term}" if term else "arXiv Preprint")


def _extract_keywords(title: str) -> str:
    """Pull meaningful words from the title as pseudo-keywords."""
    stop = {"a","an","the","of","in","for","on","with","and","or","to","by",
            "from","using","based","via","towards","approach","study","analysis"}
    words = [w.strip(".,():[]") for w in title.lower().split()]
    return "; ".join(w for w in words if w and w not in stop and len(w) > 2)


# ─────────────────────────────────────────────
# Database helpers
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
def seed_from_arxiv(topics: list[str] = None, papers_per_topic: int = 20, clear_first: bool = False):
    """
    Fetch papers from arXiv for each topic and insert into the SQLite DB.

    Args:
        topics           : list of search topics (uses DEFAULT_TOPICS if None)
        papers_per_topic : papers to fetch per topic (max ~100)
        clear_first      : if True, wipe existing articles before seeding
    """
    if topics is None:
        topics = DEFAULT_TOPICS

    if clear_first:
        clear_articles()

    print(f"\n{'='*55}")
    print(f"  Seeding from arXiv API")
    print(f"  Topics: {len(topics)}  |  Papers/topic: {papers_per_topic}")
    print(f"{'='*55}\n")

    total_inserted = 0

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] Fetching: '{topic}'")
        papers = fetch_papers(topic, max_results=papers_per_topic)
        n      = insert_articles(papers)
        total_inserted += n
        print(f"        → Fetched {len(papers)}, inserted {n} new\n")

        # arXiv asks for 3 seconds between requests
        if i < len(topics):
            time.sleep(3)

    print(f"✔ Done. Total new articles inserted: {total_inserted}")

    # Show updated DB count
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

    # Optional flags:
    #   --clear   wipe DB before seeding
    #   --topics  comma-separated custom topics
    # Examples:
    #   python arxiv_fetch.py
    #   python arxiv_fetch.py --clear
    #   python arxiv_fetch.py --topics "federated learning,quantum computing,robotics"

    clear  = "--clear"  in sys.argv
    topics = None

    if "--topics" in sys.argv:
        idx    = sys.argv.index("--topics")
        topics = [t.strip() for t in sys.argv[idx + 1].split(",")]
        print(f"Custom topics: {topics}")

    seed_from_arxiv(topics=topics, papers_per_topic=20, clear_first=clear)
