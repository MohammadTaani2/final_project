"""
Contract clause generation and contextual clause management
"""
from typing import Dict


# Standard contract clauses that should always be included
STANDARD_CLAUSES = [
    "1. Preamble (تمهيد) - parties identification with full details",
    "2. Property Description (وصف العقار) - detailed location, size, boundaries, floors",
    "3. Lease Purpose (الغرض من الإيجار) - residential/commercial use",
    "4. Lease Term (مدة الإيجار) - start date, end date, renewal options",
    "5. Rent Amount (بدل الإيجار) - monthly amount, annual amount",
    "6. Payment Terms (شروط الدفع) - due date, payment method, grace period",
    "7. Late Payment Penalties (غرامات التأخير) - late fees, interest",
    "8. Security Deposit (التأمين) - amount, conditions for return, deductions",
    "9. Utilities & Services (المرافق والخدمات) - electricity, water, internet, who pays what",
    "10. Maintenance & Repairs (الصيانة والإصلاح) - landlord vs tenant responsibilities",
    "11. Property Condition (حالة العقار) - delivered condition, inspection report",
    "12. Permitted Use (الاستخدام المسموح) - restrictions on use",
    "13. Property Modifications (التعديلات) - tenant restrictions on alterations",
    "14. Subletting (التأجير من الباطن) - allowed or prohibited",
    "15. Access Rights (حق الدخول) - landlord's right to inspect, notice period",
    "16. Insurance (التأمين) - requirements for property insurance",
    "17. Tenant Obligations (التزامات المستأجر) - multiple specific obligations",
    "18. Landlord Obligations (التزامات المؤجر) - multiple specific obligations",
    "19. Breach & Termination (الإخلال والإنهاء) - conditions, notice periods",
    "20. Early Termination (الإنهاء المبكر) - conditions and penalties",
    "21. Eviction Procedures (إجراءات الإخلاء) - legal process",
    "22. Dispute Resolution (حل النزاعات) - arbitration, jurisdiction, applicable law",
    "23. Force Majeure (القوة القاهرة) - acts of god, war, natural disasters",
    "24. Notices (الإخطارات) - how parties communicate officially",
    "25. Miscellaneous (أحكام عامة) - entire agreement, amendments, severability",
    "26. Governing Law (القانون الحاكم) - Jordanian law",
    "27. Signatures Section (التوقيعات) - parties, witnesses, date"
]


