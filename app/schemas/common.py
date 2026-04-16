from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models import AttendanceStatus, CoinSource, RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class LoginInput(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: RoleEnum
    is_active: bool


class DirectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class TeacherSummary(BaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    specialty: str | None = None


class StudentSummary(BaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    phone: str | None = None
    parent_phone: str | None = None


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    direction_id: int
    schedule: str | None = None
    lesson_time: str | None = None
    classroom: str | None = None
    duration_months: int | None = None
    starts_on: date | None = None
    teacher_id: int | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    direction_id: int | None = None
    schedule: str | None = None
    lesson_time: str | None = None
    classroom: str | None = None
    duration_months: int | None = None
    starts_on: date | None = None
    teacher_id: int | None = None


class GroupRead(BaseModel):
    id: int
    name: str
    schedule: str | None = None
    lesson_time: str | None = None
    classroom: str | None = None
    duration_months: int | None = None
    starts_on: date | None = None
    direction: DirectionRead
    teacher: TeacherSummary | None = None
    student_count: int = 0


class StudentCreate(BaseModel):
    username: str
    full_name: str
    password: str = Field(min_length=6)
    phone: str | None = None
    parent_phone: str | None = None
    joined_at: date | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    parent_phone: str | None = None
    password: str | None = Field(default=None, min_length=6)


class StudentRead(StudentSummary):
    joined_at: date | None = None
    groups: list[GroupRead] = []


class AssignStudentInput(BaseModel):
    student_id: int


class AssignTeacherInput(BaseModel):
    teacher_id: int


class AttendanceCreate(BaseModel):
    student_id: int
    lesson_date: date
    status: AttendanceStatus
    notes: str | None = None


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus
    notes: str | None = None


class AttendanceRead(BaseModel):
    id: int
    lesson_date: date
    status: AttendanceStatus
    notes: str | None = None
    student: StudentSummary


class MarkCreate(BaseModel):
    student_id: int
    score: int = Field(ge=0, le=100)
    notes: str | None = None


class MarkUpdate(BaseModel):
    score: int = Field(ge=0, le=100)
    notes: str | None = None


class MarkRead(BaseModel):
    id: int
    score: int
    notes: str | None = None
    created_at: datetime
    student: StudentSummary


class CoinGive(BaseModel):
    student_id: int
    coins: int = Field(gt=0, le=100)
    reason: str = Field(min_length=3, max_length=255)


class CoinRead(BaseModel):
    id: int
    coins: int
    reason: str
    source: CoinSource
    created_at: datetime
    student: StudentSummary


class HomeworkCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10)
    due_date: date
    max_score: int = Field(default=100, ge=1, le=100)


class HomeworkRead(BaseModel):
    id: int
    title: str
    description: str
    due_date: date
    max_score: int
    created_at: datetime
    group_id: int
    submission_count: int = 0


class HomeworkSubmissionCreate(BaseModel):
    content: str = Field(min_length=5)


class HomeworkSubmissionReview(BaseModel):
    score: int | None = Field(default=None, ge=0, le=100)
    awarded_coins: int = Field(default=0, ge=0, le=100)
    review_note: str | None = None


class HomeworkSubmissionRead(BaseModel):
    id: int
    content: str
    submitted_at: datetime
    score: int | None = None
    awarded_coins: int = 0
    review_note: str | None = None
    student: StudentSummary


class DashboardStats(BaseModel):
    total_students: int
    total_teachers: int
    total_groups: int
    attendance_summary: dict[str, int]
    direction_breakdown: list[dict[str, int | str]]


class TeacherDashboard(BaseModel):
    teacher: TeacherSummary
    groups: list[GroupRead]
    recent_homeworks: list[HomeworkRead]
    coin_summary: dict[str, int]


class StudentDashboard(BaseModel):
    student: StudentSummary
    groups: list[GroupRead]
    attendance_summary: dict[str, int]
    average_mark: float
    total_coins: int
    pending_homeworks: list[HomeworkRead]


Token.model_rebuild()
