# Import necessary libraries
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import login_required, current_user, login_user, logout_user, LoginManager, UserMixin
from flask.logging import create_logger
from flask_mysqldb import MySQL
from functools import wraps
import os
import secrets
import validators
import pickle
import urllib
from langdetect import detect
from newspaper import Article, Config
from newsapi import NewsApiClient
from werkzeug.security import generate_password_hash, check_password_hash
from utils import save_history, is_valid_url 
from config import Config as AppConfig  
import pandas as pd  
import newspaper  
import numpy as np  
from datetime import datetime  # Add this import

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
CORS(app)
app.config.from_object(AppConfig)

log = create_logger(app)
mysql = MySQL(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated

# Define User class
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

# Define user_loader function
@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    account = cursor.fetchone()
    cursor.close()
    if account:
        return User(id=account['id'], username=account['username'], email=account['email'])
    return None

# Initialize NewsAPI client
newsapi = NewsApiClient(api_key=AppConfig.NEWS_API_KEY)

@app.route('/', methods=['GET', 'POST'])
def main():
    """Render the main page with top news headlines."""
    data = newsapi.get_top_headlines(language='en', country="us", category='general', page_size=10)
    l1, l2 = zip(*[(i['title'], i['url']) for i in data['articles']])
    return render_template('main.html', l1=l1, l2=l2)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    msg = ''
    email = ''

    if current_user.is_authenticated:
        return redirect('/history')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE email LIKE %s', (email,))
            account = cursor.fetchone()

            if account:
                password_db = account['password_hash']
                if check_password_hash(password_db, password):
                    user = User(id=account['id'], username=account['username'], email=account['email'])
                    login_user(user)  # Log the user in
                    session['logged_in'] = True
                    session['username'] = account['username']
                    session['id'] = account['id']
                    flash('You have successfully logged in!', 'success')
                    return redirect(url_for('main'))
                else:
                    flash('Wrong password! Please try again!', 'danger')
                    return render_template('login.html', email=email)

                cursor.close()
            else:
                flash('Account with this email address does not exist! Please try again!', 'danger')
        except:
            flash('We are having trouble connecting to the database! Please try again later!', 'danger')

    return redirect(url_for('login'))

@app.route('/register', methods=['POST', 'GET'])
def register():
    msg = ''
    email = ''
    username = ''

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        password_hash = generate_password_hash(password)

        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE email LIKE %s', (email,))
            account = cursor.fetchone()

            if account:
                flash('Email already exists!', 'danger')
                return render_template('register.html', username=username)
            elif len(password) < 8:
                flash('Please use a stronger password (*Password must have at least 8 characters)', 'danger')
                return render_template('register.html', email=email, username=username)
            elif not username or not password or not email:
                flash('Please fill out the form to register!', 'danger')
                return render_template('register.html')
            else:
                cursor.execute("INSERT INTO users(email, username, password_hash) VALUES(%s,%s,%s)", (email, username, password_hash))
                mysql.connection.commit()
                cursor.close()
                flash('You have successfully registered and you are allowed to login', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Database connection error: {e}', 'danger')
            return render_template('register.html', email=email, username=username)

    return render_template('register.html', msg=msg)

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login to gain access of this page', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect('/')

@app.route('/history', methods=['GET', 'POST'])
@is_logged_in
def history():
    userID = session['id']
    cursor = mysql.connection.cursor()
    result = cursor.execute('SELECT * FROM history WHERE userID = %s ORDER BY historyDate DESC', (userID,))
    history = cursor.fetchall()
    cursor.close()

    if history:
        record = True
        return render_template('history.html', history=history, record=record)
    else:
        msg = 'No History Found'
        return render_template('history.html', msg=msg, record=False)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Predict whether the news is fake or real."""
    url = request.get_data(as_text=True)[5:]
    url = urllib.parse.unquote(url)

    if is_valid_url(url):  # Use renamed function
        user_agent = request.headers.get('User-Agent')
        config = Config()
        config.browser_user_agent = user_agent

        try:
            article = Article(str(url))
            article.download()
            article.parse()
            parsed = article.text

            if parsed:
                lang = detect(parsed)

                if lang == "en":
                    article.nlp()
                    news_title = article.title
                    news = article.text
                    news_html = article.html

                    if news:
                        news_to_predict = pd.Series(np.array([news]))

                        cleaner = pickle.load(open('TfidfVectorizer-new.sav', 'rb'))
                        model = pickle.load(open('ClassifierModel-new.sav', 'rb'))

                        cleaned_text = cleaner.transform(news_to_predict)
                        pred = model.predict(cleaned_text)
                        pred_outcome = format(pred[0])
                        if pred_outcome == "0":
                            outcome = "True"
                        else:
                            outcome = "False"

                        # Add prediction date
                        prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        if 'logged_in' in session:
                            userID = session['id']
                            save_history(mysql, userID, url, outcome)

                        return render_template(
                            'predict.html',
                            prediction_text=outcome,  # Ensure this is passed correctly
                            url_input=url,
                            news=news,
                            prediction_date=prediction_date  # Pass prediction date
                        )
                    else:
                        flash('Invalid URL! Please try again', 'danger')
                        return redirect(url_for('main'))
                else:
                    language_error = "We currently do not support this language"
                    return render_template('predict.html', language_error=language_error, url_input=url)
            else:
                flash('Invalid news article! Please try again', 'danger')
                return redirect(url_for('main'))
        except newspaper.article.ArticleException:
            flash('We currently do not support this website! Please try again', 'danger')
            return redirect(url_for('main'))
    else:
        flash('Please enter a valid news site URL', 'danger')
        return redirect(url_for('main'))

    return render_template('predict.html')

@app.route('/comments', methods=['GET', 'POST'])
@is_logged_in
def comments():
    if request.method == 'POST':
        comment_text = request.form.get('comment')
        user_id = session['id']
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO comments(userID, commentText) VALUES(%s, %s)", (user_id, comment_text))
        mysql.connection.commit()
        cursor.close()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('comments'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT c.commentText, u.username FROM comments c JOIN users u ON c.userID = u.id ORDER BY c.commentDate DESC")
    comments = cursor.fetchall()
    cursor.close()
    return render_template('comments.html', comments=comments)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port, debug=True, use_reloader=False)