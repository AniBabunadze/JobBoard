import os
import uuid
from bs4 import BeautifulSoup
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_user, login_required, logout_user, LoginManager
from werkzeug.utils import secure_filename
from PIL import Image
import requests

from db import db
from models import User, Vacancy
from forms import RegisterForm, LoginForm, VacancyForm
from logger import app_logger

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DEFAULT_PROFILE = "default.png"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") or "change-this-secret"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") or \
    "sqlite:///" + os.path.join(basedir, "instance", "app.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_image(file_stream):
    filename = secure_filename(file_stream.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)
    img = Image.open(file_stream)
    img.thumbnail((400, 400))
    img.save(path)
    return new_name

def strip_html(html):
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(strip=True)

# routes
@app.route('/')
def index():
    latest = Vacancy.query.order_by(Vacancy.created_at.desc()).limit(6).all()
    return render_template('index.html', latest=latest)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash('Username or email already taken.', 'warning')
            return redirect(url_for('register'))
        u = User(username=form.username.data, email=form.email.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        app_logger.info(f"New user registered: {u.email}")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            app_logger.info(f"User {user.email} logged in successfully")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid credentials', 'danger')
        app_logger.warning(f"Failed login attempt for {form.email.data}")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    app_logger.info(f"User {current_user.email} logged out")
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/vacancies')
def vacancies():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    q = Vacancy.query.order_by(Vacancy.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('vacancies.html', pagination=pagination)

@app.route('/vacancies/category/<string:name>')
def vacancies_by_category(name):
    page = request.args.get('page', 1, type=int)
    per_page = 9
    q = Vacancy.query.filter_by(category=name).order_by(Vacancy.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('vacancies.html', pagination=pagination, category=name)

@app.route('/vacancy/<int:vacancy_id>')
def vacancy_detail(vacancy_id):
    v = Vacancy.query.get_or_404(vacancy_id)
    return render_template('vacancy_detail.html', v=v)

@app.route('/vacancy/add', methods=['GET', 'POST'])
@login_required
def add_vacancy():
    form = VacancyForm()
    if form.validate_on_submit():
        v = Vacancy(
            title=form.title.data,
            short_description=form.short_description.data,
            full_description=form.full_description.data,
            company=form.company.data,
            salary=form.salary.data,
            location=form.location.data,
            category=form.category.data,
            author_id=current_user.id
        )
        db.session.add(v)
        db.session.commit()
        flash('Vacancy created.', 'success')
        app_logger.info(f"Vacancy '{v.title}' added by {current_user.email}")
        return redirect(url_for('profile'))
    return render_template('add_vacancy.html', form=form)

@app.route('/vacancy/<int:vacancy_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vacancy(vacancy_id):
    v = Vacancy.query.get_or_404(vacancy_id)
    if v.author != current_user:
        app_logger.warning(f"User {current_user.email} tried to edit vacancy {v.id} without permission")
        abort(403)
    form = VacancyForm(obj=v)
    if form.validate_on_submit():
        v.title = form.title.data
        v.short_description = form.short_description.data
        v.full_description = form.full_description.data
        v.company = form.company.data
        v.salary = form.salary.data
        v.location = form.location.data
        v.category = form.category.data
        db.session.commit()
        flash('Vacancy updated.', 'success')
        app_logger.info(f"Vacancy '{v.title}' edited by {current_user.email}")
        return redirect(url_for('vacancy_detail', vacancy_id=v.id))
    return render_template('add_vacancy.html', form=form, edit=True)

@app.route('/vacancy/<int:vacancy_id>/delete', methods=['POST'])
@login_required
def delete_vacancy(vacancy_id):
    v = Vacancy.query.get_or_404(vacancy_id)
    if v.author != current_user:
        app_logger.warning(f"User {current_user.email} tried to delete vacancy {v.id} without permission")
        abort(403)
    db.session.delete(v)
    db.session.commit()
    flash('Vacancy deleted.', 'info')
    app_logger.info(f"Vacancy '{v.title}' deleted by {current_user.email}")
    return redirect(url_for('profile'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        file = request.files.get('profile_image')
        if file and allowed_file(file.filename):
            new_img = save_image(file)
            if current_user.profile_image != DEFAULT_PROFILE:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_image))
                except Exception:
                    pass
            current_user.profile_image = new_img
            db.session.commit()
            flash('Profile image updated.', 'success')
            app_logger.info(f"User {current_user.email} updated profile image")
            return redirect(url_for('profile'))
    user_vacancies = Vacancy.query.filter_by(author_id=current_user.id).order_by(Vacancy.created_at.desc()).all()
    return render_template('profile.html', user=current_user, vacancies=user_vacancies)

@app.route('/user/<int:user_id>')
def public_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_vacancies = Vacancy.query.filter_by(author_id=user.id).order_by(Vacancy.created_at.desc()).all()
    return render_template('profile.html', user=user, vacancies=user_vacancies, public=True)

@app.route("/external_jobs")
def external_jobs():
    url = "https://remotive.com/api/remote-jobs"
    params = {"limit": 20, "category": "software-dev"}
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
    except Exception as e:
        app_logger.error(f"External API error: {e}")
        jobs = []
    return render_template("external_jobs.html", jobs=jobs)

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    app_logger.warning(f"404 error at path: {request.path}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    app_logger.error(f"500 error: {e} at path: {request.path}")
    return render_template('500.html'), 500

# Init DB
@app.cli.command("initdb")
def initdb():
    os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
    db.create_all()
    print("Initialized the database.")

if __name__ == '__main__':
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
    app.run(debug=True)
