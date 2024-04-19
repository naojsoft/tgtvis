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
from bokeh.models import Toggle
#from bokeh.models import CustomJS
from bokeh.models.callbacks import CustomJS
from bokeh.layouts import layout, row, column
from bokeh.models.widgets import CheckboxGroup
from bokeh.models import Span

try:
    from .base_plot import BasePlot
except:
    from base_plot import BasePlot

from ginga.misc import Bunch


class LaserPlot(BasePlot):

    def __init__(self, logger=None, **args):
        super(LaserPlot, self).__init__(logger, **args)

        self.toggles = []

    def plot_laser(self, site, tgt_data,  collision_time):

        self.logger.debug('plot_laser...')
        timezone = site.tz_local

        self.logger.debug('plot_base...')
        self.plot_base(site, tgt_data)
        self.collision(site, collision_time)

        #info = tgt_data[0]
        lt_data = list(map(lambda info: info.ut.astimezone(timezone), tgt_data[0].history))
        alt_data = np.array(list(map(lambda info: info.alt_deg, tgt_data[0].history)))

        self.logger.debug('target trajecotry...')
        self.target_trajectory(lt_data, alt_data, tgt_data)
        self.moon_trajectory(tgt_data, lt_data, site)
        #self.moon_distance(tgt_data, lt_data, alt_data)

        self.fig.legend.click_policy = "hide"
        self.logger.debug('plot_laser done...')

    def moon_distance(self, tgt_data, lt_data, alt_data, moon_deg_color):

        moon_sep = np.array(list(map(lambda info: info.moon_sep, tgt_data[0].history)))
        min_interval = 12  # hour/5min
        mt = lt_data[0:-1:min_interval]
        moon_sep = moon_sep[0:-1:min_interval]
        alt_interval = alt_data[0:-1:min_interval]

        moon = []
        xs = []
        ys = []
        names = []

        for x, y, v in zip(mt, alt_interval, moon_sep):
            if y < 0:
                continue
            xs.append(x)
            ys.append(y)
            names.append(f"{v:.1f}")

        deg = self.fig.scatter(xs, ys, color=moon_deg_color, size=10, fill_alpha=0.5)
        moon.append(deg)
        txt = self.fig.text(xs, ys, text=names, text_font_size="11pt", text_align="center", text_baseline="bottom")
        moon.append(txt)

        return moon

    def moon_trajectory(self, tgt_data, lt_data, site):
        # Plot moon trajectory and illumination
        moon_data = np.array(list(map(lambda info: info.moon_alt, tgt_data[0].history)))
        illum_time = lt_data[moon_data.argmax()]
        moon_illum = site.moon_phase(date=illum_time)
        moon_color = 'orange' #'#666666'
        moon_name = "Moon(Illum {:.2f} %)".format(moon_illum*100)
        moon = self.fig.line(lt_data, moon_data, line_color=moon_color, line_alpha=0.7,  line_width=3, line_dash="dashed")
        moon_legend = LegendItem(label=moon_name, renderers=[moon])

        leg = self.fig.legend.pop()
        #print('popped leg={}'.format(leg.items))
        leg.items.append(moon_legend)
        #leg.items.insert(0, moon_legend)

    def target_trajectory(self, lt_data, alt_data, tgt_data):

        target_color = 'red'
        target = self.fig.line(lt_data, alt_data, line_color=target_color, line_width=3)
        moon = self.moon_distance(tgt_data=tgt_data, lt_data=lt_data, alt_data=alt_data, moon_deg_color=target_color)
        #print('moon={}'.format(moon))

        #moon.insert(0, target)
        moon.append(target)
        #moon.insert(0, legend_title)

        target_legend = Legend(items=[LegendItem(label="{} {} {}, Moon dist(deg)".format(tgt_data[0].target.name, tgt_data[0].target.ra, tgt_data[0].target.dec), renderers=moon)], location=('top_right'), background_fill_color='white', background_fill_alpha=0.5)

        self.fig.add_layout(target_legend)

    def collision(self, site, collision_time):

        self.logger.debug('drawing collision...')
        code = '''object.visible = toggle.active'''
        #toggles = []

        for s, e in collision_time:
            self.logger.debug(f'start={s}, end={e}, tz={site.timezone}')
            s = pytz.timezone("US/Hawaii").localize(s)
            e = pytz.timezone("US/Hawaii").localize(e)

            #print('making callback...')
            #callback = CustomJS.from_coffeescript(code=code, args={})
            callback = CustomJS(code=code, args={})
            #print('making toggle...')
            toggle = Toggle(label="{}-{}".format(s.strftime("%Y-%m-%d %H:%M:%S"), e.strftime("%H:%M:%S")), button_type="default", active=True, width=20, height=25)
            toggle.js_on_click(callback)
            self.toggles.append(toggle)
            #print('making laser annotation...')
            laser_collision = BoxAnnotation(left=s, right=e, bottom=self.y_min, top=self.y_max, fill_alpha=0.2, fill_color='magenta', line_color='magenta', line_alpha=0.2)
            #print('adding layout...')
            self.fig.add_layout(laser_collision)
            callback.args = {'toggle': toggle, 'object': laser_collision}

        #return toggles

