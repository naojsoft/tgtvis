# -*- coding: utf-8 -*-

import os

import tomli
from pathlib import Path

toml = tomli.loads(Path(os.environ['CONFHOME'], 'web', 'tgtvis.toml').read_text(encoding="utf-8"))


class Config(object):

    @staticmethod
    def init_app(app):
        pass

def DevelopmentConfig():
    config_obj = Config()

    for key_, value in toml['common'].items():
        setattr(config_obj, key_, value)

    for key_, value in toml['development'].items():
        setattr(config_obj, key_, value)

    return config_obj

def TestingConfig():
    config_obj = Config()

    for key_, value in toml['common'].items():
        setattr(config_obj, key_, value)

    for key_, value in toml['testing'].items():
        setattr(config_obj, key_, value)

    return config_obj

def ProductionConfig():
    config_obj = Config()

    for key_, value in toml['common'].items():
        setattr(config_obj, key_, value)

    for key_, value in toml['production'].items():
        setattr(config_obj, key_, value)

    return config_obj

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    }
