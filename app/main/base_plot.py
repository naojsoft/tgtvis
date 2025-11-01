import os
import sys

from datetime import datetime, timedelta, timezone
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
#from qplan.util.site import get_site
from qplan.util.calcpos import load, ssbodies, alt2airmass
from ginga.misc import Bunch


class BasePlot:
    def __init__(self, logger=None, **fig_args):
        self.logger = logger
        self.utc = tz.gettz('UTC')
        self.y_min = 0
        self.y_max = 90
        self.logger.debug(f"Initializing BasePlot with args: {fig_args}")
        self.fig = figure(**fig_args)

    def plot_base(self, site):
        """Sets up the basic plot background: axes, sunset/sunrise, twilight bands, etc."""
        local_timezone = site.tz_local
        date_str = site.date.strftime("%Y-%m-%d")

        self.logger.debug(f"Plotting base for {date_str} with timezone {local_timezone}")
        self.fig.title.text = f"Visibility for the night of {date_str}"

        sunset, sunrise = self._sunset_sunrise(site)
        self._set_axes_ranges(sunset, sunrise)
        self._set_axes_labels()

        # Drawing overlays
        self.logger.debug(f"drawing sunset/sunrise..")
        self._draw_sunset_sunrise(sunset, sunrise)
        self.logger.debug(f"drawing altitude..")
        self._draw_altitude_bands()
        self.logger.debug(f"drawing twilight..")
        self._draw_twilight(site, sunset, sunrise)
        self.logger.debug(f"drawing middle night..")
        self._draw_middle_night(sunset, sunrise)
        self.logger.debug(f"drawing airmass..")
        self._draw_airmass_axis()
        self.logger.debug(f"drawing moon anno... site type={type(site)}")
        self._draw_moon_annotation(site, sunrise, local_timezone)

        self.logger.debug(f"legend click policy..")
        self.fig.legend.click_policy = "hide"
        self.logger.debug("Base plot rendering complete.")

    # -----------------------
    # Axis and Range Settings
    # -----------------------
    def _set_axes_ranges(self, sunset, sunrise):
        self.fig.x_range = Range1d(sunset, sunrise)
        self.fig.y_range = Range1d(self.y_min, self.y_max)
        self.fig.yaxis[0].ticker = FixedTicker(ticks=list(range(0, 91, 10)))  # 0 to 90 every 10 degree

    def _set_axes_labels(self):
        self.fig.xaxis.axis_label = "HST"
        self.fig.yaxis[0].axis_label = "Altitude"

    # -----------------------
    # Visual Elements
    # -----------------------
    def _draw_altitude_bands(self):
        """Highlights poor visibility regions."""
        self.fig.add_layout(BoxAnnotation(bottom=75, fill_alpha=0.1, fill_color='yellow', line_color='yellow'))
        self.fig.add_layout(BoxAnnotation(top=30, fill_alpha=0.1, fill_color='yellow', line_color='yellow'))

    def _draw_airmass_axis(self):
        """Right-hand axis: airmass values corresponding to altitude scale."""
        # Use same range as altitude axis
        self.fig.extra_y_ranges = {"Airmass": self.fig.y_range}
        axis = LinearAxis(y_range_name="Airmass", axis_label="Airmass")

        # Choose some altitude positions for ticks
        alt_ticks = [90, 80, 70, 60, 50, 40, 30, 20, 10]
        am_vals   = [alt2airmass(a) for a in alt_ticks]

        # Place ticks at those altitude values, but show airmass numbers
        axis.ticker = FixedTicker(ticks=alt_ticks)
        axis.major_label_overrides = {alt: f"{am:.2f}" for alt, am in zip(alt_ticks, am_vals)}

        self.fig.add_layout(axis, 'right')

    def _draw_middle_night(self, sunset, sunrise):
        """Draw dashed line at midnight."""
        middle = sunset + (sunrise - sunset) / 2
        line = self.fig.line([middle, middle], [self.y_min, self.y_max],
                             line_color='blue', line_width=2, line_dash='dashed')

        self._append_legend_item("Middle Night", [line])

    def _draw_moon_annotation(self, site, sunrise, local_timezone):
        """Display moon RA/Dec at midnight."""

        self.logger.debug(f"site={site}")
        today_midnight = datetime(
            site.date.year,
            site.date.month,
            site.date.day,
            0, 0, 0,
            tzinfo=local_timezone)

        midnight_local_timezone = today_midnight + timedelta(days=1)

        self.logger.debug(f"midnight={midnight_local_timezone}, site={site.__dir__()}")

        utc_dt = (midnight_local_timezone + timedelta(hours=10)).replace(tzinfo=timezone.utc)
        ts  = load.timescale()
        t   = ts.from_datetime(utc_dt)

        moon = ssbodies['moon']

        astrometric = site.location.at(t).observe(moon).apparent()
        ra, dec, distance = astrometric.radec()

        def format_hms(h, m, s):
            return f"{int(h):02d}:{int(m):02d}:{s:04.1f}"

        def format_dms(sign, d, m, s):
            return f"{sign}{abs(int(d)):02d}:{int(m):02d}:{s:04.1f}"

        h, m, s = ra.hms()
        ra_str  = format_hms(h, m, s)

        sign_num, d, mm, ss = dec.signed_dms()
        sign = "+" if sign_num >= 0 else "-"
        dec_str = format_dms(sign, d, mm, ss)

        text = f"Moon at Midnight\nRa: {ra_str}\nDec: {dec_str}"
        self.logger.debug(f"text={text}")

        self.fig.text(x=[midnight_local_timezone], y=[0.5], text=[text], text_font_size="7pt",
                      text_align="center", text_baseline="bottom")

        self.logger.debug(f"done.......")

    def _draw_twilight(self, site, sunset, sunrise):
        """Shade civil, nautical, and astronomical twilight bands."""
        et6 = site.evening_twilight_6(sunset)
        et12 = site.evening_twilight_12(sunset)
        et18 = site.evening_twilight_18(sunset)
        mt18 = site.morning_twilight_18(sunset)
        mt12 = site.morning_twilight_12(sunset)
        mt6 = site.morning_twilight_6(sunset)

        twilight_zones = [
            ("Civil Twi", sunset, et6, mt6, sunrise, "orange", 0.4),
            ("Nautical Twi", et6, et12, mt12, mt6, "navy", 0.2),
            ("Astronomical Twi", et12, et18, mt18, mt12, "navy", 0.5),
        ]

        for name, ev_start, ev_end, mn_start, mn_end, color, alpha in twilight_zones:
            y_vals = [self.y_max, self.y_min, self.y_min, self.y_max]
            patch = self.fig.patch(
                x=[ev_start, ev_start, ev_end, ev_end],
                y=y_vals,
                fill_color=color, fill_alpha=alpha,
                line_color=color, line_alpha=alpha
            )
            patch2 = self.fig.patch(
                x=[mn_start, mn_start, mn_end, mn_end],
                y=y_vals,
                fill_color=color, fill_alpha=alpha,
                line_color=color, line_alpha=alpha
            )
            label = f"{name}: {ev_start.strftime('%H:%M:%S')} {mn_end.strftime('%H:%M:%S')}"
            self._append_legend_item(label, [patch])

    def _draw_sunset_sunrise(self, sunset, sunrise):
        """Draw dashed line at sunset and sunrise."""
        line1 = self.fig.line([sunset, sunset], [self.y_min, self.y_max], line_color='red', line_width=3, line_dash='dashed')
        line2 = self.fig.line([sunrise, sunrise], [self.y_min, self.y_max], line_color='red', line_width=3, line_dash='dashed')
        label = f"Sunset/rise {sunset.strftime('%H:%M:%S')} {sunrise.strftime('%H:%M:%S')}"
        self._append_legend_item(label, [line1, line2])

    def _sunset_sunrise(self, site):
        """Return sunset and sunrise datetimes for the site/date."""
        sunset = site.sunset(site.date)
        sunrise = site.sunrise(site.date)
        self.logger.debug(f"Sunset: {sunset}, Sunrise: {sunrise}")
        return sunset, sunrise

    def _append_legend_item(self, label, renderers):
        """Add legend item safely (create if needed)."""
        if self.fig.legend:
            leg = self.fig.legend.pop()
        else:
            leg = Legend(location='top_left', background_fill_color='white', background_fill_alpha=0.7)
            self.fig.add_layout(leg, 'below')

        leg.items.append(LegendItem(label=label, renderers=renderers))


if __name__ == '__main__':
    import logging

    logger = logging.getLogger()
    logger.setLevel('DEBUG')

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    toolbar_location = 'above'

    #subaru = observer.subaru
    site = get_site('subaru')

    local_tz = site.tz_local
    date = "2019-06-28"


    title = "Visibility for the night of {}".format(date)

    output_backend="webgl"
    fig_args = {"x_axis_type": "datetime",  "title": title, "tools": TOOLS, "toolbar_location": toolbar_location, "plot_height": 800, "plot_width": 900,} # "output_backend": "webgl"}

    plot = BasePlot(logger, **fig_args)


    start_time = datetime.strptime("2019-06-28 17:00:00", "%Y-%m-%d %H:%M:%S")
    start_time = start_time.replace(tzinfo=local_tz)
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
