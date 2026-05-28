"""Export application package to Markdown for download."""
from __future__ import annotations


def package_to_markdown(pkg: dict) -> str:
    lines = [
        f"# Postulación: {pkg.get('scholarship_name', 'Beca')}",
        "",
        f"**Institución:** {pkg.get('institution', '—')}",
        f"**URL:** {pkg.get('application_url', '—')}",
        "",
        "## Propósito de la beca",
        "",
        pkg.get("analysis", {}).get("scholarship_purpose", "—"),
        "",
        "## Campos sugeridos",
        "",
    ]
    for field in pkg.get("filled_fields", []):
        lines.extend(
            [
                f"### {field.get('label', field.get('field_id'))}",
                f"- Confianza: {field.get('confidence', '—')}%",
                f"- Valor sugerido:",
                "",
                str(field.get("suggested_value", "")),
                "",
            ]
        )
    letter = pkg.get("letter_of_intent")
    if letter:
        lines.extend(["## Carta de intención / motivación", "", letter, ""])

    lines.append("## Checklist de envío")
    for item in pkg.get("submission_checklist", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Advertencias")
    for warn in pkg.get("warnings", []):
        lines.append(f"- {warn}")

    return "\n".join(lines)
