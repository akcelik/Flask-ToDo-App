import os

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/todo"
)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
db = SQLAlchemy(app)


class ToDo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    complete = db.Column(db.Boolean, default=False, nullable=False)


@app.route("/")
def index():
    todos = ToDo.query.order_by(ToDo.id).all()
    return render_template("index.html", todos = todos)

@app.route("/add", methods=["POST"])
def addTodo():
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("ToDo title cannot be empty", "error")
        return redirect(url_for("index"))
    if len(title) > 80:
        flash("ToDo title must be at most 80 characters", "error")
        return redirect(url_for("index"))
    newTodo = ToDo(title = title, complete = False)
    db.session.add(newTodo)
    db.session.commit()
    flash("ToDo added successfully", "success")
    return redirect(url_for("index"))

@app.route("/complete/<int:id>", methods=["POST"])
def complete(id):
    todo = db.get_or_404(ToDo, id)
    todo.complete = not todo.complete
    db.session.commit()
    flash("ToDo updated successfully", "warning")
    return redirect(url_for("index"))


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    todo = db.get_or_404(ToDo, id)
    db.session.delete(todo)
    db.session.commit()
    flash("ToDo deleted successfully", "error")
    return redirect(url_for("index"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
