"""Advanced Job Recommendation Engine v2.

Improvements over v1:
- Semantic skill/title matching with TF-IDF embeddings
- LLM-powered resume parsing (with regex fallback)
- Dynamic weight adjustment based on profile
- Profile enrichment and skill inference
- Job deduplication
- Live web job search (optional)
- Caching layer
- Natural language match explanations
- Config-driven architecture
"""
import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Optional dependencies
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


@dataclass
class UserProfile:
    """User profile extracted from resume."""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: List[str] = None
    experience_years: float = 0.0
    education: List[str] = None
    job_titles: List[str] = None
    locations_preferred: List[str] = None
    remote_preference: str = "any"
    salary_min: int = 0
    salary_max: int = 0
    employment_types: List[str] = None
    industries: List[str] = None
    _inferred_skills: List[str] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.education is None:
            self.education = []
        if self.job_titles is None:
            self.job_titles = []
        if self.locations_preferred is None:
            self.locations_preferred = []
        if self.employment_types is None:
            self.employment_types = ["full-time", "internship"]
        if self.industries is None:
            self.industries = []
        if self._inferred_skills is None:
            self._inferred_skills = []


@dataclass
class JobMatch:
    """A job with its match score and breakdown."""
    job: Dict
    overall_score: float = 0.0
    skill_match_score: float = 0.0
    title_match_score: float = 0.0
    experience_match_score: float = 0.0
    location_match_score: float = 0.0
    salary_match_score: float = 0.0
    type_match_score: float = 0.0
    match_reasons: List[str] = None
    explanation: str = ""

    def __post_init__(self):
        if self.match_reasons is None:
            self.match_reasons = []

    def to_dict(self) -> Dict:
        return {
            "job": self.job,
            "overall_score": round(self.overall_score, 2),
            "skill_match": round(self.skill_match_score, 2),
            "title_match": round(self.title_match_score, 2),
            "experience_match": round(self.experience_match_score, 2),
            "location_match": round(self.location_match_score, 2),
            "salary_match": round(self.salary_match_score, 2),
            "type_match": round(self.type_match_score, 2),
            "reasons": self.match_reasons,
            "explanation": self.explanation,
        }


