#!/usr/bin/env python3
"""Generates static/es/resume.pdf, the Spanish resume.

The English static/resume.pdf is exported by hand from the Apple Pages document
(Creator: Pages). This Spanish counterpart is generated instead, so that its
layout can be reproduced: edit CONTENT below, then run

    python3 -m venv .venv            # once; .venv/ is gitignored
    .venv/bin/pip install fpdf2
    .venv/bin/python tools/resume_pdf_es.py

Keep the sections in sync with the English PDF: when you update
static/resume.pdf, update the CONTENT here and re-run this script.

Fonts are the macOS system Arial TTFs (Unicode, so accents render); uses
letter page size to match the English PDF.
"""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "es" / "resume.pdf"
FONT_DIR = Path("/System/Library/Fonts/Supplemental")

LEAD = 14          # line height, pt
BULLET = "▪"
INDENT = 16        # bullet indent, pt

# ---------------------------------------------------------------- content --

NAME = "Juan Visbal"
ROLE = "Ingeniero Web y Líder Técnico"
CONTACT = [
    ("tel:+573166560635", "57 316 656 0635"),
    ("mailto:me@juanvisbal.com", "me@juanvisbal.com"),
    (None, "Bogotá, Colombia"),
]
INTRO = (
    "Soy un Ingeniero Web con más de 10 años de experiencia en Ruby on Rails y "
    "Shopify. Tras ser Jefe de Ingeniería de una empresa SaaS de e-commerce, hoy "
    "soy Líder Técnico de un Shopify Platinum Partner, enfocado en entregar "
    "soluciones de eCommerce de alta calidad."
)

# Each role: title, org, dates, bullets.
EXPERIENCE = [
    (
        "Ingeniero Senior | Líder Técnico",
        "SLTWTR",
        "2023–presente",
        [
            "Arquitecto de soluciones y líder técnico para clientes de retainer, "
            "actuando como enlace entre la gestión de producto y los equipos de "
            "desarrollo, asegurando que los proyectos se alcancen y entreguen a tiempo.",
            "Superviso el desarrollo de tiendas Shopify Plus, enfocándome en "
            "funcionalidades avanzadas y personalizaciones.",
            "Gestiono integraciones avanzadas con terceros como SearchSpring, Nosto "
            "y Swym, ampliando las capacidades de las tiendas.",
            "Hago mentoría a desarrolladores, promoviendo un entorno de equipo "
            "colaborativo e innovador, y el equipo duplicó su tamaño.",
        ],
    ),
    (
        "Ingeniero de Soporte | Jefe de Ingeniería",
        "Pasilobus",
        "2016–2023",
        [
            "Dirigí el desarrollo de producto para el Shopify App Store, alineando "
            "las funcionalidades con las necesidades del mercado.",
            "Lideré los esfuerzos de ingeniería, mejorando los tiempos de entrega de "
            "los proyectos y la calidad del producto.",
            "Brindé soporte técnico a comerciantes de Shopify, resolviendo problemas "
            "con eficacia y mejorando la satisfacción del cliente.",
            "Di mentoría a pasantes de ingeniería, fomentando el desarrollo de "
            "habilidades y el crecimiento profesional.",
        ],
    ),
    (
        "Consultor Tecnológico",
        "MAVI",
        "2018–2019",
        [
            "Creé sitios web con WordPress, enfocándome en SEO y seguridad, lo que "
            "aumentó la visibilidad de los clientes.",
            "Asesoré decisiones técnicas para cursos y gestión de redes sociales.",
        ],
    ),
    (
        "Desarrollo web freelance",
        "",
        "2015–2019",
        [
            "Diseñé y desarrollé sitios web a la medida para pequeñas y medianas "
            "empresas, garantizando interfaces amigables y la satisfacción del cliente.",
            "Gestioné el hosting y los CMS, brindando soporte y mantenimiento continuos.",
        ],
    ),
]

