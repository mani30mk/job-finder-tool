"""Job Recommendation Engine — matches jobs to user profile/resume.

Features:
- Resume parsing (PDF, DOCX, TXT)
- Skill extraction and matching
- Experience level matching
- Location preference matching
- Salary alignment
- Personalized ranking score

Usage:
    from recommendation.engine import RecommendationEngine

    engine = RecommendationEngine()
    engine.load_resume("path/to/resume.pdf")
    recommendations = engine.recommend_jobs(limit=20)
"""
import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Try to import optional dependencies
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
    remote_preference: str = "any"  # remote, onsite, hybrid, any
    salary_min: int = 0
    salary_max: int = 0
    employment_types: List[str] = None  # full-time, part-time, contract, internship
    industries: List[str] = None

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
        }


class ResumeParser:
    """Parse resume files (PDF, DOCX, TXT) to extract text."""

    # Common tech skills to detect
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

    # Job title keywords
    JOB_TITLES = {
        "software engineer", "software developer", "full stack", "fullstack", "frontend",
        "backend", "devops engineer", "data engineer", "data scientist", "ml engineer",
        "site reliability engineer", "sre", "cloud engineer", "security engineer",
        "mobile developer", "ios developer", "android developer", "web developer",
        "react developer", "python developer", "java developer", "javascript developer",
        "intern", "software intern", "engineering intern", "research intern",
        "junior", "senior", "lead", "principal", "staff engineer",
    }

    # Education keywords
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
        """Parse a resume file and extract profile."""
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
        """Parse raw text (paste resume content directly)."""
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
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    def _extract_profile(self, text: str) -> UserProfile:
        """Extract structured profile from resume text."""
        text_lower = text.lower()

        # Extract skills
        found_skills = []
        for skill in self.TECH_SKILLS:
            # Match whole words only
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        self.profile.skills = list(set(found_skills))

        # Extract job titles
        found_titles = []
        for title in self.JOB_TITLES:
            pattern = r'\b' + re.escape(title) + r'\b'
            if re.search(pattern, text_lower):
                found_titles.append(title)
        self.profile.job_titles = list(set(found_titles))

        # Extract education
        found_edu = []
        for edu in self.EDUCATION_KEYWORDS:
            pattern = r'\b' + re.escape(edu) + r'\b'
            if re.search(pattern, text_lower):
                found_edu.append(edu)
        self.profile.education = list(set(found_edu))

        # Extract experience years (look for patterns like "3 years", "5+ years")
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?exp',
            r'experience[\s:]*(\d+)\+?\s*years?',
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.profile.experience_years = float(match.group(1))
                break

        # Extract email
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
        if email_match:
            self.profile.email = email_match.group(0)

        # Extract phone
        phone_match = re.search(r'[\+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4}', text)
        if phone_match:
            self.profile.phone = phone_match.group(0)

        # Detect remote preference
        if "remote" in text_lower:
            if "prefer remote" in text_lower or "looking for remote" in text_lower:
                self.profile.remote_preference = "remote"
            elif "hybrid" in text_lower:
                self.profile.remote_preference = "hybrid"

        # Detect employment type preference
        if "intern" in text_lower or "internship" in text_lower:
            self.profile.employment_types = ["internship"]
        elif "full-time" in text_lower or "full time" in text_lower:
            self.profile.employment_types = ["full-time"]

        return self.profile


