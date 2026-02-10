"""
Migration Script: Pinecone → Supabase

This script reads your existing JSONL files and migrates them to Supabase.

Your data structure:
- leases_chunks.jsonl: Lease contract clauses (clause by clause)
- laws_chunks.jsonl: Jordanian law documents (1 law per chunk)
- mistakes_chunks.jsonl: Common mistakes (1 mistake per chunk)

Expected JSONL format:
{
    "id": "lease:file.txt:1",
    "text": "clause text here",
    "metadata": {"doc_type": "lease", "source_file": "file.txt", ...}
}
"""

import os
import json
from typing import List, Dict, Any
from tqdm import tqdm
from openai import OpenAI
from supabase import create_client

from dotenv import load_dotenv
load_dotenv()
# =========================
# CONFIG
# =========================

PREPARED_FOLDER = "prepared"
INPUT_FILES = {
    "leases_chunks.jsonl": "lease",      # Maps to lease_clauses table
    "laws_chunks.jsonl": "law",          # Maps to law_documents table
    "mistakes_chunks.jsonl": "mistake"   # Maps to mistake_documents table
}

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
BATCH_SIZE = 50  # Number of documents to process at once


# =========================
# SUPABASE TABLE NAMES
# =========================

TABLES = {
    "lease": "lease_clauses",
    "law": "law_documents",
    "mistake": "mistake_documents"
}


# =========================
# HELPERS
# =========================

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load JSONL file"""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def chunk_list(lst, n):
    """Split list into chunks of size n"""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


# =========================
# MAIN MIGRATION FUNCTION
# =========================

def main():
    # Get API keys from environment
    openai_key = os.environ.get("OPENAI_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not openai_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")
    if not supabase_url:
        raise RuntimeError("Missing SUPABASE_URL env var")
    if not supabase_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_KEY env var")

    # Initialize clients
    print("🔧 Initializing clients...")
    openai_client = OpenAI(api_key=openai_key)
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Clients initialized\n")

    # Process each file
    total_inserted = 0
    
    for filename, doc_type in INPUT_FILES.items():
        filepath = os.path.join(PREPARED_FOLDER, filename)
        table_name = TABLES[doc_type]
        
        if not os.path.exists(filepath):
            print(f"⚠️  Warning: {filepath} not found, skipping...")
            continue
        
        print(f"\n{'='*60}")
        print(f"📄 Processing: {filename} → {table_name}")
        print(f"{'='*60}")
        
        # Load data
        rows = load_jsonl(filepath)
        print(f"📊 Loaded {len(rows)} records")
        
        # Validate schema
        if rows:
            sample = rows[0]
            if "id" not in sample or "text" not in sample:
                print(f"❌ Invalid schema in {filename}. Expected 'id' and 'text' fields.")
                continue
        
        # Process in batches
        inserted = 0
        for batch in tqdm(list(chunk_list(rows, BATCH_SIZE)), desc=f"Migrating {doc_type}"):
            texts = [row["text"] for row in batch]
            ids = [row["id"] for row in batch]
            metadatas = [row.get("metadata", {}) for row in batch]
            
            try:
                # Generate embeddings
                emb_response = openai_client.embeddings.create(
                    model=EMBED_MODEL,
                    input=texts
                )
                
                # Prepare data for Supabase
                data = []
                for i, emb in enumerate(emb_response.data):
                    # Ensure doc_type is in metadata
                    metadata = metadatas[i].copy()
                    if "doc_type" not in metadata:
                        metadata["doc_type"] = doc_type
                    
                    data.append({
                        "id": ids[i],
                        "text": texts[i],
                        "embedding": emb.embedding,
                        "metadata": metadata
                    })
                
                # Insert into Supabase
                supabase.table(table_name).upsert(data).execute()
                inserted += len(data)
                
            except Exception as e:
                print(f"\n❌ Error processing batch: {e}")
                continue
        
        print(f"\n✅ Inserted {inserted}/{len(rows)} documents into {table_name}")
        total_inserted += inserted
    
    print(f"\n{'='*60}")
    print(f"🎉 MIGRATION COMPLETE!")
    print(f"{'='*60}")
    print(f"Total documents migrated: {total_inserted}")
    
    # Verify migration
    print(f"\n{'='*60}")
    print(f"🔍 VERIFYING MIGRATION")
    print(f"{'='*60}")
    
    for doc_type, table_name in TABLES.items():
        try:
            result = supabase.table(table_name).select("id", count="exact").execute()
            count = result.count or 0
            print(f"✅ {table_name}: {count} documents")
        except Exception as e:
            print(f"❌ Error counting {table_name}: {e}")
    
    print(f"\n{'='*60}")
    print("🧪 TESTING RETRIEVAL")
    print(f"{'='*60}")
    
    # Test queries for each doc type
    test_queries = [
        ("عقد ايجار شقة مفروشة", "lease", "Lease query"),
        ("قانون المالكين والمستأجرين", "law", "Law query"),
        ("أخطاء شائعة في عقود الإيجار", "mistake", "Mistake query")
    ]
    
    for query_text, doc_type, label in test_queries:
        print(f"\n🔍 {label}: '{query_text}'")
        table_name = TABLES[doc_type]
        
        try:
            # Generate query embedding
            q_emb = openai_client.embeddings.create(
                model=EMBED_MODEL,
                input=[query_text]
            ).data[0].embedding
            
            # Try RPC function first
            try:
                results = supabase.rpc(
                    'match_documents',
                    {
                        'query_embedding': q_emb,
                        'match_count': 3,
                        'filter': {},
                        'table_name': table_name
                    }
                ).execute()
                
                if results.data:
                    print(f"✅ Found {len(results.data)} matches using RPC:")
                    for match in results.data[:3]:
                        metadata = match.get('metadata', {})
                        score = match.get('similarity', 0)
                        print(f"  • Score: {round(score, 4)} | File: {metadata.get('source_file', 'N/A')}")
                        print(f"    Text: {match['text'][:100]}...")
                else:
                    print(f"⚠️  No matches found")
                    
            except Exception as rpc_error:
                print(f"⚠️  RPC function not available yet (this is OK): {rpc_error}")
                print(f"   You can still use the fallback search in supabase_client.py")
                
        except Exception as e:
            print(f"❌ Test query failed: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SUPABASE MIGRATION SCRIPT")
    print("Pinecone → Supabase + Cohere")
    print("="*60 + "\n")
    
    main()
    
    print("\n" + "="*60)
    print("✅ ALL DONE!")