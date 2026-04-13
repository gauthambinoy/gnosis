from fastapi import APIRouter
from app.llm.router import model_router, TIER_CONFIG

router = APIRouter()


@router.get("/stats")
async def get_llm_stats():
    return model_router.stats


@router.get("/tiers")
async def get_tiers():
    return {"tiers": TIER_CONFIG}


@router.get("/providers")
async def get_providers():
    return {
        "providers": [
            {"id": "openrouter", "name": "OpenRouter", "description": "200+ models via single API", "recommended": True},
            {"id": "anthropic", "name": "Anthropic", "description": "Claude models direct"},
            {"id": "openai", "name": "OpenAI", "description": "GPT models direct"},
            {"id": "google", "name": "Google AI", "description": "Gemini models"},
            {"id": "groq", "name": "Groq", "description": "Ultra-fast inference"},
            {"id": "ollama", "name": "Ollama", "description": "Local models, zero cost"},
            {"id": "together", "name": "Together AI", "description": "Open source models"},
            {"id": "custom", "name": "Custom Endpoint", "description": "Any OpenAI-compatible API"},
        ]
    }
