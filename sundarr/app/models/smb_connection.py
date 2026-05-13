from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin


class SmbConnection(TimestampMixin, Base):
    __tablename__ = "smb_connections"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=445, server_default="445")
    share: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    base_path: Mapped[str] = mapped_column(Text, nullable=False, default="/", server_default="/")
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_test_error_code: Mapped[str | None] = mapped_column(Text)
    last_test_error_message: Mapped[str | None] = mapped_column(Text)
