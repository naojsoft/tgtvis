#!/usr/bin/env python

import sys
import os

import logging

from app import create_app


def main(options, args):

    target = create_app(options, options.config)
    
    target.run(host=options.host, port=options.port)


if __name__ == '__main__':
   # Parse command line options with nifty new optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options]"
    optprs = OptionParser(usage=usage)

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    optprs.add_option("--config", dest="config", default="development",
                      metavar="CONFIG",
                      help="configuration. [development|testing|]")
    optprs.add_option("--host", dest="host", default="133.40.166.25",
                      metavar="HOST",
                      help="host")
    optprs.add_option("--port", dest="port", default=5055,
                      metavar="PORT",
                      help="port")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type="int", default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--loglimit", dest="loglimit", metavar="NUM",
                      type="int", default=200*1024*1024,
                      help="Set logging limit to NUM bytes before rollover")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
   
    (options, args) = optprs.parse_args(sys.argv[1:])

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

# END

