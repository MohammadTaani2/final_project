"""
LLM Client - INTELLIGENT ROUTING WITH DATE VALIDATION
- Let the LLM understand intent, not regex patterns
- Validate dates BEFORE sending to LLM
- Preserve contracts on failures
- Return (message, contract, action) tuple
"""

import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from supabase_client import SupabaseVectorStore
from config import ModelConfig, DOC_TYPES
from utils import detect_lease_context
from prompts import (
    SYSTEM_PROMPT,
    build_system_context,
    build_review_prompt,
    build_explanation_prompt,
    build_edit_prompt_with_preservation,
)
from date_validator import DateValidator

MIN_CONTRACT_LENGTH = 200


class LLMClient:
    def __init__(
        self,
        openai_api_key: str,
        supabase_url: str,
        supabase_key: str,
        cohere_api_key: str,
        config: ModelConfig,
    ):
        self.client = OpenAI(api_key=openai_api_key)
        self.config = config
        self.vector_store = SupabaseVectorStore(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key,
            cohere_api_key=cohere_api_key,
            embed_model=config.embed_model,
            cohere_model=config.cohere_model,
        )
        self._contract_memory: Dict[str, Optional[str]] = {}
        self.date_validator = DateValidator()

    def set_current_contract(self, contract: str, session_id: str = "default"):
        self._contract_memory[session_id] = contract
        print(f"💾 Stored contract in memory for session {session_id} (length: {len(contract)})")

    def get_current_contract(self, session_id: str = "default") -> Optional[str]:
        contract = self._contract_memory.get(session_id)
        if contract:
            print(f"📖 Retrieved contract from memory (length: {len(contract)})")
        return contract

    def clear_contract(self, session_id: str = "default"):
        if session_id in self._contract_memory:
            del self._contract_memory[session_id]
            print(f"🗑️ Cleared contract from memory for session {session_id}")

    def _retrieve_context(
        self, query: str, doc_types: Optional[List[str]] = None, top_k: int = 10
    ) -> str:
        if doc_types is None:
            doc_types = [DOC_TYPES["LEASE"]]

        all_results = []
        for doc_type in doc_types:
            try:
                results = self.vector_store.search(
                    query=query,
                    doc_type=doc_type,
                    top_k=self.config.top_k,
                    rerank_top_k=self.config.rerank_top_k,
                    use_reranking=self.config.use_reranking,
                )
                all_results.extend(results)
            except Exception as e:
                print(f"⚠️ Warning: Search failed for {doc_type}: {e}")

        context_parts = []
        for i, result in enumerate(all_results[:top_k], 1):
            score = result.get("rerank_score") or result.get("similarity", 0)
            text = result.get("text", "")
            context_parts.append(f"[{i}] (score: {score:.3f})\n{text}\n")

        return "\n".join(context_parts)

    def _chat_completion(self, messages: List[Dict], deterministic: bool = False):
        try:
            kwargs = {
                "model": self.config.chat_model,
                "messages": messages,
                "temperature": 0.0 if deterministic else self.config.temperature,
                "max_completion_tokens": self.config.max_completion_tokens,
            }
            if self.config.use_seed and deterministic:
                kwargs["seed"] = self.config.default_seed

            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return None

    def _detect_language(self, text: str) -> str:
        """
        Simple language detection based on Arabic character presence
        """
        if not text:
            return "english"
        
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = sum(1 for c in text if c.isalpha())
        
        if total_chars == 0:
            return "english"
        
        return "arabic" if (arabic_chars / total_chars) > 0.3 else "english"

    def _validate_dates_in_text(self, text: str, lang: str) -> Tuple[bool, Optional[str]]:
        """
        Validate all dates in the text BEFORE sending to LLM.
        Returns (is_valid, error_message_if_invalid)
        """
        print(f"🔍 Validating dates in text...")
        
        all_valid, error_msg, found_dates = self.date_validator.extract_and_validate_dates(
            text=text,
            allow_past_start=False
        )
        
        if not all_valid:
            print(f"❌ Date validation failed: {error_msg}")
            
            # Format error message based on language
            if lang == "arabic":
                alert = f"⚠️ خطأ في التاريخ:\n\n{error_msg}\n\nالرجاء تصحيح التاريخ والمحاولة مرة أخرى."
            else:
                alert = f"⚠️ Date Validation Error:\n\n{error_msg}\n\nPlease correct the date and try again."
            
            return False, alert
        
        if found_dates:
            print(f"✅ All dates valid: {len(found_dates)} date(s) found")
        else:
            print(f"ℹ️ No dates found in text")
        
        return True, None

    def _classify_intent(
        self, user_input: str, has_contract: bool, lang: str
    ) -> Dict[str, any]:
        """
        Ask the LLM to classify the user's intent.
        Returns: {
            'action': 'create' | 'edit' | 'explain' | 'review' | 'chat',
            'confidence': float,
            'reasoning': str
        }
        """
        classification_prompt = f"""You are an intent classifier for a legal contract assistant.

Current context:
- User has existing contract: {"YES" if has_contract else "NO"}
- User language: {lang}

User message: "{user_input}"

Classify the intent into ONE of these actions:
1. "create" - User wants to create/generate a NEW contract (even if one exists)
2. "edit" - User wants to modify/add/remove clauses in existing contract
3. "explain" - User wants explanation of a clause/term
4. "review" - User wants legal review/analysis of contract
5. "chat" - General conversation, questions, or unclear intent

Respond ONLY with valid JSON:
{{
    "action": "create|edit|explain|review|chat",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        messages = [
            {"role": "system", "content": "You are a precise intent classifier. Always respond with valid JSON only."},
            {"role": "user", "content": classification_prompt}
        ]

        response = self._chat_completion(messages, deterministic=True)
        if not response:
            return {"action": "chat", "confidence": 0.0, "reasoning": "API error"}

        try:
            import json
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            print(f"🎯 Intent: {result['action']} (confidence: {result['confidence']:.2f}) - {result['reasoning']}")
            return result
        except Exception as e:
            print(f"⚠️ Intent classification failed: {e}")
            return {"action": "chat", "confidence": 0.0, "reasoning": f"Parse error: {e}"}

    def generate_contract(
        self, user_input: str, context_hints: Optional[Dict] = None
    ) -> Optional[str]:
        """Generate contract with date validation"""
        lang = self._detect_language(user_input)
        
        # ✅ VALIDATE DATES IN USER INPUT FIRST
        dates_valid, error_msg = self._validate_dates_in_text(user_input, lang)
        if not dates_valid:
            print("❌ Cannot generate contract - invalid dates in user input")
            return error_msg
        
        # Proceed with normal generation
        rag_context = self._retrieve_context(
            query=user_input,
            doc_types=[DOC_TYPES["LEASE"]],
            top_k=self.config.rerank_top_k,
        )

        system_context = build_system_context(
            user_message=user_input, 
            rag_context=rag_context, 
            is_contract_turn=True
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": system_context},
        ]

        response = self._chat_completion(messages, deterministic=True)
        if response is None:
            if lang == "arabic":
                return "عذراً، حدث خطأ في إنشاء العقد."
            return "Sorry, error generating contract."

        generated_contract = response.choices[0].message.content.strip()
        
        # ✅ VALIDATE DATES IN GENERATED CONTRACT
        dates_valid, error_msg = self._validate_dates_in_text(generated_contract, lang)
        if not dates_valid:
            print("❌ Generated contract contains invalid dates")
            if lang == "arabic":
                return f"⚠️ العقد المُنشأ يحتوي على تواريخ غير صحيحة:\n\n{error_msg}\n\nالرجاء المحاولة مرة أخرى."
            return f"⚠️ Generated contract contains invalid dates:\n\n{error_msg}\n\nPlease try again."
        
        return generated_contract

    def edit_contract(self, current_contract: str, user_request: str) -> Optional[str]:
        """Edit contract with date validation"""
        lang = self._detect_language(user_request)
        
        # ✅ VALIDATE DATES IN EDIT REQUEST
        dates_valid, error_msg = self._validate_dates_in_text(user_request, lang)
        if not dates_valid:
            print("❌ Cannot edit - invalid dates in user request")
            # Return error message - contract will be preserved by get_chat_response
            return error_msg
        
        # Proceed with edit
        edit_prompt = build_edit_prompt_with_preservation(
            current_contract=current_contract, 
            user_request=user_request, 
            user_language=lang
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": edit_prompt},
        ]

        print("🤖 Calling OpenAI for edit...")
        response = self._chat_completion(messages, deterministic=True)
        if response is None:
            if lang == "arabic":
                return "عذراً، حدث خطأ في التعديل."
            return "Sorry, error during edit."

        edited_contract = response.choices[0].message.content.strip()
        
        # ✅ VALIDATE DATES IN EDITED CONTRACT
        dates_valid, error_msg = self._validate_dates_in_text(edited_contract, lang)
        if not dates_valid:
            print("❌ Edit produced invalid dates - returning error")
            if lang == "arabic":
                return f"⚠️ التعديل أنتج تواريخ غير صحيحة:\n\n{error_msg}\n\nالعقد الأصلي محفوظ."
            return f"⚠️ Edit produced invalid dates:\n\n{error_msg}\n\nOriginal contract preserved."
        
        return edited_contract

    def review_contract(self, contract_text: str) -> Optional[str]:
        """Review contract including date validation"""
        lang = self._detect_language(contract_text)
        
        # Get law context for review
        law_context = self._retrieve_context(
            query=contract_text[:500],
            doc_types=[DOC_TYPES["LAW"], DOC_TYPES["MISTAKE"]],
            top_k=5,
        )

        # ✅ CHECK DATES AND INCLUDE IN REVIEW
        dates_valid, date_error, found_dates = self.date_validator.extract_and_validate_dates(
            text=contract_text,
            allow_past_start=True  # Allow past dates in review mode
        )
        
        # Add date validation results to review prompt
        date_analysis = ""
        if not dates_valid:
            if lang == "arabic":
                date_analysis = f"\n\n⚠️ مشاكل في التواريخ:\n{date_error}"
            else:
                date_analysis = f"\n\n⚠️ Date Issues Found:\n{date_error}"

        review_prompt = build_review_prompt(contract_text, law_context) + date_analysis
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": review_prompt},
        ]

        response = self._chat_completion(messages)
        if response is None:
            if lang == "arabic":
                return "عذراً، حدث خطأ في المراجعة."
            return "Sorry, error during review."

        return response.choices[0].message.content.strip()

    def explain_clause(self, contract_text: str, user_query: str) -> Optional[str]:
        """Explain clause"""
        user_language = self._detect_language(user_query)
        rag_context = self._retrieve_context(
            query=user_query, doc_types=[DOC_TYPES["LEASE"]], top_k=5
        )

        explanation_prompt = build_explanation_prompt(
            clause_number=1,
            clause_info=None,
            clause_from_contract=None,
            rag_context=rag_context,
            user_language=user_language,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": explanation_prompt},
        ]

        response = self._chat_completion(messages)
        if response is None:
            if user_language == "arabic":
                return "عذراً، لم أستطع الشرح."
            return "Sorry, couldn't explain."

        return response.choices[0].message.content.strip()

    def get_chat_response(
        self,
        user_input: str,
        current_contract: Optional[str] = None,
        context_hints: Optional[Dict] = None,
        session_id: str = "default",
    ) -> Tuple[str, Optional[str], str]:
        """
        Returns (message, contract, action) where action is:
        - 'updated': Contract was modified, update display
        - 'unchanged': Contract exists but wasn't modified
        - 'none': No contract exists
        """
        lang = self._detect_language(user_input)
        print(f"\n{'='*60}")
        print(f"📨 User input: {user_input}")
        print(f"🌍 Language: {lang}")

        # Sync contract to memory
        if current_contract and current_contract.strip():
            self.set_current_contract(current_contract, session_id=session_id)

        stored_contract = self.get_current_contract(session_id=session_id)
        active_contract = (
            current_contract.strip()
            if current_contract and current_contract.strip()
            else stored_contract
        )

        has_contract = active_contract is not None
        print(f"📋 Active contract exists: {has_contract}")

        # Let LLM classify intent
        intent = self._classify_intent(user_input, has_contract, lang)
        action_type = intent["action"]

        # Route based on LLM intent classification
        if action_type == "create":
            print("📝 Routing to: CREATE")
            contract = self.generate_contract(user_input, context_hints)
            
            # Check if it's an error message (from date validation)
            if contract and (contract.startswith("⚠️") or "خطأ" in contract[:50]):
                # It's an error message
                if active_contract:
                    return (contract, active_contract, "unchanged")
                return (contract, None, "none")
            
            # It's a valid contract
            if contract:
                self.set_current_contract(contract, session_id=session_id)
                msg = "تم إنشاء العقد بنجاح ✓" if lang == "arabic" else "Contract created successfully ✓"
                return (msg, contract, "updated")
            
            error_msg = "خطأ في إنشاء العقد" if lang == "arabic" else "Error creating contract"
            if active_contract:
                return (error_msg, active_contract, "unchanged")
            return (error_msg, None, "none")

        elif action_type == "edit":
            print("✏️ Routing to: EDIT")
            if not has_contract:
                msg = (
                    "أحتاج عقد موجود لأعدله. الصق العقد أو اطلب إنشاء عقد جديد."
                    if lang == "arabic"
                    else "I need an existing contract to edit. Paste one or ask me to create a new contract."
                )
                return (msg, None, "none")

            updated = self.edit_contract(active_contract, user_input)
            
            # Check if it's an error message (from date validation)
            if updated and (updated.startswith("⚠️") or "خطأ" in updated[:50]):
                print("⚠️ Edit failed - date validation error")
                return (updated, active_contract, "unchanged")
            
            # Check if contract actually changed
            if updated and len(updated.strip()) >= MIN_CONTRACT_LENGTH and updated != active_contract:
                print("✅ Contract was updated")
                self.set_current_contract(updated, session_id=session_id)
                msg = "تم التعديل بنجاح ✓" if lang == "arabic" else "Updated successfully ✓"
                return (msg, updated, "updated")
            else:
                print("⚠️ Contract was NOT updated")
                msg = (
                    "لم أتمكن من التعديل. هل يمكنك توضيح الطلب؟"
                    if lang == "arabic"
                    else "Couldn't update. Can you clarify?"
                )
                return (msg, active_contract, "unchanged")

        elif action_type == "explain":
            print("💡 Routing to: EXPLAIN")
            if not has_contract:
                msg = (
                    "أحتاج عقد لأشرحه. الصق العقد أو اطلب إنشاء عقد جديد."
                    if lang == "arabic"
                    else "I need a contract to explain. Paste one or ask me to create a new contract."
                )
                return (msg, None, "none")

            explanation = self.explain_clause(active_contract, user_input)
            return (explanation, active_contract, "unchanged")

        elif action_type == "review":
            print("🔍 Routing to: REVIEW")
            if not has_contract:
                msg = (
                    "أحتاج عقد لأراجعه. الصق العقد أو اطلب إنشاء عقد جديد."
                    if lang == "arabic"
                    else "I need a contract to review. Paste one or ask me to create a new contract."
                )
                return (msg, None, "none")

            review = self.review_contract(active_contract)
            return (review, active_contract, "unchanged")

        else:  # chat
            print("💬 Routing to: GENERAL CHAT")
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ]

            response = self._chat_completion(messages)
            if response is None:
                msg = "عذراً، خطأ في معالجة الطلب" if lang == "arabic" else "Sorry, error processing request"
                if has_contract:
                    return (msg, active_contract, "unchanged")
                return (msg, None, "none")

            result = response.choices[0].message.content.strip()
            if has_contract:
                return (result, active_contract, "unchanged")
            return (result, None, "none")