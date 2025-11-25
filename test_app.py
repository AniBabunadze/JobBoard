import pytest
from app import app, db
from models import User, Vacancy


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


@pytest.fixture
def test_user():
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("123456")
        db.session.add(user)
        db.session.commit()
        return user


# 1. ROUTE TEST

def test_routes(client):
    response = client.get('/')
    assert response.status_code == 200

    response = client.get('/login')
    assert response.status_code == 200

    response = client.get('/register')
    assert response.status_code == 200

    response = client.get('/vacancies')
    assert response.status_code == 200



# 2. LOGIN TEST

def test_login_success(client, test_user):
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" in response.data  # navbar shows logged-in user


def test_login_fail(client, test_user):
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert b"Invalid credentials" in response.data



# 3. PERMISSIONS TEST

def test_vacancy_permissions(client, test_user):
    with app.app_context():
        # user
        author = User(username="author", email="author@example.com")
        author.set_password("111111")
        db.session.add(author)
        db.session.commit()

        vacancy = Vacancy(
            title="Test Job",
            short_description="short",
            full_description="full",
            company="Comp",
            location="Loc",
            category="IT",
            author_id=author.id
        )
        db.session.add(vacancy)
        db.session.commit()
        vacancy_id = vacancy.id

    # login as test_user (not author)
    client.post('/login', data={
        'email': 'test@example.com',
        'password': '123456'
    }, follow_redirects=True)

    # try to edit vacancy
    response = client.post(f'/vacancy/{vacancy_id}/edit', data={
        'title': 'Hacked'
    }, follow_redirects=True)
    assert b"403" in response.data or response.status_code == 403

    # try to delete vacancy
    response = client.post(f'/vacancy/{vacancy_id}/delete', follow_redirects=True)
    assert b"403" in response.data or response.status_code == 403
