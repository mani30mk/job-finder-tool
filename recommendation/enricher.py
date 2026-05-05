"""Profile enrichment and skill inference."""
from typing import List, Set, Dict


class ProfileEnricher:
    """Infer related skills and expand sparse profiles."""

    # Skill co-occurrence graph: if you have X, you likely know Y
    SKILL_INFERENCE = {
        "django": ["python", "web development", "rest api", "sql"],
        "flask": ["python", "web development", "rest api"],
        "fastapi": ["python", "web development", "rest api", "async"],
        "react": ["javascript", "frontend", "html", "css", "web development"],
        "vue": ["javascript", "frontend", "html", "css", "web development"],
        "angular": ["javascript", "typescript", "frontend", "html", "css"],
        "next.js": ["react", "javascript", "frontend", "ssr", "web development"],
        "tensorflow": ["python", "machine learning", "deep learning", "data science"],
        "pytorch": ["python", "machine learning", "deep learning", "data science"],
        "pandas": ["python", "data analysis", "data science", "sql"],
        "numpy": ["python", "data analysis", "scientific computing"],
        "scikit-learn": ["python", "machine learning", "data science"],
        "kubernetes": ["docker", "devops", "cloud", "ci/cd"],
        "docker": ["devops", "ci/cd", "linux"],
        "aws": ["cloud", "devops", "infrastructure"],
        "azure": ["cloud", "devops", "microsoft"],
        "gcp": ["cloud", "devops", "google cloud"],
        "terraform": ["devops", "infrastructure", "cloud", "iac"],
        "jenkins": ["ci/cd", "devops", "automation"],
        "github actions": ["ci/cd", "devops", "automation"],
        "mongodb": ["nosql", "database", "backend"],
        "postgresql": ["sql", "database", "backend"],
        "redis": ["database", "caching", "backend"],
        "elasticsearch": ["search", "database", "backend"],
        "graphql": ["api", "backend", "frontend"],
        "node.js": ["javascript", "backend", "web development"],
        "express": ["node.js", "javascript", "backend", "web development"],
        "spring": ["java", "backend", "web development", "enterprise"],
        "rails": ["ruby", "backend", "web development", "mvc"],
        "laravel": ["php", "backend", "web development", "mvc"],
        "swift": ["ios", "mobile development", "apple"],
        "kotlin": ["android", "mobile development", "java"],
        "flutter": ["dart", "mobile development", "cross-platform"],
        "git": ["version control", "collaboration"],
        "github": ["git", "version control", "collaboration"],
        "gitlab": ["git", "version control", "ci/cd"],
        "linux": ["bash", "shell", "system administration"],
        "ubuntu": ["linux", "bash", "shell"],
        "bash": ["linux", "shell", "scripting"],
        "powershell": ["windows", "scripting", "automation"],
        "tableau": ["data visualization", "business intelligence", "analytics"],
        "powerbi": ["data visualization", "business intelligence", "analytics"],
        "plotly": ["data visualization", "python", "javascript"],
        "matplotlib": ["data visualization", "python", "scientific computing"],
        "seaborn": ["data visualization", "python", "statistics"],
        "nlp": ["machine learning", "python", "data science", "ai"],
        "computer vision": ["machine learning", "python", "deep learning", "ai"],
        "mlops": ["machine learning", "devops", "ci/cd", "cloud"],
        "agile": ["scrum", "project management", "collaboration"],
        "scrum": ["agile", "project management", "collaboration"],
        "oauth": ["security", "authentication", "api"],
        "jwt": ["security", "authentication", "api"],
        "grpc": ["api", "microservices", "backend"],
        "websocket": ["real-time", "backend", "frontend"],
        "microservices": ["backend", "api", "cloud", "docker", "kubernetes"],
        "serverless": ["cloud", "aws", "backend", "faas"],
    }

    # Seniority inference from title keywords
    SENIORITY_MAP = {
        "intern": 0,
        "junior": 1,
        "associate": 1,
        "mid": 2,
        "mid-level": 2,
        "senior": 3,
        "lead": 4,
        "principal": 5,
        "staff": 5,
        "architect": 5,
        "manager": 4,
        "director": 6,
        "vp": 7,
        "cto": 8,
    }

    @classmethod
    def expand_skills(cls, skills: List[str], depth: int = 1) -> List[str]:
        """Infer additional skills based on known skills."""
        original = set(s.lower().strip() for s in skills)
        expanded = set(original)

        for _ in range(depth):
            new_skills = set()
            for skill in expanded:
                if skill in cls.SKILL_INFERENCE:
                    new_skills.update(cls.SKILL_INFERENCE[skill])
            expanded.update(new_skills)

        # Return original first, then inferred
        result = list(original)
        for s in expanded:
            if s not in result:
                result.append(s)
        return result

    @classmethod
    def infer_seniority(cls, job_titles: List[str]) -> int:
        """Infer seniority level from job titles (0=intern, 8=CTO)."""
        if not job_titles:
            return 2  # Default mid-level

        max_level = 0
        for title in job_titles:
            title_lower = title.lower()
            for keyword, level in cls.SENIORITY_MAP.items():
                if keyword in title_lower:
                    max_level = max(max_level, level)

        return max_level if max_level > 0 else 2

    @classmethod
    def enrich_profile(cls, profile):
        """Enrich a UserProfile with inferred skills and seniority."""
        # Expand skills
        if profile.skills:
            original_count = len(profile.skills)
            profile.skills = cls.expand_skills(profile.skills, depth=1)
            profile._inferred_skills = profile.skills[original_count:]

        # Infer seniority if experience_years is 0
        if profile.experience_years == 0 and profile.job_titles:
            seniority = cls.infer_seniority(profile.job_titles)
            # Map seniority to approximate years
            years_map = {0: 0, 1: 1, 2: 3, 3: 5, 4: 7, 5: 8, 6: 10, 7: 12, 8: 15}
            profile.experience_years = years_map.get(seniority, 3)

        # Normalize employment types
        if profile.employment_types:
            normalized = []
            for et in profile.employment_types:
                et_lower = et.lower()
                if "intern" in et_lower:
                    normalized.append("internship")
                elif "full" in et_lower or "permanent" in et_lower:
                    normalized.append("full-time")
                elif "part" in et_lower:
                    normalized.append("part-time")
                elif "contract" in et_lower or "freelance" in et_lower:
                    normalized.append("contract")
                else:
                    normalized.append(et_lower)
            profile.employment_types = list(set(normalized))

        return profile
