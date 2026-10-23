from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.academic import Course
from app.models.course_reading_list import (
    CourseReadingList,
    CourseReadingListItem,
)
from app.models.resource import Resource
from app.models.user import User
from app.schemas.reading_list import (
    ReadingListCreate,
    ReadingListItemCreate,
    ReadingListUpdate,
)

def fail(code: int, message: str):
    raise HTTPException(status_code=code, detail=message)

def clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        fail(422, "Title cannot be blank.")
    return title

def get_course_for_editor(
    db: Session,
    course_id: int,
    user: User,
) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        fail(404, "Course not found.")
    
    if (
        user.role == "lecturer"
        and course.department_id != user.department_id
    ):
        fail(403, "You cannot manage another department's course.")
    return course

def student_can_view(
    db: Session,
    reading_list: CourseReadingList,
    user: User,
) -> bool:
    if not reading_list.is_published:
        return False
    
    course = db.get(Course, reading_list.course_id)
    if course is None:
        return False
    return (
        course.department_id == user.department_id
        and (
            course.academic_level is None
            or course.academic_level == user.academic_level
        )
    )
    
def can_view(
    db: Session,
    reading_list: CourseReadingList,
    user: User,
) -> bool:
    if user.role == "librarian":
        return True
    if (
        user.role == "lecturer"
        and reading_list.created_by == user.id
    ):
        return True
    if user.role == "student":
        return student_can_view(db, reading_list, user)
    return reading_list.is_published

def can_manage(
    reading_list: CourseReadingList,
    user: User,
) -> bool:
    if user.role == "librarian":
        return True

    if user.role == "lecturer":
        return reading_list.created_by == user.id

    return False
    
def fetch_list(
    db: Session,
    reading_list_id: int,
) -> CourseReadingList:
    reading_list = db.scalar(
        select(CourseReadingList)
        .options(selectinload(CourseReadingList.items))
        .where(CourseReadingList.id == reading_list_id)
    )
    
    if reading_list is None:
        fail(404, "Reading list not found.")
    return reading_list

def get_visible_list(
    db: Session, 
    reading_list_id: int, 
    user: User,
) -> CourseReadingList:
    reading_list = fetch_list(db, reading_list_id)

    if not can_view(db, reading_list, user):
        fail(404, "Reading list not found.")

    return reading_list

def get_editable_list(
    db: Session,
    reading_list_id: int,
    user: User,
) -> CourseReadingList:
    reading_list = db.scalar(
        select(CourseReadingList)
        .where(CourseReadingList.id == reading_list_id)
        .with_for_update()
    )
    
    if reading_list is None or not can_manage(
        reading_list, user
    ):
        fail(404, "Reading list not found.")
    if reading_list.is_published:
        fail(409, "Unpublish this reading list before editing.")
    return reading_list

def create_reading_list(
    db: Session,
    user: User,
    data: ReadingListCreate
) -> CourseReadingList:
    get_course_for_editor(db, data.course_id, user)
    
    reading_list = CourseReadingList(
        course_id=data.course_id,
        title=clean_title(data.title),
        description=data.description,
        academic_session=data.academic_session,
        created_by=user.id,
        is_published=False,
    )
    db.add(reading_list)
    db.flush()

    reading_list_id = reading_list.id

    db.commit()

    return fetch_list(db, reading_list_id)


