import os
import re
import datetime
import csv
import pandas as pd

from bokeh.layouts import layout, row, column

from bokeh.models.layouts import Row, Column

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

from oscript.parse.ope import get_vars_ope, get_coords2
from g2base.astro import radec

# soss pattern. match a sequence with at least 6 consecutive digits; '+', '-', and decimal point are optional.
soss_pattern = r'(?<![+-])[+-]?\d{6,}(?:\.\d+)?'  #r'(?<![+-])[+-]?\b\d{6}\b(?:\.\d+)?'

# degree pattern  1-3 digits, decimal points
deg_pattern = r"[+-]?\d{1,3}(?:\.\d+)?"

# ra/dec 123456.789
ra_pattern1 = r"^(?:(?:[01][0-9]|2[0-3])[0-5][0-9][0-5][0-9](?:\.\d+)?|240000(?:\.0+)?)$"
ra_prog1 = re.compile(ra_pattern1)
dec_pattern1 = r"^[+-]?(?:[0-8][0-9][0-5][0-9][0-5][0-9](\.\d+)?|900000(\.0+)?)$"
dec_prog1 = re.compile(dec_pattern1)

# ra/dec hh:mm:ss.sss dd:mm:ss.ss
ra_pattern2 = r"^(?:([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.\d+)?|24:00:00(?:\.0+)?)$"
ra_prog2 = re.compile(ra_pattern2)
dec_pattern2 = r"^[+-]?(?:[0-8][0-9]:[0-5][0-9]:[0-5][0-9](?:\.\d+)?|90:00:00(?:\.0+)?)$"
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
        err_msg = f"Ra invalid value or format.  ra={ra}, format: hhmmss.s*"

    return (ra, err_msg)

def validate_dec(dec):

    err_msg = None

    if dec_prog1.match(dec):
        sign = dec.find('-') and dec.find("+")
        dec = f"{dec[:3+sign]}:{dec[3+sign:5+sign]}:{dec[5+sign:]}"
    elif dec_prog2.match(dec):
        pass
    else:
        err_msg = f"Dec invalid value or format.  dec={dec}, format: ddmmss.s*"

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

def csv_with_header(csv_file, logger):

    try:
        df = pd.read_csv(csv_file)
        cols = {}
        for col in df.columns:
            logger.debug(f'col=<{col}>, col strip lowercase =<{col.lower().strip()}>')
            cols[col] = col.lower().strip()
        logger.debug(f'cols={cols}')
        df = df.rename(columns=cols)
    except Exception as e:
        logger.error(f'error: loading csv into pandas. {e}')
        raise TargetError(f'{e}')
    logger.debug(f'df={df}')

    #for row in df.itertuples():
    #    logger.debug(f'row={row}')


    return df

def csv_without_header(csv_file, logger):

    try:
        df = pd.read_csv(csv_file, usecols=[0,1,2, 3], names=['name', 'ra', 'dec', 'equinox'], header=None)
    except Exception as e:
        logger.error(f'error: loading csv into pandas. {e}')
        raise TargetError(f'{e}')

    return df

def ra_float_to_string(val, logger):

    logger.debug(f'ra={val}')

    leading_zero = 10
    if val < 0.0:
        leading_zero = 11

    ra = f'{val:0{leading_zero}.3f}'
    logger.debug(f'ra to string={ra}')
    return ra

def dec_float_to_string(val, logger):

    logger.debug(f'dec={val}')

    leading_zero = 9
    if val < 0.0:
        leading_zero = 10

    dec = f'{val:0{leading_zero}.2f}'
    logger.debug(f'dec to string={dec}')
    return dec

def read_csv(csvs, header, radec_unit,  logger):
    targets = []

    for csv_file in csvs:
        logger.debug(f'csv file={csv_file}')
        if header is not None:
            df = csv_with_header(csv_file, logger)
        else:
            df = csv_without_header(csv_file, logger)

        for row in df.itertuples():
            logger.debug(f'row={row}')

            try:
                name = row.name.strip()
                logger.debug(f'ra={row.ra}, ra type={type(row.ra)}, dec={row.dec}, dec type={type(row.dec)}')
                if radec_unit.upper() == 'DEG':
                    hours, minutes, seconds = radec.degToHms(row.ra)
                    ra =  radec.raHmsToString(hours, minutes, seconds, format='%02d%02d%06.3f')
                    dec = radec.decDegToString(float(row.dec))
                    logger.debug(f'radec in Degree.  ra={ra}, dec={dec}')
                else: # radec_unit is HOUR
                    if isinstance(row.ra, float):
                        ra = ra_float_to_string(row.ra, logger)
                    else:
                        ra = row.ra.strip()
                    if isinstance(row.dec, float):
                        dec = dec_float_to_string(row.dec, logger)
                    else:
                        dec = row.dec.strip()

                logger.debug(f'name={name}, ra={ra}, dec={dec}, equinox={row.equinox}')
                res = _validate_target(name, ra, dec, row.equinox, logger)
                targets.append(res)
            except Exception as e:
                logger.error(f'Error: reading csv file(s). {e}')
                targets.append(Bunch.Bunch(name=name, ra=row.ra, dec=row.dec, coord=f'{ra} {dec}', equinox=row.equinox, err=e))

    logger.debug(f'targets={targets}')
    return targets

