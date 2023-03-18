import os

import re
import datetime


from bokeh.layouts import layout, row, column

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from astropy.coordinates import SkyCoord
import astropy.units as u

from qplan.common import moon
from qplan.util.site import site_subaru as subaru
from qplan.entity import StaticTarget
from ginga.misc import Bunch
#from ginga.misc.log import get_logger

from .target_plot import TargetPlot
from .laser_plot import LaserPlot

from .ope import get_vars_ope, get_coords


# ra/dec 123456.789
ra_pattern1 = "^(2[0-3]|[0-1][0-9])[0-5][0-9][0-5][0-9](\.\d+)?$"
ra_prog1 = re.compile(ra_pattern1)
dec_pattern1 = "^[+|-]?[0-8][0-9][0-5][0-9][0-5][0-9](\.\d+)?$"
dec_prog1 = re.compile(dec_pattern1)

# ra/dec hh:mm:ss.sss dd:mm:ss.ss
ra_pattern2 = "^(2[0-3]|[0-1][0-9]):[0-5][0-9]:[0-5][0-9](\.\d+)?$"
ra_prog2 = re.compile(ra_pattern2)
dec_pattern2 = "^[+|-]?[0-8][0-9]:[0-5][0-9]:[0-5][0-9](\.\d+)?$"
dec_prog2 = re.compile(dec_pattern2)


class TargetError(Exception):
    pass


def fix_time(year, month, day, hour, min, sec, logger):

    aday = 24 # hours

    dif = hour - aday
    if dif >= 0:
        logger.debug(f"hour {hour} >= 24")
        t = datetime.datetime(year, month, day, dif, min, sec)
        t += datetime.timedelta(days=1) # next day
    else:
        t = datetime.datetime(year, month, day, hour, min, sec)

    logger.debug(f"fixed time. {t}")
    return t

def get_laser_info(data, logger):

    logger.debug('get laser info...')

    targets = []

    laser_info = {}

    obs_date = data[0]
    data.remove(obs_date)
    obs_date = obs_date.decode('utf-8').strip()
    year, month, day = (int(ob) for ob in obs_date.split('-'))

    for d in data:
        logger.debug(f'data={d}')
        d = d.decode("utf-8").strip().split()
        logger.debug(f'd strip,split={d}')
        if not d:
            continue
        name = d[0]
        c = SkyCoord(ra=float(d[1])*u.degree, dec=float(d[2])*u.degree)
        ra = c.ra.to_string(unit=u.hourangle, precision=3, sep=':', pad=True)
        dec = c.dec.to_string(sep=':', precision=2, alwayssign=True, pad=True)
        equinox = 2000.0
        #targets.append(Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox))
        #t = Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox)
        #print('targets.....', targets)

        safe_time = []
        for t in d[3:]:
            t = t.split('-')
            st = t[0] # start time
            et = t[1] # end time
            # hr, min, sec
            sh, sm, ss = (int(s) for s in st.split(':'))
            eh, em, es = (int(e) for e in et.split(':'))
            start_time = fix_time(year, month, day, sh, sm, ss, logger)
            end_time = fix_time(year, month, day, eh, em, es, logger)
            #print 'name, st et ....', name, start_time, end_time
            #safe_time = laser_info.get((name, ra, dec))
            #if not safe_time:
            #    laser_info.update({(name, ra, dec): [(start_time, end_time)]})
            #else:
            safe_time.append((start_time, end_time))
        targets.append(Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox, safe_time=safe_time))

    logger.debug(f'obs_date={obs_date}')
    logger.debug(f'targets={targets}')
    #logger.debug('laser info. {}'.format(laser_info))

    return (obs_date, targets)

def validate_ra(ra):

    err_msg = None

    if ra_prog1.match(ra):
        ra = f"{ra[:2]}:{ra[2:4]}:{ra[4:]}"
    elif ra_prog2.match(ra):
        pass
    else:
        err_msg = f"Ra format does't match.  Ra={ra}, Format: hh:mm:ss.s* or hhmmss.s*"

    return (ra, err_msg)

def validate_dec(dec):

    err_msg = None

    if dec_prog1.match(dec):
        sign = dec.find('-') and dec.find("+")
        dec = f"{dec[:3+sign]}:{dec[3+sign:5+sign]}:{dec[5+sign:]}"
    elif dec_prog2.match(dec):
        pass
    else:
        err_msg = f"Dec format does't match.  Dec={dec}, Format: dd:mm:ss.s* or ddmmss.s*"

    return (dec, err_msg)

def validate_name(name):

    err_msg = None

    if not name:
        name = ''
        err_msg = "No name"
    return (name, err_msg)

def ra_format(coords):

    return "{c[0]:02d}:{c[1]:02d}:{c[2]:06.3f}".format(c=coords)

def dec_format(coords):

    return "{c[0]:+03d}:{c[1]:02d}:{c[2]:05.2f}".format(c=coords)