EDUCATION = [
    ("Seminario «Enterprise coaching y PNL»", "Coomeva", "2015"),
    ("Título de Ingeniero Electrónico", "Universidad del Norte", "2014"),
    ("Monitor de la clase «Sistemas y Señales»", "Universidad del Norte", "2013"),
]

VOLUNTEER = [
    ("Rotary International", "", "2014–actualidad"),
]

SKILLS = [
    ("Principales", "HTML5/CSS/JS, Ruby, Ruby on Rails, Shopify, Tailwind, Hotwire"),
    (
        "Código",
        "GraphQL, SCSS, JSON, Git, GitHub, Deploybot, React, Alpine, SQL, Postgres, "
        "Hydrogen, Node, Webpack",
    ),
    (
        "Otras herramientas",
        "Claude, agentes de IA para programar, Notion, Figma, Loom, ClickUp",
    ),
]

LANGUAGE = "Fluidez y dominio profesional del español y el inglés."

# (text, url or None)
PORTFOLIO = [
    ("SLTWTR", "https://sltwtr.com"),
    ("Apps de Pasilobus", "https://apps.shopify.com/partners/pasilobus"),
    ("MAVI 2017", "https://mavicol.org"),
    ("Pierrot Theater Academy 2015", None),
    ("Malinche Barranquilla 2016", None),
    ("Álvarez & Asociados 2016", None),
]

OTHER_LINKS = [
    ("LinkedIn", "https://www.linkedin.com/in/juanvisbalco/"),
    ("GitHub", "https://github.com/juanvisbal"),
]

# ----------------------------------------------------------------- layout --


class Resume(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="pt", format="letter")
        self.set_margins(54, 48, 54)
        self.set_auto_page_break(True, margin=48)
        self.add_font("Arial", "", str(FONT_DIR / "Arial.ttf"))
        self.add_font("Arial", "B", str(FONT_DIR / "Arial Bold.ttf"))
        self.add_font("Arial", "I", str(FONT_DIR / "Arial Italic.ttf"))
        self.set_title("Currículum — Juan Visbal")
        self.set_author("Juan Visbal")
        self.set_lang("es-CO")
        self.set_creator("tools/resume_pdf_es.py (fpdf2)")

    def heading(self, text):
        self._ensure(LEAD + 10)
        self.ln(10)
        self.set_font("Arial", "B", 11)
        self.cell(0, LEAD, text)
        self.set_draw_color(170)
        self.set_line_width(0.6)
        y = self.get_y() + LEAD
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_y(y + 8)

    def role(self, title, org, dates):
        self._ensure(2 * LEAD)
        self.ln(4)
        self.set_font("Arial", "B", 10.5)
        self.cell(self.get_string_width(title) + 4, LEAD, title, align="L")
        if dates:
            self.set_font("Arial", "I", 10)
            self.cell(0, LEAD, dates, align="R")
        self.ln(LEAD)
        if org:
            self.set_font("Arial", "", 10.5)
            self.cell(0, LEAD, org)
            self.ln(LEAD)

    def bullet(self, text):
        x0 = self.l_margin + INDENT
        self.set_x(x0)
        self._ensure(LEAD)
        self.set_font("Arial", "", 10)
        self.cell(INDENT - 4, LEAD, BULLET)
        self.multi_cell(self.w - self.r_margin - (x0 + INDENT - 4), LEAD, text)

    def line_item(self, left, right=""):
        """One ▪ line, optionally with a right-aligned date/org."""
        self._ensure(LEAD)
        self.set_x(self.l_margin + INDENT)
        self.set_font("Arial", "", 10)
        self.cell(INDENT - 4, LEAD, BULLET)
        if right:
            self.cell(self.w - self.r_margin - (self.get_x()), LEAD, left)
            self.cell(0, LEAD, right, align="R")
            self.ln(LEAD)
        else:
            self.multi_cell(0, LEAD, left)

    def skill_row(self, label, value):
        x_value = self.l_margin + 110
        self._ensure(LEAD)
        start_y = self.get_y()
        self.set_xy(x_value, start_y)
        self.set_font("Arial", "", 10)
        self.multi_cell(self.w - self.r_margin - x_value, LEAD, value)
        end_y = self.get_y()
        self.set_xy(self.l_margin, start_y)
        self.set_font("Arial", "B", 10)
        self.cell(110, LEAD, label)
        self.set_y(end_y + 2)

    def _ensure(self, height):
        if self.will_page_break(height):
            self.add_page()


