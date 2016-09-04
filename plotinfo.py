# -*- coding: UTF-8 -*-
# -------------------------------------------------------------------------------
# Name:        plotinfo.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр 2011
# -------------------------------------------------------------------------------
try:
    import matplotlib.pylab as plt
    import matplotlib as mpl
except:
    raise ImportError
import calendar
import datetime
##mpl.rcParams['font.serif']="Verdana, Arial"
##mpl.rcParams['font.cursive']="Courier New, Arial"
##mpl.rcParams['font.fantasy']="Comic Sans MS, Arial"
##mpl.rcParams['font.monospace']="Arial"
mpl.rcParams['font.sans-serif'] = "Tahoma, Arial, DejaVu Serif"
_Months = {1: u'Января', 2: u'Февраля', 3: u'Марта', 4: u'Апреля', 5: u'Мая', 6: u'Июня', 7: u'Июля', 8: u'Августа',
           9: u'Сентября', 10: u'Октября', 11: u'Ноября', 12: u'Декабря'}


def _getweekends(date):
    '''Get date and return list of weekeds in this month'''
    if not type(date) == datetime.datetime:
        return
    try:
        for i in range(1, 32):
            day = date.replace(day=i)
            if day.weekday() > 4:
                yield i
    except:
        return


class Plotter(object):
    """
        Class for plotting
    """

    def __init__(self):
        pass

    def _get_traf_peaks(self, sessions):
        """traf in days of month"""
        x1 = {}
        BeginDate = datetime.datetime(sessions[0].begin.year, sessions[0].begin.month, 1)  ## Can be 1-th day of month
        year_add = 1 if sessions[-1].begin.month == 12 else 0
        EndDate = datetime.datetime(sessions[-1].begin.year + year_add, (sessions[-1].begin.month + 1) % 12,
                                    1)  ##first day of next month
        x = BeginDate
        maxday = calendar.monthrange(BeginDate.year, BeginDate.month)[1]
        for i in range(1, maxday + 1):
            x1[i] = 0
        for session in sessions:
            x1[session.begin.day] += session.ingoing
        return [list(x1.keys()), list(x1.values()), maxday]

    def _get_time_peaks(self, sessions):
        """fill the month structure - tuple of x,y and maxday of month"""
        x1 = []  ## Day
        y1 = []  ##time of connectoin
        BeginDate = datetime.datetime(sessions[0].begin.year, sessions[0].begin.month, 1)  ## Can be 1-th day of month
        year_add = 1 if sessions[-1].begin.month == 12 else 0
        EndDate = datetime.datetime(sessions[-1].begin.year + year_add, (sessions[-1].begin.month + 1) % 12,
                                    1)  ##first day of next month
        x = BeginDate
        dx = datetime.timedelta(minutes=1)
        for session in sessions:
            while (x < session.end):
                if session.begin < x < session.end:
                    x1.append(x.day)
                    y1.append(x.hour + float(x.minute) / 60)
                x += dx
        maxday = calendar.monthrange(BeginDate.year, BeginDate.month)[1]
        result = [x1, y1, maxday]
        return result

    def plot_time_allocation(self, sessions, fname=None, title=None, show=True):
        if not sessions:
            return False
        timepeaks = self._get_time_peaks(sessions)
        plt.clf()
        plt.plot(timepeaks[0], timepeaks[1], 'b.', linewidth=1, label=u'Время использования соединения')
        plt.grid(True)
        plt.xlabel(u"Дни %s" % (_Months[sessions[0].begin.month].lower()))
        plt.ylabel(u"Время")
        plt.legend(loc='best')
        _, la = plt.xticks(range(1, timepeaks[2] + 1))
        for i in _getweekends(sessions[0].begin):
            la[i - 1].set_backgroundcolor('red')
        plt.yticks(range(24))
        if title:
            plt.title(title)
        if fname:
            try:
                plt.savefig(fname)
            except Exception, e:
                print "Exception: %s" % e
        if show:
            plt.show()

    def plot_traf_allocation(self, sessions, fname=None, title=None, show=True):
        if not sessions:
            return False
        timepeaks = self._get_traf_peaks(sessions)
        # plt.clf()
        fig = plt.figure()
        ax = fig.add_subplot(111)
        for i, j in enumerate(timepeaks[0]):
            timepeaks[0][i] = j - 0.5
        rects = ax.bar(timepeaks[0], timepeaks[1], width=0.5, label=u'Трафик за день')
        # Создаем подписи для файлов
        for i, rect in enumerate(rects):
            height = rect.get_height()
            traf = timepeaks[1][i]
            if traf == 0:
                continue
            ax.text(rect.get_x() + rect.get_width() / 1.5, 1.05 * height, '%.2f' % traf,
                    ha='center', va='bottom', rotation='vertical', color='green')
        ax.grid(True)
        plt.xlabel(u"Дни %s" % (_Months[sessions[0].begin.month].lower()))
        plt.ylabel("MB")
        ax.legend(loc='best')
        _, la = plt.xticks(range(1, timepeaks[2] + 1))
        for i in _getweekends(sessions[0].begin):
            la[i - 1].set_backgroundcolor('red')
        if title:
            plt.title(title)
        if fname:
            try:
                plt.savefig(fname)
            except Exception, e:
                print "Exception: %s" % e
        if show:
            plt.show()