class RecommendationEngine:
    """Match jobs to user profile and generate recommendations."""

    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self.profile = None
        self.parser = ResumeParser()

        # Scoring weights (adjustable)
        self.weights = {
            "skills": 0.35,
            "title": 0.20,
            "experience": 0.15,
            "location": 0.10,
            "salary": 0.10,
            "type": 0.10,
        }

    def load_resume(self, filepath: str) -> UserProfile:
        """Load and parse resume file."""
        self.profile = self.parser.parse_file(filepath)
        print(f"\n[Resume] Loaded profile for {self.profile.email}")
        print(f"[Resume] Skills found: {', '.join(self.profile.skills[:10])}...")
        print(f"[Resume] Experience: {self.profile.experience_years} years")
        print(f"[Resume] Preferred types: {', '.join(self.profile.employment_types)}")
        return self.profile

    def load_profile_text(self, text: str) -> UserProfile:
        """Load profile from raw text (no file needed)."""
        self.profile = self.parser.parse_text(text)
        print(f"\n[Profile] Skills found: {', '.join(self.profile.skills[:10])}...")
        print(f"[Profile] Experience: {self.profile.experience_years} years")
        return self.profile

    def set_profile(self, profile: UserProfile):
        """Set profile manually (programmatic usage)."""
        self.profile = profile

    def recommend_jobs(self, limit: int = 20, min_score: float = 0.1) -> List[JobMatch]:
        """Get top job recommendations for the loaded profile."""
        if not self.profile:
            raise ValueError("No profile loaded. Call load_resume() or set_profile() first.")

        # Fetch jobs from database
        jobs = self._fetch_jobs()
        print(f"\n[Recommend] Matching against {len(jobs)} jobs...")

        # Score each job
        matches = []
        for job in jobs:
            match = self._score_job(job)
            if match.overall_score >= min_score:
                matches.append(match)

        # Sort by overall score descending
        matches.sort(key=lambda x: x.overall_score, reverse=True)

        print(f"[Recommend] Found {len(matches)} matches above threshold {min_score}")

        return matches[:limit]

    def _fetch_jobs(self) -> List[Dict]:
        """Fetch active jobs from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM jobs 
            WHERE is_active = 1 
            ORDER BY posted_date DESC 
            LIMIT 1000
        """)

        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs

    def _score_job(self, job: Dict) -> JobMatch:
        """Calculate match scores for a single job."""
        match = JobMatch(job=job)

        # 1. Skill match (35%)
        match.skill_match_score = self._score_skills(job)

        # 2. Title match (20%)
        match.title_match_score = self._score_title(job)

        # 3. Experience match (15%)
        match.experience_match_score = self._score_experience(job)

        # 4. Location match (10%)
        match.location_match_score = self._score_location(job)

        # 5. Salary match (10%)
        match.salary_match_score = self._score_salary(job)

        # 6. Employment type match (10%)
        match.type_match_score = self._score_type(job)

        # Calculate overall weighted score
        match.overall_score = (
            match.skill_match_score * self.weights["skills"] +
            match.title_match_score * self.weights["title"] +
            match.experience_match_score * self.weights["experience"] +
            match.location_match_score * self.weights["location"] +
            match.salary_match_score * self.weights["salary"] +
            match.type_match_score * self.weights["type"]
        )

        # Generate human-readable reasons
        match.match_reasons = self._generate_reasons(match)

        return match

    def _score_skills(self, job: Dict) -> float:
        """Score based on skill overlap."""
        if not self.profile.skills:
            return 0.5  # Neutral if no skills extracted

        job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}".lower()

        matched_skills = []
        for skill in self.profile.skills:
            if skill.lower() in job_text:
                matched_skills.append(skill)

        if not matched_skills:
            return 0.0

        # Score = matched / total skills, with diminishing returns
        ratio = len(matched_skills) / len(self.profile.skills)
        score = min(1.0, ratio * 1.5)  # Boost slightly

        return score

    def _score_title(self, job: Dict) -> float:
        """Score based on job title similarity."""
        job_title = job.get("title", "").lower()

        if not self.profile.job_titles:
            return 0.5

        for title in self.profile.job_titles:
            if title.lower() in job_title:
                return 1.0

        # Partial match
        for title in self.profile.job_titles:
            words = title.lower().split()
            matches = sum(1 for word in words if word in job_title)
            if matches >= len(words) * 0.5:
                return 0.6

        return 0.1

    def _score_experience(self, job: Dict) -> float:
        """Score based on experience level alignment."""
        job_title = job.get("title", "").lower()
        description = job.get("description", "").lower()

        # Detect seniority from job
        is_senior = any(word in job_title for word in ["senior", "lead", "principal", "staff"])
        is_junior = any(word in job_title for word in ["junior", "entry", "associate", "intern"])

        user_exp = self.profile.experience_years

        if user_exp >= 5 and is_senior:
            return 1.0
        elif user_exp >= 5 and is_junior:
            return 0.3  # Overqualified
        elif user_exp < 2 and is_junior:
            return 1.0
        elif user_exp < 2 and is_senior:
            return 0.2  # Underqualified
        elif 2 <= user_exp < 5 and not is_senior and not is_junior:
            return 0.9  # Mid-level, good fit
        else:
            return 0.5

    def _score_location(self, job: Dict) -> float:
        """Score based on location preference."""
        job_location = job.get("location", "").lower()

        # Remote preference
        if self.profile.remote_preference == "remote":
            if "remote" in job_location:
                return 1.0
            else:
                return 0.2
        elif self.profile.remote_preference == "hybrid":
            if "hybrid" in job_location or "remote" in job_location:
                return 1.0
            else:
                return 0.5

        # Check preferred locations
        if self.profile.locations_preferred:
            for loc in self.profile.locations_preferred:
                if loc.lower() in job_location:
                    return 1.0
            return 0.3

        return 0.7  # No preference, neutral

    def _score_salary(self, job: Dict) -> float:
        """Score based on salary alignment."""
        job_salary_min = job.get("salary_min", 0)
        job_salary_max = job.get("salary_max", 0)

        if not job_salary_min and not job_salary_max:
            return 0.5  # No salary info

        user_min = self.profile.salary_min
        user_max = self.profile.salary_max

        if not user_min and not user_max:
            return 0.5  # No preference

        # If job salary meets user's minimum
        if job_salary_min and user_min:
            if int(job_salary_min) >= int(user_min):
                return 1.0
            elif int(job_salary_min) >= int(user_min) * 0.8:
                return 0.7
            else:
                return 0.3

        return 0.5

    def _score_type(self, job: Dict) -> float:
        """Score based on employment type preference."""
        job_type = job.get("employment_type", "").lower()

        if not self.profile.employment_types:
            return 0.5

        for preferred in self.profile.employment_types:
            if preferred.lower() in job_type:
                return 1.0

        # Partial matches
        if "intern" in job_type and "internship" in self.profile.employment_types:
            return 1.0
        if "full-time" in job_type and "full-time" in self.profile.employment_types:
            return 1.0

        return 0.2

    def _generate_reasons(self, match: JobMatch) -> List[str]:
        """Generate human-readable match reasons."""
        reasons = []
        job = match.job

        if match.skill_match_score >= 0.7:
            reasons.append(f"Strong skill match ({int(match.skill_match_score * 100)}%)")
        elif match.skill_match_score >= 0.4:
            reasons.append(f"Good skill overlap")

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
            reasons.append(f"Matches your preferred type ({job.get('employment_type', '')})")

        if not reasons:
            reasons.append("General match based on your profile")

        return reasons

    def save_profile(self, filepath: str = "profile.json"):
        """Save extracted profile to JSON for reuse."""
        if not self.profile:
            raise ValueError("No profile loaded")

        with open(filepath, "w") as f:
            json.dump(asdict(self.profile), f, indent=2)
        print(f"[Profile] Saved to {filepath}")

    def load_saved_profile(self, filepath: str = "profile.json"):
        """Load profile from saved JSON."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self.profile = UserProfile(**data)
        print(f"[Profile] Loaded from {filepath}")
        return self.profile