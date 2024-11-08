from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import app, db
from models import User
from werkzeug.security import check_password_hash
from email_validator import validate_email, EmailNotValidError

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Successfully logged in!', 'success')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password', 'error')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Validate email
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError:
            flash('Invalid email address', 'error')
            return render_template('auth/register.html')

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email address already registered', 'error')
            return render_template('auth/register.html')

        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('auth/register.html')

    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('index'))
