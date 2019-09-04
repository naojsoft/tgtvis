import os
import sys

from datetime import datetime, timedelta
import time
from dateutil import tz
import pytz
import numpy as np
from math import pi, isclose

from bokeh.models import BoxAnnotation
from bokeh.layouts import gridplot
from bokeh.plotting import figure, output_file, show
from bokeh.models import SingleIntervalTicker, LinearAxis
from bokeh.models import FixedTicker, ContinuousTicker
from bokeh.models import Range1d, DataRange1d
from bokeh.models import Label
from bokeh.models import Legend, LegendItem
from bokeh.models import Toggle, CustomJS
from bokeh.layouts import layout, row, column
from bokeh.models.widgets import CheckboxGroup
from bokeh.models import Span

from qplan import entity, common
from qplan.util.site import get_site

#from astropy.coordinates import get_mooni
#from astroplan import Observer 
#from astropy.utils.iers import conf
#conf.auto_max_age = None

from ginga.misc import Bunch


class BasePlot(object):

    def __init__(self, logger=None, **args):
        super(BasePlot, self).__init__()

        self.utc = tz.gettz('UTC')
        self.y_min = 0 # degree
        self.y_max = 90 
        
        self.logger = logger
        
        self.logger.debug("args={}".format(args))
        
        self.fig = figure(**args)

        #self.subaru = Observer.at_site('subaru')
        #self.subaru.timezone = pytz.timezone('US/Hawaii')

        self.subaru = get_site('subaru')
        
        #self.subaru = observer.subaru
        
        
    def plot_base(self, site, tgt_data):

        timezone = site.tz_local
        
        print('timezone={}, type={}'.format(timezone, type(timezone)))
        self.logger.debug('plot_target timezone={} tzname={}'.format(timezone, timezone.tzname(None)))
        #lt_data = list(map(lambda info: info.ut.astimezone(timezone), tgt_data[0].history))
        #print("LT DATA ", lt_data)
        #print("TGT DATA ", tgt_data)
        title = "Visibility for the night of {}".format(site.date.strftime("%Y-%m-%d"))
        self.fig.title.text = title

        sunset, sunrise = self.sunset_sunrise(site, timezone)
        
        # X(time)/Y(degree) axis range
        self.fig.y_range = Range1d(self.y_min, self.y_max)
        self.fig.x_range = Range1d(sunset, sunrise)

        self.altitude()
        self.twilight(site, sunset, sunrise, timezone)
        #self.middle_night(site, sunset, sunrise, timezone)
        self.middle_night(sunset, sunrise)
        self.airmass()
        self.moon_at_midnight(site, sunrise, timezone)
        

        # label X/Y axis
        self.fig.xaxis.axis_label = "HST"
        self.fig.yaxis[0].axis_label = "Altitude"
        self.fig.yaxis[1].axis_label = "Airmass"

        self.fig.legend.click_policy = "hide"

    def altitude(self):

        self.fig.add_layout(BoxAnnotation(bottom=75,  fill_alpha=0.1, fill_color='yellow', line_color='yellow'))
        self.fig.add_layout(BoxAnnotation(top=30, fill_alpha=0.1, fill_color='yellow', line_color='yellow'))
        
    def airmass(self):

        altitude_deg = np.arange(10, 90.5, 0.5)
        airmass_f = 1.0/np.cos(np.radians(90-altitude_deg))
        airmass = list(map(lambda n: "%.3f" % n, airmass_f))

        alt_airmass = {}
        for alt, airmass in zip(altitude_deg, airmass):
            res = alt % 1
            if isclose(res, 0.0, abs_tol=0.01):
                #print('close alt={:.0f}, res={}'.format(alt, res))
                alt_airmass['{:.0f}'.format(alt)] = "{}".format(airmass)
            else:
                #print('no close alt={:.1f}, res={}'.format(alt, res))
                alt_airmass['{:.1f}'.format(alt)] = "{}".format(airmass)


        self.fig.extra_y_ranges = {"Airmass": Range1d(start=self.y_min, end=self.y_max)}
        self.fig.add_layout(LinearAxis(y_range_name="Airmass"), 'right')
        self.fig.yaxis[1].major_label_overrides = alt_airmass
        
                
    def sunset_sunrise(self, site, timezone):
        #hst = tz.gettz(timezone)

        self.logger.debug('site date={} type={}'.format(site.date, type(site.date)))

        #sunset = datetime(site.date.year, site.date.month, site.date.day, tzinfo=timezone)
        #sunrise = site.date + timedelta(days=1)
        #sunrise = datetime(sunrise.year, sunrise.month, sunrise.day, 0, 0, 0,  tzinfo=timezone)
        #astro_sunset = self.subaru.datetime_to_astropy_time(site.date)
        #sunset = self.subaru.astropy_time_to_datetime(self.subaru.sun_set_time(astro_sunset))
        sunset = site.sunset(site.date)
        #sunset = sunset.replace(tzinfo=timezone)
        #astro_sunrise = self.subaru.datetime_to_astropy_time(sunrise)
        #sunrise = self.subaru.astropy_time_to_datetime(self.subaru.sun_rise_time(astro_sunrise))
        sunrise = site.sunrise(site.date)
        #sunrise = sunrise.replace(tzinfo=timezone)
        print("sunset={}".format(sunset.strftime('%Y-%m-%d %H:%M:%S')))
        print("sunrise={}".format(sunrise.strftime('%Y-%m-%d %H:%M:%S')))
        
        sunset_line = self.fig.line([sunset, sunset], [self.y_min, self.y_max], line_color='red', line_width=3, line_dash='dashed')
        
        sunrise_line = self.fig.line([sunrise, sunrise], [self.y_min, self.y_max], line_color='red', line_width=3, line_dash='dashed')
        
        sun_legend = Legend(items=[LegendItem(label="Sunset/rise {} {}".format( sunset.strftime('%H:%M:%S'), sunrise.strftime('%H:%M:%S')), renderers=[sunset_line, sunrise_line])], location=('bottom_left'), background_fill_color='white', background_fill_alpha=1)

        # note: legend layout options: left, right, above, below or center
        self.fig.add_layout(sun_legend, 'below')
        
        return (sunset, sunrise)

    def moon_at_midnight(self, site, sunrise, timezone):

        obs_date = site.date

        mid_night = site.date + timedelta(days=1)
        mid_night = datetime(mid_night.year, mid_night.month, mid_night.day, 0, 0, 0, tzinfo=timezone)
        
        #astropy_time = self.subaru.datetime_to_astropy_time(mid_night)
        #moon = get_moon(astropy_time, observer.location)
        #moon = get_moon(astropy_time, self.subaru.location)
        
        #self.fig.text(x=[mid_night], y=[0.5], text=["Moon at Midnight\nRa: {:02.0f}:{:02.0f}:{:02.3f}\nDec: {:02.0f}:{:02.0f}:{:02.2f}".format(moon.ra.hms.h, moon.ra.hms.m, moon.ra.hms.s, moon.dec.dms.d, moon.dec.dms.m, moon.dec.dms.s)], text_font_size="7pt", text_align="center", text_baseline="bottom")
        
        # print('mid_night={}'.format(mid_night))
        
        site.moon_set(mid_night)
        self.fig.text(x=[mid_night], y=[0.5], text=["Moon at Midnight\nRa: {}\nDec: {}".format(site.moon.ra, site.moon.dec)], text_font_size="7pt", text_align="center", text_baseline="bottom")
        # print('moon ra={}, dec={}'.format(site.moon.ra, site.moon.dec))
        
        # #site.set_date(obs_date)
        # print('site date after moon_mid={}'.format(site.date))
        
        
        # mid_night = datetime(sunrise.year, sunrise.month, sunrise.day, 0, 0, 0, tzinfo=timezone)
        # self.logger.debug('moon at  midnight. ra={}, dec={}'.format(site.moon.ra, site.moon.dec))
        # self.fig.text(x=[mid_night], y=[0.5], text=["Moon at Midnight\nRa: {}\nDec: {}".format(site.moon.ra, site.moon.dec)], text_font_size="7pt", text_align="center", text_baseline="bottom")

    #def middle_night(self, site, sunset, sunrise, timezone):
    def middle_night(self, sunset, sunrise):        

        # middle of the night
        middle_night = sunset + timedelta(0, (sunrise-sunset).total_seconds() / 2.0)
        print('MIddle night ', middle_night)

        mn_line = self.fig.line([middle_night, middle_night], [self.y_min, self.y_max], line_color='blue', line_width=2, line_dash='dashed')

        print('legend={}'.format(self.fig.legend))
        mid_legend = LegendItem(label="Middle Night", renderers=[mn_line])

        leg = self.fig.legend.pop()
        print('popped leg={}'.format(leg.items))
        leg.items.append(mid_legend)
        
        # middle_night = site.night_center()
        # print('MIddle night ', middle_night)
        # mn = middle_night.astimezone(timezone)
        # middle_night = datetime(mn.year, mn.month, mn.day, mn.hour, mn.minute, mn.second)
                  
        # middle_night = (middle_night - datetime(1970, 1, 1)).total_seconds() * 1000 

        # mn_line = self.fig.line([middle_night, middle_night], [self.y_min, self.y_max], line_color='blue', line_width=2, line_dash='dashed')


        # print('legend={}'.format(self.fig.legend))
        # mid_legend = LegendItem(label="Middle Night", renderers=[mn_line])

        # leg = self.fig.legend.pop()
        # print('popped leg={}'.format(leg.items))
        # leg.items.append(mid_legend)
        
    def twilight(self, site,  sunset, sunrise, timezone):
        print('twilight....')    

        # evening  civil twilight 6 degree
        #et6 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_evening_civil(self.subaru.datetime_to_astropy_time(sunset)))
        
        et6 = site.evening_twilight_6(sunset)
        print('Evening Civil Twi={}'.format(et6))
        
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #et6 = et6.replace(tzinfo=self.utc)
        # et6 = et6.astimezone(timezone)
        # et6 = datetime(et6.year, et6.month, et6.day, et6.hour, et6.minute, et6.second)

        # evening  nautical twilight 12 degree
        #et12 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_evening_nautical(self.subaru.datetime_to_astropy_time(sunset)))
        
        et12 = site.evening_twilight_12(sunset)
        print('Evening Nautical Twi={}'.format(et12))
        
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #et12 = et12.replace(tzinfo=utc)
        # et12 = et12.astimezone(timezone)
        # et12 = datetime(et12.year, et12.month, et12.day, et12.hour, et12.minute, et12.second)
        # evening  astronomical twilight 18 degree
        #et18 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_evening_astronomical(self.subaru.datetime_to_astropy_time(sunset)))
      
        et18 = site.evening_twilight_18(sunset)
        print('Evening Astro Twi={}'.format(et18))
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #et18 = et18.replace(tzinfo=utc)
        # et18 = et18.astimezone(timezone)
        # et18 = datetime(et18.year, et18.month, et18.day, et18.hour, et18.minute, et18.second)
        # morning  astronomical twilight 18 degree
        #mt18 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_morning_astronomical(self.subaru.datetime_to_astropy_time(sunrise)))
        
        mt18 = site.morning_twilight_18(sunset)
        print('Morning Astro Twi={}'.format(mt18))
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #mt18 = mt18.replace(tzinfo=utc)
        # mt18 = mt18.astimezone(timezone)
        # mt18 = datetime(mt18.year, mt18.month, mt18.day, mt18.hour, mt18.minute, mt18.second)
        # morning  nautical twilight 12 degree
        #mt12 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_morning_nautical(self.subaru.datetime_to_astropy_time(sunrise)))
        
        mt12 = site.morning_twilight_12(sunset)
        print('Morning Nautical Twi={}'.format(mt12))
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #mt12 = mt12.replace(tzinfo=utc)
        # mt12 = mt12.astimezone(timezone)
        # mt12 = datetime(mt12.year, mt12.month, mt12.day, mt12.hour, mt12.minute, mt12.second)
        # morning  civil twilight 6 degree
        #mt6 = self.subaru.astropy_time_to_datetime(self.subaru.twilight_morning_civil(self.subaru.datetime_to_astropy_time(sunrise)))
        
        mt6 = site.morning_twilight_6(sunset)
        print('Morning Civil Twi={}'.format(mt6))
        # # note important:  this "repalce" is for python3.6 not python3.5
        # #mt6 = mt6.replace(tzinfo=self.utc)
        # mt6 = mt6.astimezone(timezone)
        # mt6 = datetime(mt6.year, mt6.month, mt6.day, mt6.hour, mt6.minute, mt6.second)

        #Twi6 = BoxAnnotation(left=sunset, right=et6, bottom=self.y_min, top=self.y_max, fill_alpha=0.4, fill_color='orange', line_color='orange', line_alpha=0.4)
        
        twi6 = self.fig.patches(xs=[[sunset, sunset, et6, et6], [mt6, mt6, sunrise, sunrise]], ys=[[self.y_max, self.y_min, self.y_min, self.y_max], [self.y_max, self.y_min, self.y_min, self.y_max]], fill_color='orange', fill_alpha=0.4, line_color='orange', line_alpha=0.4)

        twi12 = self.fig.patches(xs=[[et6, et6, et12, et12], [mt12, mt12, mt6, mt6]], ys=[[self.y_max, self.y_min, self.y_min, self.y_max], [self.y_max, self.y_min, self.y_min, self.y_max]], fill_color='navy', fill_alpha=0.2, line_color='navy', line_alpha=0.2)

        twi18 = self.fig.patches(xs=[[et12, et12, et18, et18], [mt18, mt18, mt12, mt12]], ys=[[self.y_max, self.y_min, self.y_min, self.y_max], [self.y_max, self.y_min, self.y_min, self.y_max]], fill_color='navy', fill_alpha=0.5, line_color='navy', line_alpha=0.5)


        twi_legend = Legend(items=[LegendItem(label="Civil Twi: {} {}".format(et6.strftime("%H:%M:%S"), mt6.strftime("%H:%M:%S")), renderers=[twi6]),
                                   LegendItem(label="Nautical Twi: {}  {}".format(et12.strftime("%H:%M:%S"), mt12.strftime("%H:%M:%S")), renderers=[twi12]),
                                   LegendItem(label="Astronomical Twi: {}  {}".format(et18.strftime("%H:%M:%S"), mt18.strftime("%H:%M:%S")), renderers=[twi18])], location=('top_left'), background_fill_color='white', background_fill_alpha=0.7)

        civil_legend = LegendItem(label="Civil Twi: {} {}".format(et6.strftime("%H:%M:%S"), mt6.strftime("%H:%M:%S")), renderers=[twi6])

        nautical_legend = LegendItem(label="Nautical Twi: {}  {}".format(et12.strftime("%H:%M:%S"), mt12.strftime("%H:%M:%S")), renderers=[twi12])           

        astronomical_legend = LegendItem(label="Astronomical Twi: {}  {}".format(et18.strftime("%H:%M:%S"), mt18.strftime("%H:%M:%S")), renderers=[twi18])
        
        leg = self.fig.legend.pop()
        #print('popped leg={}'.format(leg.items))
        leg.items.append(civil_legend)
        leg.items.append(nautical_legend)
        leg.items.append(astronomical_legend)
        #leg.items.append(twi_legend)       

        
