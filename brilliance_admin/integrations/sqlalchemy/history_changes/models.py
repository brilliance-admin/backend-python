from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from brilliance_admin.schema.table.history_change_provider import LogType


class HistoryChangesBase(DeclarativeBase):
    pass


class HistoryChange(HistoryChangesBase):
    __tablename__ = 'brilliance_admin_history_change'
    __table_args__ = (
        Index('brilliance_history_category_action_time_idx', 'category_path', 'action_time'),
        Index('brilliance_history_pk_idx', 'pk'),
        Index('brilliance_history_log_type_action_time_idx', 'log_type', 'action_time'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    user: Mapped[str] = mapped_column(String(255))
    pk: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_type: Mapped[int] = mapped_column(Integer)
    action_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_path: Mapped[str] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
