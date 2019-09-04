#!/usr/bin/env python3

# This file is used when we run the target visibility application in Apache mod_wsgi.
# Add a line like the following to the Apache configuration file:
#
#   WSGIScriptAlias /wsgi-scripts/target /usr/lib/wsgi-scripts/target/target.wsgi

import sys, os

sys.stderr.write("start of %s\n" % __file__)

sys.path.insert(0, '/gen2/share/Git/python')

sys.path.insert(0, os.path.dirname(__file__))

wsgi_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.stderr.write("wsgi_dir is %s \n" % wsgi_dir)
sys.path.insert(0, wsgi_dir)



sys.stderr.write("sys.path %s\n" % sys.path)
sys.stderr.write("sys.version %s\n" % sys.version)

from target import app as application
