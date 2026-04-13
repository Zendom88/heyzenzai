import json
import logging
from app.config import settings
from app.models.schemas import IntentResult, IntentType

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

INTENT_ROUTER_SYSTEM_PROMPT = """You are an intent classifier for a WhatsApp booking assistant serving Singapore beauty and wellness salons.

Your ONLY job is to classify the customer's message into one of these intents:

BOOKING   - Customer wants to make a new appointment
           Examples: "hi want to book facial", "can i make appt tmr", "slots available Thursday?"
           
MODIFY    - Customer wants to reschedule or cancel an existing appointment
           Examples: "can i change my appt", "need to push to next week", "want to cancel"
           
FAQ       - Customer is asking about services, pricing, location, or policies
           Examples: "how much is waxing", "where are you located", "do you do eyelash extensions"
           
ESCALATE  - Customer is upset, has a complaint, a medical concern, or explicitly wants a human
           Examples: "i got reaction from the cream", "speak to manager", "this is ridiculous",
                     "allergic reaction", "emergency"
           
UNKNOWN   - Cannot be classified (e.g. spam, random text, test message)

RULES:
- If the message contains MULTIPLE intents, classify the most urgent one as primary, the other as secondary.
- Escalation always takes priority over everything else.
- Respond ONLY with valid JSON. No explanation. No extra text.

OUTPUT FORMAT:
{
  "primary_intent": "BOOKING" | "MODIFY" | "FAQ" | "ESCALATE" | "UNKNOWN",
  "secondary_intent": "BOOKING" | "MODIFY" | "FAQ" | "ESCALATE" | "UNKNOWN" | null,
  "confidence": 0.0-1.0
}"""


async def classify_intent(message: str) -> IntentResult:
    """
    Classify the intent of an incoming WhatsApp message.
    Returns an IntentResult with primary + optional secondary intent.
    """
    prompt = f"Customer message: \"{message}\""

    try:
        raw = await _call_llm(system=INTENT_ROUTER_SYSTEM_PROMPT, user=prompt)
        data = json.loads(raw)
        return IntentResult(
            primary_intent=IntentType(data.get("primary_intent", "UNKNOWN")),
            secondary_intent=IntentType(data["secondary_intent"]) if data.get("secondary_intent") else None,
            confidence=float(data.get("confidence", 0.5)),
            raw_message=message,
        )
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return IntentResult(
            primary_intent=IntentType.UNKNOWN,
            confidence=0.0,
            raw_message=message,
        )


async def _call_llm(system: str, user: str) -> str:
    """Route to the configured AI provider."""
    if settings.ai_provider == "gemini":
        return await _call_gemini(system, user)
    return await _call_openai(system, user)


async def _call_gemini(system: str, user: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system,
        generation_config={"response_mime_type": "application/json"},
    )
    response = model.generate_content(user)
    return response.text


async def _call_openai(system: str, user: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content
