from datetime import datetime
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ChatbotConfig(Base):
    __tablename__ = "ChatbotConfig"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interaction_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    crisis_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, default=0.55)
    top_p: Mapped[float | None] = mapped_column(Float, default=0.9)
    max_tokens: Mapped[int | None] = mapped_column(Integer, default=420)
    max_tokens_user: Mapped[int | None] = mapped_column(Integer, default=2000)
    daily_message_limit: Mapped[int | None] = mapped_column(Integer, default=20)
    actualizado_por: Mapped[int | None] = mapped_column(Integer, ForeignKey("Register.idUsuario", ondelete="SET NULL"), nullable=True)
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "system_prompt": self.system_prompt,
            "tone": self.tone,
            "interaction_rules": self.interaction_rules,
            "risk_terms": self.risk_terms,
            "crisis_response": self.crisis_response,
            "medium_terms": self.medium_terms,
            "medium_response": self.medium_response,
            "fallback_response": self.fallback_response,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "max_tokens_user": self.max_tokens_user,
            "daily_message_limit": self.daily_message_limit,
            "actualizado_por": self.actualizado_por,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }
