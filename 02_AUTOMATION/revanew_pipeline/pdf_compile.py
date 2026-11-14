"""Markdown/HTML asset -> publication-grade PDF (reportlab).

Ported from Erik's Gemini spec with fixes: bold/italic markers stripped,
numbered lists, fenced code as body text, HTML tag stripping for landing pages.
"""
import io
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def _esc(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", t)
    return t


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)


def compile_pdf(title: str, content: str, is_html: bool = False) -> bytes:
    if is_html:
        content = _strip_html(content)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54, title=title)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                 fontSize=18, leading=22, textColor=colors.HexColor("#111111"), spaceAfter=14)
    h2_style = ParagraphStyle("DocH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                              fontSize=13, leading=16, textColor=colors.HexColor("#222222"),
                              spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle("DocBody", parent=styles["Normal"], fontName="Helvetica",
                                fontSize=10, leading=14, textColor=colors.HexColor("#333333"), spaceAfter=8)
    bullet_style = ParagraphStyle("DocBullet", parent=body_style, leftIndent=15, spaceAfter=4)

    story = []
    lines = content.splitlines()
    first_h1 = next((l for l in lines if l.strip().startswith("# ")), None)
    if first_h1:
        story.append(Paragraph(_esc(first_h1[2:].strip()), title_style))
    else:
        story.append(Paragraph(_esc(title), title_style))
    story.append(Spacer(1, 8))
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("```") or (first_h1 and line == first_h1.strip()):
            continue
        if line.startswith("### "):
            story.append(Paragraph(_esc(line[4:]), h2_style))
        elif line.startswith("## "):
            story.append(Paragraph(_esc(line[3:]), h2_style))
        elif line.startswith("# "):
            story.append(Paragraph(_esc(line[2:]), title_style))
        elif line.startswith(("- ", "* ")):
            story.append(Paragraph("• " + _esc(line[2:]), bullet_style))
        elif re.match(r"^\d+[\.\)] ", line):
            story.append(Paragraph(_esc(line), bullet_style))
        else:
            story.append(Paragraph(_esc(line), body_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