# Context-specific clause templates
CONTEXTUAL_CLAUSE_TEMPLATES = {
    'furnished': {
        'title': 'FURNISHED APARTMENT CLAUSES (5 additional clauses)',
        'clauses': [
            "28. Furniture Inventory (جرد الأثاث المفصل) - complete list with conditions",
            "29. Furniture Maintenance & Damage Liability (الصيانة والمسؤولية عن الأضرار)",
            "30. Appliances List & Warranties (الأجهزة الكهربائية والضمانات)",
            "31. Furniture Return Conditions (شروط إعادة الأثاث)",
            "32. Prohibited Furniture Modifications (التعديلات المحظورة على الأثاث)"
        ]
    },
    'commercial': {
        'title': 'COMMERCIAL LEASE CLAUSES (4 additional clauses)',
        'clauses': [
            "Business License Requirements (متطلبات الترخيص التجاري)",
            "Permitted Business Activities (الأنشطة التجارية المسموحة)",
            "Signage & Branding Rights (حقوق اللافتات والعلامة التجارية)",
            "Commercial Insurance Requirements (متطلبات التأمين التجاري)"
        ]
    },
    'short_term': {
        'title': 'SHORT-TERM LEASE CLAUSES (3 additional clauses)',
        'clauses': [
            "Extended Stay Conditions (شروط الإقامة الممتدة)",
            "Daily/Weekly Rate Structure (هيكل الأسعار اليومي/الأسبوعي)",
            "Early Checkout Penalties (غرامات المغادرة المبكرة)"
        ]
    },
    'shared': {
        'title': 'SHARED ACCOMMODATION CLAUSES (4 additional clauses)',
        'clauses': [
            "Roommate Rights & Responsibilities (حقوق ومسؤوليات الزملاء)",
            "Shared Space Usage Rules (قواعد استخدام المساحات المشتركة)",
            "Individual vs Joint Liability (المسؤولية الفردية مقابل المشتركة)",
            "Roommate Change Procedures (إجراءات تغيير الزملاء)"
        ]
    },
    'with_parking': {
        'title': 'PARKING CLAUSES (2 additional clauses)',
        'clauses': [
            "Parking Space Assignment (تخصيص موقف السيارات)",
            "Parking Violations & Penalties (مخالفات المواقف والغرامات)"
        ]
    },
    'with_pets': {
        'title': 'PET CLAUSES (3 additional clauses)',
        'clauses': [
            "Permitted Pet Types & Sizes (أنواع وأحجام الحيوانات المسموحة)",
            "Pet Deposit & Damage Liability (تأمين الحيوانات والمسؤولية عن الأضرار)",
            "Pet Care & Neighbor Considerations (العناية بالحيوانات ومراعاة الجيران)"
        ]
    },
    'with_garden': {
        'title': 'GARDEN/YARD CLAUSES (2 additional clauses)',
        'clauses': [
            "Garden Maintenance Responsibilities (مسؤوليات صيانة الحديقة)",
            "Landscaping Restrictions (قيود تنسيق الحدائق)"
        ]
    },
    'villa': {
        'title': 'VILLA-SPECIFIC CLAUSES (3 additional clauses)',
        'clauses': [
            "Pool Maintenance & Safety (صيانة المسبح والسلامة)",
            "External Areas Responsibilities (مسؤوليات المناطق الخارجية)",
            "Staff/Helper Accommodation (إقامة العمالة المساعدة)"
        ]
    },
    'office': {
        'title': 'OFFICE LEASE CLAUSES (4 additional clauses)',
        'clauses': [
            "Working Hours & Access (ساعات العمل والدخول)",
            "Office Equipment & Fixtures (المعدات والتجهيزات المكتبية)",
            "Client/Visitor Policies (سياسات العملاء والزوار)",
            "Data/Internet Infrastructure (البنية التحتية للبيانات والإنترنت)"
        ]
    },
    'shop': {
        'title': 'SHOP/RETAIL CLAUSES (4 additional clauses)',
        'clauses': [
            "Display Window Rights (حقوق واجهة العرض)",
            "Operating Hours Restrictions (قيود ساعات التشغيل)",
            "Customer Parking Arrangements (ترتيبات مواقف العملاء)",
            "Retail License Compliance (الامتثال لترخيص البيع بالتجزئة)"
        ]
    },
    'warehouse': {
        'title': 'WAREHOUSE CLAUSES (4 additional clauses)',
        'clauses': [
            "Loading/Unloading Facilities (مرافق التحميل والتفريغ)",
            "Storage Material Restrictions (قيود مواد التخزين)",
            "Fire Safety & Security Requirements (متطلبات السلامة من الحرائق والأمن)",
            "Inventory Management Rules (قواعد إدارة المخزون)"
        ]
    },
    'agricultural': {
        'title': 'AGRICULTURAL LAND CLAUSES (5 additional clauses)',
        'clauses': [
            "Permitted Crops/Activities (المحاصيل/الأنشطة المسموحة)",
            "Water Rights & Irrigation (حقوق المياه والري)",
            "Equipment & Machinery Storage (تخزين المعدات والآلات)",
            "Harvest Rights & Distribution (حقوق الحصاد والتوزيع)",
            "Land Improvement Ownership (ملكية تحسينات الأرض)"
        ]
    },
    'tourism': {
        'title': 'TOURISM/VACATION RENTAL CLAUSES (4 additional clauses)',
        'clauses': [
            "Tourist Registration Requirements (متطلبات تسجيل السياح)",
            "Cleaning & Housekeeping Services (خدمات التنظيف)",
            "Maximum Occupancy Limits (حد أقصى للإشغال)",
            "Cancellation & Refund Policy (سياسة الإلغاء والاسترداد)"
        ]
    },
    'seasonal': {
        'title': 'SEASONAL LEASE CLAUSES (3 additional clauses)',
        'clauses': [
            "Off-Season Property Access (الوصول للعقار خارج الموسم)",
            "Seasonal Rate Variations (تفاوت الأسعار الموسمية)",
            "Property Winterization/Preparation (تجهيز العقار للمواسم)"
        ]
    },
    'students': {
        'title': 'STUDENT HOUSING CLAUSES (4 additional clauses)',
        'clauses': [
            "Academic Calendar Alignment (التوافق مع التقويم الأكاديمي)",
            "Parent/Guardian Guarantees (ضمانات ولي الأمر)",
            "Study Environment Rules (قواعد بيئة الدراسة)",
            "Summer Break Arrangements (ترتيبات العطلة الصيفية)"
        ]
    }
}


def generate_contextual_clauses(contexts: Dict[str, bool]) -> str:
    """
    Generate additional clause requirements based on detected contexts.

    Args:
        contexts: e.g. {'furnished': True, 'commercial': False, ...}

    Returns:
        Formatted string of context-specific clauses (empty string if none active)
    """
    active = [
        CONTEXTUAL_CLAUSE_TEMPLATES[ctx]
        for ctx, is_active in contexts.items()
        if is_active and ctx in CONTEXTUAL_CLAUSE_TEMPLATES
    ]

    if not active:
        return ""

    sections = []
    for template in active:
        clauses = "\n".join(f"- {c}" for c in template["clauses"])
        sections.append(f"\n**{template['title']}:**\n{clauses}")

    return "\n\n**ADDITIONAL CONTEXT-SPECIFIC CLAUSES:**" + "".join(sections)


def get_standard_clauses_text() -> str:
    """Get formatted text of standard contract clauses."""
    return "\n".join(STANDARD_CLAUSES)