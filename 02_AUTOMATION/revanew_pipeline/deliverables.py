"""Designed, printable deliverables (not prose documents).

- cards_pdf: flashcard grid with cut lines, Q top / A bottom
- worksheet_pdf: sections with ruled fill-in lines
- ebook_pdf: cover page from TITLE/SUBTITLE + chapter body
All letter-size, Helvetica, magenta accent. Visual polish is a proposal until Erik approves.
"""
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as Canvas

INK = colors.HexColor("#1c1c1c")
ACCENT = colors.HexColor("#d01e98")
GREY = colors.HexColor("#777777")
LINE = colors.HexColor("#bbbbbb")


def _plain(t):
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t or "")
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _wrap(c, text, width, font, size):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------- flashcards ----------

def parse_cards(md: str):
    cards = []
    for b in re.split(r"^### Card \d+.*$", md, flags=re.M)[1:]:
        m = re.search(r"Q:\s*(.+)", b)
        if not m:
            continue
        q = _plain(m.group(1))
        a = _plain(" ".join(b[m.end():].split()))
        cards.append((q, a))
    return cards


def cards_pdf(md: str, out_path: str, title="Framework Flashcards"):
    cards = parse_cards(md)
    if not cards:
        return False
    c = Canvas.Canvas(out_path, pagesize=letter)
    W, H = letter
    cw = (W - 1.6 * inch - 0.2 * inch) / 2
    ch = (H - 1.6 * inch - 0.8 * inch) / 3
    page_slots = 6
    for i, (q, a) in enumerate(cards):
        if i % page_slots == 0:
            if i:
                c.showPage()
            c.setFillColor(GREY)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(0.8 * inch, H - 0.55 * inch, title.upper())
            c.setStrokeColor(LINE)
            c.setLineWidth(0.5)
        slot = i % page_slots
        x0 = 0.8 * inch + (slot % 2) * (cw + 0.2 * inch)
        y0 = H - 0.9 * inch - (slot // 2 + 1) * (ch + 0.15 * inch)
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.rect(x0, y0, cw, ch, stroke=1, fill=1)
        mid = y0 + ch * 0.55
        c.setDash(2, 2)
        c.line(x0, mid, x0 + cw, mid)
        c.setDash()
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x0 + 8, y0 + ch - 18, "Q")
        c.setFillColor(INK)
        y = y0 + ch - 34
        for ln in _wrap(c, q, cw - 16, "Helvetica", 9):
            c.drawString(x0 + 8, y, ln)
            y -= 11
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x0 + 8, mid - 16, "A")
        c.setFillColor(INK)
        y = mid - 30
        for ln in _wrap(c, a, cw - 16, "Helvetica", 8.5):
            if y > y0 + 8:
                c.drawString(x0 + 8, y, ln)
            y -= 10
    c.save()
    return True


# ---------- worksheet ----------

def worksheet_pdf(md: str, out_path: str, title="Market Avatar Worksheet"):
    sections = []
    cur = None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = (_plain(line[3:]), [])
            sections.append(cur)
        elif line.strip().startswith("- ") and cur:
            cur[1].append(_plain(line[2:]))
    if not sections:
        return False
    c = Canvas.Canvas(out_path, pagesize=letter)
    W, H = letter
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.8 * inch, H - 0.9 * inch, title)
    c.setFillColor(GREY)
    c.setFont("Helvetica", 9)
    c.drawString(0.8 * inch, H - 1.1 * inch, "Fill in each block. Write in your own words.")
    y = H - 1.6 * inch
    for name, prompts in sections:
        need = 24 + len(prompts) * 10 + len(prompts) * 26 + 14
        if y - need < 0.9 * inch:
            c.showPage()
            y = H - 1.0 * inch
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.8 * inch, y, name)
        y -= 16
        c.setFillColor(INK)
        for p in prompts:
            c.setFont("Helvetica-Oblique", 8.5)
            c.setFillColor(GREY)
            c.drawString(0.9 * inch, y, p)
            y -= 12
            c.setStrokeColor(LINE)
            c.setLineWidth(0.7)
            c.line(0.9 * inch, y, W - 0.8 * inch, y)
            c.line(0.9 * inch, y - 14, W - 0.8 * inch, y - 14)
            y -= 26
        y -= 10
    c.save()
    return True


# ---------- ebook ----------

def ebook_pdf(md: str, out_path: str, fallback_title="RevAnew Ebook", price=""):
    price = str(price or "").strip()
    if price and not price.startswith("$"):
        price = "$" + price
    lines = md.splitlines()
    title = fallback_title
    subtitle = ""
    body = lines
    if lines and lines[0].startswith("TITLE:"):
        title = _plain(lines[0][6:])
        body = lines[1:]
    if body and body[0].startswith("SUBTITLE:"):
        subtitle = _plain(body[0][9:])
        body = body[1:]
    c = Canvas.Canvas(out_path, pagesize=letter)
    W, H = letter
    # cover
    c.setFillColor(colors.HexColor("#101114"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(0.8 * inch, H * 0.42, W - 1.6 * inch, 3, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    ty = H * 0.60
    for ln in _wrap(c, title, W - 1.6 * inch, "Helvetica-Bold", 30):
        c.drawString(0.8 * inch, ty, ln)
        ty -= 38
    if subtitle:
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#cccccc"))
        for ln in _wrap(c, subtitle, W - 1.6 * inch, "Helvetica", 14):
            ty -= 24
            c.drawString(0.8 * inch, ty, ln)
    if price:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.8 * inch, 1.0 * inch, price)
    c.showPage()
    # body
    c.setFillColor(INK)
    y = H - 1.0 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.8 * inch, y, _plain(title))
    y -= 26
    for raw in body:
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        if line.startswith("## "):
            if y < 2.0 * inch:
                c.showPage()
                y = H - 1.0 * inch
            y -= 10
            c.setFillColor(ACCENT)
            c.setFont("Helvetica-Bold", 13)
            for ln in _wrap(c, _plain(line[3:]), W - 1.6 * inch, "Helvetica-Bold", 13):
                c.drawString(0.8 * inch, y, ln)
                y -= 16
            c.setFillColor(INK)
            y -= 4
        else:
            c.setFont("Helvetica", 10)
            if y < 1.2 * inch:
                c.showPage()
                y = H - 1.0 * inch
            for ln in _wrap(c, _plain(line), W - 1.6 * inch, "Helvetica", 10):
                if y < 1.0 * inch:
                    c.showPage()
                    y = H - 1.0 * inch
                c.drawString(0.8 * inch, y, ln)
                y -= 13
            y -= 4
    c.save()
    return True