def list_reading_lists(
    db: Session,
    user: User,
    limit: int,
    offset: int,
    course_id: int | None = None,
):
    statement = select(CourseReadingList).join(
        Course, Course.id == CourseReadingList.course_id
    )
    
    if course_id is not None:
        statement = statement.where(
            CourseReadingList.course_id == course_id
        )
    if user.role == "student":
        statement = statement.where(
            CourseReadingList.is_published.is_(True),
            Course.department_id == user.department_id,
        )
        if user.academic_level is not None:
            statement = statement.where(
                (Course.academic_level.is_(None))
                | (Course.academic_level == user.academic_level)
            )
        else:
            statement = statement.where(
                Course.academic_level.is_(None)
            )
    elif user.role == "lecturer":
        statement = statement.where(
            (CourseReadingList.is_published.is_(True))
            | (CourseReadingList.created_by == user.id)
        )
    elif user.role != "librarian":
        statement = statement.where(
            CourseReadingList.is_published.is_(True)
        )
    total = db.scalar(
        select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
    ) or 0
    
    items = db.scalars(
        statement
        .options(selectinload(CourseReadingList.items))
        .order_by(CourseReadingList.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return items, total

def update_reading_list(
    db: Session, 
    reading_list_id: int,
    user: User,
    data: ReadingListUpdate,
) -> CourseReadingList:
    reading_list = get_editable_list(
        db, reading_list_id, user
    )
    
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes:
        if changes["title"] is None:
            fail(422, "Title cannot be null.")
        changes["title"] = clean_title(changes["title"])
    for key, value in changes.items():
        setattr(reading_list, key, value)
    db.commit()
    return fetch_list(db, reading_list_id)

def add_reading_item(
    db: Session,
    reading_list_id: int,
    user: User,
    data: ReadingListItemCreate,
) -> CourseReadingList:
    get_editable_list(db, reading_list_id, user)
    
    resource = db.get(Resource, data.resource_id)
    
    if (
        resource is None
        or not resource.is_published
        or resource.is_archived
    ):
        fail(400, "Resource must be published and available.")
        
    existing = db.scalar(
        select(CourseReadingListItem).where(
            CourseReadingListItem.reading_list_id == reading_list_id,
            CourseReadingListItem.resource_id == data.resource_id,
        )
    )

    if existing is not None:
        fail(409, "Resource is already in this reading list.")
        
    highest = db.scalar(
        select(func.max(CourseReadingListItem.position))
        .where(
            CourseReadingListItem.reading_list_id == reading_list_id
        )
    ) or 0
    
    item = CourseReadingListItem(
        reading_list_id=reading_list_id,
        resource_id=data.resource_id,
        position=highest + 1,
        notes=data.notes,
        is_required=data.is_required,
    )
    db.add(item)
    db.commit()
    
    return fetch_list(db, reading_list_id)

def remove_reading_item(
    db: Session,
    reading_list_id: int,
    item_id: int,
    user: User,
) -> None:
    get_editable_list(db, reading_list_id, user)
    
    item = db.scalar(
        select(CourseReadingListItem).where(
            CourseReadingListItem.id == item_id,
            CourseReadingListItem.reading_list_id == reading_list_id,
        )
    )
    
    if item is None:
        fail(404, "Reading list item not found.")
    db.delete(item)
    db.commit()
    
def set_publication(
    db: Session,
    reading_list_id: int,
    user: User,
    publish: bool,
) -> CourseReadingList:
    reading_list = db.scalar(
        select(CourseReadingList)
        .where(CourseReadingList.id == reading_list_id)
        .with_for_update()
    )
    
    if reading_list is None or not can_manage(
        reading_list, user
    ):
        fail(404, "Reading list not found.")
        
    if reading_list.is_published == publish:
        fail(409, "Reading list is already in this state.")
    if publish:
        items = db.scalars(
            select(CourseReadingListItem).where(
                CourseReadingListItem.reading_list_id == reading_list_id
            )
        ).all()
        if not items:
            fail(400, "Add a resource before publsihing.")
        
        resource_ids = [item.resource_id for item in items]
        
        valid_count = db.scalar(
            select(func.count(Resource.id)).where(
                Resource.id.in_(resource_ids),
                Resource.is_published.is_(True),
                Resource.is_archived.is_(False),
            )
        ) or 0
        if valid_count != len(resource_ids):
            fail(400, "Reading list contains unavailable resources.")
    reading_list.is_published = publish
    db.commit()
    
    return fetch_list(db, reading_list_id)