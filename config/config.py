import os
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY',
                                'Subaru-target')

    APP_STATIC = os.path.join(basedir, 'app', 'static')
    APP_IMAGE = os.path.join(basedir, 'app', 'static', 'image')
    APP_OPE = os.path.join(basedir, 'app', 'static', 'ope')
    APP_UPLOAD = '/tmp'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    

class TestingConfig(Config):
    TESTING = True

class ProductionConfig(Config):
    DEBUG = True
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
    }
