from types import SimpleNamespace
import logging

from .app import create_app

config = "development"
#config = "production"

options = SimpleNamespace()
options.logfile = '/var/www/log/target.log'
options.logstderr = False
options.loglevel = logging.DEBUG
options.loglimit = 200*1024*1024

app = create_app(options, config)