if __name__ == '__main__':
    import sys
    import logging
    from qplan import entity, common
    from qplan.util.site import get_site

    logger = logging.getLogger()
    logger.setLevel('DEBUG')

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'

    site = get_site('subaru')
    timezone = site.tz_local
    date = "2019-06-28"

    title = "Visibility for the night of {}".format(date)

    # note: output_backend: webgl is to optimize drawings
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "height": 850, "width": 900,} #  "output_backend": "webgl"}

    plot = LaserPlot(logger, **fig_args)

    site = get_site('subaru')
    timezone = site.tz_local

    start_time = datetime.strptime("2019-06-28 17:00:00", "%Y-%m-%d %H:%M:%S")
    start_time = start_time.replace(tzinfo=timezone)
    t = start_time
    # if schedule starts after midnight, change start date to the
    # day before
    if 0 <= t.hour < 12:
        t -= timedelta(0, 3600*12)
    ndate = t.strftime("%Y/%m/%d")

    targets = []
    site.set_date(t)
    tgt = entity.StaticTarget(name='SgrAS', ra='14:20:00.00', dec='48:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sf', ra='09:40:00.00', dec='43:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sm', ra='10:30:00.00', dec='36:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sn', ra='15:10:00.00', dec='34:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sn!4$#$@$', ra='20:10:00.00', dec='34:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sssn', ra='15:10:00.00', dec='24:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='nnnn', ra='15:10:00.00', dec='14:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='mmmmm', ra='05:10:00.00', dec='14:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='hohoho', ra='10:10:00.00', dec='54:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='hello', ra='11:10:00.00', dec='-04:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='iiiiiiii', ra='09:10:00.00', dec='44:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='fofoffo', ra='20:10:00.00', dec='04:00:00.00')
    targets.append(tgt)

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

    target = {'SgrAS': [(datetime(2019, 6, 28, 19, 13), datetime(2019, 6, 28, 21, 45, 2)), (datetime(2019, 6, 28, 21, 45, 21), datetime(2019, 6, 28, 21, 52, 16)), (datetime(2019, 6, 28, 21, 52, 32), datetime(2019, 6, 28, 22, 1, 19)), (datetime(2019, 6, 28, 22, 1, 34), datetime(2019, 6, 28, 22, 39, 28)), (datetime(2019, 6, 28, 22, 40, 27), datetime(2019, 6, 28, 23, 14, 18)), (datetime(2019, 6, 28, 23, 14, 36), datetime(2019, 6, 28, 23, 17, 6)), (datetime(2019, 6, 28, 23, 17, 32), datetime(2019, 6, 28, 23, 18, 31)), (datetime(2019, 6, 28, 23, 18, 44), datetime(2019, 6, 28, 23, 19, 29)), (datetime(2019, 6, 28, 23, 34, 32), datetime(2019, 6, 28, 23, 38, 6)), (datetime(2019, 6, 28, 23, 38, 24), datetime(2019, 6, 28, 23, 53, 27)), (datetime(2019, 6, 28, 23, 53, 31), datetime(2019, 6, 29, 0, 6, 4)), (datetime(2019, 6, 29, 0, 8, 9), datetime(2019, 6, 29, 0, 40, 37)), (datetime(2019, 6, 29, 1, 18, 57), datetime(2019, 6, 29, 1, 35, 28))]}

    collision_time = target['SgrAS']

    plot.plot_laser(site, target_data, collision_time)
    show(row(plot.fig, column(plot.toggles)))
    #show(plot.fig)

    #END
