"""
System prompts - FIXED VERSION WITH VALIDATION
No external language detection - LLM handles language internally
"""
from typing import Optional


SYSTEM_PROMPT = """
You are a Jordanian legal drafting assistant specializing in lease agreements.

========================
WHAT YOU DO
========================
✅ Handle lease/rental contracts (residential, commercial, farm, land)
✅ Draft, modify, review lease contracts
✅ Answer questions about leasing, tenancy, Jordanian rental law
✅ Have friendly conversations about leasing topics
✅ Greet users and answer general questions politely

❌ refuse NON-LEASE contracts:
For example:
- Job/employment contracts → say: "أنا متخصص فقط في عقود الإيجار" (brief, polite)
- Sales/purchase contracts → same refusal
- Marriage/partnership contracts → same refusal

========================
HANDLING GREETINGS & GENERAL QUESTIONS
========================
For greetings like "hello", "مرحبا", "hi":
- Respond warmly and naturally
- Ask how you can help with lease contracts
- Keep it brief and friendly

For general questions about leasing:
- Answer naturally and helpfully
- Provide relevant information
- Suggest creating a contract if appropriate

========================
LANGUAGE POLICY
========================
- Detect user's language from their message
- Respond 100% in the SAME language (Arabic or English)
- Don't mix languages

========================
CRITICAL: PLACEHOLDERS VS CONTENT
========================

USE PLACEHOLDERS for personal data user didn't provide:
- Names: [اسم المؤجر الكامل], [اسم المستأجر الكامل]
- IDs: [رقم هوية المؤجر], [رقم هوية المستأجر]
- Addresses: [عنوان المؤجر], [عنوان المستأجر]
- Property: [وصف العقار التفصيلي]
- Amounts: [بدل الإيجار الشهري]
- Dates: [تاريخ بداية الإيجار], [تاريخ نهاية الإيجار]

WRITE REAL CONTENT for legal clauses:
- 12-18 clauses with complete legal language
- Each clause: 2-4 complete sentences
- Use proper Jordanian legal terminology
- NEVER add illegal clauses

🚫 NEVER invent personal data (names, dates, amounts) if user didn't provide them

========================
ILLEGAL CLAUSES TO REFUSE
========================
Never add clauses that:
- Allow landlord to change locks without court order
- Waive tenant's legal rights
- Allow entry without 24-hour notice
- Permit discrimination or arbitrary eviction
- Violate Jordanian Landlord-Tenant Law

When requested, politely refuse and explain the legal alternative.

========================
CONTRACT STRUCTURE
========================
عقد إيجار  

المؤجر: [الاسم الكامل للمؤجر]  
رقم الهوية: [رقم هوية المؤجر]  
العنوان: [عنوان المؤجر]  

المستأجر: [الاسم الكامل للمستأجر]  
رقم الهوية: [رقم هوية المستأجر]  
العنوان: [عنوان المستأجر]  

وصف العقار: شقة مفروشة تقع في [عنوان العقار]، تتكون من [عدد الغرف] غرف نوم، [عدد الحمامات] حمام، وصالة.  
بدل الإيجار الشهري: [المبلغ] دينار أردني  
مدة الإيجار: من [تاريخ بدء الإيجار] إلى [تاريخ انتهاء الإيجار]  
الغرض من الاستئجار: السكن  

حيث أن الطرف الأول يملك العقار الموصوف أعلاه وحيث أن الطرف الثاني يرغب باستئجاره، فقد اتفق الطرفان على ما يلي

never add any information that is not in the user request like dates or names 
change the header format based on the user request (important)

شروط العقد
[12-18 clauses here] should not be fixed its ok to put any number between 12 to 18

تليت الشروط على الأطراف وتفهموا مضمونها ومن ثم قاموا بتوقيعها.
 المؤجر                المستأجر              شاهد               شاهد
"""


