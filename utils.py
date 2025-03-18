from flask import session
from validators import url as validate_url

def save_history(mysql, user_id, url, outcome):
    """Save prediction history to the database."""
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO history(historyURL, historyLabel, userID) VALUES(%s, %s, %s)", (url, outcome, user_id))
    mysql.connection.commit()
    cursor.close()

def is_valid_url(url):
    """Validate the given URL."""
    return validate_url(url)
