import os
import random

from flask import render_template, redirect, url_for, request, current_app, session, send_from_directory
#from flask.ext.login import login_required, login_user, logout_user
from . import main
#from .forms import TargetForm
from flask import make_response

from werkzeug import secure_filename

from functools import wraps, update_wrapper
from datetime import datetime
from app.main import helper_func as helper


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
        
    return update_wrapper(no_cache, view)


def delete_files(files):

    for f in files:
        os.remove(f)

@main.route('/')
def index():

    return render_template('menu.html')

@main.route('/ope')
def ope():

    return render_template('ope.html')

@main.route('/text')
def text():

    return render_template('text.html')

#@main.route('/single')
#@nocache
#def single():
#    return render_template('target.html')

@main.route('/help')
def help():

    return render_template('help.html')


@main.route('/opeError/<error>')

def opeError(error):

    return render_template('opeError.html', error=error)

@main.route('/visibility/<filename>/<errors>')
def visibility(filename, errors=None):

    return render_template('visibility.html', filename=filename, errors=errors)

@main.route('/target/<filename>')
def display(filename):
    return send_from_directory(current_app.config['APP_IMAGE'], filename, cache_timeout=0)

@main.route('/opeP', methods=['POST'])
def opeP():

    files = request.files.getlist("ope[]")
    opes = []
    del_files = []
    include_dir = current_app.config['APP_UPLOAD']

    for f in files:
        filename = secure_filename(f.filename)
        
        ope = os.path.join(include_dir, filename) 
        f.save(ope)
        del_files.append(ope)
        if filename.lower().endswith(".ope"):
            opes.append(ope)

    try:  
        targets = helper.ope(opes, include_dir)
        errors = helper.format_error(targets)
    except Exception as e:
        print 'OPE ERROR ', e 
        delete_files(del_files)   

        return render_template('opeError.html', error=e)

    num = random.randrange(0, 500)
    target_name = 'target{}.png'.format(num)
    image_path = os.path.join(current_app.config['APP_IMAGE'], target_name)

    try:
        mysite = helper.site(request.form)
        mydate = helper.date(request.form)
        helper.populate(targets, mysite, mydate, filename=image_path)
    except Exception as e:
        print "EEEEEEEEEEEEEEE", e
        target_name = None

    delete_files(del_files)

    return render_template('visibility.html', filename=target_name, errors=errors)


@main.route('/textP', methods=['POST'])
def textP():

    num = random.randrange(0, 100)
    filename = 'target{}.png'.format(num)
    image_path = os.path.join(current_app.config['APP_IMAGE'], filename)

    equinox = helper.equinox(request.form)
    targets = helper.text_dict(target_form=request.form, equinox=equinox)
    errors = helper.format_error(targets)

    try:
        mysite = helper.site(request.form)
        mydate = helper.date(request.form)
        helper.populate(targets, mysite, mydate, filename=image_path)
    except Exception as e:
        print e
        filename = None

    return render_template('visibility.html', filename=filename, errors=errors)


# @main.route('/target', methods=['POST'])
# #@nocache
# def target():

#     print "##########", len(request.form), request
#     if len(request.form) == 5:
#         print 'EMPTY'
#         return render_template('target.html')

 
#     targets = []
#     target_dict = {}
#     ra = 'ra'
#     dec = 'dec'
#     name = 'name'
#     print request.form
#     print request
#     #print request.form['target']
 
#     #image_dir = current_app.config['APP_IMAGE']

#     num = random.randrange(0, 100)
#     filename = 'target{}.png'.format(num)

#     #print url_for('static', filename=filename)
#     #print  os.path.dirname(__file__)

#     #path = os.path.join('/home/takeshi/target/app/static/target_AAA.png')
#     #print 'PATH ', path
#     #try:
#     #    os.remove(path)
#     #except Exception:
#     #    pass

#     image_path = os.path.join(current_app.config['APP_IMAGE'], filename)
#     #print "IMAGE PATH ", image_path 



    
#     targets = helper.target_dict(request.form)
#     print targets
#     mysite = helper.site(request.form)
#     mydate = helper.date(request.form)
#     helper.populate(targets, mysite, mydate, filename=image_path)

#     return render_template('visibility.html', filename=filename, errors=[])
#     #return redirect(url_for('main.visibility', filename=filename))

