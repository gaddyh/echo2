from openai import AsyncOpenAI

from app.config import settings
from app.schema import AgentResponse

client = AsyncOpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """
You are a helpful WhatsApp assistant.

Reply naturally.

Keep replies short.

Return ONLY the structured response.
"""


async def run_agent(user_message: str) -> AgentResponse:
    response = await client.responses.parse(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        text_format=AgentResponse,
    )

    return response.output_parsed