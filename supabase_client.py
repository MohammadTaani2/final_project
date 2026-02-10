"""
Supabase Vector Store Client with Cohere Reranking

This module handles:
1. Connecting to Supabase pgvector database
2. Storing embeddings in appropriate tables (lease_clauses, law_documents, mistake_documents)
3. Similarity search with metadata filtering
4. Cohere reranking for improved relevance
"""

from typing import List, Dict, Optional, Any
import cohere
from supabase import create_client, Client
from openai import OpenAI


class SupabaseVectorStore:
    """
    Vector store using Supabase (pgvector) with Cohere reranking
    
    Supports three document types:
    - lease: Lease contract clauses (table: lease_clauses)
    - law: Jordanian law documents (table: law_documents)
    - mistake: Common mistakes in writing (table: mistake_documents)
    """
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        cohere_api_key: str,
        embed_model: str = "text-embedding-3-small",
        cohere_model: str = "rerank-multilingual-v3.0"
    ):
        """
        Initialize Supabase vector store
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
            openai_api_key: OpenAI API key for embeddings
            cohere_api_key: Cohere API key for reranking
            embed_model: OpenAI embedding model
            cohere_model: Cohere reranking model (supports Arabic)
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai = OpenAI(api_key=openai_api_key)
        self.cohere = cohere.Client(cohere_api_key)
        self.embed_model = embed_model
        self.cohere_model = cohere_model
        
        # Table mapping for different document types
        self.tables = {
            "lease": "lease_clauses",
            "law": "law_documents",
            "mistake": "mistake_documents",
        }
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai.embeddings.create(
                model=self.embed_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise
    
    def insert(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any],
        doc_type: str = "lease"
    ) -> bool:
        """
        Insert document into Supabase
        
        Args:
            doc_id: Unique document ID
            text: Document text
            metadata: Document metadata (e.g., source_file, clause_id, etc.)
            doc_type: Document type (lease/law/mistake)
            
        Returns:
            True if successful
        """
        try:
            table_name = self.tables.get(doc_type, "lease_clauses")
            embedding = self._get_embedding(text)
            
            data = {
                "id": doc_id,
                "text": text,
                "embedding": embedding,
                "metadata": metadata
            }
            
            result = self.supabase.table(table_name).upsert(data).execute()
            return True
            
        except Exception as e:
            print(f"❌ Error inserting document {doc_id}: {e}")
            return False
    
    def search(
        self,
        query: str,
        doc_type: str = "lease",
        top_k: int = 50,
        rerank_top_k: int = 8,
        metadata_filter: Optional[Dict] = None,
        use_reranking: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents with optional Cohere reranking
        
        Args:
            query: Search query
            doc_type: Document type to search (lease/law/mistake)
            top_k: Number of results to retrieve before reranking
            rerank_top_k: Number of results to keep after reranking
            metadata_filter: Optional metadata filters
            use_reranking: Whether to use Cohere reranking
            
        Returns:
            List of results with text, metadata, and score
        """
        try:
            # Step 1: Get embedding for query
            query_embedding = self._get_embedding(query)
            table_name = self.tables.get(doc_type, "lease_clauses")
            
            # Step 2: Perform similarity search using RPC function
            # NOTE: Parameter order matches the SQL function signature
            try:
                results = self.supabase.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding,
                        'match_count': top_k,
                        'table_name': table_name,
                        'filter': metadata_filter or {}
                    }
                ).execute()
            except Exception as rpc_error:
                # Fallback to manual search if RPC doesn't exist
                print(f"⚠️ RPC function not found, using fallback search: {rpc_error}")
                return self._fallback_search(query, doc_type, top_k, rerank_top_k, use_reranking)
            
            if not results.data:
                return []
            
            # Step 3: Format results
            documents = []
            for row in results.data:
                documents.append({
                    'id': row['id'],
                    'text': row['text'],
                    'metadata': row.get('metadata', {}),
                    'similarity': row.get('similarity', 0)
                })
            
            # Step 4: Apply Cohere reranking if enabled
            if use_reranking and len(documents) > 0:
                documents = self._rerank_with_cohere(
                    query=query,
                    documents=documents,
                    top_k=rerank_top_k
                )
            else:
                # Just take top_k without reranking
                documents = documents[:rerank_top_k]
            
            return documents
            
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return []
    
    def _fallback_search(
        self,
        query: str,
        doc_type: str,
        top_k: int,
        rerank_top_k: int,
        use_reranking: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fallback search using basic Supabase query with manual similarity calculation
        Used if RPC function doesn't exist yet or tables are not set up
        """
        try:
            table_name = self.tables.get(doc_type, "lease_clauses")
            
            # Try to check if table exists first
            try:
                # Simple count query to verify table exists
                count_result = self.supabase.table(table_name).select("id", count="exact").limit(1).execute()
                print(f"✅ Table '{table_name}' exists with {count_result.count} documents")
            except Exception as table_error:
                print(f"❌ Table '{table_name}' does not exist or is not accessible: {table_error}")
                print(f"⚠️ Please run the SUPABASE_SETUP.sql file to create tables and RPC function")
                return []
            
            # Get query embedding
            query_embedding = self._get_embedding(query)
            
            # Get all documents (limited to avoid too much data)
            result = self.supabase.table(table_name).select("*").limit(min(top_k * 3, 200)).execute()
            
            if not result.data:
                print(f"⚠️ No documents found in table '{table_name}'")
                return []
            
            # Calculate similarity manually
            documents = []
            for row in result.data:
                if row.get('embedding'):
                    similarity = self._cosine_similarity(query_embedding, row['embedding'])
                    documents.append({
                        'id': row['id'],
                        'text': row['text'],
                        'metadata': row.get('metadata', {}),
                        'similarity': similarity
                    })
            
            # Sort by similarity
            documents.sort(key=lambda x: x['similarity'], reverse=True)
            documents = documents[:top_k]
            
            # Rerank if requested
            if use_reranking and len(documents) > 0:
                documents = self._rerank_with_cohere(query, documents, rerank_top_k)
            else:
                documents = documents[:rerank_top_k]
            
            return documents
            
        except Exception as e:
            print(f"❌ Fallback search failed: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)
        except Exception as e:
            print(f"⚠️ Error calculating similarity: {e}")
            return 0.0
    
    def _rerank_with_cohere(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using Cohere's reranking API
        
        This significantly improves relevance by understanding semantic meaning
        beyond simple embedding similarity.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked documents (best matches first)
        """
        try:
            # Prepare documents for Cohere
            texts = [doc['text'] for doc in documents]
            
            # Call Cohere rerank API
            rerank_response = self.cohere.rerank(
                model=self.cohere_model,
                query=query,
                documents=texts,
                top_n=min(top_k, len(documents))
            )
            
            # Reorder documents based on Cohere scores
            reranked_docs = []
            for result in rerank_response.results:
                original_doc = documents[result.index]
                # Add Cohere relevance score
                original_doc['rerank_score'] = result.relevance_score
                reranked_docs.append(original_doc)
            
            return reranked_docs
            
        except Exception as e:
            print(f"⚠️ Reranking failed, using original order: {e}")
            # Fallback to original order if reranking fails
            return documents[:top_k]
    
    def delete(self, doc_id: str, doc_type: str = "lease") -> bool:
        """Delete document from Supabase"""
        try:
            table_name = self.tables.get(doc_type, "lease_clauses")
            self.supabase.table(table_name).delete().eq("id", doc_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error deleting document {doc_id}: {e}")
            return False
    
    def count(self, doc_type: str = "lease") -> int:
        """Count documents in table"""
        try:
            table_name = self.tables.get(doc_type, "lease_clauses")
            result = self.supabase.table(table_name).select("id", count="exact").execute()
            return result.count or 0
        except Exception as e:
            print(f"❌ Error counting documents: {e}")
            return 0
    
    def batch_insert(
        self,
        documents: List[Dict[str, Any]],
        doc_type: str = "lease",
        batch_size: int = 50
    ) -> int:
        """
        Insert multiple documents in batches
        
        Args:
            documents: List of dicts with 'id', 'text', 'metadata'
            doc_type: Document type
            batch_size: Number of documents per batch
            
        Returns:
            Number of successfully inserted documents
        """
        inserted = 0
        table_name = self.tables.get(doc_type, "lease_clauses")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                # Generate embeddings for batch
                texts = [doc['text'] for doc in batch]
                response = self.openai.embeddings.create(
                    model=self.embed_model,
                    input=texts
                )
                
                # Prepare data for insertion
                data = []
                for j, doc in enumerate(batch):
                    data.append({
                        "id": doc['id'],
                        "text": doc['text'],
                        "embedding": response.data[j].embedding,
                        "metadata": doc.get('metadata', {})
                    })
                
                # Insert batch
                self.supabase.table(table_name).upsert(data).execute()
                inserted += len(batch)
                print(f"✅ Inserted {len(batch)} documents ({inserted} total)")
                
            except Exception as e:
                print(f"❌ Error inserting batch: {e}")
                continue
        
        return inserted