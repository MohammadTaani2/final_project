"""
Configuration settings for Jordanian Legal Lease Assistant - SUPABASE + COHERE VERSION

Migration changes:
- Removed Pinecone configuration
- Added Supabase configuration (URL + Service Key)
- Added Cohere configuration for reranking
- Updated to use gpt-4o-2024-08-06 (latest GPT-4o model)
- Note: There is no "gpt-5-mini" model yet from OpenAI
"""

import os
from dataclasses import dataclass


# =========================
# API Configuration
# =========================

@dataclass
class APIConfig:
    """API configuration settings"""
    openai_api_key: str
    supabase_url: str
    supabase_key: str
    cohere_api_key: str

    @classmethod
    def from_env(cls) -> "APIConfig":
        openai_key = os.environ.get("OPENAI_API_KEY")
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        cohere_key = os.environ.get("COHERE_API_KEY")

        if not openai_key:
            raise ValueError("Missing OPENAI_API_KEY")
        if not supabase_url:
            raise ValueError("Missing SUPABASE_URL")
        if not supabase_key:
            raise ValueError("Missing SUPABASE_SERVICE_KEY")
        if not cohere_key:
            raise ValueError("Missing COHERE_API_KEY")

        return cls(
            openai_api_key=openai_key,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            cohere_api_key=cohere_key
        )


# =========================
# Model Configuration
# =========================

@dataclass
class ModelConfig:
    """Model configuration settings"""

    # Embedding model (for Supabase vectors)
    embed_model: str = "text-embedding-3-small"
    embed_dimensions: int = 1536
    
   
    chat_model: str = "gpt-4o-mini"  
    
    # Retrieval settings with Cohere reranking
    top_k: int = 30  # Get more results from Supabase before reranking
    rerank_top_k: int = 12  # After Cohere reranking, keep top 8 most relevant
    
    # Token limits
    max_completion_tokens: int = 4000
    max_tokens: int = 4000
    
    # Sampling
    temperature: float = 0.1
    
    # Cohere reranking configuration
    cohere_model: str = "rerank-multilingual-v3.0"  # Supports Arabic + English
    use_reranking: bool = True  # Enable/disable Cohere reranking
    
    # Determinism
    use_seed: bool = False
    default_seed: int = 42


# =========================
# UI Configuration
# =========================

@dataclass
class UIConfig:
    """UI configuration settings"""
    page_title: str = "مساعد العقود القانوني الأردني"
    page_icon: str = "⚖️"
    layout: str = "wide"


# =========================
# Document Types (Supabase Tables)
# =========================

DOC_TYPES = {
    "LEASE": "lease",
    "LAW": "law",
    "MISTAKE": "mistake",
}

# Supabase table names mapping
SUPABASE_TABLES = {
    "lease": "lease_clauses",
    "law": "law_documents",
    "mistake": "mistake_documents",
}


# =========================
# Context Detection Patterns
# =========================

CONTEXT_PATTERNS = {
    "furnished": ["furnished", "مفروش", "مفروشة", "أثاث", "furniture"],
    "commercial": ["commercial", "business", "تجاري", "تجارية", "محل", "مكتب"],
    "short_term": ["short", "daily", "weekly", "monthly", "قصيرة", "يومي", "أسبوعي", "شهري"],
    "shared": ["shared", "roommate", "مشترك", "مشاركة", "زميل سكن"],
    "with_parking": ["parking", "garage", "موقف", "جراج", "سيارة"],
    "with_pets": ["pet", "dog", "cat", "حيوان", "كلب", "قطة", "حيوانات أليفة"],
    "with_garden": ["garden", "yard", "حديقة", "فناء"],
    "villa": ["villa", "فيلا"],
    "office": ["office", "مكتب"],
    "shop": ["shop", "store", "retail", "محل", "متجر"],
    "warehouse": ["warehouse", "storage", "مستودع", "مخزن"],
    "agricultural": ["agricultural", "farm", "land", "زراعي", "مزرعة", "أرض"],
    "tourism": ["tourism", "vacation", "holiday", "سياحي", "إجازة", "عطلة"],
    "seasonal": ["seasonal", "summer", "winter", "موسمي", "صيفي", "شتوي"],
    "students": ["student", "university", "college", "طالب", "جامعة", "طلاب"],
}