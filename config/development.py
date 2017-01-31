import os

DEBUG = True
SECRET_KEY = 'WQCS!'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
    os.path.dirname(__file__), '../wqcs-dev.sqlite3')

APP_STATIC = os.path.join(os.path.dirname(__file__), '../app', 'static')
APP_IMAGE = os.path.join(os.path.dirname(__file__), '../app', 'static', 'image')
APP_OPE = os.path.join(os.path.dirname(__file__), '../app', 'static', 'ope')
APP_UPLOAD = '/tmp'



HOST = "133.40.166.37"
PORT = 5000

QDB_PORT = 9800
QDB_HOST = 'localhost'


