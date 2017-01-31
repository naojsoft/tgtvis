import os

import re

from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from qplan.common import moon
from qplan.util.site import site_subaru as subaru
from qplan.entity import StaticTarget
from ginga.misc import Bunch
from ginga.misc.log import get_logger

import airmass2
from ope import get_vars_ope, get_coords


logger = get_logger('target', log_stderr=True)

# ra/dec 123456.789
ra_pattern1 = "^(2[0-3]|[0-1][0-9])[0-5][0-9][0-5][0-9](\.\d{1,3})?$"
ra_prog1 = re.compile(ra_pattern1)
dec_pattern1 = "^[+|-]?[0-8][0-9][0-5][0-9][0-5][0-9](\.\d{1,3})?$"
dec_prog1 = re.compile(dec_pattern1)

# ra/dec hh:mm:ss.sss dd:mm:ss.ss    
ra_pattern2 = "^(2[0-3]|[0-1][0-9]):[0-5][0-9]:[0-5][0-9](\.\d{1,3})?$"
ra_prog2 = re.compile(ra_pattern2)
dec_pattern2 = "^[+|-]?[0-8][0-9]:[0-5][0-9]:[0-5][0-9](\.\d{1,3})?$"
dec_prog2 = re.compile(dec_pattern2)


class TargetError(Exception):
    pass


# RA = 'ra'
# DEC = 'dec'
# NAME = 'name'
# EQUINOX = 'equinox'
# VALID = 'valid'

# def target_dict(target_form):

#     target = {}
#     ignore = ['ra0', 'dec0', 'name0', 'site', 'date', 'del0']
#     for k, v in target_form.items():
#         if k in ignore:
#             continue
#         _target_dictionary(k, v, target)

#     print "TARGET DICT: ", target

#     return target

# def _target_dictionary(k, v, target):

#     print k, v, target

#     if k.startswith(NAME):
#         num_key = k[len(NAME):]
#         name_key = NAME  
#     elif k.startswith(RA):
#         num_key = k[len(RA):]
#         name_key = RA
#     else:
#         num_key = k[len(DEC):]
#         name_key = DEC

#     try:
#         val = target[num_key]
#         print 'VAL: ', val

#         if not name_key in val.keys():
#             val.update({name_key:v})
#             print 'UPDATE: ', num_key, v, val
#     except:
#         target[num_key] = {name_key:v}
#         target[num_key].update({VALID: True}) # always validated true
#         print 'NEW TARGET: ', num_key, v,  target


def validate_ra(target):

    valid = True

    try:
        ra = target[0]
    except Exception as e:
        ra = None
        valid = False
    else:
        if ra_prog1.match(ra):
            ra = "{}:{}:{}".format(ra[:2], ra[2:4], ra[4:])
        elif ra_prog2.match(ra):
            pass
        else:
            valid = False
 
    print 'RA VALID ', ra, valid
    return (ra, valid)

def validate_dec(target):

    valid = True

    try:
        dec = target[1]
    except Exception as e:
        dec = None
        valid = False
    else:
        if dec_prog1.match(dec):
            sign = dec.find('-') and dec.find("+")
            dec = "{}:{}:{}".format(dec[:3+sign], dec[3+sign:5+sign], dec[5+sign:])
        elif dec_prog2.match(dec):
            pass
        else:
            valid = False

    return (dec, valid)

def validate_name(target):

    valid = True

    name = ' '.join(target[2:])

    if not name:
        name = 'No Name'
        valid = False



    return (name, valid)

def ra_format(coords):

    return "{c[0]:02d}{c[1]:02d}{c[2]:06.3f}".format(c=coords)

def dec_format(coords):

    return "{c[0]:+03d}{c[1]:02d}{c[2]:05.2f}".format(c=coords)

def equinox_format(equinox):

    return "{:.1f}".format(equinox)

def ope(opes, include_dir):

    targets = []

    for ope in opes:
        try:
            with open(ope, "r") as in_f:
                buf = in_f.read()
        except Exception as e:
            print e

        else:
            d = get_vars_ope(buf, [include_dir,])

            for name, line in d.items():
                coords = get_coords(line)
                if coords is not None:
                    ra = ra_format(coords[0])
                    dec = dec_format(coords[1])
                    equinox = equinox_format(coords[2])
                    targets.append(Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox, valid=True))
        in_f.close() 
    return targets

def _target_validate(target, equinox):

    t = target.split()

    print 'TARGET VALIDATE ', t

    ra, ra_valid = validate_ra(target=t)
    dec, dec_valid = validate_dec(target=t)
    name, name_valid = validate_name(target=t)

    valid  = False if False in [ra_valid, dec_valid, name_valid] else True

    return  Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox, valid=valid)

def text_dict(target_form, equinox):

    targets = []
    target_list = target_form['radec'].split("\r\n")

    for t in target_list:
        if not t.strip():
            continue
        targets.append(_target_validate(t, equinox))

    return targets


def site(target_form):

    site_dict = {"Mauna Kea": subaru}
    mysite = [v for k, v in target_form.items() if k == 'site'][0]
    return site_dict[mysite]

def date(target_form):

    return [v for k, v in target_form.items() if k == 'date'][0]

def equinox(target_form):

    return float([v for k, v in target_form.items() if k == 'equinox'][0])

def format_error(targets):

    errors = []

    for t in targets:
        if not t.valid: 
            errors.append(Bunch.Bunch(name=t.name, ra=t.ra, dec=t.dec, equinox=t.equinox))

    return errors

def populate(target_list, mysite, mydate, filename):

    targets = []

    mydate = '{} 17:00:00'.format(mydate)
    mysite.set_date(mysite.get_date(mydate))

    for t in target_list:
        if t.valid: 
            targets.append(StaticTarget(name=t.name, ra=t.ra, dec=t.dec, equinox=t.equinox))

    target_data = []
    for tgt in targets:
        info_list = mysite.get_target_info(tgt)
        target_data.append(Bunch.Bunch(history=info_list, target=tgt))

    amp = airmass2.AirMassPlot2(1200, 740, logger=logger)

    try:
        amp.plot_altitude(mysite, target_data, mysite.timezone)
    except Exception as e:
        print e
        raise TargetError("error: {}".format(e))    

    else:
        buf = BytesIO()
        canvas = FigureCanvas(amp.fig)
        canvas.print_figure(buf, format='png')
        fo = open(filename, 'wb')
        fo.write(bytes(buf.getvalue()))
        fo.close()

    return 