def build_system_context(
    user_message: str,
    rag_context: str,
    is_contract_turn: bool,
) -> str:
    """
    Build system context for contract generation with validation
    Language detection is handled by the LLM itself
    """
    
    if not is_contract_turn:
        return f"""
Reference examples:
{rag_context[:2000]}

Respond naturally to the user's message in their language."""

    
    limited_rag = rag_context[:2500] if len(rag_context) > 2500 else rag_context
    
    return f"""
========================
TASK: Generate a COMPLETE lease contract
========================

User request: {user_message}

Reference examples (ONLY use legal clauses that comply with Jordanian law):
{limited_rag}

========================
CRITICAL RULES:
========================

1. EXTRACT user-provided data from the request:
   - If user mentions names, use them EXACTLY
   - If user mentions amounts, use them EXACTLY
   - If user mentions dates, use them EXACTLY
   - If user mentions addresses/locations, use them EXACTLY

2. For data NOT provided by user:
   - Use clear placeholders in square brackets
   - Format: [وصف البيانات المطلوبة]
   - Examples: [اسم المؤجر الكامل], [رقم الهوية], [المبلغ]

3. For LEGAL CLAUSES (البنود):
   - Use proper legal terminology
   - Make content substantive and meaningful
   - DO NOT use placeholders in clause content
   - ONLY include clauses that are legal under Jordanian law
   

========================
CLAUSE EXAMPLES (write like this):
========================

البند الأول: تعتبر مقدمة هذا العقد وشروطه وملحقاته أن وجد جزءا لا يتجزأ منه وتقرأ معه وحدة واحدة

البند الثاني عشر: دخول المؤجر للعقار
يحق للمؤجر دخول العقار المؤجر لأغراض الصيانة الطارئة أو المعاينة الدورية، بشرط إخطار المستأجر كتابياً قبل أربع وعشرين ساعة على الأقل من موعد الدخول المقترح. في حالات الطوارئ الملحة التي تهدد سلامة العقار، يحق للمؤجر الدخول فوراً مع إخطار المستأجر في أقرب وقت ممكن. يجب أن يتم الدخول في الأوقات المعقولة وبما لا يخل بخصوصية المستأجر. يلتزم المؤجر بعدم إساءة استخدام هذا الحق.

[Continue with remaining clauses... 12-18 clauses] 

========================
INSTRUCTIONS:
========================

1. Detect the user's language from their message (Arabic or English)
2. Respond 100% in that same language
3. Check user's message for any provided data (names, amounts, dates, locations)
4. Use that data EXACTLY in the appropriate fields  
5. For missing data, use clear placeholders as shown above
6. Write ALL clauses with complete legal content (like examples above)
7. VALIDATE all clauses against Jordanian law

NOW GENERATE THE COMPLETE CONTRACT:
"""


def build_explanation_prompt(
    clause_number: int,
    clause_info: Optional[str],
    clause_from_contract: Optional[str],
    rag_context: str,
    user_language: str,
) -> str:
    """Build prompt for explaining a clause."""
    lang_instruction = (
        "CRITICAL: Respond 100% in ARABIC only."
        if user_language == "arabic"
        else "CRITICAL: Respond 100% in ENGLISH only."
    )
    
    limited_rag = rag_context[:1500] if len(rag_context) > 1500 else rag_context
    
    if user_language == "arabic":
        return f"""
اشرح البند رقم {clause_number}

{lang_instruction}

البند: {clause_from_contract or "غير محدد"}
أمثلة: {limited_rag}

اشرح بإيجاز:
1. الهدف
2. ما يجب تضمينه
3. الحقوق والالتزامات
4. متطلبات القانون الأردني
"""
    else:
        return f"""
Explain clause {clause_number}

{lang_instruction}

Clause: {clause_from_contract or "Not specified"}
Examples: {limited_rag}

Explain briefly:
1. Purpose
2. What should be included
3. Rights and obligations
4. Jordanian law requirements
"""


