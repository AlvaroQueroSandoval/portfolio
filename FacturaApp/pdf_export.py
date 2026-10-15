from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def render_pdf(document):
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallText", fontName="Helvetica", fontSize=8, leading=11))
    styles.add(ParagraphStyle(name="Amount", parent=styles["SmallText"], alignment=TA_RIGHT))
    def paragraph(text, style="SmallText"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])
    story = [
        paragraph("FacturaApp", "Title"),
        paragraph(document["kind"].upper(), "Heading2"),
        paragraph(f"{document['number']} · {document['created_at'][:10]}"),
        Spacer(1, 16),
        paragraph("EMISOR", "Heading3"), paragraph(document["issuer"]),
        paragraph("DESTINATARIO", "Heading3"), paragraph(document["recipient"]),
        paragraph("OBRA / DESTINO", "Heading3"), paragraph(document["worksite"]),
        Spacer(1, 18),
    ]
    rows = [[paragraph(x) for x in ["Material / presentación", "Cantidad", "P. ud.\nIVA incl.", "Base", "IVA", "Total"]]]
    for item in document["lines"]:
        rows.append([paragraph(item["name"] + "\n" + item["unit"]),
                     paragraph(item["quantity"], "Amount"), paragraph(item["unit_gross"], "Amount"),
                     paragraph(item["net"], "Amount"), paragraph(item["tax"], "Amount"),
                     paragraph(item["gross"], "Amount")])
    table = Table(rows, colWidths=[190, 45, 65, 65, 55, 65], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f0ed")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#177766")),
        ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#d6e1de")),
    ]))
    story += [table, Spacer(1, 16), KeepTogether([
        paragraph(f"Base: {document['subtotal']} EUR", "Normal"),
        paragraph(f"IVA: {document['tax']} EUR", "Normal"),
        paragraph(f"TOTAL: {document['total']} EUR", "Heading2"),
    ])]
    if document.get("notes"):
        story += [paragraph("Observaciones", "Heading3"), paragraph(document["notes"])]
    story += [Spacer(1, 12), paragraph(
        "Precios de referencia de catálogo. Transporte, descuentos y condiciones de compra no incluidos. "
        "Documento de demostración; no acredita una compra ni sustituye una factura del proveedor.")]
    sources = sorted({(item["supplier"], item["source"], item["checked_at"]) for item in document["lines"]})
    story += [paragraph("Trazabilidad de precios", "Heading3")]
    for supplier, url, checked in sources:
        story.append(paragraph(f"{supplier} · Consultado: {checked}\n{url}"))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#63736e"))
        canvas.drawString(40, 25, "FacturaApp · Importes en EUR · Documento de demostración")
        canvas.drawRightString(A4[0]-40, 25, f"Página {doc.page}")
        canvas.restoreState()
    SimpleDocTemplate(output, pagesize=A4, leftMargin=40, rightMargin=40,
                      topMargin=35, bottomMargin=45,
                      title=document["number"], author="FacturaApp").build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
