"""Run: uv run pytest tests/test_search_fields.py -q"""
from sqlalchemy.orm import Session
from app.models.resource import Resource, ResourceAuthor


def test_search_by_specific_fields(client, student, librarian, test_engine):
    with Session(test_engine) as db:
        book = Resource(title="Quantum River Text", resource_type="book",
                        isbn="9781112223334", doi="10.1234/example.field",
                        abstract="advanced orbital notes", uploaded_by=librarian,
                        is_published=True, is_archived=False)
        book.authors.append(ResourceAuthor(author_name="Nneka Eze", author_order=1))
        other = Resource(title="Nneka Eze Manual", resource_type="book",
                         uploaded_by=librarian, is_published=True, is_archived=False)
        draft = Resource(title="Hidden Draft", resource_type="book",
                         isbn="9780000000000", uploaded_by=librarian,
                         is_published=False, is_archived=False)
        db.add_all([book, other, draft]);db.commit()
    r=client.post('/auth/login',json={'email':'student@test.com','password':'TestPassword123!'})
    assert r.status_code==200
    h={'Authorization':f"Bearer {r.json()['access_token']}"}
    cases=[('title','Quantum River',1),('author','Nneka Eze',1),
           ('isbn','9781112223334',1),('doi','10.1234/example.field',1),
           ('abstract','orbital notes',1),('all','Nneka Eze',2),
           ('isbn','9780000000000',0)]
    for field,term,expected in cases:
        response=client.get('/resources',params={'search_field':field,'search':term},headers=h)
        assert response.status_code==200,(field,response.text)
        assert response.json()['total']==expected,(field,response.json())
    invalid=client.get('/resources',params={'search_field':'publisher','search':'x'},headers=h)
    assert invalid.status_code==422
