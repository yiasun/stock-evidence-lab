"""Build a five-page PDF from the versioned submission note (dev dependency)."""
import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether

ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor("#173d55")
TEAL=colors.HexColor("#217d82")
PALE=colors.HexColor("#eef4f8")


def build(output,font_path,screenshot):
    pdfmetrics.registerFont(TTFont("CJK",str(font_path)))
    styles={
        "title":ParagraphStyle("title",fontName="CJK",fontSize=24,leading=31,textColor=NAVY,spaceAfter=16,wordWrap="CJK"),
        "h2":ParagraphStyle("h2",fontName="CJK",fontSize=13,leading=19,textColor=TEAL,spaceBefore=12,spaceAfter=8,wordWrap="CJK"),
        "body":ParagraphStyle("body",fontName="CJK",fontSize=10,leading=16,textColor=colors.HexColor("#253c49"),spaceAfter=8,wordWrap="CJK"),
        "cell":ParagraphStyle("cell",fontName="CJK",fontSize=9,leading=14,textColor=NAVY,wordWrap="CJK"),
        "caption":ParagraphStyle("caption",fontName="CJK",fontSize=8,leading=12,textColor=colors.HexColor("#627a88"),spaceAfter=8,wordWrap="CJK"),
    }
    def paragraph(text,style="body"):
        text=html.escape(text)
        text=re.sub(r"(https://[^\s]+)",r'<link href="\1" color="#217d82">\1</link>',text)
        return Paragraph(text,styles[style])
    def table(rows):
        widths=[150,A4[0]-92-150]
        cells=[[paragraph(c,"cell") for c in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),PALE),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LINEBELOW",(0,0),(-1,0),1,TEAL),("LINEBELOW",(0,1),(-1,-1),0.4,colors.HexColor("#dae3e9")),
            ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
        return t
    source=(ROOT/"docs/PRODUCT_REPORT.md").read_text(encoding="utf-8")
    story=[]
    lines=source.splitlines()
    index=0
    while index<len(lines):
        line=lines[index].strip()
        if not line:
            index+=1
            continue
        if line=="<!-- PAGE -->": story.append(PageBreak())
        elif line=="{{SCREENSHOT}}":
            if not screenshot.is_file(): raise FileNotFoundError(screenshot)
            image=Image(str(screenshot))
            ratio=min((A4[0]-92)/image.imageWidth,550/image.imageHeight)
            image.drawWidth=image.imageWidth*ratio
            image.drawHeight=image.imageHeight*ratio
            image.hAlign="LEFT"
            story += [image,Spacer(1,6),paragraph("提交演示版真实页面；运行状态以页面标签为准。","caption")]
        elif line.startswith("| "):
            rows=[]
            while index<len(lines) and lines[index].strip().startswith("|"):
                row=[cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[- :]+",cell) for cell in row): rows.append(row)
                index+=1
            story += [table(rows),Spacer(1,7)]
            continue
        elif line.startswith("# "): story.append(paragraph(line[2:],"title"))
        elif line.startswith("## "): story.append(paragraph(line[3:],"h2"))
        elif line.startswith("- "): story.append(paragraph("- "+line[2:]))
        else: story.append(paragraph(line))
        index+=1
    output.parent.mkdir(parents=True,exist_ok=True)
    def chrome(canvas,doc):
        width,height=A4
        canvas.setFillColor(TEAL)
        canvas.rect(0,height-12,width,12,fill=1,stroke=0)
        canvas.setFont("CJK",8)
        canvas.setFillColor(colors.HexColor("#627a88"))
        canvas.drawString(46,27,"Stock Evidence Lab · 提交演示版 v3.0 · 2026-10-16")
        canvas.drawRightString(width-46,27,str(doc.page))
        canvas.setTitle("证据镜 · Stock Evidence Lab 产品说明")
        canvas.setAuthor("Stock Evidence Lab")
    doc=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=46,rightMargin=46,topMargin=40,bottomMargin=48)
    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    from pypdf import PdfReader
    pages=len(PdfReader(str(output)).pages)
    if pages!=5: raise ValueError(f"Expected 5 pages, generated {pages}; review layout")
    print(f"Created {output} ({pages} pages)")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--font",type=Path,default=Path("C:/Windows/Fonts/simhei.ttf"))
    parser.add_argument("--screenshot",type=Path,default=ROOT/"docs/images/submission-ui.png")
    parser.add_argument("--output",type=Path,default=ROOT/"output/pdf/stock-evidence-lab-report.pdf")
    args=parser.parse_args()
    build(args.output,args.font,args.screenshot)
