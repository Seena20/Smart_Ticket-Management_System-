from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "secret123"   # 🔥 required for login

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- LOGIN SETUP ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------- USER MODEL ----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default="user")  # user / admin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- TICKET MODEL ----------------
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    issue = db.Column(db.String(200))
    priority = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Open")
    response=db.Column(db.Text)

    # 🔥 NEW: Link ticket to user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))



# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if user:
            login_user(user)
            return redirect("/")
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=request.form["password"],
            role=request.form["role"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ---------------- HOME ----------------
@app.route("/")
@login_required
def home():

    total = Ticket.query.count()

    open_tickets = Ticket.query.filter(
        db.func.lower(Ticket.status) == "open"
    ).count()

    closed_tickets = Ticket.query.filter(
        db.func.lower(Ticket.status) == "closed"
    ).count()

    high = Ticket.query.filter(
        db.func.lower(Ticket.priority) == "high"
    ).count()

    medium = Ticket.query.filter(
        db.func.lower(Ticket.priority) == "medium"
    ).count()

    low = Ticket.query.filter(
        db.func.lower(Ticket.priority) == "low"
    ).count()

    latest = Ticket.query.order_by(Ticket.id.desc()).limit(5).all()

    return render_template(
        "home.html",
        total=total,
        open=open_tickets,
        closed=closed_tickets,
        high=high,
        medium=medium,
        low=low,
        latest=latest,
        user=current_user
    )


# ---------------- ADD ----------------
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        t = Ticket(
            name=request.form["name"],
            issue=request.form["issue"],
            priority=request.form["priority"],
            user_id=current_user.id   # 🔥 link user
        )
        db.session.add(t)
        db.session.commit()
        return redirect("/tickets")

    return render_template("add_ticket.html")
# ---------------- VIEW ----------------
@app.route("/tickets")
@login_required
def tickets():

    # 🔥 Admin sees all, user sees only their tickets
    if current_user.role == "admin":
        data = Ticket.query.all()
    else:
        data = Ticket.query.filter_by(user_id=current_user.id).all()

    return render_template("view_tickets.html", tickets=data)


# ---------------- SEARCH ----------------
@app.route("/search")
@login_required
def search():
    q = request.args.get("q")

    data = Ticket.query.filter(
        (Ticket.name.contains(q)) | (Ticket.issue.contains(q))
    ).all()

    return render_template("view_tickets.html", tickets=data)


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    t = Ticket.query.get(id)

    # 🔥 Only owner or admin can delete
    if current_user.role == "admin" or t.user_id == current_user.id:
        db.session.delete(t)
        db.session.commit()

    return redirect("/tickets")


# ---------------- CLOSE ----------------
@app.route("/close/<int:id>")
@login_required
def close(id):
    t = Ticket.query.get(id)
    t.status = "Closed"
    db.session.commit()
    return redirect("/tickets")

#reply
@app.route("/reply/<int:id>", methods=["GET", "POST"])
def reply(id):
    t = Ticket.query.get(id)

    if request.method == "POST":
        t.response = request.form["response"]
        db.session.commit()
        return redirect("/tickets")

    return render_template("reply.html", t=t)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)