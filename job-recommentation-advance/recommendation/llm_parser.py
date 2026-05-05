"""LLM-powered resume parsing with regex fallback."""
import json
import re
from typing import Dict, Optional
from dataclasses import asdict


class LLMResumeParser:
    """Parse resumes using LLM APIs with fallback to regex."""

    SYSTEM_PROMPT = """You are a resume parser. Extract structured information from the resume text below.
Return ONLY a valid JSON object with these exact keys:
- name: string (full name)
- email: string
- phone: string
- skills: array of strings (technical and soft skills)
- experience_years: number (total years of professional experience, infer from dates if needed)
- education: array of strings (degrees, schools, fields)
- job_titles: array of strings (previous job titles)
- locations_preferred: array of strings (preferred work locations)
- remote_preference: string ("remote", "onsite", "hybrid", or "any")
- salary_min: number (minimum expected salary, 0 if not mentioned)
- salary_max: number (maximum expected salary, 0 if not mentioned)
- employment_types: array of strings (e.g., ["full-time", "internship"])
- industries: array of strings

Be thorough but concise. If information is missing, use empty strings/arrays/0.
Resume text:"""

    def __init__(self, provider: str = "openai", model: str = "gpt-3.5-turbo", api_key: str = ""):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize LLM client if dependencies available."""
        if self.provider == "openai" and self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                pass
        elif self.provider == "anthropic" and self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                pass

    def parse(self, text: str) -> Optional[Dict]:
        """Parse resume text using LLM. Returns dict or None if failed."""
        if not self.client:
            return None

        try:
            if self.provider == "openai":
                return self._parse_openai(text)
            elif self.provider == "anthropic":
                return self._parse_anthropic(text)
            else:
                return None
        except Exception as e:
            print(f"[LLM Parser] Error: {e}")
            return None

    def _parse_openai(self, text: str) -> Dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text[:4000]}  # Limit context
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def _parse_anthropic(self, text: str) -> Dict:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.1,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:4000]}]
        )
        content = message.content[0].text
        # Extract JSON from potential markdown
        json_match = re.search(r"```json\s*(.*?)```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        return json.loads(content)

    def merge_with_fallback(self, llm_result: Dict, fallback_profile) -> "UserProfile":
        """Merge LLM results with fallback profile, preferring LLM data."""
        from recommendation.engine_v2 import UserProfile

        profile = UserProfile()

        # Use LLM values if present, else fallback
        profile.name = llm_result.get("name", fallback_profile.name)
        profile.email = llm_result.get("email", fallback_profile.email)
        profile.phone = llm_result.get("phone", fallback_profile.phone)
        profile.skills = llm_result.get("skills", fallback_profile.skills) or fallback_profile.skills
        profile.experience_years = llm_result.get("experience_years", fallback_profile.experience_years)
        profile.education = llm_result.get("education", fallback_profile.education) or fallback_profile.education
        profile.job_titles = llm_result.get("job_titles", fallback_profile.job_titles) or fallback_profile.job_titles
        profile.locations_preferred = llm_result.get("locations_preferred", fallback_profile.locations_preferred) or fallback_profile.locations_preferred
        profile.remote_preference = llm_result.get("remote_preference", fallback_profile.remote_preference)
        profile.salary_min = llm_result.get("salary_min", fallback_profile.salary_min)
        profile.salary_max = llm_result.get("salary_max", fallback_profile.salary_max)
        profile.employment_types = llm_result.get("employment_types", fallback_profile.employment_types) or fallback_profile.employment_types
        profile.industries = llm_result.get("industries", fallback_profile.industries) or fallback_profile.industries

        return profile
