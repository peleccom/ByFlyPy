# -*- coding: UTF-8 -*-

'''If Matplotlib not installed import this module fail'''
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
mpl.rcParams['font.sans-serif']="Tahoma, Arial, DejaVu Serif"
_Months={1:u'Января',2:u'Февраля',3:u'Марта',4:u'Апреля',5:u'Мая',6:u'Июня',7:u'Июля',8:u'Августа',9:u'Сентября',10:u'Октября',11:u'Ноября',12:u'Декабря'}
class Plotter(object):
    """
        Class for plotting
    """

    def __init__(self):
        pass
    def _get_traf_peaks(self,sessions):
        """traf in days of month"""
        x1={}
        BeginDate=datetime.datetime(sessions[0].begin.year,sessions[0].begin.month,1)  ## Can be 1-th day of month
        EndDate=datetime.datetime(sessions[-1].begin.year,sessions[-1].begin.month+1,1) ##first day of next month
        x=BeginDate
        maxday=calendar.monthrange(BeginDate.year,BeginDate.month)[1]
        for i in range(1,maxday+1):
            x1[i]=0
        for session in sessions:
            x1[session.begin.day]+=session.ingoing
        return [list(x1.keys()),list(x1.values()),maxday]
    def _get_time_peaks(self,sessions):
        """fill the month structure - tuple of x,y and maxday of month"""
        x1=[]  ## Day
        y1=[]   ##time of connectoin
        BeginDate=datetime.datetime(sessions[0].begin.year,sessions[0].begin.month,1)  ## Can be 1-th day of month
        EndDate=datetime.datetime(sessions[-1].begin.year,sessions[-1].begin.month+1,1) ##first day of next month
        x=BeginDate
        dx=datetime.timedelta(minutes=1)
        for session in sessions:
            while (x<session.end):
                if session.begin<x<session.end:
                    x1.append(x.day)
                    y1.append(x.hour+float(x.minute)/60)
                x+=dx
        maxday=calendar.monthrange(BeginDate.year,BeginDate.month)[1]
        result=[x1,y1,maxday]
        return result
    def PlotTimeAllocation(self,sessions,fname=None,title=None):
        if not sessions:
            return False
        timepeaks=self._get_time_peaks(sessions)
        plt.clf()
        plt.plot(timepeaks[0],timepeaks[1],'b.',linewidth=1,label=u'Время использования соединения')
        plt.grid(True)
        plt.xlabel(u"Дни %s"%(_Months[sessions[0].begin.month].lower()))
        plt.ylabel(u"Время")
        plt.legend(loc='best')
        plt.xticks(range(1,timepeaks[2]+1))
        plt.yticks(range(24))
        if title:
            plt.title(title)
        if fname:
            plt.savefig(fname)
        plt.show()
    def PlotTrafAllocation(self,sessions,fname=None,title=None):
            timepeaks=self._get_traf_peaks(sessions)
            plt.clf()
            plt.bar(timepeaks[0],timepeaks[1],label=u'Трафик за день')
            plt.grid(True)
            plt.xlabel(u"Дни %s"%(_Months[sessions[0].begin.month].lower()))
            plt.ylabel("MB")
            plt.legend(loc='best')
            plt.xticks(range(1,timepeaks[2]+1))
            plt.axes([1,timepeaks[2],0,1000])
            if title:
                plt.title(title)
            if fname:
                plt.savefig(fname)
            plt.show()