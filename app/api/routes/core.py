from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.seed import attendance_breakdown
from app.db.session import get_db
from app.models import (
    Attendance,
    CoinSource,
    CoinTransaction,
    Direction,
    Group,
    GroupStudent,
    Homework,
    HomeworkSubmission,
    Mark,
    RoleEnum,
    StudentProfile,
    TeacherProfile,
    User,
)
from app.schemas.common import (
    AssignStudentInput,
    AssignTeacherInput,
    AttendanceCreate,
    AttendanceRead,
    AttendanceUpdate,
    CoinGive,
    CoinRead,
    DashboardStats,
    DirectionRead,
    GroupCreate,
    GroupRead,
    GroupUpdate,
    HomeworkCreate,
    HomeworkRead,
    HomeworkSubmissionCreate,
    HomeworkSubmissionRead,
    HomeworkSubmissionReview,
    LoginInput,
    MarkCreate,
    MarkRead,
    MarkUpdate,
    StudentCreate,
    StudentDashboard,
    StudentRead,
    StudentSummary,
    StudentUpdate,
    TeacherDashboard,
    TeacherSummary,
    Token,
    UserRead,
)
from app.services.logic import (
    ValidationError,
    ensure_coin_limit,
    ensure_student_in_group,
    ensure_teacher_owns_group,
    get_group_coin_limit,
    get_group_coin_usage,
    get_group_or_404,
    get_homework_or_404,
    get_student_or_404,
    get_submission_or_404,
    get_teacher_or_404,
)

router = APIRouter(prefix="/api")


def teacher_summary(teacher: TeacherProfile | None) -> TeacherSummary | None:
    if not teacher:
        return None
    return TeacherSummary(
        id=teacher.id,
        user_id=teacher.user_id,
        full_name=teacher.user.full_name,
        username=teacher.user.username,
        specialty=teacher.specialty,
    )


def student_summary(student: StudentProfile) -> StudentSummary:
    return StudentSummary(
        id=student.id,
        user_id=student.user_id,
        full_name=student.user.full_name,
        username=student.user.username,
        phone=student.phone,
        parent_phone=student.parent_phone,
    )


def group_read(db: Session, group: Group) -> GroupRead:
    student_count = db.query(func.count(GroupStudent.id)).filter(GroupStudent.group_id == group.id).scalar() or 0
    return GroupRead(
        id=group.id,
        name=group.name,
        schedule=group.schedule,
        starts_on=group.starts_on,
        direction=DirectionRead.model_validate(group.direction),
        teacher=teacher_summary(group.teacher),
        student_count=int(student_count),
    )


def homework_read(db: Session, homework: Homework) -> HomeworkRead:
    submission_count = db.query(func.count(HomeworkSubmission.id)).filter(HomeworkSubmission.homework_id == homework.id).scalar() or 0
    return HomeworkRead(
        id=homework.id,
        title=homework.title,
        description=homework.description,
        due_date=homework.due_date,
        max_score=homework.max_score,
        created_at=homework.created_at,
        group_id=homework.group_id,
        submission_count=int(submission_count),
    )


