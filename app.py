import os, secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
db_url = os.environ.get("DATABASE_URL", "sqlite:///captchaearn.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
csrf = CSRFProtect(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    balance_paise = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    instruction = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(300), nullable=False)
    reward_paise = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

class Completion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "task_id", name="unique_user_task"),)

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_paise = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(20), nullable=False)
    destination = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_note = db.Column(db.String(300), default="")

class Ledger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_paise = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(250), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=40)])
    email = StringField("Email", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class TaskForm(FlaskForm):
    title = StringField("Task title", validators=[DataRequired(), Length(max=100)])
    instruction = TextAreaField("Text users should transcribe", validators=[DataRequired(), Length(max=500)])
    answer = StringField("Expected answer", validators=[DataRequired(), Length(max=300)])
    reward = DecimalField("Reward (₹)", validators=[DataRequired(), NumberRange(min=0.01, max=100)], places=2)
    submit = SubmitField("Add task")

class WithdrawForm(FlaskForm):
    amount = DecimalField("Amount (₹)", validators=[DataRequired(), NumberRange(min=10, max=5000)], places=2)
    method = SelectField("Payment method", choices=[("UPI","UPI"),("Paytm","Paytm")])
    destination = StringField("UPI ID or Paytm number", validators=[DataRequired(), Length(min=5, max=120)])
    submit = SubmitField("Request withdrawal")

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

@app.template_filter("rupees")
def rupees(paise):
    return f"₹{paise / 100:.2f}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        username = form.username.data.strip()
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("Email or username already exists.", "error")
        else:
            user = User(username=username, email=email, password_hash=generate_password_hash(form.password.data))
            db.session.add(user); db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for("admin") if user.is_admin else url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    completed = {c.task_id for c in Completion.query.filter_by(user_id=current_user.id).all()}
    tasks = Task.query.filter_by(active=True).order_by(Task.id.desc()).all()
    history = Ledger.query.filter_by(user_id=current_user.id).order_by(Ledger.created_at.desc()).limit(12).all()
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id).order_by(Withdrawal.created_at.desc()).limit(8).all()
    return render_template("dashboard.html", tasks=tasks, completed=completed, history=history, withdrawals=withdrawals)

@app.route("/task/<int:task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task or not task.active:
        abort(404)
    if Completion.query.filter_by(user_id=current_user.id, task_id=task.id).first():
        flash("You have already completed this task.", "error")
        return redirect(url_for("dashboard"))
    typed = request.form.get("typed_answer", "").strip().casefold()
    if typed != task.answer.strip().casefold():
        flash("That answer does not match. Please try again.", "error")
        return redirect(url_for("dashboard"))
    # Unique constraint protects against duplicate rewards.
    db.session.add(Completion(user_id=current_user.id, task_id=task.id))
    current_user.balance_paise += task.reward_paise
    db.session.add(Ledger(user_id=current_user.id, amount_paise=task.reward_paise,
                          kind="Task reward", note=f"Completed: {task.title}"))
    db.session.commit()
    flash(f"Correct! {task.reward_paise/100:.2f} credited to your wallet.", "success")
    return redirect(url_for("dashboard"))

@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    form = WithdrawForm()
    if form.validate_on_submit():
        amount = int(form.amount.data * 100)
        destination = form.destination.data.strip()
        if amount > current_user.balance_paise:
            flash("Insufficient wallet balance.", "error")
        else:
            current_user.balance_paise -= amount
            w = Withdrawal(user_id=current_user.id, amount_paise=amount,
                           method=form.method.data, destination=destination)
            db.session.add(w)
            db.session.add(Ledger(user_id=current_user.id, amount_paise=-amount,
                                  kind="Withdrawal hold", note=f"{form.method.data} withdrawal requested"))
            db.session.commit()
            flash("Withdrawal request submitted for admin review.", "success")
            return redirect(url_for("dashboard"))
    else:
        flash("Enter a valid amount (₹10–₹5,000) and payment destination.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin")
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).limit(100).all()
    tasks = Task.query.order_by(Task.id.desc()).all()
    withdrawals = Withdrawal.query.order_by(Withdrawal.created_at.desc()).all()
    form = TaskForm()
    return render_template("admin.html", users=users, tasks=tasks, withdrawals=withdrawals, form=form)

@app.route("/admin/task", methods=["POST"])
@admin_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        reward = int(form.reward.data * 100)
        db.session.add(Task(title=form.title.data.strip(), instruction=form.instruction.data.strip(),
                            answer=form.answer.data.strip(), reward_paise=reward))
        db.session.commit()
        flash("Task added.", "success")
    else:
        flash("Please check the task fields. Reward must be ₹0.01–₹100.", "error")
    return redirect(url_for("admin"))

@app.route("/admin/task/<int:task_id>/toggle", methods=["POST"])
@admin_required
def toggle_task(task_id):
    task = db.session.get(Task, task_id)
    if not task: abort(404)
    task.active = not task.active
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/withdrawal/<int:wid>/<action>", methods=["POST"])
@admin_required
def decide_withdrawal(wid, action):
    w = db.session.get(Withdrawal, wid)
    if not w: abort(404)
    if w.status != "Pending":
        flash("This request has already been processed.", "error")
    elif action == "approve":
        w.status = "Approved"
        w.admin_note = "Marked paid by admin. Complete the actual transfer separately."
        db.session.commit()
        flash("Marked approved. Remember to make the actual payment.", "success")
    elif action == "reject":
        w.status = "Rejected"
        user = db.session.get(User, w.user_id)
        user.balance_paise += w.amount_paise
        db.session.add(Ledger(user_id=user.id, amount_paise=w.amount_paise,
                              kind="Withdrawal refund", note="Withdrawal request rejected"))
        db.session.commit()
        flash("Request rejected and balance refunded.", "success")
    else:
        abort(400)
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(e):
    return render_template("message.html", title="Access denied", message="Admin access is required."), 403

with app.app_context():
    db.create_all()
    # Create the first admin only when credentials are explicitly configured.
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password and not User.query.filter_by(email=admin_email.lower()).first():
        db.session.add(User(username="admin", email=admin_email.lower(),
                            password_hash=generate_password_hash(admin_password), is_admin=True))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
