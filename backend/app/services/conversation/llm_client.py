from functools import lru_cache

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.conversation.language import language_name


class LLMConfigurationError(RuntimeError):
    pass


class LLMServiceError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = settings.anthropic_api_key,
        model: str = settings.anthropic_model,
        mock_mode: bool = settings.llm_mock_mode,
        max_tokens: int = settings.llm_max_tokens,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.model = model
        self.mock_mode = mock_mode
        self.max_tokens = max_tokens
        self._client = (
            None
            if mock_mode or not self.api_key
            else AsyncAnthropic(api_key=self.api_key)
        )

    async def generate_reply(
        self,
        *,
        user_name: str,
        detected_language: str,
        detected_emotion: str | None,
        is_live: bool,
        messages: list[dict[str, str]],
        should_greet: bool,
    ) -> str:
        if self.mock_mode:
            return self._mock_reply(
                user_name=user_name,
                language=detected_language,
                emotion=detected_emotion,
                should_greet=should_greet,
            )
        if not self.api_key or self._client is None:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is required when LLM_MOCK_MODE is false."
            )

        system_prompt = self._system_prompt(
            user_name=user_name,
            detected_language=detected_language,
            detected_emotion=detected_emotion,
            is_live=is_live,
            should_greet=should_greet,
        )
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.4,
                system=system_prompt,
                messages=messages,
            )
        except Exception as exc:
            raise LLMServiceError("Anthropic could not generate a response.") from exc

        text_blocks = [block.text for block in response.content if block.type == "text"]
        reply = "\n".join(text_blocks).strip()
        if not reply:
            raise LLMServiceError("Anthropic returned no text content.")
        return reply

    @staticmethod
    def _system_prompt(
        *,
        user_name: str,
        detected_language: str,
        detected_emotion: str | None,
        is_live: bool,
        should_greet: bool,
    ) -> str:
        emotion = detected_emotion or "unknown"
        greeting_instruction = (
            f"Begin by greeting {user_name} by name and say it is good to "
            "see them again. "
            if should_greet
            else ""
        )
        return (
            "You are VirtualPresence, a concise and thoughtful virtual assistant. "
            f"The recognized user is {user_name}. Their latest verified face "
            f"interaction reports emotion={emotion} and is_live={is_live}. "
            f"The user's input language is {language_name(detected_language)} "
            f"({detected_language}); reply entirely in that same language. "
            f"{greeting_instruction}"
            "Adapt your tone gently: be warmer and reassuring for sad, fearful, "
            "angry, or stressed signals; be upbeat for happy signals; otherwise "
            "stay calm and neutral. Never diagnose their emotional state or claim "
            "the camera signal is certain. Use prior messages for continuity. "
            "Answer the user's request directly and keep the response under "
            "three short paragraphs unless they ask for detail."
        )

    @staticmethod
    def _mock_reply(
        *,
        user_name: str,
        language: str,
        emotion: str | None,
        should_greet: bool,
    ) -> str:
        stressed = emotion in {"sad", "fearful", "angry", "stressed"}
        happy = emotion == "happy"
        templates = {
            "en": {
                "greeting": f"Good to see you again, {user_name}. ",
                "warm": "I’m here with you—let’s take this one step at a time. ",
                "upbeat": "It’s lovely to see that positive energy. ",
                "neutral": "How can I help you today? ",
                "close": "Tell me what you’d like to work on.",
            },
            "ms": {
                "greeting": f"Gembira berjumpa lagi, {user_name}. ",
                "warm": "Saya di sini bersama anda—mari kita uruskan satu demi satu. ",
                "upbeat": "Seronok melihat tenaga positif itu. ",
                "neutral": "Bagaimana saya boleh membantu anda hari ini? ",
                "close": "Beritahu saya perkara yang anda ingin lakukan.",
            },
            "zh": {
                "greeting": f"很高兴再次见到你，{user_name}。 ",
                "warm": "我会陪着你，我们可以一步一步来。 ",
                "upbeat": "很高兴感受到你的积极状态。 ",
                "neutral": "今天我可以怎样帮助你？ ",
                "close": "请告诉我你想处理什么事情。",
            },
            "es": {
                "greeting": f"Me alegra verte de nuevo, {user_name}. ",
                "warm": "Estoy aquí contigo; avancemos paso a paso. ",
                "upbeat": "Me alegra percibir esa energía positiva. ",
                "neutral": "¿Cómo puedo ayudarte hoy? ",
                "close": "Cuéntame en qué te gustaría trabajar.",
            },
            "fr": {
                "greeting": f"Ravi de vous revoir, {user_name}. ",
                "warm": "Je suis là avec vous ; avançons étape par étape. ",
                "upbeat": "C’est agréable de ressentir cette énergie positive. ",
                "neutral": "Comment puis-je vous aider aujourd’hui ? ",
                "close": "Dites-moi ce que vous souhaitez faire.",
            },
            "de": {
                "greeting": f"Schön, Sie wiederzusehen, {user_name}. ",
                "warm": "Ich bin für Sie da; gehen wir es Schritt für Schritt an. ",
                "upbeat": "Es ist schön, diese positive Energie zu spüren. ",
                "neutral": "Wie kann ich Ihnen heute helfen? ",
                "close": "Sagen Sie mir, woran Sie arbeiten möchten.",
            },
            "id": {
                "greeting": f"Senang bertemu lagi, {user_name}. ",
                "warm": "Saya di sini bersama Anda; mari kita lakukan selangkah demi selangkah. ",
                "upbeat": "Senang melihat energi positif itu. ",
                "neutral": "Bagaimana saya dapat membantu Anda hari ini? ",
                "close": "Ceritakan apa yang ingin Anda kerjakan.",
            },
            "ja": {
                "greeting": f"またお会いできてうれしいです、{user_name}さん。 ",
                "warm": "そばにいますので、一歩ずつ進めましょう。 ",
                "upbeat": "前向きな様子が感じられてうれしいです。 ",
                "neutral": "今日はどのようにお手伝いできますか？ ",
                "close": "取り組みたいことを教えてください。",
            },
            "ko": {
                "greeting": f"다시 만나서 반가워요, {user_name}님. ",
                "warm": "제가 함께할게요. 한 단계씩 해 봅시다. ",
                "upbeat": "긍정적인 에너지가 느껴져서 좋네요. ",
                "neutral": "오늘 무엇을 도와드릴까요? ",
                "close": "하고 싶은 일을 말씀해 주세요.",
            },
            "pt": {
                "greeting": f"É bom ver você novamente, {user_name}. ",
                "warm": "Estou aqui com você; vamos por etapas. ",
                "upbeat": "É ótimo perceber essa energia positiva. ",
                "neutral": "Como posso ajudar você hoje? ",
                "close": "Conte no que você gostaria de trabalhar.",
            },
        }
        localized = templates.get(language, templates["en"])
        greeting = localized["greeting"] if should_greet else ""
        tone = (
            localized["warm"]
            if stressed
            else localized["upbeat"]
            if happy
            else localized["neutral"]
        )
        return f"{greeting}{tone}{localized['close']}".strip()


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient()
