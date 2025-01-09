from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

# Models
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    available = db.Column(db.Boolean, default=True)

class Patron(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    borrowed_books = db.relationship('Borrow', backref='patron', lazy=True)

class Borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    patron_id = db.Column(db.Integer, db.ForeignKey('patron.id'), nullable=False)
    borrow_date = db.Column(db.String(100), nullable=False)
    return_date = db.Column(db.String(100), nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

# Configuration for Scopus API
SCOPUS_API_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_API_KEY = "your_scopus_api_key"

# Helper function to fetch books from APIs
def fetch_books_from_apis():
    try:
        scopus_response = requests.get(
            SCOPUS_API_URL,
            headers={"X-ELS-APIKey": SCOPUS_API_KEY},
            params={"query": "ALL(*)"}  # Example query to fetch all data
        )
        scopus_books = scopus_response.json().get("search-results", {}).get("entry", [])
    except Exception as e:
        print(f"Error fetching Scopus data: {e}")
        scopus_books = []

    books = []
    for book in scopus_books:
        books.append({
            "title": book.get("dc:title"),
            "author": book.get("dc:creator"),
            "category": book.get("prism:teaser", "N/A"),
            "available": True
        })

    return books

# Routes
@app.route('/')
def index():
    local_books = Book.query.all()
    api_books = fetch_books_from_apis()
    all_books = [{"id": book.id, **book.__dict__} for book in local_books] + api_books
    return render_template('index.html', books=all_books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or email already exists.", "error")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        new_book = Book(title=title, author=author, category=category)
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/add_patron', methods=['GET', 'POST'])
def add_patron():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        new_patron = Patron(name=name, email=email)
        db.session.add(new_patron)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_patron.html')

@app.route('/borrow_book', methods=['GET', 'POST'])
def borrow_book():
    if request.method == 'POST':
        book_id = request.form['book_id']
        patron_id = request.form['patron_id']
        borrow_date = request.form['borrow_date']
        book = Book.query.get(book_id)
        if book and book.available:
            book.available = False
            new_borrow = Borrow(book_id=book_id, patron_id=patron_id, borrow_date=borrow_date)
            db.session.add(new_borrow)
            db.session.commit()
        return redirect(url_for('index'))
    books = Book.query.filter_by(available=True).all()
    patrons = Patron.query.all()
    return render_template('borrow_book.html', books=books, patrons=patrons)

@app.route('/return_book/<int:borrow_id>', methods=['POST'])
def return_book(borrow_id):
    borrow_record = Borrow.query.get(borrow_id)
    if borrow_record:
        book = Book.query.get(borrow_record.book_id)
        if book:
            book.available = True
        db.session.delete(borrow_record)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
