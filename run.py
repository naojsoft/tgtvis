#!/usr/bin/env python

import sys
import os

from app import create_app


def main(options, args):

    app = create_app(options.appdir, options.config)
    app.run(host=options.host, port=int(options.port))


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
    optprs.add_option("--appdir", dest="appdir", default="/home/takeshi/target",
                      metavar="APPDIR",
                      help="application directory.")
    optprs.add_option("--host", dest="host", default="133.40.166.37",
                      metavar="HOST",
                      help="host")
    optprs.add_option("--port", dest="port", default=5001,
                      metavar="PORT",
                      help="port")


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