def linked_link_cell(pdf, text, url, width, lead):
    pdf.set_text_color(20, 60, 160) if url else None
    pdf.cell(width, lead, text, link=url or "")
    pdf.set_text_color(0)


def build():
    pdf = Resume()
    pdf.add_page()

    # Header
    pdf.set_font("Arial", "B", 22)
    pdf.cell(0, 30, NAME, align="C")
    pdf.ln(30)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, LEAD + 2, ROLE, align="C")
    pdf.ln(LEAD + 2)
    pdf.set_font("Arial", "", 10)
    sep = "  ·  "
    # contact as one centered line with links on the first two items
    x = pdf.l_margin
    line_w = pdf.w - pdf.l_margin - pdf.r_margin
    parts_w = [pdf.get_string_width(t) for _, t in CONTACT]
    total = sum(parts_w) + pdf.get_string_width(sep) * (len(CONTACT) - 1)
    pdf.set_xy(pdf.l_margin + (line_w - total) / 2, pdf.get_y())
    for i, (url, text) in enumerate(CONTACT):
        if i:
            pdf.set_text_color(90)
            pdf.cell(pdf.get_string_width(sep), LEAD, sep)
            pdf.set_text_color(0)
        linked_link_cell(pdf, text, url, parts_w[i], LEAD)
    pdf.ln(LEAD)

    # Intro
    pdf.ln(4)
    pdf.set_font("Arial", "", 10.5)
    pdf.multi_cell(0, LEAD, INTRO)

    pdf.heading("Experiencia laboral")
    for title, org, dates, bullets in EXPERIENCE:
        pdf.role(title, org, dates)
        for b in bullets:
            pdf.bullet(b)

    pdf.heading("Educación")
    for left, org, year in EDUCATION:
        pdf.line_item(f"{left} — {org}", year)

    pdf.heading("Trabajo voluntario")
    for left, org, dates in VOLUNTEER:
        pdf.line_item(left + (f" — {org}" if org else ""), dates)

    pdf.heading("Habilidades")
    for label, value in SKILLS:
        pdf.skill_row(label, value)

    pdf.heading("Idiomas")
    pdf.set_x(pdf.l_margin + INDENT)
    pdf.set_font("Arial", "", 10)
    pdf.cell(INDENT - 4, LEAD, BULLET)
    pdf.multi_cell(0, LEAD, LANGUAGE)

    pdf.heading("Portafolio")
    for text, url in PORTFOLIO:
        pdf._ensure(LEAD)
        pdf.set_x(pdf.l_margin + INDENT)
        pdf.set_font("Arial", "", 10)
        pdf.cell(INDENT - 4, LEAD, BULLET)
        if url:
            label = f"{text} — {url.replace('https://', '').replace('http://', '')}"
            linked_link_cell(pdf, label, url, pdf.get_string_width(label) + 2, LEAD)
            pdf.ln(LEAD)
        else:
            pdf.multi_cell(0, LEAD, text)

    pdf.heading("Otros enlaces")
    for text, url in OTHER_LINKS:
        pdf._ensure(LEAD)
        pdf.set_x(pdf.l_margin + INDENT)
        pdf.set_font("Arial", "", 10)
        pdf.cell(INDENT - 4, LEAD, BULLET)
        linked_link_cell(pdf, text, url, pdf.get_string_width(text) + 2, LEAD)
        pdf.ln(LEAD)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {pdf.pages_count} pages)")


if __name__ == "__main__":
    build()
