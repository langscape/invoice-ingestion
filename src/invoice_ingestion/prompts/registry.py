"""Prompt template registry with variable injection and versioning."""
from __future__ import annotations
from pathlib import Path
import hashlib
import re

TEMPLATES_DIR = Path(__file__).parent / "templates"
DOMAIN_DIR = Path(__file__).parent / "domain_knowledge"


class PromptRegistry:
    """Manages prompt templates with variable injection and versioning."""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._hashes: dict[str, str] = {}

    def load_template(self, name: str) -> str:
        """Load a prompt template by name (e.g., 'classification')."""
        if name not in self._cache:
            path = TEMPLATES_DIR / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            self._cache[name] = path.read_text(encoding="utf-8")
        return self._cache[name]

    def load_domain_knowledge(self, name: str) -> str:
        """Load domain knowledge file (e.g., 'gas_concepts')."""
        path = DOMAIN_DIR / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Domain knowledge not found: {path}")
        return path.read_text(encoding="utf-8")

    def render(self, template_name: str, variables: dict | None = None,
               few_shot_context: str | None = None,
               domain_knowledge: list[str] | None = None) -> str:
        """Render a prompt template with variable substitution.

        Args:
            template_name: Name of the template (without .md extension)
            variables: Dict of {placeholder: value} to inject
            few_shot_context: Optional few-shot examples to inject
            domain_knowledge: Optional list of domain knowledge file names to inject
        """
        template = self.load_template(template_name)

        # Inject domain knowledge
        if domain_knowledge:
            dk_content = "\n\n".join(
                f"--- {name.upper().replace('_', ' ')} ---\n{self.load_domain_knowledge(name)}"
                for name in domain_knowledge
            )
            template = template.replace("{domain_knowledge}", dk_content)
        else:
            template = template.replace("{domain_knowledge}", "")

        # Inject few-shot context
        if few_shot_context:
            template = template.replace("{few_shot_context}", few_shot_context)
        else:
            template = template.replace("{few_shot_context}", "")

        # Inject variables
        if variables:
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))

        return template

    def get_hash(self, template_name: str) -> str:
        """Get SHA-256 hash of a template (for reproducibility tracking)."""
        if template_name not in self._hashes:
            content = self.load_template(template_name)
            self._hashes[template_name] = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return self._hashes[template_name]

    def get_version(self, template_name: str) -> str:
        """Get version string for a template (hash-based)."""
        return f"v1.0-{self.get_hash(template_name)[:8]}"

    def clear_cache(self):
        """Clear the template cache (useful for reloading after edits)."""
        self._cache.clear()
        self._hashes.clear()
