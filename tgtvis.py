#!/usr/bin/env python

import logging
import os
import sys
from argparse import ArgumentParser
from ginga.misc import log

# TODO: is there a way to import the app module that can work for both
# a standalone application and as a module in the Flask
# DispatcherMiddleware?
try:
    from app import create_app
except ModuleNotFoundError as e:
    from .app import create_app

def main(options, args):

    logger = log.get_logger('tgtvis', level=options.loglevel,
                            options=options, log_file=options.logfile, log_stderr=options.logstderr)

    logger.debug('starting tgtvis...')

    target = create_app(options.config, logger)

    target.run(host=options.host, port=options.port)

if __name__ == '__main__':
    # Running as a Flask standalone web server application

    # Parse command line options with argparse module
    argprs = ArgumentParser(description="target visibility")

    argprs.add_argument("--debug", dest="debug", default=False, action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    argprs.add_argument("--config", dest="config", default="development",
                        metavar="CONFIG",
                        help="configuration. [development|testing|]")
    argprs.add_argument("--host", dest="host", default="0.0.0.0",
                        metavar="HOST",
                        help="host")
    argprs.add_argument("--port", dest="port", default=5000,
                        metavar="PORT",
                        help="port")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print("%s profile:" % sys.argv[0])
        profile.run('main(options, args)')


    else:
        main(options, args)

else:
    # Running as a Flask WSGI web server

    argprs = ArgumentParser(description="target visibility")
    log.addlogopts(argprs)
    (options, args) = argprs.parse_known_args([])

    loghome = os.environ.get('LOGHOME', '/tmp')
    options.logfile = os.path.join(loghome, 'tgtvis.log')
    options.loglevel = logging.DEBUG

    # TODO: Can we set config_name to 'production'?
    config_name = os.environ.get('TGTVIS_CONFIG_NAME', 'development')

    logger = log.get_logger('tgtvis', level=options.loglevel, options=options, log_file=options.logfile)

    tgtvis_app = create_app(config_name, logger)

# END
