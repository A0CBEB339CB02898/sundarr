from typing import Any

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin
from sundarr.app.models.types import JsonObject


class Setting(TimestampMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JsonObject, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