@router.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_access_token(subject=user.username)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/auth/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/meta/directions", response_model=list[DirectionRead])
def list_directions(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[DirectionRead]:
    return [DirectionRead.model_validate(direction) for direction in db.query(Direction).order_by(Direction.name).all()]


@router.get("/admin/dashboard", response_model=DashboardStats)
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> DashboardStats:
    direction_breakdown = []
    rows = (
        db.query(Direction.name, func.count(Group.id))
        .outerjoin(Group, Group.direction_id == Direction.id)
        .group_by(Direction.id)
        .order_by(Direction.name)
        .all()
    )
    for name, count in rows:
        direction_breakdown.append({"name": name, "groups": int(count)})
    return DashboardStats(
        total_students=db.query(func.count(StudentProfile.id)).scalar() or 0,
        total_teachers=db.query(func.count(TeacherProfile.id)).scalar() or 0,
        total_groups=db.query(func.count(Group.id)).scalar() or 0,
        attendance_summary=attendance_breakdown(db),
        direction_breakdown=direction_breakdown,
    )


@router.get("/groups", response_model=list[GroupRead])
def list_groups(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[GroupRead]:
    groups = db.query(Group).options(joinedload(Group.direction), joinedload(Group.teacher).joinedload(TeacherProfile.user)).order_by(Group.name).all()
    return [group_read(db, group) for group in groups]


@router.post("/groups", response_model=GroupRead)
def create_group(payload: GroupCreate, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> GroupRead:
    if not db.query(Direction).filter(Direction.id == payload.direction_id).first():
        raise HTTPException(404, "Direction not found")
    if payload.teacher_id:
        get_teacher_or_404(db, payload.teacher_id)
    group = Group(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    group = get_group_or_404(db, group.id)
    return group_read(db, group)


@router.put("/groups/{group_id}", response_model=GroupRead)
def update_group(group_id: int, payload: GroupUpdate, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> GroupRead:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(404, "Group not found")
    updates = payload.model_dump(exclude_unset=True)
    if "teacher_id" in updates and updates["teacher_id"] is not None:
        get_teacher_or_404(db, updates["teacher_id"])
    if "direction_id" in updates and updates["direction_id"] is not None:
        if not db.query(Direction).filter(Direction.id == updates["direction_id"]).first():
            raise HTTPException(404, "Direction not found")
    for key, value in updates.items():
        setattr(group, key, value)
    db.commit()
    return group_read(db, get_group_or_404(db, group_id))


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> dict[str, str]:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(404, "Group not found")
    db.delete(group)
    db.commit()
    return {"message": "Group deleted"}


@router.post("/groups/{group_id}/students", response_model=GroupRead)
def assign_student(group_id: int, payload: AssignStudentInput, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> GroupRead:
    get_group_or_404(db, group_id)
    get_student_or_404(db, payload.student_id)
    exists = db.query(GroupStudent).filter(GroupStudent.group_id == group_id, GroupStudent.student_id == payload.student_id).first()
    if exists:
        raise ValidationError("Student already assigned to this group")
    db.add(GroupStudent(group_id=group_id, student_id=payload.student_id))
    db.commit()
    return group_read(db, get_group_or_404(db, group_id))


@router.post("/groups/{group_id}/teacher", response_model=GroupRead)
def assign_teacher(group_id: int, payload: AssignTeacherInput, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> GroupRead:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(404, "Group not found")
    teacher = get_teacher_or_404(db, payload.teacher_id)
    group.teacher_id = teacher.id
    db.commit()
    return group_read(db, get_group_or_404(db, group_id))


@router.get("/teachers", response_model=list[TeacherSummary])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[TeacherSummary]:
    teachers = db.query(TeacherProfile).options(joinedload(TeacherProfile.user)).order_by(TeacherProfile.id).all()
    return [teacher_summary(teacher) for teacher in teachers if teacher_summary(teacher)]


@router.get("/teachers/{teacher_id}", response_model=TeacherSummary)
def teacher_detail(teacher_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> TeacherSummary:
    teacher = get_teacher_or_404(db, teacher_id)
    return teacher_summary(teacher)


@router.get("/students", response_model=list[StudentRead])
def list_students(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[StudentRead]:
    students = db.query(StudentProfile).options(joinedload(StudentProfile.user)).order_by(StudentProfile.id).all()
    result = []
    for student in students:
        group_links = db.query(GroupStudent).filter(GroupStudent.student_id == student.id).all()
        groups = [group_read(db, get_group_or_404(db, link.group_id)) for link in group_links]
        result.append(
            StudentRead(
                **student_summary(student).model_dump(),
                joined_at=student.joined_at,
                groups=groups,
            )
        )
    return result


@router.post("/students", response_model=StudentRead)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> StudentRead:
    if db.query(User).filter(User.username == payload.username).first():
        raise ValidationError("Username already exists")
    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=RoleEnum.STUDENT,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    student = StudentProfile(
        user_id=user.id,
        phone=payload.phone,
        parent_phone=payload.parent_phone,
        joined_at=payload.joined_at or datetime.utcnow().date(),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    student = get_student_or_404(db, student.id)
    return StudentRead(**student_summary(student).model_dump(), joined_at=student.joined_at, groups=[])


@router.put("/students/{student_id}", response_model=StudentRead)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> StudentRead:
    student = get_student_or_404(db, student_id)
    updates = payload.model_dump(exclude_unset=True)
    if "full_name" in updates and updates["full_name"]:
        student.user.full_name = updates.pop("full_name")
    if "password" in updates and updates["password"]:
        student.user.hashed_password = hash_password(updates.pop("password"))
    for key, value in updates.items():
        setattr(student, key, value)
    db.commit()
    group_links = db.query(GroupStudent).filter(GroupStudent.student_id == student_id).all()
    groups = [group_read(db, get_group_or_404(db, link.group_id)) for link in group_links]
    return StudentRead(**student_summary(student).model_dump(), joined_at=student.joined_at, groups=groups)


@router.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(RoleEnum.ADMIN))) -> dict[str, str]:
    student = get_student_or_404(db, student_id)
    user = student.user
    db.delete(student)
    db.flush()
    db.delete(user)
    db.commit()
    return {"message": "Student deleted"}


@router.get("/teacher/dashboard", response_model=TeacherDashboard)
def teacher_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> TeacherDashboard:
    teacher = db.query(TeacherProfile).options(joinedload(TeacherProfile.user)).filter(TeacherProfile.user_id == current_user.id).first()
    groups = db.query(Group).options(joinedload(Group.direction), joinedload(Group.teacher).joinedload(TeacherProfile.user)).filter(Group.teacher_id == teacher.id).all()
    homeworks = db.query(Homework).filter(Homework.teacher_id == teacher.id).order_by(Homework.created_at.desc()).limit(5).all()
    total_given = db.query(func.coalesce(func.sum(CoinTransaction.coins), 0)).filter(CoinTransaction.teacher_id == teacher.id).scalar() or 0
    total_capacity = sum(get_group_coin_limit(db, group.id) for group in groups)
    return TeacherDashboard(
        teacher=teacher_summary(teacher),
        groups=[group_read(db, group) for group in groups],
        recent_homeworks=[homework_read(db, homework) for homework in homeworks],
        coin_summary={"used": int(total_given), "capacity": int(total_capacity)},
    )


@router.get("/teacher/groups/{group_id}")
def teacher_group_detail(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> dict:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    group = get_group_or_404(db, group_id)
    ensure_teacher_owns_group(group, teacher.id)
    student_links = db.query(GroupStudent).options(joinedload(GroupStudent.student).joinedload(StudentProfile.user)).filter(GroupStudent.group_id == group_id).all()
    homeworks = db.query(Homework).filter(Homework.group_id == group_id).order_by(Homework.created_at.desc()).all()
    marks = db.query(Mark).options(joinedload(Mark.student).joinedload(StudentProfile.user)).filter(Mark.group_id == group_id).order_by(Mark.created_at.desc()).limit(20).all()
    attendance_rows = db.query(Attendance).options(joinedload(Attendance.student).joinedload(StudentProfile.user)).filter(Attendance.group_id == group_id).order_by(Attendance.lesson_date.desc()).limit(20).all()
    coins = db.query(CoinTransaction).options(joinedload(CoinTransaction.student).joinedload(StudentProfile.user)).filter(CoinTransaction.group_id == group_id).order_by(CoinTransaction.created_at.desc()).limit(20).all()
    return {
        "group": group_read(db, group).model_dump(),
        "students": [student_summary(link.student).model_dump() for link in student_links],
        "attendance": [AttendanceRead(id=row.id, lesson_date=row.lesson_date, status=row.status, notes=row.notes, student=student_summary(row.student)).model_dump() for row in attendance_rows],
        "marks": [MarkRead(id=row.id, score=row.score, notes=row.notes, created_at=row.created_at, student=student_summary(row.student)).model_dump() for row in marks],
        "coins": [CoinRead(id=row.id, coins=row.coins, reason=row.reason, source=row.source, created_at=row.created_at, student=student_summary(row.student)).model_dump() for row in coins],
        "homeworks": [homework_read(db, homework).model_dump() for homework in homeworks],
        "coin_usage": {"used": get_group_coin_usage(db, group_id, teacher.id), "limit": get_group_coin_limit(db, group_id)},
    }


@router.post("/groups/{group_id}/attendance", response_model=AttendanceRead)
def create_attendance(group_id: int, payload: AttendanceCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> AttendanceRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    group = get_group_or_404(db, group_id)
    ensure_teacher_owns_group(group, teacher.id)
    ensure_student_in_group(db, group_id, payload.student_id)
    existing = db.query(Attendance).filter(Attendance.group_id == group_id, Attendance.student_id == payload.student_id, Attendance.lesson_date == payload.lesson_date).first()
    if existing:
        existing.status = payload.status
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        return AttendanceRead(id=existing.id, lesson_date=existing.lesson_date, status=existing.status, notes=existing.notes, student=student_summary(get_student_or_404(db, existing.student_id)))
    row = Attendance(group_id=group_id, student_id=payload.student_id, teacher_id=teacher.id, lesson_date=payload.lesson_date, status=payload.status, notes=payload.notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return AttendanceRead(id=row.id, lesson_date=row.lesson_date, status=row.status, notes=row.notes, student=student_summary(get_student_or_404(db, row.student_id)))


@router.get("/groups/{group_id}/attendance", response_model=list[AttendanceRead])
def list_attendance(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[AttendanceRead]:
    group = get_group_or_404(db, group_id)
    if current_user.role == RoleEnum.TEACHER:
        teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
        ensure_teacher_owns_group(group, teacher.id)
    rows = db.query(Attendance).options(joinedload(Attendance.student).joinedload(StudentProfile.user)).filter(Attendance.group_id == group_id).order_by(Attendance.lesson_date.desc()).all()
    return [AttendanceRead(id=row.id, lesson_date=row.lesson_date, status=row.status, notes=row.notes, student=student_summary(row.student)) for row in rows]


@router.put("/attendance/{attendance_id}", response_model=AttendanceRead)
def update_attendance(attendance_id: int, payload: AttendanceUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> AttendanceRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    row = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not row:
        raise HTTPException(404, "Attendance not found")
    ensure_teacher_owns_group(get_group_or_404(db, row.group_id), teacher.id)
    row.status = payload.status
    row.notes = payload.notes
    db.commit()
    db.refresh(row)
    return AttendanceRead(id=row.id, lesson_date=row.lesson_date, status=row.status, notes=row.notes, student=student_summary(get_student_or_404(db, row.student_id)))


@router.post("/groups/{group_id}/marks", response_model=MarkRead)
def create_mark(group_id: int, payload: MarkCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> MarkRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    group = get_group_or_404(db, group_id)
    ensure_teacher_owns_group(group, teacher.id)
    ensure_student_in_group(db, group_id, payload.student_id)
    mark = Mark(group_id=group_id, student_id=payload.student_id, teacher_id=teacher.id, score=payload.score, notes=payload.notes)
    db.add(mark)
    db.commit()
    db.refresh(mark)
    return MarkRead(id=mark.id, score=mark.score, notes=mark.notes, created_at=mark.created_at, student=student_summary(get_student_or_404(db, mark.student_id)))


@router.get("/groups/{group_id}/marks", response_model=list[MarkRead])
def list_marks(group_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[MarkRead]:
    rows = db.query(Mark).options(joinedload(Mark.student).joinedload(StudentProfile.user)).filter(Mark.group_id == group_id).order_by(Mark.created_at.desc()).all()
    return [MarkRead(id=row.id, score=row.score, notes=row.notes, created_at=row.created_at, student=student_summary(row.student)) for row in rows]


@router.put("/marks/{mark_id}", response_model=MarkRead)
def update_mark(mark_id: int, payload: MarkUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> MarkRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    mark = db.query(Mark).options(joinedload(Mark.student).joinedload(StudentProfile.user)).filter(Mark.id == mark_id).first()
    if not mark:
        raise HTTPException(404, "Mark not found")
    ensure_teacher_owns_group(get_group_or_404(db, mark.group_id), teacher.id)
    mark.score = payload.score
    mark.notes = payload.notes
    db.commit()
    db.refresh(mark)
    return MarkRead(id=mark.id, score=mark.score, notes=mark.notes, created_at=mark.created_at, student=student_summary(mark.student))


@router.post("/groups/{group_id}/coins", response_model=CoinRead)
def give_coin(group_id: int, payload: CoinGive, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> CoinRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    group = get_group_or_404(db, group_id)
    ensure_teacher_owns_group(group, teacher.id)
    ensure_student_in_group(db, group_id, payload.student_id)
    ensure_coin_limit(db, group_id, teacher.id, payload.coins)
    coin = CoinTransaction(group_id=group_id, student_id=payload.student_id, teacher_id=teacher.id, coins=payload.coins, reason=payload.reason, source=CoinSource.MANUAL)
    db.add(coin)
    db.commit()
    db.refresh(coin)
    return CoinRead(id=coin.id, coins=coin.coins, reason=coin.reason, source=coin.source, created_at=coin.created_at, student=student_summary(get_student_or_404(db, coin.student_id)))


@router.get("/groups/{group_id}/coins", response_model=list[CoinRead])
def list_coins(group_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[CoinRead]:
    rows = db.query(CoinTransaction).options(joinedload(CoinTransaction.student).joinedload(StudentProfile.user)).filter(CoinTransaction.group_id == group_id).order_by(CoinTransaction.created_at.desc()).all()
    return [CoinRead(id=row.id, coins=row.coins, reason=row.reason, source=row.source, created_at=row.created_at, student=student_summary(row.student)) for row in rows]


@router.post("/groups/{group_id}/homeworks", response_model=HomeworkRead)
def create_homework(group_id: int, payload: HomeworkCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> HomeworkRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    group = get_group_or_404(db, group_id)
    ensure_teacher_owns_group(group, teacher.id)
    homework = Homework(group_id=group_id, teacher_id=teacher.id, **payload.model_dump())
    db.add(homework)
    db.commit()
    db.refresh(homework)
    return homework_read(db, homework)


@router.get("/groups/{group_id}/homeworks", response_model=list[HomeworkRead])
def list_group_homeworks(group_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[HomeworkRead]:
    rows = db.query(Homework).filter(Homework.group_id == group_id).order_by(Homework.created_at.desc()).all()
    return [homework_read(db, row) for row in rows]


@router.get("/homeworks/{homework_id}")
def homework_detail(homework_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    homework = get_homework_or_404(db, homework_id)
    submissions = (
        db.query(HomeworkSubmission)
        .options(joinedload(HomeworkSubmission.student).joinedload(StudentProfile.user))
        .filter(HomeworkSubmission.homework_id == homework_id)
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
    )
    return {
        "homework": homework_read(db, homework).model_dump(),
        "submissions": [
            HomeworkSubmissionRead(
                id=row.id,
                content=row.content,
                submitted_at=row.submitted_at,
                score=row.score,
                awarded_coins=row.awarded_coins,
                review_note=row.review_note,
                student=student_summary(row.student),
            ).model_dump()
            for row in submissions
        ],
    }


@router.post("/homeworks/{homework_id}/submit", response_model=HomeworkSubmissionRead)
def submit_homework(homework_id: int, payload: HomeworkSubmissionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.STUDENT))) -> HomeworkSubmissionRead:
    homework = get_homework_or_404(db, homework_id)
    student = db.query(StudentProfile).options(joinedload(StudentProfile.user)).filter(StudentProfile.user_id == current_user.id).first()
    ensure_student_in_group(db, homework.group_id, student.id)
    existing = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework_id, HomeworkSubmission.student_id == student.id).first()
    if existing:
        existing.content = payload.content
        existing.submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return HomeworkSubmissionRead(id=existing.id, content=existing.content, submitted_at=existing.submitted_at, score=existing.score, awarded_coins=existing.awarded_coins, review_note=existing.review_note, student=student_summary(student))
    submission = HomeworkSubmission(homework_id=homework_id, student_id=student.id, content=payload.content)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return HomeworkSubmissionRead(id=submission.id, content=submission.content, submitted_at=submission.submitted_at, score=submission.score, awarded_coins=submission.awarded_coins, review_note=submission.review_note, student=student_summary(student))


@router.post("/submissions/{submission_id}/review", response_model=HomeworkSubmissionRead)
def review_submission(submission_id: int, payload: HomeworkSubmissionReview, db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.TEACHER))) -> HomeworkSubmissionRead:
    teacher = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    submission = get_submission_or_404(db, submission_id)
    homework = get_homework_or_404(db, submission.homework_id)
    group = get_group_or_404(db, homework.group_id)
    ensure_teacher_owns_group(group, teacher.id)
    submission.score = payload.score
    submission.review_note = payload.review_note
    submission.reviewed_by_teacher_id = teacher.id
    submission.awarded_coins = payload.awarded_coins
    existing_awarded = submission.coin_transaction.coins if submission.coin_transaction else 0
    coin_delta = payload.awarded_coins - existing_awarded
    if coin_delta > 0:
        ensure_coin_limit(db, group.id, teacher.id, coin_delta)
    if payload.awarded_coins:
        if submission.coin_transaction:
            submission.coin_transaction.coins = payload.awarded_coins
            submission.coin_transaction.reason = f"Homework review: {homework.title}"
        else:
            db.add(
                CoinTransaction(
                    group_id=group.id,
                    student_id=submission.student_id,
                    teacher_id=teacher.id,
                    coins=payload.awarded_coins,
                    reason=f"Homework review: {homework.title}",
                    source=CoinSource.HOMEWORK_REVIEW,
                    submission_id=submission.id,
                )
            )
    elif submission.coin_transaction:
        db.delete(submission.coin_transaction)
    db.commit()
    db.refresh(submission)
    return HomeworkSubmissionRead(id=submission.id, content=submission.content, submitted_at=submission.submitted_at, score=submission.score, awarded_coins=submission.awarded_coins, review_note=submission.review_note, student=student_summary(submission.student))


@router.get("/student/dashboard", response_model=StudentDashboard)
def student_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_role(RoleEnum.STUDENT))) -> StudentDashboard:
    student = db.query(StudentProfile).options(joinedload(StudentProfile.user)).filter(StudentProfile.user_id == current_user.id).first()
    links = db.query(GroupStudent).filter(GroupStudent.student_id == student.id).all()
    groups = [group_read(db, get_group_or_404(db, link.group_id)) for link in links]
    attendance_rows = db.query(Attendance.status, func.count(Attendance.id)).filter(Attendance.student_id == student.id).group_by(Attendance.status).all()
    attendance_stats = {"present": 0, "late": 0, "absent": 0}
    for status_value, count in attendance_rows:
        attendance_stats[status_value.value] = count
    average_mark = db.query(func.avg(Mark.score)).filter(Mark.student_id == student.id).scalar() or 0
    total_coins = db.query(func.coalesce(func.sum(CoinTransaction.coins), 0)).filter(CoinTransaction.student_id == student.id).scalar() or 0
    group_ids = [link.group_id for link in links]
    pending = []
    if group_ids:
        pending = (
            db.query(Homework)
            .filter(Homework.group_id.in_(group_ids))
            .order_by(Homework.due_date.asc())
            .limit(10)
            .all()
        )
    return StudentDashboard(
        student=student_summary(student),
        groups=groups,
        attendance_summary={key: int(value) for key, value in attendance_stats.items()},
        average_mark=round(float(average_mark), 2),
        total_coins=int(total_coins),
        pending_homeworks=[homework_read(db, row) for row in pending],
    )
