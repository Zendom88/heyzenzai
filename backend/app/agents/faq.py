import logging
from app.config import settings
from app.models.schemas import SalonConfig

logger = logging.getLogger(__name__)

FAQ_SYSTEM_PROMPT = """You are a helpful assistant for a Singapore beauty and wellness salon.
Answer the customer's question based ONLY on the salon information provided below.
Do NOT invent prices, services, or policies that are not listed.
If the answer is not in the salon info, say: "I'm not sure about that — let me get someone from our team to help you! 😊"
Keep responses short and friendly. Max 3 sentences.

SALON INFORMATION:
{salon_context}"""


async def handle_faq(salon: SalonConfig, message: str) -> str:
    """Answer a customer FAQ using the salon's knowledge base."""
    context = _build_faq_context(salon)
    system = FAQ_SYSTEM_PROMPT.format(salon_context=context)

    try:
        return await _call_llm(system=system, user=message)
    except Exception as e:
        logger.error(f"FAQ LLM call failed: {e}")
        return "Let me get someone from our team to help you with that! 😊"


def _build_faq_context(salon: SalonConfig) -> str:
    services_text = "\n".join(
        f"- {s.name}: SGD {s.price_sgd:.0f} ({s.duration_mins} mins)"
        + (f" — {s.description}" if s.description else "")
        for s in salon.services
    )
    hours_text = "\n".join(
        f"- {day.capitalize()}: {h.open}–{h.close}"
        for day, h in salon.hours.items()
    )
    return f"""Salon: {salon.business_name}
Location: {salon.location}

Services & Pricing:
{services_text}

Opening Hours:
{hours_text}

Policies:
{salon.policies}"""


async def _call_llm(system: str, user: str) -> str:
    if settings.ai_provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system,
        )
        response = model.generate_content(user)
        return response.text
    else:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
