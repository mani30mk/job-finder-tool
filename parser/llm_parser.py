"""Ollama-powered parser for unstructured job pages."""
import json
from selectolax.parser import HTMLParser

from app_config.settings import OLLAMA_HOST, OLLAMA_MODEL


class LLMJobParser:
    """Parse unstructured HTML career pages using local Ollama LLM."""

    def __init__(self):
        try:
            import ollama
            self.client = ollama.Client(host=OLLAMA_HOST)
            self.model = OLLAMA_MODEL
            self.available = True
        except ImportError:
            print("[LLM] ollama package not installed. LLM parser disabled.")
            self.available = False

    def parse_page(self, html: str, url: str) -> dict:
        """Extract job details from unstructured HTML."""
        if not self.available:
            return None

        # Clean HTML
        tree = HTMLParser(html)
        for tag in tree.css("script, style, nav, footer, header, aside"):
            tag.decompose()

        text = tree.body.text(separator="\n") if tree.body else tree.text(separator="\n")
        text = text[:6000]  # Keep under token limit

        prompt = f"""You are a precise job posting parser. Extract from the text below and return ONLY a valid JSON object with these exact keys and no markdown:
{{
  "title": "string",
  "company": "string", 
  "location": "string",
  "employment_type": "One of: Full-time, Part-time, Internship, Contract",
  "description": "string (max 300 words)",
  "requirements": "string (max 200 words)",
  "apply_url": "string"
}}

Rules:
- If a field cannot be found, use empty string ""
- employment_type MUST be exactly one of the four options above
- Return ONLY the JSON object, no explanation, no markdown code blocks

Text to parse:
{text}

Source URL: {url}"""

        try:
            response = self.client.generate(model=self.model, prompt=prompt, options={"temperature": 0.1})
            raw = response.get("response", "")

            # Clean up potential markdown
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            result = json.loads(raw)

            # Validate required keys
            for key in ["title", "company", "location", "employment_type", "description", "requirements", "apply_url"]:
                if key not in result:
                    result[key] = ""

            result["job_id"] = f"llm_{hash(url) & 0xFFFFFFFF}"
            result["source_platform"] = "custom"
            result["source_url"] = url
            result["posted_date"] = ""

            return result
        except Exception as e:
            print(f"[LLM] Parse error: {e}")
            return None