def ope(opes, include_dir, logger):

    targets = []

    try:
        for ope in opes:
            with open(ope, "r") as in_f:
                buf = in_f.read()
                d = get_vars_ope(buf, [include_dir,])
                target = d.varDict

                for name, line in target.items():
                    logger.debug(f'name={name}, line={line}, linetype={type(line)}')
                    coords = get_coords2(line)
                    logger.debug(f'ope target name={name}, coords={coords}, type={type(coords)}')
                    if coords is not None:
                        logger.debug(f'ra={coords.ra}, dec={coords.dec}, equinox={coords.equinox}')
                        res = _validate_target(name, coords.ra, coords.dec, coords.equinox, logger)
                        targets.append(res)
    except Exception as e:
        logger.error(f'Error: opening an ope file. {e}')
        raise TargetError(f'open/read ope file. ope={ope}, {e}')

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

    return  Bunch.Bunch(name=name, ra=ra, dec=dec, coord=f'{ra} {dec}', equinox=equinox, err=errs)


def validate_ra_dec_format(name, coord, equinox, logger, unit=''):
    name, name_error = validate_name(name)
    try:
        if unit.lower() == "degree":
            logger.debug(f'coord deg={coord}')
            c = SkyCoord(coord, unit=(u.deg, u.deg))
        elif unit.lower() == 'hourangle':
            logger.debug(f'coord hourangle={coord}')
            c = SkyCoord(coord, unit=(u.hourangle, u.deg))

        #hours, minutes, seconds = radec.degToHms(c.ra.deg[0])
        ra = radec.raHmsToString(c.ra.hms.h, c.ra.hms.m, c.ra.hms.s, format='%02d:%02d:%06.3f')
        dec = radec.decDegToString(c.dec.deg, format='%s%02d:%02d:%05.2f')
        coord_error = None
    except Exception as e:
        logger.error(f'error={e}')
        coord_error = f'{e}'

    errs = [err for err in [name_error, coord_error] if err]
    logger.debug(f'errs={errs}')

    errs = ', '.join(errs)

    if not errs:
        ra_dec = Bunch.Bunch(name=name, ra=ra, dec=dec, coord=f'{ra} {dec}', equinox=equinox, err=errs)
        logger.debug(f'deg to hms/dms. {ra_dec}')
    else:
        ra_dec = Bunch.Bunch(name=name, ra=None, dec=None, coord=coord, equinox=equinox, err=errs)
    return ra_dec


def verify_coord_format(name, coord, equinox, logger):

    logger.debug(f'coord=<{coord}>, type{type(coord)}')
    matches = re.findall(soss_pattern , coord)
    if len(matches) == 2:
        logger.debug(f'soss pattern={matches}')
        coord = coord.split()
        ra = coord[0].strip()
        dec = coord[1].strip()
        res = _validate_target(name, ra, dec, equinox, logger)
        return res

    matches = re.findall(deg_pattern, coord)
    if len(matches) == 2:
        logger.debug(f'degree pattern={matches}')
        return validate_ra_dec_format(name, coord, equinox, logger, unit='degree')
        #print(f'degree pattern. matches={matches}')

    else:
        return validate_ra_dec_format(name, coord, equinox, logger, unit='hourangle')



def text_dict(target, equinox, logger):

    targets = []
    target_list = target.split("\r\n")

    logger.debug(f'text target_list={target_list}')

    for t in target_list:
        logger.debug(f'target={t}')
        name = t.split()[0]
        idx = t.find(' ')
        coord = t[idx:].strip()
        logger.debug(f'name={name}, coord={coord}')
        res = verify_coord_format(name, coord, equinox, logger)
        targets.append(res)

    return targets

def site(mysite):

    site_dict = {"subaru": subaru}
    return site_dict.get(mysite)

def populate_interactive_target(target_list, mysite, mydate, logger):

    logger.debug('poplulate interactive target...')

    targets = []

    title = f"Visibility for the night of {mydate}"
    mydate_time = f'{mydate} 17:00:00'
    mysite.set_date(mysite.get_date(mydate_time))
    timezone = mysite.tz_local

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'
    plot_height = 1230
    plot_width = 1580
    # note: output_backend: webgl is to optimize drawings, but can't draw dotted line
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "height": plot_height, "width": plot_width,} #  "output_backend": "webgl"}

    plot = TargetPlot(logger, **fig_args)

    errors = []
    for t in target_list:
        if not t.err:
            targets.append(StaticTarget(name=t.name, ra=t.ra, dec=t.dec, equinox=t.equinox))
        else:
            errors.append(f'name={t.name}, coord={t.coord}, equinox={t.equinox}. err={t.err}')

    target_data = []
    for tgt in targets:
        info_list = mysite.get_target_info(tgt)
        target_data.append(Bunch.Bunch(history=info_list, target=tgt))

    if not target_data:
        return (plot.fig, errors)

    try:
        plot.plot_target(mysite, target_data)
    except Exception as e:
        logger.error(f'error: plotting targets. {e}')
        errors.append(f"plotting target(s). {e}")
        #raise TargetError(f"ploting targets. {e}")

    return (plot.fig, errors)

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
    plot_height = 930
    plot_width = 1000

    sizing_mode = 'scale_both' #'stretch_both'
    # note: output_backend: webgl is to optimize drawings, but can't draw dotted line
    #fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "sizing_mode": sizing_mode} #  "output_backend": "webgl"}

    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "height": plot_height, "width": plot_width} # "sizing_mode": sizing_mode} #  "output_backend": "webgl"}

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
