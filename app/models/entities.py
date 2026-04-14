from datetime import datetime, date
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RoleEnum(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class CoinSource(str, Enum):
    MANUAL = "manual"
    HOMEWORK_REVIEW = "homework_review"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[RoleEnum] = mapped_column(SqlEnum(RoleEnum), index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    teacher_profile: Mapped["TeacherProfile | None"] = relationship(back_populates="user", uselist=False)
    student_profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False)


class TeacherProfile(TimestampMixin, Base):
    __tablename__ = "teacher_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="teacher_profile")
    groups: Mapped[list["Group"]] = relationship(back_populates="teacher")


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    joined_at: Mapped[date] = mapped_column(Date, default=date.today)

    user: Mapped[User] = relationship(back_populates="student_profile")
    group_links: Mapped[list["GroupStudent"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Direction(TimestampMixin, Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    groups: Mapped[list["Group"]] = relationship(back_populates="direction")


class Group(TimestampMixin, Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    direction_id: Mapped[int] = mapped_column(ForeignKey("directions.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teacher_profiles.id"), nullable=True)
    schedule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    direction: Mapped[Direction] = relationship(back_populates="groups")
    teacher: Mapped[TeacherProfile | None] = relationship(back_populates="groups")
    students: Mapped[list["GroupStudent"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    marks: Mapped[list["Mark"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    homeworks: Mapped[list["Homework"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    coin_transactions: Mapped[list["CoinTransaction"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupStudent(TimestampMixin, Base):
    __tablename__ = "group_students"
    __table_args__ = (UniqueConstraint("group_id", "student_id", name="uq_group_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))

    group: Mapped[Group] = relationship(back_populates="students")
    student: Mapped[StudentProfile] = relationship(back_populates="group_links")


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("group_id", "student_id", "lesson_date", name="uq_attendance_entry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"))
    lesson_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AttendanceStatus] = mapped_column(SqlEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    group: Mapped[Group] = relationship(back_populates="attendances")
    student: Mapped[StudentProfile] = relationship()
    teacher: Mapped[TeacherProfile] = relationship()


class Mark(TimestampMixin, Base):
    __tablename__ = "marks"
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 100", name="ck_mark_score_range"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"))
    score: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    group: Mapped[Group] = relationship(back_populates="marks")
    student: Mapped[StudentProfile] = relationship()
    teacher: Mapped[TeacherProfile] = relationship()


class Homework(TimestampMixin, Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[date] = mapped_column(Date)
    max_score: Mapped[int] = mapped_column(Integer, default=100)

    group: Mapped[Group] = relationship(back_populates="homeworks")
    teacher: Mapped[TeacherProfile] = relationship()
    submissions: Mapped[list["HomeworkSubmission"]] = relationship(back_populates="homework", cascade="all, delete-orphan")


class HomeworkSubmission(TimestampMixin, Base):
    __tablename__ = "homework_submissions"
    __table_args__ = (UniqueConstraint("homework_id", "student_id", name="uq_homework_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    content: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    awarded_coins: Mapped[int] = mapped_column(Integer, default=0)
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teacher_profiles.id"), nullable=True)

    homework: Mapped[Homework] = relationship(back_populates="submissions")
    student: Mapped[StudentProfile] = relationship()
    reviewed_by_teacher: Mapped[TeacherProfile | None] = relationship()
    coin_transaction: Mapped["CoinTransaction | None"] = relationship(back_populates="submission", uselist=False)


class CoinTransaction(TimestampMixin, Base):
    __tablename__ = "coin_transactions"
    __table_args__ = (CheckConstraint("coins > 0", name="ck_coin_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"))
    coins: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    source: Mapped[CoinSource] = mapped_column(SqlEnum(CoinSource), default=CoinSource.MANUAL)
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("homework_submissions.id"), nullable=True, unique=True)

    group: Mapped[Group] = relationship(back_populates="coin_transactions")
    student: Mapped[StudentProfile] = relationship()
    teacher: Mapped[TeacherProfile] = relationship()
    submission: Mapped[HomeworkSubmission | None] = relationship(back_populates="coin_transaction")
