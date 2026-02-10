"""
PDF generation utilities - PROPERLY FIXED ARABIC TEXT
"""
import re
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER, TA_JUSTIFY

# CRITICAL: Import these for proper Arabic support
try:
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    print("⚠️ Install: pip install arabic-reshaper python-bidi")



def _clean_contract_text(text: str) -> str:
    """Remove LLM preambles"""
    preambles = [
        r"^Here is the (?:complete|full|updated)?\s*(?:lease )?contract.*?:\s*\n",
        r"^I've (?:created|generated|prepared).*?contract.*?:\s*\n",
        r"^تم إنشاء العقد.*?:\s*\n",
        r"^إليك العقد.*?:\s*\n",
    ]
    
    cleaned = text
    for pattern in preambles:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    return cleaned.strip()


def _register_arabic_font() -> str:
    """Register Arabic-compatible font"""
    font_paths = [
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        # MacOS
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        # Relative
        "DejaVuSans.ttf",
        "arial.ttf",
    ]
    
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont("ArabicFont", path))
            print(f"✅ Font registered: {path}")
            return "ArabicFont"
        except Exception:
            continue
    
    print("⚠️ Using Helvetica - Arabic may not display correctly")
    return "Helvetica"


def _prepare_arabic_text(text: str) -> str:
    """
    CRITICAL FIX: Properly reshape Arabic text for PDF rendering
    
    This is REQUIRED for Arabic text to display correctly in PDFs.
    Without this, text appears scrambled when extracted.
    """
    if not ARABIC_SUPPORT:
        return text
    
    if not is_arabic(text):
        return text
    
    try:
        # Step 1: Reshape Arabic characters (connect them properly)
        reshaped = reshape(text)
        
        # Step 2: Apply bidirectional algorithm (handle RTL)
        bidi_text = get_display(reshaped)
        
        return bidi_text
    except Exception as e:
        print(f"⚠️ Arabic reshaping failed: {e}")
        return text


def generate_pdf(contract_text: str) -> BytesIO:
    """
    Generate PDF with PROPER Arabic text support
    """
    # Clean text
    contract_text = _clean_contract_text(contract_text)
    
    if not contract_text or len(contract_text.strip()) < 50:
        raise ValueError("Contract text too short")
    
    is_rtl = is_arabic(contract_text)
    font_name = _register_arabic_font()
    
    # PDF setup
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    
    # Styles
    title_style = ParagraphStyle(
        "Title",
        fontName=font_name,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        leading=22,
        textColor='#1a1a1a',
    )
    
    section_header_style = ParagraphStyle(
        "SectionHeader",
        fontName=font_name,
        fontSize=13,
        alignment=TA_CENTER,
        spaceAfter=15,
        spaceBefore=20,
        leading=18,
        textColor='#2c3e50',
    )
    
    field_style = ParagraphStyle(
        "Field",
        fontName=font_name,
        fontSize=11,
        alignment=TA_RIGHT if is_rtl else TA_LEFT,
        spaceAfter=6,
        leading=18,
    )
    
    clause_style = ParagraphStyle(
        "Clause",
        fontName=font_name,
        fontSize=11,
        alignment=TA_JUSTIFY if is_rtl else TA_LEFT,
        leading=20,
        spaceBefore=8,
        spaceAfter=8,
        rightIndent=15 if is_rtl else 0,
        leftIndent=0 if is_rtl else 15,
    )
    
    signature_style = ParagraphStyle(
        "Signature",
        fontName=font_name,
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6,
        spaceBefore=15,
        leading=16,
    )
    
    story = []
    lines = contract_text.split("\n")
    
    in_header = True
    in_clauses = False
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        if not line:
            if story:
                story.append(Spacer(1, 0.1 * inch))
            continue
        
        # CRITICAL: Reshape Arabic text BEFORE escaping XML
        if is_rtl:
            line = _prepare_arabic_text(line)
        
        # Escape XML
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Detect sections
        is_title = False
        is_section_header = False
        is_field = False
        is_clause = False
        is_signature = False
        
        # Title (first line with contract keyword)
        if i < 3 and ("عقد" in line or "CONTRACT" in line.upper()):
            is_title = True
        
        # Section headers
        elif line in ["شروط العقد", "TERMS AND CONDITIONS", "البنود"]:
            is_section_header = True
            in_clauses = True
            in_header = False
            story.append(Spacer(1, 0.2 * inch))
        
        # Header fields
        elif any(kw in line for kw in [
            "المؤجر:", "المستأجر:", "أوصاف المأجور:", "مقدار الإيجار:",
            "تاريخ ابتداء الإيجار", "مدة الإيجار:", "استعمال المأجور:",
            "كيفية دفع"
        ]):
            is_field = True
        
        # Clauses
        elif re.match(r"^البند\s+(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[\u0660-\u0669]+|[0-9]+)", line):
            is_clause = True
            in_clauses = True
        elif in_clauses and re.match(r"^(Article|Clause)\s+\d+", line):
            is_clause = True
        
        # Signature section
        elif "تليت الشروط" in line or "التوقيع" in line or "Signature" in line:
            is_signature = True
            in_clauses = False
            story.append(Spacer(1, 0.3 * inch))
        
        # Auto-detect: if we're in clauses section, treat as clause
        elif in_clauses and len(line) > 30:
            is_clause = True
        
        # Select style
        if is_title:
            style = title_style
        elif is_section_header:
            style = section_header_style
        elif is_signature:
            style = signature_style
        elif is_clause:
            style = clause_style
        elif is_field:
            style = field_style
        else:
            style = field_style
        
        # Add to story
        try:
            para = Paragraph(line, style)
            story.append(para)
        except Exception as e:
            print(f"⚠️ Failed to add: {line[:50]}... Error: {e}")
            continue
    
    # Build PDF
    if not story:
        raise ValueError("No content to render")
    
    try:
        doc.build(story)
        print(f"✅ PDF generated successfully ({len(story)} elements)")
    except Exception as e:
        raise ValueError(f"PDF build failed: {e}")
    
    buffer.seek(0)
    return buffer