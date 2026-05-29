from __future__ import annotations

from enum import Enum
from uuid import UUID

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class TaskStatus(str, Enum):
    todo = "todo"
    done = "done"
    cancelled = "cancelled"


class RestMode(str, Enum):
    team = "team"
    free = "free"
    hybrid = "hybrid"


class CascadeMode(str, Enum):
    delete = "delete"
    detach = "detach"


class User(SQLAlchemyBaseUserTableUUID, Base, TimestampMixin):
    __tablename__ = "users"

    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    onboarded: Mapped[bool] = mapped_column(default=False, nullable=False)


class Settings(Base, UUIDMixin):
    __tablename__ = "settings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    week_budget: Mapped[int] = mapped_column(default=10, nullable=False)
    rest_mode: Mapped[str] = mapped_column(String(16), default=RestMode.team.value, nullable=False)
    hard_protection: Mapped[bool] = mapped_column(default=False, nullable=False)


class Theme(Base, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "themes"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(9), nullable=False)


class Year(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "years"
    __table_args__ = (UniqueConstraint("user_id", "year_number", name="uq_year_user_number"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year_number: Mapped[int] = mapped_column(nullable=False)

    weeks: Mapped[list[Week]] = relationship(back_populates="year", cascade="all, delete-orphan")
    quarter_notes: Mapped[list[QuarterNote]] = relationship(
        back_populates="year", cascade="all, delete-orphan"
    )


class QuarterNote(Base, UUIDMixin):
    __tablename__ = "quarter_notes"
    __table_args__ = (UniqueConstraint("year_id", "quarter", name="uq_quarter_note_year_q"),)

    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id", ondelete="CASCADE"), nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)

    year: Mapped[Year] = relationship(back_populates="quarter_notes")


class Week(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "weeks"

    year_id: Mapped[UUID] = mapped_column(ForeignKey("years.id", ondelete="CASCADE"), nullable=False)
    iso_week: Mapped[int] = mapped_column(nullable=False)
    display_position: Mapped[int] = mapped_column(nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False)
    is_rest_week: Mapped[bool] = mapped_column(default=False, nullable=False)
    cached_load: Mapped[int] = mapped_column(default=0, nullable=False)

    year: Mapped[Year] = relationship(back_populates="weeks")
    marks: Mapped[list[WeekMark]] = relationship(back_populates="week", cascade="all, delete-orphan")
    week_tasks: Mapped[list[WeekTask]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    day_tasks: Mapped[list[DayTask]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    review: Mapped[WeeklyReview | None] = relationship(
        back_populates="week", cascade="all, delete-orphan", uselist=False
    )


class WeekMark(Base, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "week_marks"

    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False)
    theme_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("themes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    week: Mapped[Week] = relationship(back_populates="marks")
    theme: Mapped[Theme | None] = relationship()
    week_tasks: Mapped[list[WeekTask]] = relationship(back_populates="mark")


class WeekTask(Base, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "week_tasks"

    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False)
    mark_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("week_marks.id", ondelete="SET NULL"), nullable=True
    )
    theme_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("themes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=TaskStatus.todo.value, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    week: Mapped[Week] = relationship(back_populates="week_tasks")
    mark: Mapped[WeekMark | None] = relationship(back_populates="week_tasks")
    day_tasks: Mapped[list[DayTask]] = relationship(back_populates="week_task")


class DayTask(Base, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "day_tasks"

    week_id: Mapped[UUID] = mapped_column(ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False)
    week_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("week_tasks.id", ondelete="SET NULL"), nullable=True
    )
    day_of_week: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=TaskStatus.todo.value, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    week: Mapped[Week] = relationship(back_populates="day_tasks")
    week_task: Mapped[WeekTask | None] = relationship(back_populates="day_tasks")


class Pile(Base, UUIDMixin):
    __tablename__ = "piles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    items: Mapped[list[PileItem]] = relationship(back_populates="pile", cascade="all, delete-orphan")


class PileItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pile_items"

    pile_id: Mapped[UUID] = mapped_column(ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    distributed: Mapped[bool] = mapped_column(default=False, nullable=False)

    pile: Mapped[Pile] = relationship(back_populates="items")


class WeeklyReview(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "weekly_reviews"

    week_id: Mapped[UUID] = mapped_column(
        ForeignKey("weeks.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    raw_input: Mapped[str] = mapped_column(Text, default="", nullable=False)
    achievements: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lessons: Mapped[str] = mapped_column(Text, default="", nullable=False)
    corrections: Mapped[str] = mapped_column(Text, default="", nullable=False)

    week: Mapped[Week] = relationship(back_populates="review")