if __name__ == '__main__':
    import logging

    logger = logging.getLogger()
    logger.setLevel('DEBUG')

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'

    #subaru = observer.subaru
    site = get_site('subaru')

    timezone = site.tz_local
    date = "2019-06-28"

    
    title = "Visibility for the night of {}".format(date)
 
    output_backend="webgl"
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "plot_height": 800, "plot_width": 900,} # "output_backend": "webgl"}
    
    plot = BasePlot(logger, **fig_args)
    
    
    start_time = datetime.strptime("2019-06-28 17:00:00", "%Y-%m-%d %H:%M:%S")
    start_time = start_time.replace(tzinfo=timezone)
    t = start_time
    # if schedule starts after midnight, change start date to the
    # day before
    if 0 <= t.hour < 12:
        t -= timedelta(0, 3600*12)
    ndate = t.strftime("%Y/%m/%d")

    print('what is t={}'.format(t))
    targets = []
    site.set_date(start_time)

    tgt = entity.StaticTarget(name='aaaa', ra='12:34:56.789', dec='12:34:56.78')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='bbbb', ra='23:23:23.123', dec='45:45:45.34')
    targets.append(tgt)
    
    
    # tgt = entity.StaticTarget(name='S5', ra='14:20:00.00', dec='48:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='Sf', ra='09:40:00.00', dec='43:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='Sm', ra='10:30:00.00', dec='36:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='Sn', ra='15:10:00.00', dec='34:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='Sn!4$#$@$', ra='20:10:00.00', dec='34:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='Sssn', ra='15:10:00.00', dec='24:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='nnnn', ra='15:10:00.00', dec='14:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='mmmmm', ra='05:10:00.00', dec='14:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='hohoho', ra='10:10:00.00', dec='54:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='hello', ra='11:10:00.00', dec='-04:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='iiiiiiii', ra='09:10:00.00', dec='44:00:00.00')
    # targets.append(tgt)
    # tgt = entity.StaticTarget(name='fofoffo', ra='20:10:00.00', dec='04:00:00.00')
    # targets.append(tgt)

    # make airmass plot
    num_tgts = len(targets)
    target_data = []
    lengths = []
    if num_tgts > 0:
        for tgt in targets:
            info_list = site.get_target_info(tgt)
            target_data.append(Bunch.Bunch(history=info_list, target=tgt))
            lengths.append(len(info_list))

    # clip all arrays to same length
    min_len = min(*lengths)
    for il in target_data:
        il.history = il.history[:min_len]

    ## info = Bunch.Bunch(site=site, num_tgts=num_tgts,
    ##                    target_data=target_data)
    plot.plot_base(site, target_data)

    show(plot.fig)