class ResumeParser:
    """Parse resume files (PDF, DOCX, TXT) to extract text."""

    TECH_SKILLS = {
        "python", "javascript", "js", "typescript", "ts", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql",
        "react", "vue", "angular", "svelte", "next.js", "nuxt", "django", "flask",
        "fastapi", "spring", "express", "rails", "laravel", "nodejs", "node.js",
        "html", "css", "sass", "less", "tailwind", "bootstrap",
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "github actions", "gitlab ci", "circleci",
        "mongodb", "postgresql", "postgres", "mysql", "sqlite", "redis", "elasticsearch",
        "dynamodb", "cassandra", "neo4j", "firebase", "supabase",
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
        "matplotlib", "seaborn", "plotly", "tableau", "powerbi",
        "machine learning", "deep learning", "nlp", "computer vision", "data science",
        "data engineering", "mlops", "ai", "artificial intelligence",
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "linux", "ubuntu", "centos", "bash", "shell", "powershell",
        "rest api", "graphql", "grpc", "websocket", "oauth", "jwt",
        "agile", "scrum", "kanban", "ci/cd", "devops", "sre",
    }

    JOB_TITLES = {
        "software engineer", "software developer", "full stack", "fullstack", "frontend",
        "backend", "devops engineer", "data engineer", "data scientist", "ml engineer",
        "site reliability engineer", "sre", "cloud engineer", "security engineer",
        "mobile developer", "ios developer", "android developer", "web developer",
        "react developer", "python developer", "java developer", "javascript developer",
        "intern", "software intern", "engineering intern", "research intern",
        "junior", "senior", "lead", "principal", "staff engineer",
    }

    EDUCATION_KEYWORDS = {
        "bachelor", "bs", "b.s.", "btech", "b.tech", "be", "b.e.",
        "master", "ms", "m.s.", "mtech", "m.tech", "me", "m.e.",
        "phd", "ph.d", "doctorate",
        "computer science", "cs", "software engineering", "information technology",
        "data science", "artificial intelligence", "mathematics", "statistics",
    }

    def __init__(self):
        self.profile = UserProfile()

    def parse_file(self, filepath: str) -> UserProfile:
        path = Path(filepath)
        text = ""

        if path.suffix.lower() == ".pdf":
            text = self._parse_pdf(path)
        elif path.suffix.lower() == ".docx":
            text = self._parse_docx(path)
        elif path.suffix.lower() in [".txt", ".md"]:
            text = path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return self._extract_profile(text)

    def parse_text(self, text: str) -> UserProfile:
        return self._extract_profile(text)

    def _parse_pdf(self, path: Path) -> str:
        if not HAS_PDF:
            raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _parse_docx(self, path: Path) -> str:
        if not HAS_DOCX:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
        doc = docx.Document(path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _extract_profile(self, text: str) -> UserProfile:
        text_lower = text.lower()
        self.profile = UserProfile()

        found_skills = []
        for skill in self.TECH_SKILLS:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        self.profile.skills = list(set(found_skills))

        found_titles = []
        for title in self.JOB_TITLES:
            pattern = r'\b' + re.escape(title) + r'\b'
            if re.search(pattern, text_lower):
                found_titles.append(title)
        self.profile.job_titles = list(set(found_titles))

        found_edu = []
        for edu in self.EDUCATION_KEYWORDS:
            pattern = r'\b' + re.escape(edu) + r'\b'
            if re.search(pattern, text_lower):
                found_edu.append(edu)
        self.profile.education = list(set(found_edu))

        exp_patterns = [
            r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
            r"(\d+)\+?\s*yrs?\s*(?:of\s*)?exp",
            r"experience[\s:]*(\d+)\+?\s*years?",
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.profile.experience_years = float(match.group(1))
                break

        email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", text)
        if email_match:
            self.profile.email = email_match.group(0)

        phone_match = re.search(r"[\+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4}", text)
        if phone_match:
            self.profile.phone = phone_match.group(0)

        if "remote" in text_lower:
            if "prefer remote" in text_lower or "looking for remote" in text_lower:
                self.profile.remote_preference = "remote"
            elif "hybrid" in text_lower:
                self.profile.remote_preference = "hybrid"

        if "intern" in text_lower or "internship" in text_lower:
            self.profile.employment_types = ["internship"]
        elif "full-time" in text_lower or "full time" in text_lower:
            self.profile.employment_types = ["full-time"]

        return self.profile


class RecommendationEngine:
    """Advanced job recommendation engine."""

    def __init__(self, config_path: str = None, db_path: str = None):
        from recommendation.config import Config
        from recommendation.cache_manager import CacheManager
        from recommendation.semantic_matcher import SemanticMatcher
        from recommendation.deduplicator import JobDeduplicator

        self.config = Config.from_file(config_path) if config_path else Config()

        # Allow explicit db_path override (backward compat with v1)
        if db_path:
            self.config.db_path = db_path

        self.db_path = self.config.db_path
        self.cache = CacheManager(self.config.cache_path)
        self.semantic = SemanticMatcher(self.config.embedding_model, self.cache)
        self.deduplicator = JobDeduplicator(self.config.dedup_threshold)
        self.parser = ResumeParser()
        self.profile = None

        # Try to init LLM parser (only if configured)
        self.llm_parser = None
        if self.config.use_llm_parsing and self.config.llm_api_key:
            try:
                from recommendation.llm_parser import LLMResumeParser
                self.llm_parser = LLMResumeParser(
                    self.config.llm_provider,
                    self.config.llm_model,
                    self.config.llm_api_key
                )
            except Exception:
                pass

        # Try to init web searcher (only if configured)
        self.web_searcher = None
        if self.config.enable_web_search:
            try:
                from recommendation.web_searcher import WebJobSearcher
                self.web_searcher = WebJobSearcher(max_results=self.config.max_web_jobs)
            except Exception:
                pass

    def load_resume(self, filepath: str) -> UserProfile:
        """Load and parse resume with caching and LLM enhancement."""
        filepath = str(Path(filepath).resolve())

        # Check cache
        cached = self.cache.get_profile(filepath)
        if cached:
            # Filter out internal fields that aren't part of UserProfile constructor
            clean = {k: v for k, v in cached.items() if not k.startswith('_')}
            self.profile = UserProfile(**clean)
            if '_inferred_skills' in cached:
                self.profile._inferred_skills = cached['_inferred_skills']
            print(f"[Resume] Loaded cached profile for {self.profile.email}")
            return self.profile

        # Parse with regex fallback
        fallback = self.parser.parse_file(filepath)

        # Try LLM enhancement
        if self.llm_parser:
            try:
                text = Path(filepath).read_text() if Path(filepath).suffix in [".txt", ".md"] else ""
                if not text and HAS_PDF and Path(filepath).suffix == ".pdf":
                    import PyPDF2
                    with open(filepath, "rb") as f:
                        text = "\n".join(p.extract_text() or "" for p in PyPDF2.PdfReader(f).pages)

                if text:
                    llm_result = self.llm_parser.parse(text)
                    if llm_result:
                        self.profile = self.llm_parser.merge_with_fallback(llm_result, fallback)
                        print("[Resume] Enhanced with LLM parsing")
                    else:
                        self.profile = fallback
                else:
                    self.profile = fallback
            except Exception as e:
                print(f"[Resume] LLM parsing failed, using fallback: {e}")
                self.profile = fallback
        else:
            self.profile = fallback

        # Enrich profile with inferred skills
        from recommendation.enricher import ProfileEnricher
        self.profile = ProfileEnricher.enrich_profile(self.profile)

        # Cache
        self.cache.save_profile(filepath, self.profile)

        print(f"\n[Resume] Loaded profile for {self.profile.email or 'Unknown'}")
        print(f"[Resume] Skills: {len(self.profile.skills)} ({len(self.profile._inferred_skills)} inferred)")
        print(f"[Resume] Experience: {self.profile.experience_years} years")
        print(f"[Resume] Types: {', '.join(self.profile.employment_types)}")
        return self.profile

    def load_profile_text(self, text: str) -> UserProfile:
        """Load profile from raw text."""
        fallback = self.parser.parse_text(text)

        if self.llm_parser:
            try:
                llm_result = self.llm_parser.parse(text)
                if llm_result:
                    from recommendation.llm_parser import LLMResumeParser
                    self.profile = LLMResumeParser.merge_with_fallback(llm_result, fallback)
                else:
                    self.profile = fallback
            except Exception:
                self.profile = fallback
        else:
            self.profile = fallback

        from recommendation.enricher import ProfileEnricher
        self.profile = ProfileEnricher.enrich_profile(self.profile)

        print(f"\n[Profile] Skills: {len(self.profile.skills)} ({len(self.profile._inferred_skills)} inferred)")
        print(f"[Profile] Experience: {self.profile.experience_years} years")
        return self.profile

    def set_profile(self, profile: UserProfile):
        """Set profile manually (programmatic usage).

        Also applies enrichment if the profile hasn't been enriched yet.
        """
        self.profile = profile
        # Enrich if not already enriched
        if not self.profile._inferred_skills:
            from recommendation.enricher import ProfileEnricher
            self.profile = ProfileEnricher.enrich_profile(self.profile)

    def recommend_jobs(self, limit: int = None, min_score: float = None) -> List[JobMatch]:
        """Get top job recommendations."""
        if not self.profile:
            raise ValueError("No profile loaded.")

        limit = limit or self.config.default_limit
        min_score = min_score if min_score is not None else self.config.default_min_score

        # Get jobs from DB + web
        jobs = self._fetch_jobs()
        print(f"\n[Recommend] Matching against {len(jobs)} jobs...")

        # Deduplicate
        jobs = self.deduplicator.deduplicate(jobs)
        print(f"[Recommend] {len(jobs)} unique jobs after deduplication")

        # Score each job
        matches = []
        for job in jobs:
            match = self._score_job(job)
            if match.overall_score >= min_score:
                matches.append(match)

        # Sort priority (lower = higher priority):
        #   1. Internshala jobs (guaranteed India-based internships) — listed first
        #   2. Other India internships
        #   3. India full-time/other roles
        #   4. Non-India internships
        #   5. Everything else
        # Within each group, sort by overall score descending.
        def _priority_sort_key(match: JobMatch) -> Tuple:
            job = match.job
            job_location = (job.get("location") or "").lower()
            job_type = (job.get("employment_type") or "").lower()
            job_title = (job.get("title") or "").lower()
            source = (job.get("source_platform") or "").lower()

            is_internshala = source == "internshala"
            is_india = is_internshala or any(kw in job_location for kw in self.INDIA_LOCATIONS)
            is_internship = ("intern" in job_type) or ("intern" in job_title) or is_internshala

            # Tier ordering — lower numbers come first
            if is_internshala:
                tier = 0
            elif is_india and is_internship:
                tier = 1
            elif is_india:
                tier = 2
            elif is_internship:
                tier = 3
            else:
                tier = 4

            return (tier, -match.overall_score)

        matches.sort(key=_priority_sort_key)

        print(f"[Recommend] Found {len(matches)} matches above threshold {min_score}")

        return matches[:limit]

    # India location keywords for SQL-level filtering
    INDIA_LOCATIONS = [
        "india", "bangalore", "bengaluru", "chennai", "hyderabad",
        "pune", "mumbai", "delhi", "noida", "gurgaon", "gurugram",
        "kolkata", "ahmedabad", "jaipur", "kochi", "coimbatore",
        "indore", "nagpur", "lucknow", "chandigarh", "remote",
    ]

    def _fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from database — Internshala first, then India/remote, then others.

        3-tier priority:
          Tier 1: Internshala jobs (guaranteed India-based internships) — up to 400
          Tier 2: Other India/remote jobs matched by location — up to 200
          Tier 3: Remaining jobs from other regions — up to 100
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        keywords = []
        if self.profile:
            keywords.extend(self.profile.skills[:10])
            keywords.extend(self.profile.job_titles[:6])
        keywords = list({k.strip().lower() for k in keywords if k.strip()})

        # Build keyword filter clause
        kw_clause = ""
        kw_params = []
        if keywords:
            like_clauses = []
            for kw in keywords:
                like_clauses.append("(title LIKE ? OR description LIKE ? OR requirements LIKE ?)")
                kw_params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            kw_clause = " AND (" + " OR ".join(like_clauses) + ")"

        # Build India/remote location clause
        loc_clauses = []
        loc_params = []
        for loc in self.INDIA_LOCATIONS:
            loc_clauses.append("location LIKE ?")
            loc_params.append(f"%{loc}%")
        loc_filter = " OR ".join(loc_clauses)

        seen_ids = set()
        db_jobs = []

        try:
            # ── Tier 1: Internshala jobs (India internships by definition) ──
            # No keyword filter — all Internshala jobs are India internships and relevant.
            # High limit because many share URLs and will be deduped.
            internshala_query = (
                f"SELECT * FROM jobs WHERE is_active = 1"
                f" AND source_platform = 'internshala'"
                f" ORDER BY posted_date DESC LIMIT 600"
            )
            cursor.execute(internshala_query)
            internshala_jobs = [dict(row) for row in cursor.fetchall()]
            for j in internshala_jobs:
                seen_ids.add(j.get("job_id", j.get("id")))

            # ── Tier 2: Other India/remote jobs (not already from Internshala) ──
            india_query = (
                f"SELECT * FROM jobs WHERE is_active = 1{kw_clause}"
                f" AND source_platform != 'internshala'"
                f" AND ({loc_filter})"
                f" ORDER BY posted_date DESC LIMIT 200"
            )
            cursor.execute(india_query, kw_params + loc_params)
            india_jobs = [dict(row) for row in cursor.fetchall()
                          if (row["job_id"] or row["id"]) not in seen_ids]
            for j in india_jobs:
                seen_ids.add(j.get("job_id", j.get("id")))

            # ── Tier 3: Fill remaining with non-India jobs ──
            fetched = len(internshala_jobs) + len(india_jobs)
            remaining = max(0, 700 - fetched)
            if remaining > 0:
                other_query = (
                    f"SELECT * FROM jobs WHERE is_active = 1{kw_clause}"
                    f" AND source_platform != 'internshala'"
                    f" AND NOT ({loc_filter})"
                    f" ORDER BY posted_date DESC LIMIT {remaining}"
                )
                cursor.execute(other_query, kw_params + loc_params)
                other_jobs = [dict(row) for row in cursor.fetchall()
                              if (row["job_id"] or row["id"]) not in seen_ids]
            else:
                other_jobs = []

            # Internshala first → India/remote → rest
            db_jobs = internshala_jobs + india_jobs + other_jobs
            print(f"[DB] Fetched {len(internshala_jobs)} Internshala"
                  f" + {len(india_jobs)} India/remote"
                  f" + {len(other_jobs)} other = {len(db_jobs)} total")

        except sqlite3.OperationalError as e:
            print(f"[DB] Warning: {e}")
            # Fallback: simple query without location priority
            try:
                fallback = (
                    f"SELECT * FROM jobs WHERE is_active = 1{kw_clause}"
                    f" ORDER BY CASE WHEN source_platform = 'internshala' THEN 0 ELSE 1 END,"
                    f" posted_date DESC LIMIT 700"
                )
                cursor.execute(fallback, kw_params)
                db_jobs = [dict(row) for row in cursor.fetchall()]
            except Exception:
                pass

        conn.close()

        # Fetch web jobs (only if enabled)
        web_jobs = []
        if self.web_searcher:
            try:
                web_jobs = self.web_searcher.search_by_profile(self.profile, max_results=self.config.max_web_jobs)
                for job in web_jobs:
                    self.cache.save_job(job.get("id", ""), job, job.get("source", "web"))
            except Exception as e:
                print(f"[Web] Search error: {e}")

        return db_jobs + web_jobs

    def _score_job(self, job: Dict) -> JobMatch:
        """Calculate comprehensive match scores."""
        match = JobMatch(job=job)
        weights = self.config.get_dynamic_weights(self.profile)

        # Semantic skill matching
        if self.config.use_semantic_matching:
            job_text = "{} {} {}".format(
                job.get('title', ''),
                job.get('description', ''),
                job.get('requirements', '')
            )
            match.skill_match_score, matched_skills = self.semantic.match_skills_semantic(
                self.profile.skills, job_text
            )
        else:
            match.skill_match_score = self._score_skills(job)
            matched_skills = []

        # Semantic title matching
        if self.config.use_semantic_matching and self.profile.job_titles:
            match.title_match_score = self.semantic.match_title_semantic(
                self.profile.job_titles, job.get("title", "")
            )
        else:
            match.title_match_score = self._score_title(job)

        match.experience_match_score = self._score_experience(job)
        match.location_match_score = self._score_location(job)
        match.salary_match_score = self._score_salary(job)
        match.type_match_score = self._score_type(job)

        match.overall_score = (
            match.skill_match_score * weights["skills"] +
            match.title_match_score * weights["title"] +
            match.experience_match_score * weights["experience"] +
            match.location_match_score * weights["location"] +
            match.salary_match_score * weights["salary"] +
            match.type_match_score * weights["type"]
        )

        match.match_reasons = self._generate_reasons(match, matched_skills)
        match.explanation = self._generate_explanation(match, matched_skills)

        return match

    def _score_skills(self, job: Dict) -> float:
        if not self.profile.skills:
            return 0.5
        job_text = "{} {} {}".format(
            job.get('title', ''),
            job.get('description', ''),
            job.get('requirements', '')
        ).lower()
        matched = [s for s in self.profile.skills if s.lower() in job_text]
        if not matched:
            return 0.0
        ratio = len(matched) / len(self.profile.skills)
        return min(1.0, ratio * 1.5)

    def _score_title(self, job: Dict) -> float:
        job_title = job.get("title", "").lower()
        if not self.profile.job_titles:
            return 0.5
        for title in self.profile.job_titles:
            if title.lower() in job_title:
                return 1.0
        for title in self.profile.job_titles:
            words = title.lower().split()
            matches = sum(1 for word in words if word in job_title)
            if matches >= len(words) * 0.5:
                return 0.6
        return 0.1

    def _score_experience(self, job: Dict) -> float:
        job_title = job.get("title", "").lower()
        is_senior = any(w in job_title for w in ["senior", "lead", "principal", "staff"])
        is_junior = any(w in job_title for w in ["junior", "entry", "associate", "intern"])
        user_exp = self.profile.experience_years

        if user_exp >= 5 and is_senior:
            return 1.0
        elif user_exp >= 5 and is_junior:
            return 0.3
        elif user_exp < 2 and is_junior:
            return 1.0
        elif user_exp < 2 and is_senior:
            return 0.2
        elif 2 <= user_exp < 5 and not is_senior and not is_junior:
            return 0.9
        else:
            return 0.5

    def _score_location(self, job: Dict) -> float:
        """Score based on location preference — India locations get priority."""
        job_location = job.get("location", "").lower()

        # Indian cities / regions for boosted matching
        india_keywords = [
            "india", "bangalore", "bengaluru", "chennai", "hyderabad",
            "pune", "mumbai", "delhi", "noida", "gurgaon", "gurugram",
            "kolkata", "ahmedabad", "jaipur", "kochi", "thiruvananthapuram",
            "coimbatore", "indore", "nagpur", "lucknow", "chandigarh",
        ]

        # 1. Check preferred locations first (highest priority)
        if self.profile.locations_preferred:
            for loc in self.profile.locations_preferred:
                if loc.lower() in job_location:
                    return 1.0

        # 2. Check if job is in India (boost even if not explicitly in preferred list)
        is_india = any(kw in job_location for kw in india_keywords)
        if is_india:
            return 1.0

        # 3. Remote/worldwide jobs are acceptable
        is_remote = any(w in job_location for w in ["remote", "worldwide", "anywhere", "work from home"])
        if is_remote:
            if self.profile.remote_preference == "remote":
                return 1.0
            return 0.7  # Remote is okay but India is preferred

        # 4. Hybrid preference
        if self.profile.remote_preference == "hybrid":
            if "hybrid" in job_location:
                return 0.8

        # 5. Jobs outside India with no remote option
        return 0.15  # Penalize non-India, non-remote jobs

    def _score_salary(self, job: Dict) -> float:
        job_min = job.get("salary_min", 0)
        job_max = job.get("salary_max", 0)
        if not job_min and not job_max:
            return 0.5
        user_min = self.profile.salary_min
        if not user_min:
            return 0.5
        if job_min and int(job_min) >= int(user_min):
            return 1.0
        elif job_min and int(job_min) >= int(user_min) * 0.8:
            return 0.7
        return 0.3

    def _score_type(self, job: Dict) -> float:
        job_type = (job.get("employment_type") or "").lower().strip()
        if not job_type:
            return 0.7
        if not self.profile.employment_types:
            return 0.7
        for preferred in self.profile.employment_types:
            if preferred.lower() in job_type or job_type in preferred.lower():
                return 1.0
        if "intern" in job_type and "internship" in self.profile.employment_types:
            return 1.0
        if ("full" in job_type or "permanent" in job_type) and "full-time" in self.profile.employment_types:
            return 1.0
        return 0.3

    def _generate_reasons(self, match: JobMatch, matched_skills: List[str]) -> List[str]:
        reasons = []
        job = match.job

        if match.skill_match_score >= 0.7:
            reasons.append(f"Strong skill match ({int(match.skill_match_score * 100)}%)")
        elif match.skill_match_score >= 0.4:
            reasons.append("Good skill overlap")

        if matched_skills[:3]:
            reasons.append("Skills: {}".format(", ".join(matched_skills[:3])))

        if match.title_match_score >= 0.6:
            reasons.append("Title aligns with your experience")

        if match.experience_match_score >= 0.8:
            reasons.append("Experience level is a great fit")
        elif match.experience_match_score <= 0.3:
            reasons.append("Experience level may not match")

        if match.location_match_score >= 0.8:
            reasons.append("Matches your location preference")

        if match.salary_match_score >= 0.8:
            reasons.append("Salary meets your expectations")

        if match.type_match_score >= 0.8:
            reasons.append("Matches preferred type ({})".format(job.get('employment_type', '')))

        if not reasons:
            reasons.append("General match based on your profile")

        return reasons

    def _generate_explanation(self, match: JobMatch, matched_skills: List[str]) -> str:
        """Generate natural language explanation."""
        job = match.job
        parts = []

        # Title fit
        if match.title_match_score >= 0.8:
            parts.append("The {} title closely matches your previous positions.".format(
                job.get('title', 'role')))
        elif match.title_match_score >= 0.4:
            parts.append("The {} title is somewhat related to your background.".format(
                job.get('title', 'role')))

        # Skills
        if matched_skills:
            top = ", ".join(matched_skills[:4])
            parts.append("Your profile shows expertise in {}, which are key for this role.".format(top))

        # Experience
        if match.experience_match_score >= 0.8:
            parts.append("Your experience level is an ideal fit.")
        elif match.experience_match_score <= 0.3:
            parts.append("Note: the required experience level may differ from your background.")

        # Location
        if match.location_match_score >= 0.8:
            loc = job.get("location", "this location")
            parts.append("The {} location matches your preferences.".format(loc))

        # Salary
        if match.salary_match_score >= 0.8:
            parts.append("The compensation aligns with your expectations.")

        return " ".join(parts) if parts else "This job matches your profile based on overall compatibility."

    def save_profile(self, filepath: str = "profile.json"):
        if not self.profile:
            raise ValueError("No profile loaded")
        with open(filepath, "w") as f:
            json.dump(asdict(self.profile), f, indent=2)
        print(f"[Profile] Saved to {filepath}")

    def load_saved_profile(self, filepath: str = "profile.json"):
        with open(filepath, "r") as f:
            data = json.load(f)
        # Filter out internal fields
        clean = {k: v for k, v in data.items() if not k.startswith('_')}
        self.profile = UserProfile(**clean)
        if '_inferred_skills' in data:
            self.profile._inferred_skills = data['_inferred_skills']
        print(f"[Profile] Loaded from {filepath}")
        return self.profile

    def clear_cache(self):
        """Clear all caches."""
        self.cache.clear_expired(days=0)
        print("[Cache] Cleared all cached data")
