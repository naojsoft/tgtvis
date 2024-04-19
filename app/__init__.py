import os

import logging, logging.handlers

from flask import Flask
from flask_bootstrap import Bootstrap5 as Bootstrap

from ginga.misc import log

# TODO: is there a way to import the config module that can work for
# both a standalone application and as a module in the Flask
# DispatcherMiddleware?
try:
    from config import config
except ModuleNotFoundError as e:
    from ..config import config

bootstrap = Bootstrap()


def create_app(config_name, logger):

    """Create an application instance."""
    app = Flask(__name__)

    # import configuration
    config_obj = config[config_name]()

    app.config.from_object(config_obj)
    #config[config_name].init_app(app)

    app.logger = logger

    # initialize extensions
    bootstrap.init_app(app)

    # import blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
