import logging
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import httpx

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    async def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def rewrite(self, text: str, prompt: str, replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": "Analyze content and return JSON response."},
            {"role": "user", "content": f"{prompt}\n\nContent:\n{text}"},
        ]
        return await self._call(messages)

    async def rewrite(self, text: str, prompt: str, replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        messages = [
            {"role": "system", "content": "You are a professional content editor."},
            {"role": "user", "content": f"{prompt}\n\nContent:\n{text}"},
        ]
        result = await self._call(messages)
        return result.get("content", text)

    async def _call(self, messages: list) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {"content": content, "tokens": data["usage"]["total_tokens"]}
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e)}


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com"

    async def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        full_prompt = f"{prompt}\n\nContent:\n{text}"
        return await self._call(full_prompt, system="Analyze and return JSON.")

    async def rewrite(self, text: str, prompt: str, replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        full_prompt = f"{prompt}\n\nContent:\n{text}"
        result = await self._call(full_prompt, system="You are a professional editor.")
        return result.get("content", text)

    async def _call(self, prompt: str, system: str = "") -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    json={
                        "model": self.model,
                        "max_tokens": 2000,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["content"][0]["text"]
                return {"content": content, "tokens": data["usage"]["output_tokens"]}
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {"error": str(e)}


class MockProvider(LLMProvider):
    """Mock AI provider for testing without external API."""
    def __init__(self, api_key: str = "", model: str = "mock"):
        self.api_key = api_key
        self.model = model

    async def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        import json
        result = {
            "relevant": True,
            "category": "tech",
            "importance": 7,
            "sentiment": "positive",
            "clickbait": False,
            "summary": f"Summary of: {text[:100]}..."
        }
        return {"content": json.dumps(result)}

    async def rewrite(self, text: str, prompt: str, replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        result_text = text

        # Apply text replacement if specified
        if replace_from and replace_to:
            result_text = result_text.replace(replace_from, replace_to)

        styles = {
            "engaging": f"✨ {result_text}",
            "professional": f"[Professional] {result_text}",
            "informative": f"📚 {result_text}",
            "neutral": result_text,
        }
        # Extract style from prompt if possible
        for style, prefix in styles.items():
            if style in prompt.lower():
                return prefix
        return f"✏️ {result_text}"


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        full_prompt = f"{prompt}\n\nContent:\n{text}"
        return await self._call(full_prompt)

    async def rewrite(self, text: str, prompt: str, replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        full_prompt = f"{prompt}\n\nContent:\n{text}"
        result = await self._call(full_prompt)
        return result.get("content", text)

    async def _call(self, prompt: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return {"content": data.get("response", prompt)}
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return {"error": str(e)}


class AIService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze content for relevance, category, sentiment, etc."""
        prompt = """Analyze this content and provide a JSON response with:
{
    "relevant": boolean,
    "category": string,
    "importance": number (1-10),
    "sentiment": string (positive, negative, neutral),
    "clickbait": boolean,
    "summary": string,
    "keywords": list of strings
}"""
        try:
            result = await self.provider.analyze(text, prompt)
            if "error" in result:
                return {"error": result["error"]}
            content = result.get("content", "{}")
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI analysis JSON")
            return {"relevant": True, "importance": 5}

    async def rewrite_content(self, text: str, style: str = "neutral", replace_from: Optional[str] = None, replace_to: Optional[str] = None) -> str:
        """Rewrite content in specified style and optionally replace text."""
        prompt = f"""Rewrite this content in a {style} professional style.
Keep all facts and information intact.
Do not add information that wasn't in the original.
Improve clarity and engagement."""

        if replace_from and replace_to:
            prompt += f"\n\nAlso replace mentions of '{replace_from}' with '{replace_to}' where contextually appropriate."

        try:
            result = await self.provider.rewrite(text, prompt, replace_from=replace_from, replace_to=replace_to)
            return result
        except Exception as e:
            logger.error(f"Rewrite error: {e}")
            return text

    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate summary of content."""
        prompt = f"Generate a summary of this content in maximum {max_length} characters."
        try:
            result = await self.provider.rewrite(text, prompt)
            return result[:max_length]
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return text[:max_length]
