from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Column, Table
from typing import Optional, List


class Base(DeclarativeBase):
  pass


class User(Base):
  __tablename__ = "users"

  uid: Mapped[int] = mapped_column(primary_key=True)
  username: Mapped[Optional[str]]
  firstname: Mapped[Optional[str]]
  hearts: Mapped[str]


class Poll(Base):
  __tablename__ = "polls"

  id: Mapped[int] = mapped_column(primary_key=True)
  uid: Mapped[int] = mapped_column(ForeignKey("users.uid", ondelete="CASCADE"))
  user: Mapped["User"] = relationship()
  time: Mapped[str]
  tpe: Mapped[str]


class Response(Base):
  __tablename__ = "responses"

  id: Mapped[int] = mapped_column(primary_key=True)
  uid: Mapped[int] = mapped_column(ForeignKey("users.uid", ondelete="CASCADE"))
  user: Mapped["User"] = relationship()
  date: Mapped[str]
  time: Mapped[str]
  tpe: Mapped[str]
  score: Mapped[int]


class Achievement(Base):
  __tablename__ = "achievements"
  
  uid: Mapped[int] = mapped_column(ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True)
  name: Mapped[str] = mapped_column(primary_key=True)
  user: Mapped["User"] = relationship()
  weight: Mapped[int]


class Meta(Base):
  __tablename__ = "meta"
  
  uid: Mapped[int] = mapped_column(ForeignKey("users.uid", ondelete="CASCADE"), primary_key=True)
  key: Mapped[str] = mapped_column(primary_key=True)
  value: Mapped[str]


association_table = Table(
  "association_table",
  Base.metadata,
  Column("left_id", ForeignKey("users.uid")),
  Column("right_id", ForeignKey("groups.tag")),
)


class Group(Base):
  __tablename__ = "groups"
  
  tag: Mapped[str] = mapped_column(primary_key=True)
  name: Mapped[str]
  description: Mapped[str]
  users: Mapped[List["User"]] = relationship(secondary=association_table)


class Tracker(Base):
  __tablename__ = "trackers"
  
  chat_id: Mapped[int] = mapped_column(primary_key=True)
  message_id: Mapped[int] = mapped_column(primary_key=True)
  tpe: Mapped[str]
  current_text: Mapped[str]


class LastDay(Base):
  __tablename__ = "lastdays"

  id: Mapped[int] = mapped_column(primary_key=True)
  uid: Mapped[int] = mapped_column(ForeignKey("users.uid", ondelete="CASCADE"))
  user: Mapped["User"] = relationship()
  date: Mapped[str]
  tpe: Mapped[str] = mapped_column(default="mood")
  count: Mapped[int] = mapped_column(default=0)