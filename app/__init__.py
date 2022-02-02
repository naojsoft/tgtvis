import os

import logging, logging.handlers

from flask import Flask
from flask_bootstrap import Bootstrap

from ginga.misc import log

# TODO: is there a way to import the config module that can work for
# both a standalone application and as a module in the Flask
# DispatcherMiddleware?
try:
    from config.config import config
except ModuleNotFoundError as e:
    from ..config.config import config

bootstrap = Bootstrap()

def create_app(options, config_name):

    """Create an application instance."""
    
    app = Flask(__name__)

    # import configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # initialize extensions
    bootstrap.init_app(app)

    # import blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Configure the logger.
    app.logger.setLevel(options.loglevel)
    fmt = logging.Formatter(log.LOG_FORMAT)

    # Add output to file, if requested
    if options.logfile:
        fileHdlr = logging.handlers.RotatingFileHandler(options.logfile,
                                                        maxBytes=options.logsize,
                                                        backupCount=options.logbackups)
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
