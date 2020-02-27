from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

pg_user = "postgres"
pg_pw = "********"
pg_db = "todo"
pg_host = "localhost"
pg_port = "5432"

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://{}:{}@{}:{}/{}".format(pg_user, pg_pw, pg_host, pg_port, pg_db)
db = SQLAlchemy(app)

@app.route("/")
def index():
    todos = ToDo.query.order_by("id").all()
    return render_template("index.html", todos = todos)

@app.route("/add", methods=["POST"])
def addTodo():
    title=request.form.get("title")
    newTodo = ToDo(title = title, complete = False)
    db.session.add(newTodo)
    db.session.commit()
    flash("ToDo added successfuly", "success")
    return redirect(url_for("index"))

@app.route("/complete/<string:id>")
def complete(id):
    todo = ToDo.query.filter_by(id=id).first()
    todo.complete = not todo.complete
    db.session.commit()
    flash("ToDo update successfuly", "warning")
    return redirect(url_for("index"))


@app.route("/delete/<string:id>")
def delete(id):
    todo = ToDo.query.filter_by(id=id).first()
    db.session.delete(todo)
    db.session.commit()
    flash("ToDo deleted successfuly", "error")
    return redirect(url_for("index"))


class ToDo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    complete = db.Column(db.Boolean)

if __name__ == "__main__":
    app.secret_key = 'super secret key'
    db.create_all()
    app.run(debug=True)
