from dataclasses import dataclass, field


@dataclass
class BundleItem:
    filename: str
    content: str | None = None
    description: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


class MarkdownBuilder:
    def __init__(self, title: str = "Project Context"):
        self.title = title

    def build_bundle(self, items: list[BundleItem]) -> str:
        if not items:
            return f"# {self.title}\n\n*(Tidak ada file yang diproses)*"

        lines: list[str] = [f"# {self.title}\n"]

        # 1. Bagian Source Index
        lines.append("## Source Index")
        for item in items:
            if item.error:
                lines.append(f"- `{item.filename}` — ❌ **Gagal:** {item.error}")
            else:
                desc = f" — {item.description}" if item.description else ""
                lines.append(f"- `{item.filename}`{desc}")
        lines.append("\n---\n")

        # 2. Bagian Konten Setiap File
        content_sections: list[str] = []
        for item in items:
            if item.content:
                section = f"## File: {item.filename}\n\n{item.content}"
                content_sections.append(section)

        if content_sections:
            lines.append("\n\n---\n\n".join(content_sections))
        else:
            lines.append("*(Semua file gagal dikonversi)*")

        return "\n".join(lines)