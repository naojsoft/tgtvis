import os

import logging, logging.handlers

from flask import Flask
#from flask.ext.bootstrap import Bootstrap
from flask_bootstrap import Bootstrap
#from flask.ext.sqlalchemy import SQLAlchemy
#from flask.ext.login import LoginManager

from config.config import config

LOG_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d | %(message)s'

bootstrap = Bootstrap()
#db = SQLAlchemy()
#lm = LoginManager()
#lm.login_view = 'main.login'


def create_app(options, config_name):
    """Create an application instance."""
    
    app = Flask(__name__)

    # import configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    #cfg = os.path.join(app_dir, 'config', config_name + '.py')
    #app.config.from_pyfile(cfg)

    # initialize extensions
    bootstrap.init_app(app)
    #db.init_app(app)
    #lm.init_app(app)

    # import blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    #logger = app.logger

    #logger.
    app.logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(LOG_FORMAT)

    # Add output to stderr, if requested
    if options.logfile:
        fileHdlr  = logging.handlers.RotatingFileHandler(
                        options.logfile,
                        maxBytes=options.loglimit,
                        backupCount=4)
        fileHdlr.setFormatter(fmt)
        fileHdlr.setLevel(options.loglevel)
        app.logger.addHandler(fileHdlr)

    # Add output to stderr, if requested
    if options.logstderr or (not options.logfile):
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setFormatter(fmt)
        stderrHdlr.setLevel(options.loglevel)
        app.logger.addHandler(stderrHdlr)
    
    return app
