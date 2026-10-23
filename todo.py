import os

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user, logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/todo"
)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to see your ToDo list"
login_manager.login_message_category = "warning"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    todos = db.relationship("ToDo", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ToDo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    complete = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def get_own_todo_or_404(id):
    return db.first_or_404(db.select(ToDo).filter_by(id=id, user_id=current_user.id))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    username = (request.form.get("username") or "").strip()
    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        error = None
        if not username or len(username) > 80:
            error = "Username must be between 1 and 80 characters"
        elif len(password) < 6:
            error = "Password must be at least 6 characters"
        elif password != confirm:
            error = "Passwords do not match"
        elif db.session.execute(db.select(User).filter_by(username=username)).scalar():
            error = "This username is already taken"
        if error:
            flash(error, "error")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Registered successfully", "success")
            return redirect(url_for("index"))
    return render_template("auth_form.html", heading="Register", confirm=True, username=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    username = (request.form.get("username") or "").strip()
    if request.method == "POST":
        password = request.form.get("password") or ""
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password", "error")
    return render_template("auth_form.html", heading="Login", confirm=False, username=username)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out", "warning")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total = ToDo.query.filter_by(user_id=current_user.id).count()
    done = ToDo.query.filter_by(user_id=current_user.id, complete=True).count()
    percent = round(done * 100 / total) if total else 0
    return render_template("dashboard.html", total=total, done=done, percent=percent)


@app.route("/")
@login_required
def index():
    todos = ToDo.query.filter_by(user_id=current_user.id).order_by(ToDo.id).all()
    return render_template("index.html", todos = todos)

@app.route("/add", methods=["POST"])
@login_required
def addTodo():
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("ToDo title cannot be empty", "error")
        return redirect(url_for("index"))
    if len(title) > 80:
        flash("ToDo title must be at most 80 characters", "error")
        return redirect(url_for("index"))
    newTodo = ToDo(title = title, complete = False, user_id = current_user.id)
    db.session.add(newTodo)
    db.session.commit()
    flash("ToDo added successfully", "success")
    return redirect(url_for("index"))

@app.route("/complete/<int:id>", methods=["POST"])
@login_required
def complete(id):
    todo = get_own_todo_or_404(id)
    todo.complete = not todo.complete
    db.session.commit()
    flash("ToDo updated successfully", "warning")
    return redirect(url_for("index"))


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    todo = get_own_todo_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    flash("ToDo deleted successfully", "error")
    return redirect(url_for("index"))


def init_db():
    db.create_all()
    # Databases created before user accounts existed have no user_id column.
    table = ToDo.__tablename__
    columns = [c["name"] for c in inspect(db.engine).get_columns(table)]
    if "user_id" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES "user" (id)'))


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
