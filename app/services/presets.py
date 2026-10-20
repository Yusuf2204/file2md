from datetime import datetime, timezone
import re


class PresetService:
    @staticmethod
    def format_chatgpt(content: str, filename: str) -> str:
        """Format standar Markdown untuk ChatGPT / OpenAI Context."""
        return content.strip()

    @staticmethod
    def format_claude(content: str, filename: str) -> str:
        """Format XML terstruktur rekomendasi Anthropic untuk Claude Context Caching."""
        clean_name = filename.strip()
        return (
            "<documents>\n"
            f'  <document index="1">\n'
            f"    <source>{clean_name}</source>\n"
            "    <document_content>\n"
            f"{content.strip()}\n"
            "    </document_content>\n"
            "  </document>\n"
            "</documents>"
        )

    @staticmethod
    def format_obsidian(content: str, filename: str) -> str:
        """Format catatan Obsidian dengan YAML Frontmatter."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title = re.sub(r"\.[^/.]+$", "", filename).replace("_", " ").title()
        frontmatter = (
            "---\n"
            f'title: "{title}"\n'
            f'source: "{filename}"\n'
            f"created: {today}\n"
            "tags:\n"
            "  - file2md\n"
            "  - ai-context\n"
            "---\n\n"
        )
        return frontmatter + content.strip()

    @staticmethod
    def format_html(content: str, filename: str) -> str:
        """Format semantic HTML document dengan tag dan metadata."""
        title = re.sub(r"\.[^/.]+$", "", filename).replace("_", " ").title()
        return (
            "<!DOCTYPE html>\n"
            '<html lang="id">\n'
            "<head>\n"
            '  <meta charset="UTF-8">\n'
            f"  <title>{title}</title>\n"
            "  <style>\n"
            "    body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 820px; margin: 2rem auto; padding: 0 1.25rem; color: #1e293b; background: #ffffff; }\n"
            "    img { max-width: 100%; height: auto; border-radius: 8px; }\n"
            "    pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 1rem; border-radius: 8px; overflow-x: auto; }\n"
            "    table { border-collapse: collapse; width: 100%; margin: 1.5rem 0; }\n"
            "    th, td { border: 1px solid #cbd5e1; padding: 0.5rem 0.75rem; text-align: left; }\n"
            "    th { background: #f1f5f9; }\n"
            "    hr { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            "  <article>\n"
            f"    <h1>{title}</h1>\n"
            f"    <p><em>Sumber: {filename}</em></p>\n"
            "    <hr>\n"
            f"{content.strip()}\n"
            "  </article>\n"
            "</body>\n"
            "</html>"
        )

    @classmethod
    def apply_preset(cls, content: str, filename: str, preset: str = "chatgpt") -> str:
        preset_key = (preset or "chatgpt").lower().strip()
        if preset_key in ("claude", "xml"):
            return cls.format_claude(content, filename)
        elif preset_key in ("obsidian", "yaml"):
            return cls.format_obsidian(content, filename)
        elif preset_key in ("html", "rich"):
            return cls.format_html(content, filename)
        return cls.format_chatgpt(content, filename)

