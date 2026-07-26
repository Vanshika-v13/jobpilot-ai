import logging
import httpx
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableLambda
from core.config import settings

logger = logging.getLogger(__name__)

def check_ollama_status() -> bool:
    """Check if Ollama server is running and reachable."""
    base_url = settings.ollama_base_url
    try:
        response = httpx.get(base_url, timeout=2.0)
        if response.status_code == 200:
            return True
    except Exception:
        pass
    return False

def verify_ollama_reachability():
    """Verify reachability of Ollama; raise clear error if not reachable."""
    if not check_ollama_status():
        raise ConnectionError(
            f"Ollama is unreachable at {settings.ollama_base_url}. "
            "Please make sure Ollama is running (run 'ollama serve' in your terminal)."
        )

class ReachableChatOllama(ChatOllama):
    """ChatOllama wrapper that verifies reachability and provides clear errors."""
    
    def _generate(self, *args, **kwargs) -> ChatResult:
        verify_ollama_reachability()
        try:
            return super()._generate(*args, **kwargs)
        except Exception as e:
            if "connect" in str(e).lower() or "connection" in str(e).lower():
                verify_ollama_reachability()
            raise e

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        structured_runnable = super().with_structured_output(schema, **kwargs)
        
        def invoke_with_check(input_data: Any, config: Optional[Any] = None) -> Any:
            verify_ollama_reachability()
            try:
                return structured_runnable.invoke(input_data, config)
            except Exception as e:
                if "connect" in str(e).lower() or "connection" in str(e).lower():
                    verify_ollama_reachability()
                raise e
                
        return RunnableLambda(invoke_with_check)

class FallbackChatModel(BaseChatModel):
    """Custom LangChain chat model wrapper to support automatic fallback to Ollama."""
    primary: BaseChatModel
    fallback: BaseChatModel

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return self.primary._generate(messages, stop, run_manager, **kwargs)
        except Exception as e:
            logger.warning(f"Primary LLM provider failed: {e}. Falling back to Ollama.")
            return self.fallback._generate(messages, stop, run_manager, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "fallback-chat-model"

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        primary_structured = self.primary.with_structured_output(schema, **kwargs)
        fallback_structured = self.fallback.with_structured_output(schema, **kwargs)
        
        def invoke_with_fallback(input_data: Any, config: Optional[Any] = None) -> Any:
            try:
                return primary_structured.invoke(input_data, config)
            except Exception as e:
                logger.warning(f"Primary LLM structured output failed: {e}. Falling back to Ollama.")
                return fallback_structured.invoke(input_data, config)
                
        return RunnableLambda(invoke_with_fallback)

def get_llm() -> BaseChatModel:
    """Factory function to get correct LangChain chat model based on configuration."""
    provider = settings.llm_provider.lower()
    
    ollama_model = ReachableChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0,
    )
    
    if provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY is not set. Falling back to Ollama.")
            return ollama_model
        
        gemini_model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0,
        )
        return FallbackChatModel(primary=gemini_model, fallback=ollama_model)
        
    return ollama_model
