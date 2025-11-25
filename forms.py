from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6, 128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


CATEGORY_CHOICES = [
    ("IT", "IT"),
    ("Design", "Design"),
    ("Marketing", "Marketing"),
    ("Sales", "Sales"),
    ("Management", "Management"),
    ("Finance", "Finance"),
    ("HR", "HR"),
    ("Customer Support", "Customer Support"),
    ("Engineering", "Engineering"),
    ("Other", "Other"),
]

class VacancyForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    short_description = StringField("Short Description", validators=[DataRequired(), Length(max=300)])
    full_description = TextAreaField("Full Description", validators=[DataRequired()])
    company = StringField("Company", validators=[DataRequired()])
    salary = StringField("Salary")
    location = StringField("Location", validators=[DataRequired()])
    category = SelectField("Category", choices=CATEGORY_CHOICES, validators=[DataRequired()])
    submit = SubmitField("Save")