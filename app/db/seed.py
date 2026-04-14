from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Attendance,
    AttendanceStatus,
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


def seed_database(db: Session) -> None:
    if db.query(User).first():
        return

    directions = [
        Direction(name="Frontend", description="HTML, CSS, JS va zamonaviy UI asoslari."),
        Direction(name="Backend", description="Python, FastAPI va database bilan ishlash."),
        Direction(name="Design", description="Figma, branding va UX tafakkuri."),
        Direction(name="Beginner", description="Boshlang'ich IT savodxonligi va mantiq."),
    ]
    db.add_all(directions)
    db.flush()

    admin = User(username="admin", full_name="MARS IT Admin", role=RoleEnum.ADMIN, hashed_password=hash_password("admin123"))
    db.add(admin)

    teacher_users = []
    teacher_profiles = []
    for idx, specialty in enumerate(["Frontend Mentor", "Backend Mentor", "Design Mentor"], start=1):
        user = User(
            username=f"teacher{idx}",
            full_name=f"Teacher {idx}",
            role=RoleEnum.TEACHER,
            hashed_password=hash_password("teacher123"),
        )
        db.add(user)
        db.flush()
        profile = TeacherProfile(user_id=user.id, specialty=specialty, bio=f"{specialty} bo'yicha tajribali mentor")
        db.add(profile)
        teacher_users.append(user)
        teacher_profiles.append(profile)
    db.flush()

    groups = [
        Group(name="Frontend N1", direction_id=directions[0].id, teacher_id=teacher_profiles[0].id, schedule="Mon/Wed/Fri 10:00", starts_on=date.today() - timedelta(days=21)),
        Group(name="Backend N1", direction_id=directions[1].id, teacher_id=teacher_profiles[1].id, schedule="Tue/Thu/Sat 14:00", starts_on=date.today() - timedelta(days=30)),
        Group(name="Design N1", direction_id=directions[2].id, teacher_id=teacher_profiles[2].id, schedule="Mon/Wed 16:00", starts_on=date.today() - timedelta(days=14)),
        Group(name="Beginner N1", direction_id=directions[3].id, teacher_id=teacher_profiles[0].id, schedule="Sat/Sun 09:00", starts_on=date.today() - timedelta(days=10)),
    ]
    db.add_all(groups)
    db.flush()

    students = []
    for idx in range(1, 11):
        user = User(
            username=f"student{idx}",
            full_name=f"Student {idx}",
            role=RoleEnum.STUDENT,
            hashed_password=hash_password("student123"),
        )
        db.add(user)
        db.flush()
        student = StudentProfile(user_id=user.id, phone=f"+998900000{idx:02d}", parent_phone=f"+998911111{idx:02d}")
        db.add(student)
        students.append(student)
    db.flush()

    assignments = []
    for idx, student in enumerate(students):
        group = groups[idx % len(groups)]
        assignments.append(GroupStudent(group_id=group.id, student_id=student.id))
        if idx < 4:
            extra_group = groups[(idx + 1) % len(groups)]
            if extra_group.id != group.id:
                assignments.append(GroupStudent(group_id=extra_group.id, student_id=student.id))
    db.add_all(assignments)
    db.flush()

    attendance_rows = []
    mark_rows = []
    coin_rows = []
    homework_rows = []
    submission_rows = []

    for group in groups:
        linked_students = db.query(GroupStudent).filter(GroupStudent.group_id == group.id).all()
        for day_offset in range(1, 4):
            lesson_date = date.today() - timedelta(days=day_offset * 2)
            for link in linked_students:
                status = [AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.ABSENT][(link.student_id + day_offset) % 3]
                attendance_rows.append(
                    Attendance(
                        group_id=group.id,
                        student_id=link.student_id,
                        teacher_id=group.teacher_id,
                        lesson_date=lesson_date,
                        status=status,
                        notes="Seeded attendance",
                    )
                )
                mark_rows.append(
                    Mark(
                        group_id=group.id,
                        student_id=link.student_id,
                        teacher_id=group.teacher_id,
                        score=70 + ((link.student_id + day_offset) % 30),
                        notes="Weekly performance",
                    )
                )
                coin_rows.append(
                    CoinTransaction(
                        group_id=group.id,
                        student_id=link.student_id,
                        teacher_id=group.teacher_id,
                        coins=10 + ((link.student_id + day_offset) % 10),
                        reason="Faollik uchun",
                        source=CoinSource.MANUAL,
                    )
                )
        homework = Homework(
            group_id=group.id,
            teacher_id=group.teacher_id,
            title=f"{group.name} haftalik vazifa",
            description="Platformadagi topshiriqni bajarib, javobingizni tizimga yuboring.",
            due_date=date.today() + timedelta(days=5),
            max_score=100,
        )
        db.add(homework)
        db.flush()
        homework_rows.append(homework)
        for link in linked_students[: min(3, len(linked_students))]:
            submission = HomeworkSubmission(
                homework_id=homework.id,
                student_id=link.student_id,
                content="Seed qilingan javob: mavzu bo'yicha amaliy ish tayyorlandi.",
                score=85,
                awarded_coins=15,
                review_note="Yaxshi ishlangan",
                reviewed_by_teacher_id=group.teacher_id,
            )
            db.add(submission)
            db.flush()
            submission_rows.append(submission)
            coin_rows.append(
                CoinTransaction(
                    group_id=group.id,
                    student_id=link.student_id,
                    teacher_id=group.teacher_id,
                    coins=15,
                    reason="Homework bonus",
                    source=CoinSource.HOMEWORK_REVIEW,
                    submission_id=submission.id,
                )
            )

    db.add_all(attendance_rows)
    db.add_all(mark_rows)
    db.add_all(coin_rows)
    db.commit()


def attendance_breakdown(db: Session) -> dict[str, int]:
    rows = db.query(Attendance.status, func.count(Attendance.id)).group_by(Attendance.status).all()
    stats = {"present": 0, "late": 0, "absent": 0}
    for status, count in rows:
        stats[str(status.value)] = count
    return stats
