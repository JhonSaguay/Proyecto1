import os, json

from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

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
@login_required # Calls the decorator from required.py using @, AKA index = login_required(index)
def index():
    return render_template("index.html")

#login

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear() # Forget old sessions

    username = request.form.get("tbuser")

    if request.method == "POST":

        # Render error.html in case of not username and password
        if not request.form.get("tbuser"):
            return render_template("error.html", message="Please enter a username")

        elif not request.form.get("tbpass"):
            return render_template("error.html", message="Please enter a password")

        # Connect to database
        query = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})

        # Fetch row to check if username
        result = query.fetchone()

        # Ensure username exists and password is correct
        if result == None or not check_password_hash(result[1], request.form.get("tbpass")):
            return render_template("error.html", message="invalid username and/or password")

        # Remember users
        #session["user_id"] = result[0]
        session["user_id"] = result[2]
        session["user_name"] = result[0]

        # Redirect user to index page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("loginvista.html")

# Register user function
@app.route("/register", methods=["GET", "POST"])
# Register user function
@app.route("/register", methods=["GET", "POST"])
def register():

    # Clear session before any new user
    session.clear()

    if request.method == "POST":

        # Render error.html in case of not username
        if not request.form.get("username"):
            return render_template("error.html", message="Please enter a username")

        # Query database for username
        user = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check if username already exist
        if user:
            return render_template("error.html", message="username already exist")

        # Check if password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="Please enter a password")

        # Check if password confirmation form was filled
        elif not request.form.get("confirmation"):
            return render_template("error.html", message="Please confirm password")

        # Check if passwords are equal
        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords did not match")

        # Store hashed password
        hashedPass = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                            {"username":request.form.get("username"),
                             "password":hashedPass})

        # Commit
        db.commit()

        flash('Account created', 'info')

        # Redirect user to login page
        return redirect("/login")

    else:
        return render_template("register.html")


# Logout user -- Clear session
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# Search feature
@app.route("/searching", methods=["POST"])
@login_required
def search():
    #if not request.form.get("tblibro"):
    #    return render_template("error.html", message="you must provide a book name.")

    str=request.form.get("tblibro")
    consulta="select * from books where \
                    author like "+"'%"+str+"%' or \
                    isbn like '%"+str+"%' or \
                    title like '%"+str+"%'"

    booklist=db.execute(consulta).fetchall()
    if len(booklist)==0:
        return render_template("error.html", message="we can not find the book in our database")
    return  render_template("index.html", books=booklist)




@app.route("/review/<isbn>", methods=['GET','POST'])
@login_required
def review(isbn):

    if request.method == "POST":

        # To save the user review
        currentUser = session["user_id"]

        # Fetch rating and comment from DB
        rating = request.form.get("rating")
        comment = request.form.get("comment")

        # Query
        query1 = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save book ID
        bookId = query1.fetchone()
        bookId = bookId[0]

        # Count user reviews
        query2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND bookid = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})

        # If a review already exists
        if query2.rowcount == 1:

            flash('You already submitted a review for this book', 'error')
            return redirect("/review/" + isbn)

        # Save review and rating
        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, bookid, review, rate) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": currentUser,
                    "book_id": bookId,
                    "comment": comment,
                    "rating": rating})

        # Commit
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/review/" + isbn)

    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()


        # Read API key from env variable
        key =  "MqYsUeFuM3qV5wcqdqJlSQ"

        # API call
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})


        # Save data in json format
        json = query.json()
        json = json['books'][0]
        bookInfo.append(json)

        # Get book ID and saved
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        book = row.fetchone()
        book = book[0]

        # Query for reviews
        results = db.execute("SELECT users.username, review, rate \
                            FROM users \
                            INNER JOIN reviews \
                            ON users.user_id = reviews.user_id \
                            WHERE bookid = :book",
                            {"book": book})

        reviews = results.fetchall()

        return render_template("review.html", bookInfo=bookInfo, reviews=reviews)


# Page for the website's API
@app.route("/api/<ISBN>", methods=["GET"])
def api(ISBN):
    book = db.execute("SELECT * FROM books WHERE isbn = :ISBN", {"ISBN": ISBN}).fetchone()
    if book is None:
        return render_template("error.html", error_message="ERROR 404 no ISBN. "
                                                           "Please check for the errors and try again.")
    reviews = db.execute("SELECT * FROM reviews WHERE bookid = :book_id", {"book_id": book.id}).fetchall()
    count = 0
    rating = 0
    for review in reviews:
        count += 1
        rating += review.rate
    if count:
        average_rating = rating / count
    else:
        average_rating = 0

    return jsonify(
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        review_count=count,
        average_score=average_rating
    )

if __name__== "__main__":
    app.run(debug=True)