def equinox_format(equinox):

    return float("{:.1f}".format(equinox))

def ope(opes, include_dir, logger):

    targets = []

    for ope in opes:
        try:
            with open(ope, "r") as in_f:
                buf = in_f.read()
        except Exception as e:
            logger.error(f'Error: opening an ope file. {e}')
        else:
            d = get_vars_ope(buf, [include_dir,])

            for name, line in d.items():
                coords = get_coords(line)
                logger.debug(f'ope target name={name}, coords={coords}')
                if coords is not None:
                    ra = ra_format(coords[0])
                    dec = dec_format(coords[1])
                    equinox = equinox_format(coords[2])
                    res = _validate_target(name, ra, dec, equinox, logger)
                    targets.append(res)
        in_f.close()
    logger.debug(f'ope targets={targets}')
    return targets

def _validate_target(name, ra, dec, equinox, logger):

    logger.debug(f'validate name={name}, ra={ra}, dec={dec}, equinox={equinox}')

    ra, ra_valid = validate_ra(ra)
    dec, dec_valid = validate_dec(dec)
    name, name_valid = validate_name(name)
    equinox = float(equinox)

    errs = [err for err in [ra_valid, dec_valid, name_valid] if err]
    errs = ', '.join(errs)

    return  Bunch.Bunch(name=name, ra=ra, dec=dec, equinox=equinox, err=errs)

def text_dict(radec, equinox, logger):

    targets = []
    target_list = radec.split("\r\n")

    logger.debug(f'text target_list={target_list}')

    for t in target_list:
        t = t.strip().split()
        logger.debug(f'target={t}')
        if not t:
            continue
        try:
            name = t[0]
        except Exception as e:
            name = 'No Name'
        try:
            ra = t[1]
        except Exception as e:
            ra = 'None'
        try:
            dec = t[2]
        except Exception as e:
            dec = 'None'
        res = _validate_target(name, ra, dec, equinox, logger)

        targets.append(res)

    logger.debug(f'text targets={targets}')
    return targets


def site(mysite):

    site_dict = {"subaru": subaru}
    return site_dict.get(mysite)


def format_error(targets, logger):

    errors = []

    for t in targets:
        if t.err:
            logger.debug(f'error. {t.err}')
            errors.append(t.err)

    return errors

def populate_interactive_target(target_list, mysite, mydate, logger):

    logger.debug('poplulate interactive target...')

    targets = []

    title = f"Visibility for the night of {mydate}"
    mydate_time = f'{mydate} 17:00:00'
    mysite.set_date(mysite.get_date(mydate_time))
    timezone = mysite.tz_local

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'
    plot_height = 930
    plot_width = 1200
    # note: output_backend: webgl is to optimize drawings, but can't draw dotted line
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "plot_height": plot_height, "plot_width": plot_width,} #  "output_backend": "webgl"}

    plot = TargetPlot(logger, **fig_args)

    for t in target_list:
        if not t.err:
            targets.append(StaticTarget(name=t.name, ra=t.ra, dec=t.dec, equinox=t.equinox))

    target_data = []
    for tgt in targets:
        info_list = mysite.get_target_info(tgt)
        target_data.append(Bunch.Bunch(history=info_list, target=tgt))

    try:
        plot.plot_target(mysite, target_data)
    except Exception as e:
        logger.error(f'error: ploting targets. {e}')
        raise TargetError(f"Error: ploting targets. {e}")

    else:
        return plot.fig


def populate_interactive_laser(target, collision_time, mysite, mydate, logger):
    logger.debug('populate_interactive_laser...')

    mydate = f'{mydate} 17:00:00'
    mysite.set_date(mysite.get_date(mydate))

    title = f"Laser collision for the night of {mydate}"
    mydate_time = f'{mydate} 17:00:00'
    #mysite.set_date(mysite.get_date(mydate_time))

    logger.debug(f'my date={mydate}')
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'
    plot_height = 810
    plot_width = 770
    sizing_mode = 'scale_both' #'stretch_both'
    # note: output_backend: webgl is to optimize drawings, but can't draw dotted line
    #fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "sizing_mode": sizing_mode} #  "output_backend": "webgl"}

    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "plot_height": plot_height, "plot_width": plot_width, "sizing_mode": sizing_mode} #  "output_backend": "webgl"}

    plot = LaserPlot(logger, **fig_args)

    tgt = StaticTarget(name=target.name, ra=target.ra, dec=target.dec, equinox=target.equinox)

    info_list = mysite.get_target_info(tgt)
    tgt_data = [Bunch.Bunch(history=info_list, target=tgt)]

    try:
        logger.debug('calling plot_laser...')
        plot.plot_laser(mysite, tgt_data, collision_time)
    except Exception as e:
        #print(e)
        raise TargetError(f"error: {e}")

    else:
        logger.debug('returning plot fig...')
        return row(plot.fig, column(plot.toggles))
