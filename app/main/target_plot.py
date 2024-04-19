from datetime import datetime, timedelta
import time
from dateutil import tz
import numpy as np
from math import pi, isclose
import random
from operator import itemgetter


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
from bokeh.core.properties import String

try:
    from .base_plot import BasePlot
except:
    from base_plot import BasePlot

from ginga.misc import Bunch
import matplotlib.dates as mpl_dt


class TargetPlot(BasePlot):

    def __init__(self, logger=None, **args):
        super(TargetPlot, self).__init__(logger, **args)

    def plot_target(self, site, tgt_data):

        self.logger.debug(f'plotting targets...')
        timezone = site.tz_local
        self.plot_base(site, tgt_data)

        lt_data = list(map(lambda info: info.ut.astimezone(timezone), tgt_data[0].history))

        self.logger.debug(f'target trajectory...')
        self.target_trajectory(lt_data, tgt_data)

        self.logger.debug(f'calling moon trajectory...')
        self.moon_trajectory(tgt_data, lt_data, site)

        self.fig.legend.click_policy = "hide"

        self.logger.debug(f'plot_target done...')

    def moon_trajectory(self, tgt_data, lt_data, site):

        self.logger.debug(f'moon_trajectory...')
        # Plot moon trajectory and illumination
        moon_data = np.array(list(map(lambda info: info.moon_alt, tgt_data[0].history)))
        illum_time = lt_data[moon_data.argmax()]
        moon_illum = site.moon_phase(date=illum_time)
        moon_color = "orange" # '#666666'
        moon_name = "Moon(Illum {:.2f} %)".format(moon_illum*100)
        self.logger.debug(f'moon name={moon_name}')
        moon = self.fig.line(lt_data, moon_data, line_color=moon_color, line_alpha=0.5, line_dash="dashed",  line_width=3)
        moon_legend = LegendItem(label=moon_name, renderers=[moon])
        self.logger.debug(f'moon legend={moon_legend}')

        leg = self.fig.legend.pop()
        leg.items.insert(0, moon_legend)
        self.logger.debug(f'moon_trajectory done...')

    def moon_distance(self, info, lt_data, alt_data, color):

        self.logger.debug(f'moon_distance...')
        moon_sep = np.array(list(map(lambda info: info.moon_sep, info.history)))
        min_interval = 12  # hour/5min
        mt = lt_data[0:-1:min_interval]
        moon_sep = moon_sep[0:-1:min_interval]
        alt_interval = alt_data[0:-1:min_interval]

        moon = []
        xs = []
        ys = []
        texts = []
        for x, y, v in zip(mt, alt_interval, moon_sep):
            if y < 0:
                continue

            xs.append(x)
            ys.append(y)
            texts.append(f'{v:.1f}')

        deg = self.fig.scatter(xs, ys, color=color, size=10.0,  fill_alpha=0.8)
        moon.append(deg)
        txt = self.fig.text(xs, ys, text=texts, text_font_size="9pt", text_align="center", text_baseline="bottom")
        moon.append(txt)

        return moon

    def target_trajectory(self, lt_data, tgt_data):

        legend_items = []

        self.logger.debug(f'TARGET DATA type={type(tgt_data)}')

        #for i, info in enumerate(tgt_data):
        for info in sorted(tgt_data, key=lambda k: k.target.name, reverse=False):
            alt_data = np.array(list(map(lambda info: info.alt_deg, info.history)))
            alt_min = np.argmin(alt_data)
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            self.logger.debug(f'color={color}')
            target = self.fig.line(lt_data, alt_data, line_color=color, line_width=3)

            x = lt_data[alt_data.argmax()]
            y = alt_data.max()
            targetname = info.target.name

            self.logger.debug(f'x={x}, y={y}, targetname={targetname}')
            target_label = self.fig.text([x,], [y,], text=[targetname,], text_color=color, text_alpha=1.0, text_align='center', text_baseline ='bottom')

            self.logger.debug(f'callling moon distance...')
            moon = self.moon_distance(info, lt_data, alt_data, color)
            moon.insert(0, target_label)
            moon.insert(0, target)

            legend_items.append(LegendItem(label=f"{targetname} {info.target.ra} {info.target.dec}", renderers=moon))

        legend_title = LegendItem(label="Name,Ra and Dec.  Moon distance in deg(circle)", renderers=[])
        legend_items.insert(0, legend_title)

        target_legends = Legend(items=legend_items, location="top_right", background_fill_color='white', background_fill_alpha=0.7)
        self.fig.add_layout(target_legends, 'right')

        self.logger.debug(f'target_trajectory done...')

if __name__ == '__main__':
    import sys
    import logging
    from qplan import entity, common
    from qplan.util.site import get_site

    logger = logging.getLogger()

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'

    site = get_site('subaru')
    timezone = site.tz_local
    date = "2019-06-28"

    title = "Visibility for the night of {}".format(date)

    # note: output_backend: webgl is to optimize drawings
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "height": 850, "width": 1200,} #  "output_backend": "webgl"}

    plot = TargetPlot(logger, **fig_args)

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
    tgt = entity.StaticTarget(name='S5', ra='14:20:00.00', dec='48:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sf', ra='09:40:00.00', dec='43:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='long long long name', ra='10:30:00.00', dec='36:00:00.00')
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


    plot.plot_target(site, target_data)
    #show(row(plot.fig, column(plot.target_legend)))
    show(plot.fig)
