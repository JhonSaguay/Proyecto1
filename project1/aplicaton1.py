mport os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from required import login_required
app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")

def index():
    return render_template("register.html")

@app.route("/register")

def register():
    return render_template("register.html")
@app.route("/login")
def login():
    return render_template("loginvista.html")

@app.route("/searching", methods=["POST"])
def search():
    str=request.form.get("tblibro")
    #print(str)
    consulta="select * from books where author like "+"'%"+str+"%'"
    booklist=db.execute(consulta).fetchall()
    return  render_template("index.html", cadena=str,books=booklist)
    #return "Project 1: TODO"
@app.route("/register", methods=["POST"])
def user_new():
    user=request.form.get("tbuser")
    password=request.form.get("tbpass")
    confpassword=request.form.get("tbconfpass")
    if password==confpassword:
        consulta="INSERT INTO users(username,password) VALUES (:username,:password)"
        db.execute(consulta,{"username":user,"password":password})
        db.commit()
        return  render_template("index.html")
    else:
        print("valio verga")
        return render_template("register.html")
    #return "Project 1: TODO"
