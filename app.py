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
from datetime import datetime  

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
CORS(app)
app.config.from_object(AppConfig)

log = create_logger(app)
mysql = MySQL(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  

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
    """Render the login page."""
    registered = request.args.get('registered')  # Check if redirected from registration
    if registered:
        flash('Registration successful! You can now log in.', 'login_success')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """Handle login form submission for both users and admin."""
    email = request.form.get('email')
    password = request.form.get('password')

    if current_user.is_authenticated:
        return redirect('/history')

    cursor = None  # Initialize cursor to None
    try:
        # Check if the login is for admin
        if email == "admin@fakenews.com" and password == "admin123":
            session.clear()  # Clear any existing session
            session['admin_logged_in'] = True
            flash('Admin login successful!', 'login_success')
            return redirect(url_for('admin_dashboard'))

        # Check if the login is for a regular user
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            if account['banned']:
                flash('Your account has been banned. Please contact support.', 'login_error')
                return redirect(url_for('login'))
            password_db = account['password_hash']
            if check_password_hash(password_db, password):
                user = User(id=account['id'], username=account['username'], email=account['email'])
                login_user(user)
                session['logged_in'] = True
                session['username'] = account['username']
                session['id'] = account['id']
                flash('You have successfully logged in!', 'login_success')
                return redirect(url_for('main'))
            else:
                flash('Incorrect password. Please try again.', 'login_error')
        else:
            flash('No account found with this email address.', 'login_error')
    except Exception as e:
        flash(f'Error: {e}', 'login_error')
    finally:
        if cursor:  # Close the cursor only if it was initialized
            cursor.close()

    return render_template('login.html', email=email)

@app.route('/register', methods=['POST', 'GET'])
def register():
    """Handle registration form submission."""
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')

    if request.method == 'POST':
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE email LIKE %s', (email,))
            account = cursor.fetchone()

            if account:
                flash('An account with this email already exists.', 'register_error')
            elif len(password) < 8:
                flash('Password must be at least 8 characters long.', 'register_error')
            elif not username or not password or not email:
                flash('All fields are required.', 'register_error')
            else:
                password_hash = generate_password_hash(password)
                cursor.execute("INSERT INTO users(email, username, password_hash) VALUES(%s, %s, %s)", (email, username, password_hash))
                mysql.connection.commit()
                flash('Registration successful! You can now log in.', 'register_success')
                return redirect(url_for('login', registered=True))  # Pass a query parameter
        except Exception as e:
            flash(f'Error: {e}', 'register_error')
        finally:
            cursor.close()

    return render_template('register.html', email=email, username=username)

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login to gain access of this page', 'access_error')
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

    if is_valid_url(url): 
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
                            prediction_text=outcome, 
                            url_input=url,
                            news=news,
                            prediction_date=prediction_date 
                        )
                    else:
                        flash('Invalid URL! Please try again', 'predict_error')
                        return redirect(url_for('main'))
                else:
                    language_error = "We currently do not support this language"
                    return render_template('predict.html', language_error=language_error, url_input=url)
            else:
                flash('Invalid news article! Please try again', 'predict_error')
                return redirect(url_for('main'))
        except newspaper.article.ArticleException:
            flash('We currently do not support this website! Please try again', 'predict_error')
            return redirect(url_for('main'))
    else:
        flash('Please enter a valid news site URL', 'predict_error')
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
        flash('Comment added successfully!', 'comment_success')
        return redirect(url_for('comments'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT c.commentText, u.username FROM comments c JOIN users u ON c.userID = u.id ORDER BY c.commentDate DESC")
    comments = cursor.fetchall()
    cursor.close()
    return render_template('comments.html', comments=comments)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check admin credentials
        if email == "admin@fakenews.com" and password == "admin123":
            session.clear()  # Clear any existing session
            session['admin_logged_in'] = True
            flash('Admin login successful!', 'admin_success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials. Please try again.', 'admin_error')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard."""
    if not session.get('admin_logged_in'):
        flash('Please log in as admin to access this page.', 'admin_error')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM users WHERE banned = 0')  # Fetch active users
    users = cursor.fetchall()
    cursor.execute('SELECT * FROM users WHERE banned = 1')  # Fetch banned users
    banned_users = cursor.fetchall()
    cursor.execute('SELECT * FROM comments')
    comments = cursor.fetchall()
    cursor.close()

    return render_template('admin_dashboard.html', users=users, banned_users=banned_users, comments=comments)

@app.route('/admin/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    """Remove a user."""
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'admin_error')
        return redirect(url_for('login'))

    try:
        cursor = mysql.connection.cursor()
        # Delete related rows in the history and comments tables
        cursor.execute('DELETE FROM history WHERE userID = %s', (user_id,))
        cursor.execute('DELETE FROM comments WHERE userID = %s', (user_id,))
        # Delete the user
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        mysql.connection.commit()
        flash('User removed successfully.', 'admin_success')
    except Exception as e:
        flash(f'Error: {e}', 'admin_error')
    finally:
        cursor.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_comment/<int:comment_id>', methods=['POST'])
def remove_comment(comment_id):
    """Remove a comment."""
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'admin_error')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM comments WHERE id = %s', (comment_id,))
    mysql.connection.commit()
    cursor.close()

    flash('Comment removed successfully.', 'admin_success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
def ban_user(user_id):
    """Ban a user."""
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'admin_error')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET banned = 1 WHERE id = %s', (user_id,))
    mysql.connection.commit()
    cursor.close()

    flash('User banned successfully.', 'admin_success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unban_user/<int:user_id>', methods=['POST'])
def unban_user(user_id):
    """Unban a user."""
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'admin_error')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET banned = 0 WHERE id = %s', (user_id,))
    mysql.connection.commit()
    cursor.close()

    flash('User unbanned successfully.', 'admin_success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    session.clear()  # Clear all session data
    flash('You have been logged out as admin.', 'admin_success')
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port, debug=True, use_reloader=False)