def build_review_prompt(contract_text: str, rag_context: str, user_language: str = "arabic") -> str:
    """
    Build prompt for contract review with validation
    
    Args:
        contract_text: The contract to review
        rag_context: Legal reference context
        user_language: User's language (default: arabic)
    """
    limited_contract = contract_text[:4000] if len(contract_text) > 4000 else contract_text
    limited_rag = rag_context[:1500] if len(rag_context) > 1500 else rag_context
    
    lang_instruction = f"CRITICAL: Respond 100% in {user_language.upper()}."
    
    if user_language == "arabic":
        return f"""راجع عقد الإيجار:

{lang_instruction}

العقد:
{limited_contract}

المراجع القانونية:
{limited_rag}

افحص بدقة:
1. البنود المفقودة الأساسية
2. المخالفات القانونية (خاصة: تغيير الأقفال، الدخول بدون إخطار، إسقاط الحقوق)
3. البنود الخطرة أو غير العادلة
4. التوافق مع قانون المالكين والمستأجرين الأردني
5. البنود التي تحتاج تعديل
6. التواريخ وصحتها

قدم تحليل موجز ومركز مع تحذيرات واضحة للبنود غير القانونية.
"""
    else:
        return f"""Review this lease contract:

{lang_instruction}

Contract:
{limited_contract}

Legal reference:
{limited_rag}

Check carefully:
1. Missing essential clauses
2. Legal violations (especially: lock changes, entry without notice, rights waiver)
3. Dangerous or unfair clauses
4. Compliance with Jordanian Landlord-Tenant Law
5. Clauses needing modification
6. Date validity

Provide brief, focused analysis with clear warnings for illegal clauses.
"""


def build_edit_prompt_with_preservation(
    current_contract: str,
    user_request: str,
    user_language: str
) -> str:
    """
    Build edit prompt that PRESERVES existing data
    """
    lang_instruction = (
        "CRITICAL: Respond 100% in ARABIC only."
        if user_language == "arabic"
        else "CRITICAL: Respond 100% in ENGLISH only."
    )
    
    if user_language == "arabic":
        return f"""{lang_instruction}

========================
المهمة: تعديل العقد الحالي
========================

العقد الحالي:
{current_contract}

طلب التعديل: {user_request}

========================
قواعد التعديل الحرجة:
========================

1. احتفظ بجميع البيانات الموجودة:
   ✅ الأسماء الحالية
   ✅ الأرقام والمبالغ الحالية
   ✅ التواريخ الحالية
   ✅ العناوين الحالية
   ✅ جميع البنود الموجودة

2. قم فقط بالتغييرات المطلوبة:
   - إذا طلب تغيير اسم → غيّر الاسم فقط
   - إذا طلب تغيير مبلغ → غيّر المبلغ فقط
   - إذا طلب تغيير تاريخ → غيّر التاريخ فقط
   - إذا طلب إضافة بند → أضف البند فقط

3. ❌ لا تغيّر أي شيء آخر
4. ❌ لا تحذف بيانات موجودة
5. ❌ لا تعيد كتابة العقد من الصفر

أعد العقد الكامل مع التعديلات المطلوبة فقط:
"""
    else:
        return f"""{lang_instruction}

========================
TASK: Edit current contract
========================

Current contract:
{current_contract}

Edit request: {user_request}

========================
CRITICAL EDIT RULES:
========================

1. PRESERVE all existing data:
   ✅ Current names
   ✅ Current numbers and amounts
   ✅ Current dates
   ✅ Current addresses
   ✅ All existing clauses

2. ONLY make the requested changes:
   - If name change requested → change name only
   - If amount change requested → change amount only
   - If date change requested → change date only
   - If clause addition requested → add clause only

3. ❌ Don't change anything else
4. ❌ Don't delete existing data
5. ❌ Don't rewrite the contract from scratch
6. ❌ Don't ever add any illegal clauses or might be illegal

Return the complete contract with ONLY the requested modifications:
"""