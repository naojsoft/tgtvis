from __future__ import print_function

from datetime import datetime, timedelta
import numpy

from matplotlib.figure import SubplotParams
from matplotlib.patches import Circle
from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, DrawingArea, HPacker

import matplotlib.dates as mpl_dt
import matplotlib as mpl
from matplotlib.ticker import FormatStrFormatter

from qplan.plots import airmass

from ginga.misc import Bunch


class AirMassPlot2(airmass.AirMassPlot):

    def __init__(self, width, height, logger=None):
        super(AirMassPlot2, self).__init__(width=width, height=height,
                                          logger=logger)


    def plot_altitude(self, site, tgt_data, tz):
        self._plot_altitude(self.fig, site, tgt_data, tz)


    def _plot_altitude(self, figure, site, tgt_data, tz):
        """
        Plot into `figure` an altitude chart using target data from `info`
        with time plotted in timezone `tz` (a tzinfo instance).
        """
        ## site = info.site
        ## tgt_data = info.target_data
        # Urk! This seems to be necessary even though we are plotting
        # python datetime objects with timezone attached and setting
        # date formatters with the timezone
        tz_str = tz.tzname(None)
        mpl.rcParams['timezone'] = tz_str

        # set major ticks to hours
        majorTick = mpl_dt.HourLocator(tz=tz)
        majorFmt = mpl_dt.DateFormatter('%Hh')
        # set minor ticks to 15 min intervals
        minorTick = mpl_dt.MinuteLocator(list(range(0,59,15)), tz=tz)

        figure.clf()
        ax1 = figure.add_subplot(111)
        figure.set_tight_layout(False)
        figure.subplots_adjust(left=0.05, right=0.65, bottom=0.12, top=0.95)  

        #lstyle = 'o'
        lstyle = '-'
        lt_data = list(map(lambda info: info.ut.astimezone(tz),
                      tgt_data[0].history))
        # sanity check on dates in preferred timezone
        ## for dt in lt_data[:10]:
        ##     print(dt.strftime("%Y-%m-%d %H:%M:%S"))


        min_interval = 12  # hour/5min
        mt = lt_data[0:-1:min_interval]
        targets = []
        legend = [] 


        # plot targets elevation vs. time
        for i, info in enumerate(tgt_data):
            alt_data = numpy.array(list(map(lambda info: info.alt_deg, info.history)))
            alt_min = numpy.argmin(alt_data)
            alt_data_dots = alt_data
            color = self.colors[i % len(self.colors)]
            lc = color + lstyle
            # ax1.plot_date(lt_data, alt_data, lc, linewidth=1.0, alpha=0.3, aa=True, tz=tz)
            ax1.plot_date(lt_data, alt_data_dots, lc, linewidth=2.0,
                          aa=True, tz=tz)

            legend.extend(ax1.plot_date(lt_data, alt_data_dots, lc, linewidth=2.0,aa=True, tz=tz))   
            targets.append("{0} {1} {2}".format(info.target.name, info.target.ra, info.target.dec))

            alt_interval = alt_data[0:-1:min_interval]
            moon_sep = numpy.array(map(lambda info: info.moon_sep, info.history))
            moon_sep = moon_sep[0:-1:min_interval]

            # plot moon separations 
            for x, y, v in zip(mt, alt_interval, moon_sep):
                if y < 0:
                    continue
                ax1.text(x, y, '%.1f' %v, fontsize=7,  ha='center', va='bottom')
                ax1.plot_date(x, y, 'ko', ms=3)

            #xs, ys = mpl.mlab.poly_between(lt_data, 2.02, alt_data)
            #ax1.fill(xs, ys, facecolor=self.colors[i], alpha=0.2)

            # plot object label
            targname = info.target.name
            ax1.text(mpl_dt.date2num(lt_data[alt_data.argmax()]),
                     alt_data.max() + 4.0, targname, color=color,
                     ha='center', va='center')



        # legend moon distance
        box1 = TextArea("Moon distance(deg)   ", textprops=dict(color="k", size=7.5))
        box2 = DrawingArea(48, 10, 0, 0)
        circle1 = Circle((5, 5), 2.3, fc="k", ec=None)
        box2.add_artist(circle1)
        box = HPacker(children=[box2, box1], align="center", pad=2.5, sep=-35)
        args = dict(alpha=0.5,)
        anchored_box = AnchoredOffsetbox(loc=3,
                                 child=box, pad=0.,
                                 frameon=True,
                                 bbox_to_anchor=(0.009, 0.9630), #(0.25, -0.140)
                                 bbox_transform=ax1.transAxes,
                                         borderpad=0.)
        ax1.add_artist(anchored_box)
        #x = mpl_dt.date2num(lt_data[len(lt_data)/2])

         # legend target list
        self.fig.legend(legend, sorted(targets), 'upper right', fontsize=9, framealpha=0.5, frameon=True, ncol=1, bbox_to_anchor=[0.3, 0.865, .7, 0.1])


        ax1.set_ylim(0.0, 90.0)
        ax1.set_xlim(lt_data[0], lt_data[-1])
        ax1.xaxis.set_major_locator(majorTick)
        ax1.xaxis.set_minor_locator(minorTick)
        ax1.xaxis.set_major_formatter(majorFmt)
        labels = ax1.get_xticklabels()
        ax1.grid(True, color='#999999')

        # label axes
        localdate = lt_data[0].astimezone(tz).strftime("%Y-%m-%d")
        title = 'Visibility for the night of %s' % (localdate)
        ax1.set_title(title)
        ax1.set_xlabel(tz.tzname(None))
        ax1.set_ylabel('Altitude')

        # Plot moon trajectory and illumination
        moon_data = numpy.array(list(map(lambda info: info.moon_alt,
                                    tgt_data[0].history)))
        illum_time = lt_data[moon_data.argmax()]
        moon_illum = site.moon_phase(date=illum_time)
        moon_color = '#666666'
        moon_name = "Moon (%.2f %%)" % (moon_illum*100)
        ax1.plot_date(lt_data, moon_data, moon_color, linewidth=2.0,
                      alpha=0.5, aa=True, tz=tz)
        ax1.text(mpl_dt.date2num(illum_time),
                 moon_data.max() + 4.0, moon_name, color=moon_color,
                 ha='center', va='center')

        # Plot airmass scale
        altitude_ticks = numpy.array([20, 30, 40, 50, 60, 70, 80, 90])
        airmass_ticks = 1.0/numpy.cos(numpy.radians(90 - altitude_ticks))
        airmass_ticks = list(map(lambda n: "%.3f" % n, airmass_ticks))

        ax2 = ax1.twinx()
        #ax2.set_ylim(None, 0.98)
        #ax2.set_xlim(lt_data[0], lt_data[-1])
        ax2.set_yticks(altitude_ticks)
        ax2.set_yticklabels(airmass_ticks)
        ax2.set_ylim(ax1.get_ylim())
        ax2.set_ylabel('Airmass')
        ax2.set_xlabel('')
        ax2.yaxis.tick_right()

        ## mxs, mys = mpl.mlab.poly_between(lt_data, 0, moon_data)
        ## # ax2.fill(mxs, mys, facecolor='#666666', alpha=moon_illum)

        # plot moon label
        targname = "moon"
        ## ax1.text(mpl_dt.date2num(moon_data[moon_data.argmax()]),
        ##          moon_data.max() + 0.08, targname.upper(), color=color,
        ##          ha='center', va='center')

        # plot lower and upper safe limits for clear observing
        min_alt, max_alt = 30.0, 75.0
        self._plot_limits(ax1, min_alt, max_alt)

        self._plot_twilight(ax1, site, tz)

        # plot current hour
        lo = datetime.now(tz)
        hi = lo + timedelta(0, 3600.0)
        if lt_data[0] < lo < lt_data[-1]:
            self._plot_current_time(ax1, lo, hi)

        canvas = self.fig.canvas
        if canvas is not None:
            canvas.draw()

        # draw target's name
        #for t in tgt_data:
        #    tgt = "{2} {0} {1}".format(t.target.ra, t.target.dec, t.target.name)
        #    ax1.text(0, -1, tgt)


    def _plot_twilight(self, ax, site, tz):
        # plot sunset
        t = site.sunset().astimezone(tz)

        # plot evening twilight 6/12/18 degrees
        et6 = site.evening_twilight_6(t).astimezone(tz)
        et12 = site.evening_twilight_12(t).astimezone(tz)
        et18 = site.evening_twilight_18(t).astimezone(tz)

        #n, n2 = list(map(mpl_dt.date2num, [t, t2]))
        ymin, ymax = ax.get_ylim()

        # civil twilight 6 degree
        ct = ax.axvspan(t, et6, facecolor='#FF6F00', lw=None, ec='none', alpha=0.35)
        # nautical twilight 12 degree
        nt = ax.axvspan(et6, et12, facecolor='#947DC0', lw=None, ec='none', alpha=0.5)
        # astronomical twilight 18 degree
        at = ax.axvspan(et12, et18, facecolor='#3949AB', lw=None, ec='none', alpha=0.65)

        ss = ax.vlines(t, ymin, ymax, colors=['red'],
                   linestyles=['dashed'], label='Sunset')

        sunset = "Sunset {}".format(t.strftime("%H:%M:%S"))
        civil_twi = "Civil Twi {}".format(et6.strftime("%H:%M:%S"))
        nautical_twi = "Nautical Twi {}".format(et12.strftime("%H:%M:%S"))
        astro_twi = "Astronomical Twi {}".format(et18.strftime("%H:%M:%S"))

        self.fig.legend((ss, ct, nt, at), (sunset, civil_twi, nautical_twi, astro_twi), 'upper left', fontsize=7,  framealpha=0.5,  bbox_to_anchor=[0.045, -0.02, .7, 0.113])
        #self.ax3.legend((ss, etw), (sunset, e_twilight), 'upper left', fontsize='small',  framealpha=0.5)

        # plot morning twilight 6/12/18 degrees
        mt6 = site.morning_twilight_6(et6).astimezone(tz)
        mt12 = site.morning_twilight_12(et12).astimezone(tz)
        mt18= site.morning_twilight_18(et18).astimezone(tz)

        # plot sunrise
        t2 = site.sunrise(mt18).astimezone(tz)

        # astronomical twilight 18 degree
        at = ax.axvspan(mt18, mt12, facecolor='#3949AB', lw=None, ec='none', alpha=0.65)

        # nautical twilight 12 degree
        nt = ax.axvspan(mt12, mt6, facecolor='#947DC0', lw=None, ec='none', alpha=0.5)

        # civil twilight 6 degree
        ct = ax.axvspan(mt6, t2, facecolor='#FF6F00', lw=None, ec='none', alpha=0.35)

        sr = ax.vlines(t2, ymin, ymax, colors=['red'],
                   linestyles=['dashed'], label='Sunrise')

        sunrise = "Sunrise {}".format(t2.strftime("%H:%M:%S"))
        civil_twi = "Civil Twi {}".format(mt6.strftime("%H:%M:%S"))
        nautical_twi = "Nautical Twi {}".format(mt12.strftime("%H:%M:%S"))
        astro_twi = "Astronomical Twi {}".format(mt18.strftime("%H:%M:%S"))

        self.fig.legend((sr, ct, nt, at), (sunrise, civil_twi, nautical_twi, astro_twi), fontsize=7,  framealpha=0.5, bbox_to_anchor=[-0.043, -0.02, .7, 0.113])

        # night center
        night_center = et18 + ((mt18-et18)/2)
        ax.vlines(night_center, ymin, ymax, colors='blue',
                  linestyles='dashed', label='Mid Point')

    def _plot_current_time(self, ax, lo, hi):
        ax.axvspan(lo, hi, facecolor='#7FFFD4', alpha=0.25)

    def _plot_limits(self, ax, lo_lim, hi_lim):
        ymin, ymax = ax.get_ylim()
        ax.axhspan(ymin, lo_lim, facecolor='#F9EB4E', alpha=0.20)

        ax.axhspan(hi_lim, ymax, facecolor='#F9EB4E', alpha=0.20)


if __name__ == '__main__':
    import sys
    from qplan import entity, common
    from qplan.util.site import get_site

    from ginga import toolkit
    toolkit.use('qt')

    from ginga.gw import Widgets, Plot
    plot = AirMassPlot2(1200, 740)

    outfile = None
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    if outfile == None:
        app = Widgets.Application()
        topw = app.make_window()
        plotw = Plot.PlotWidget(plot)
        topw.set_widget(plotw)
        topw.add_callback('close', lambda w: w.delete())
    else:
        from ginga.aggw import Plot
        plotw = Plot.PlotWidget(plot)

    plot.setup()
    site = get_site('subaru')
    tz = site.tz_local

    start_time = datetime.strptime("2015-03-30 18:30:00", "%Y-%m-%d %H:%M:%S")
    start_time = tz.localize(start_time)
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
    plot.plot_altitude(site, target_data, tz)

    if outfile == None:
        topw.show()
    else:
        plot.fig.savefig(outfile)

    app.mainloop()

#END
