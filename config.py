import secrets

class Config:
    SECRET_KEY = secrets.token_urlsafe(32)
    MYSQL_HOST = '127.0.0.1'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'root'
    MYSQL_DB = 'fakenewsapp_db'
    MYSQL_CURSORCLASS = 'DictCursor'
    NEWS_API_KEY = '8b72ac79fc194ae28d89879ac09e53a8'
    MYSQL_PORT = 3306
