"""A signed note as a PDF, in the same look as the printed page: dark header, numbered sections, prescription, addenda.
Text stays text (searchable, small file). Manrope is bundled (fonts/, SIL Open Font License)."""
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).parent / "fonts"
INK, SURFACE, MUTED, LIME, TILE, LIGHT = (11, 20, 17), (246, 250, 247), (107, 124, 117), (182, 243, 107), (232, 241, 236), (159, 177, 169)
M = 14          # page margin, mm
W = 210 - 2 * M


class _Doc(FPDF):
    def __init__(self, footer_text: str):
        super().__init__(format="A4", unit="mm")
        self.footer_text = footer_text
        self.add_font("M", "", str(FONTS / "Manrope-Medium.ttf"))
        self.add_font("M", "B", str(FONTS / "Manrope-ExtraBold.ttf"))
        self.set_margins(M, M, M)
        self.set_auto_page_break(True, 18)

    def header(self):
        self.set_fill_color(*SURFACE)
        self.rect(0, 0, 210, 297, "F")

    def footer(self):
        if self.pages_count > 1:
            self.set_y(-12)
            self.set_font("M", "", 8)
            self.set_text_color(*MUTED)
            self.cell(W, 4, f"{self.footer_text} · page {self.page_no()} of {{nb}}", align="R")


def _label(pdf: _Doc, text: str, x: float, w: float):
    pdf.set_xy(x, pdf.get_y())
    pdf.set_font("M", "B", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.set_char_spacing(0.8)
    pdf.multi_cell(w, 4, text.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_char_spacing(0)


def note_pdf(*, clinic: dict, patient: dict, who: str, when: str, doctor: str, title: str, vitals: str,
             sections: list[tuple[str, str, str]], rx: list[dict], addenda: list[tuple[str, str]], signed: str,
             signature: bytes | None = None) -> bytes:
    """sections: (tile, label, text). addenda: (stamp · name, text)."""
    pdf = _Doc(f"{patient['name']} · {when}")
    pdf.set_title(title)
    pdf.set_author(doctor)
    pdf.set_creator("Dictate")
    pdf.alias_nb_pages()
    pdf.add_page()

    # header: clinic on the left, patient on the right, on a dark rounded block
    top, h = M, 30
    pdf.set_fill_color(*INK)
    pdf.rect(M, top, W, h, "F", round_corners=True, corner_radius=5)
    pad, half = 7, (W - 14) / 2
    pdf.set_xy(M + pad, top + 7)
    pdf.set_font("M", "B", 15)
    pdf.set_text_color(*TILE)
    pdf.cell(half, 7, clinic["name"])
    pdf.set_xy(M + pad, top + 15)
    pdf.set_font("M", "", 8.5)
    pdf.set_text_color(*LIGHT)
    pdf.multi_cell(half, 4.2, " · ".join(x for x in [clinic.get("place") or clinic.get("address"), clinic.get("phone")] if x), max_line_height=4.2)
    rx_x = M + W - pad - half
    pdf.set_xy(rx_x, top + 7)
    pdf.set_font("M", "B", 11.5)
    pdf.set_text_color(*TILE)
    pdf.cell(half, 6, patient["name"], align="R")
    pdf.set_xy(rx_x, top + 14)
    pdf.set_font("M", "", 8.5)
    pdf.set_text_color(*LIGHT)
    pdf.cell(half, 4.5, who, align="R")
    pdf.set_xy(rx_x, top + 19.5)
    date_w = pdf.get_string_width(when)
    rest = f" · {doctor}"
    total = date_w + pdf.get_string_width(rest)
    pdf.set_x(M + W - pad - total)
    pdf.set_text_color(*LIME)
    pdf.cell(date_w, 4.5, when)
    pdf.set_text_color(*LIGHT)
    pdf.cell(pdf.get_string_width(rest), 4.5, rest)
    pdf.set_y(top + h + 9)

    text_x, text_w = M + 12, W - 12
    if vitals:
        _label(pdf, "Vitals", M, W)
        pdf.set_font("M", "B", 10.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(W, 5.5, vitals, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # sections: dark numbered tile, small label, the text
    for tile, label, text in sections:
        if pdf.get_y() > 297 - 40:
            pdf.add_page()
        y = pdf.get_y()
        pdf.set_fill_color(*INK)
        pdf.rect(M, y, 7, 7, "F", round_corners=True, corner_radius=1.8)
        pdf.set_xy(M, y + 0.2)
        pdf.set_font("M", "B", 7.5 if len(tile) > 1 else 8.5)
        pdf.set_text_color(*TILE)
        pdf.cell(7, 6.6, tile, align="C")
        pdf.set_y(y + 0.6)
        _label(pdf, label, text_x, text_w)
        pdf.set_x(text_x)
        pdf.set_font("M", "", 10.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(text_w, 5.6, text, new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(max(pdf.get_y(), y + 7) + 5)

    if rx:
        if pdf.get_y() > 297 - 50:
            pdf.add_page()
        pdf.ln(2)
        _label(pdf, "Prescription", M, W)
        pdf.ln(1)
        pdf.set_font("M", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.set_fill_color(*SURFACE)
        with pdf.table(col_widths=(38, 18, 18, 26), text_align="LEFT", borders_layout="NONE", line_height=6.2, padding=(2, 3),
                       cell_fill_color=TILE, cell_fill_mode="EVEN_ROWS",
                       headings_style=_heading_style()) as t:
            t.row(["Medicine", "Dose", "Duration", "Instructions"])
            for r in rx:
                row = t.row()
                pdf.set_font("M", "B", 9.5)
                row.cell(r.get("medicine", ""))
                pdf.set_font("M", "", 9.5)
                for k in ("dose", "duration", "instructions"):
                    row.cell(r.get(k, "") or "")
        pdf.ln(3)

    if addenda:
        pdf.ln(2)
        _label(pdf, "Addenda", M, W)
        for meta, text in addenda:
            y = pdf.get_y() + 1
            pdf.set_xy(M + 5, y)
            pdf.set_font("M", "B", 8)
            pdf.set_text_color(*MUTED)
            pdf.cell(W - 5, 4.5, meta, new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(M + 5)
            pdf.set_font("M", "", 10.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(W - 5, 5.6, text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_fill_color(*LIME)
            pdf.rect(M, y, 1.1, pdf.get_y() - y, "F")
            pdf.ln(3)

    # signed line and the signature box
    if pdf.get_y() > 297 - 42:
        pdf.add_page()
    y = max(pdf.get_y() + 14, 297 - 46)
    pdf.set_draw_color(*INK)
    pdf.set_line_width(0.4)
    pdf.line(M + W - 60, y + 10, M + W, y + 10)
    if signature:   # the doctor's own signature, sitting on the line, kept in proportion
        import io
        try:
            pdf.image(io.BytesIO(signature), x=M + W - 55, y=y - 8, w=50, h=17, keep_aspect_ratio=True)
        except Exception:
            pass
    pdf.set_xy(M + W - 60, y + 12)
    pdf.set_font("M", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(60, 4, "Doctor's signature", align="C")
    pdf.set_xy(M, y + 8)
    pdf.set_font("M", "B", 8.5)
    pdf.cell(W - 70, 4, signed)
    return bytes(pdf.output())


def _heading_style():
    from fpdf.fonts import FontFace
    return FontFace(family="M", emphasis="BOLD", size_pt=7.5, color=MUTED, fill_color=SURFACE)
