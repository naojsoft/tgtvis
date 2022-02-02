import os

import collections
from datetime import datetime
import operator

from flask import render_template, redirect, url_for, request, current_app, session, send_from_directory
#from flask.ext.login import login_required, login_user, logout_user
from . import main
#from .forms import TargetForm
from flask import make_response
from flask import current_app as app

#from werkzeug import secure_filename
from werkzeug.utils import secure_filename

from functools import wraps, update_wrapper
from . import helper_func as helper

import tempfile

from bokeh.embed import components
#from bokeh.util.string import encode_utf8
from bokeh.resources import INLINE

from bokeh.resources import CDN
from bokeh.embed import file_html

from ginga.misc import Bunch

def delete_files(files):

    for f in files:
        os.remove(f)

@main.route('/')
def index():

    app.logger.debug('target index...')
    return render_template('menu.html')

@main.route('/help')
def help():

    return render_template('help.html')

@main.route('/opeError/<error>')

def opeError(error):

    return render_template('opeError.html', error=error)

@main.route('/Laser', methods=['POST'])
def Laser():

    errors = []

    if  not request.method in ['POST']:
        return redirect(url_for('main.index'))

    file = request.files.get("laser")
    #mydate = request.form.get("date")
    mysite = helper.site(request.form.get('site'))

    app.logger.debug('laser file. {}'.format(file))
    
    try:
        data = file.readlines()
        app.logger.debug('file data={}'.format(data))
        #mydate, targets, laser_safe_time = helper.get_laser_info(data, app.logger)
        mydate, targets = helper.get_laser_info(data, app.logger)
    except Exception as e:
        app.logger.error('Error: reading laser file. {}'.format(e))
        err = 'Reading laser file. {}'.format(e)
        errors.append(err)

    plots = []

    # Grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    for target in sorted(targets, key = lambda i: (i.name, i.ra, i.dec)):
        
        safe_time = target.safe_time
        app.logger.debug('Name: {}'.format(target.name))
        app.logger.debug('Laser safe time. {}'.format(safe_time))
        
        try:
            fig = helper.populate_interactive_laser(target, safe_time, mysite, mydate, app.logger)
        except Exception as e:
            app.logger.error('Error: failed to populate laser plot. {}'.format(e))
            err = 'Plotting laser collision for {}. {}'.format(target.name, e)
            errors.append(err)
            return render_template('laser_visibility.html', js_resources=js_resources, css_resources=css_resources, targets=plots, errors=errors)
        else:
            script, div = components(fig)
            plots.append(Bunch.Bunch(plot_script=script, plot_div=div, name=target.name, ra=target.ra, dec=target.dec))
    
            # render template
    html = render_template('laser_visibility.html', js_resources=js_resources, css_resources=css_resources, targets=plots)

    #return html
    html = html.encode('utf-8')
    return html
    #return encode_utf8(html)

@main.route('/Ope', methods=['POST'])
def Ope():

    if  not request.method in ['POST']:
        return redirect(url_for('main.index'))
    
    files = request.files.getlist("ope[]")
    app.logger.debug('files={}'.format(files))
    
    opes = []
    del_files = []
    upload_dir = current_app.config['APP_UPLOAD']

    for f in files:
        filename = secure_filename(f.filename)
        
        ope = os.path.join(upload_dir, filename) 
        f.save(ope)
        del_files.append(ope)
        if filename.lower().endswith(".ope"):
            opes.append(ope)

    app.logger.debug('opes={}'.format(opes))        
 
    try:  
        targets = helper.ope(opes, upload_dir, app.logger)
        #errors = helper.format_error(targets, app.logger)
    except Exception as e:
        app.logger.error('Error: invalid ope file. {}'.format(e))
        err_msg = "Plot Error: {}".format(e)
        #errors.append(err_msg)
        delete_files(del_files)
        return render_template('target_visibility.html', errors=[err_msg])

    #filepath = tempfile.NamedTemporaryFile().name
    #filepath = os.path.join(current_app.config['APP_UPLOAD'], filename)

    mysite = helper.site(request.form.get('site'))
    mydate = request.form.get('date')

    #app.logger.debug('targets={}'.format(targets))
    #app.logger.debug('filepath={}'.format(filepath))
    app.logger.debug('mydate={}'.format(mydate))

    delete_files(del_files)
    
    try:
        #fig = helper.populate_target2(targets, mysite, mydate, filepath, app.logger)
        fig = helper.populate_interactive_target(target_list=targets, mysite=mysite, mydate=mydate, logger=app.logger)
    except Exception as e:
        app.logger.error('Error: failed to populate ope plot. {}'.format(e))
        err_msg = "Plot Error: {}".format(e)
        #errors.append(err_msg)
        return render_template('target_visibility.html', errors=[err_msg])
    else:

        # Grab the static resources
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()

        # render template
        script, div = components(fig)
        html = render_template(
            'target_visibility.html',
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
            errors=None)

        html = html.encode('utf-8')
        return html
        #return encode_utf8(html)

@main.route('/Text', methods=['POST'])
def Text():

    if  not request.method in ['POST']:
        return redirect(url_for('main.index'))
        #return render_template('menu.html')

    #print("Form action={}".format(request.form['action']))
    #print("Form={}".format(request.form))

    equinox = request.form.get('equinox')
    radec = request.form.get('radec')
    targets = helper.text_dict(radec=radec, equinox=equinox, logger=app.logger)
    app.logger.debug('Text targets. {}'.format(targets))
    errors = helper.format_error(targets, app.logger)

    mysite = helper.site(request.form.get('site'))
    mydate = request.form.get('date')

    try:
        fig = helper.populate_interactive_target(target_list=targets, mysite=mysite, mydate=mydate, logger=app.logger)
    except Exception as e:
        app.logger.error('Error: failed to populate text plot. {}'.format(e))
        err_msg = "Plot Error: {}".format(e)
        errors.append(err_msg)
        return render_template('target_visibility.html', errors=errors)
    else:    
        # Grab the static resources
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()

        # render template
        script, div = components(fig)

        #print('div={}'.format(div))
        
        html = render_template(
            'target_visibility.html',
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
            errors=errors)

        #return html
        html = html.encode('utf-8')
        return html
        #return encode_utf8(html)
