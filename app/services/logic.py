from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models import CoinTransaction, Group, GroupStudent, Homework, HomeworkSubmission, StudentProfile, TeacherProfile


class NotFoundError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)



def get_group_or_404(db: Session, group_id: int) -> Group:
    group = (
        db.query(Group)
        .options(joinedload(Group.direction), joinedload(Group.teacher).joinedload(TeacherProfile.user))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise NotFoundError("Group not found")
    return group



def get_student_or_404(db: Session, student_id: int) -> StudentProfile:
    student = db.query(StudentProfile).options(joinedload(StudentProfile.user)).filter(StudentProfile.id == student_id).first()
    if not student:
        raise NotFoundError("Student not found")
    return student



def get_teacher_or_404(db: Session, teacher_id: int) -> TeacherProfile:
    teacher = db.query(TeacherProfile).options(joinedload(TeacherProfile.user)).filter(TeacherProfile.id == teacher_id).first()
    if not teacher:
        raise NotFoundError("Teacher not found")
    return teacher



def ensure_student_in_group(db: Session, group_id: int, student_id: int) -> None:
    link = db.query(GroupStudent).filter(GroupStudent.group_id == group_id, GroupStudent.student_id == student_id).first()
    if not link:
        raise ValidationError("Student is not assigned to this group")



def ensure_teacher_owns_group(group: Group, teacher_id: int) -> None:
    if group.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Teacher is not assigned to this group")



def get_group_coin_usage(db: Session, group_id: int, teacher_id: int) -> int:
    total = db.query(func.coalesce(func.sum(CoinTransaction.coins), 0)).filter(
        CoinTransaction.group_id == group_id,
        CoinTransaction.teacher_id == teacher_id,
    ).scalar()
    return int(total or 0)



def get_group_coin_limit(db: Session, group_id: int) -> int:
    student_count = db.query(func.count(GroupStudent.id)).filter(GroupStudent.group_id == group_id).scalar()
    return int(student_count or 0) * 100



def ensure_coin_limit(db: Session, group_id: int, teacher_id: int, coins_to_add: int) -> tuple[int, int]:
    current_usage = get_group_coin_usage(db, group_id, teacher_id)
    limit = get_group_coin_limit(db, group_id)
    if current_usage + coins_to_add > limit:
        raise ValidationError(
            f"Coin limit exceeded for this group. Used {current_usage} of {limit}, attempted +{coins_to_add}."
        )
    return current_usage, limit



def get_homework_or_404(db: Session, homework_id: int) -> Homework:
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise NotFoundError("Homework not found")
    return homework



def get_submission_or_404(db: Session, submission_id: int) -> HomeworkSubmission:
    submission = (
        db.query(HomeworkSubmission)
        .options(joinedload(HomeworkSubmission.student).joinedload(StudentProfile.user))
        .filter(HomeworkSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise NotFoundError("Submission not found")
    return submission
