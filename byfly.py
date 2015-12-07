#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        byfly.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр -2011
#-------------------------------------------------------------------------------
#To install MatPlotLib in Debian/Ubuntu Linux run
# > sudo apt-get install python-matplotlib
import logging
import optparse
import time
import ByFlyUser
import sys
import sqlite3 as db
import getpass
import os.path
__VERSION__='3.1'
__FIGURE_FORMATS__=['png', 'pdf', 'svg','eps','ps']

__DEFAULT_DATABASE_FILENAME = 'users.db'


Has_Matplot=False

logger = logging.getLogger(__name__)


def pause():
    """Show 'press any key'"""
    raw_input("Press <Enter> to close")

def ImportPlot():
    global plotinfo
    global Has_Matplot
    if not sys.modules.has_key('plotinfo'):
        try:

            print("Enabling plotting. Wait a few seconds...")
            import plotinfo
            print("All OK. Plotting enabled")
            Has_Matplot=True

        except:
            print ("Warning: MatPlotlib not installed - Plotting not working.")

def PassFromDB(login):
    """Get password from database file. Return password or None """
    import database
    try:
        db_manager = database.DBManager(database.Table(DATABASE_FILENAME))
        res = db_manager.get_password(login)
        if res:
            opt.login = res[0]
            return res[1]
        else:
            return None
    except Exception,e:
        print e
        return None

def UI(opt,showgraph=None):
    '''Output all information. If showgraph=='always' graph show and save to file'''
    if opt.graph:
        ImportPlot()
    user=ByFlyUser.ByFlyUser(opt.login,opt.password)
    if user.login():
        user.print_info()
        return
        # user.PrintAdditionInfo()
        if opt.graph and Has_Matplot:
            plt=plotinfo.Plotter()
            if  opt.imagefilename:
                fname=opt.imagefilename
                show=False
            else:
                show=True
                fname=None
            if showgraph=='always':
                show=True
            if opt.graph=='time':
                plt.PlotTimeAllocation(user.GetLog(),title=user.info,show=show,fname=fname)
            elif opt.graph=='traf':
                plt.PlotTrafAllocation(user.GetLog(),title=user.info,show=show,fname=fname)
    else:
        print "Can't Log: "+user.LastError()

def checkimagefilename(option, opt_str, value, parser):
    '''Check image format'''
    if not value:
        raise optparse.OptionValueError("option -s: Can't use without parameter")
    if not parser.values.graph:
        raise optparse.OptionValueError("option -s: Can't use without -g")
    if [value for ext in __FIGURE_FORMATS__ if value.endswith(ext)]:
        parser.values.imagefilename=value
    else:
        raise optparse.OptionValueError("option -s: Not correct file format. Use formats: %s"%__FIGURE_FORMATS__)

p=optparse.OptionParser(description=u'Проверка баланса ByFly',prog='ByFlyPy',version=u'%%prog %s'%__VERSION__)
p.add_option("-i",action="store_true",dest="interactive",help="Enable interactive mode")
p.add_option("-l","--login",action="store",type="string",dest="login",help='Login')
p.add_option("--list",type="string",dest="check_list",metavar='<filename>',help="Check accounts in file. Each line of file must be login:password")
p.add_option("-p","--p",action="store",type="string",dest="password",help='Password')
p.add_option("-g","--graph",action="store",dest="graph",type='choice',help="Plot a graph. Parameters MUST BE traf or time ",choices=['traf','time'])
p.add_option("-s","--save",action='callback',help='save graph to file',callback=checkimagefilename,type='string')
p.add_option("-n", "--nologo", action='store_true', dest='nologo' , help="Don't show logo at startup")
p.add_option("--pause",action="store_true", dest="pause", help="Don't close console window immediately")
p.add_option("--debug", action="store", type="choice", dest="debug" , choices=['yes','no'], help="Debug yes/no")
p.add_option("--db", action="store", type="string", dest="db" , help="Database filename")
p.set_defaults(
                interactive=False,
                graph=None,
                imagefilename=None,
                nologo = False,
                debug = False
                )


# print help
if len(sys.argv)==1:
    p.print_help()
    sys.exit()

opt,args=p.parse_args()

# Enable/Disable Debug mode
if opt.debug == "yes":
    opt.debug = True
elif opt.debug == "no":
    opt.debug = False
ByFlyUser._DEBUG_ = opt.debug
log_level = logging.DEBUG if opt.debug else logging.ERROR
logging.basicConfig(stream=sys.stdout, level=log_level)


#pause at exit?
if opt.pause:
    import atexit
    atexit.register(pause)

if not opt.nologo:
    p.print_version()
if opt.db:
    DATABASE_FILENAME = opt.db
else:
    DATABASE_FILENAME = __DEFAULT_DATABASE_FILENAME
if opt.interactive:
    try:
        a=True
        while a:
            a=raw_input("Login:")
            if a=='':
                print "Incorrect data"
                sys.exit(1)
            opt.login=a
            a = PassFromDB(opt.login)
            if a==None:
                a=getpass.getpass("Password:")
            if a=='':
                print "Incorrect data"
                sys.exit(1)
            opt.password=a
            ImportPlot()
            if Has_Matplot:
                a=raw_input("Plot graph? [y/n]")
                if a=='y' or a=='Y':
                    opt.graph=True
                    a=raw_input("Which kind of graph [time/traf]")
                    if a=='time':
                        opt.graph='time'
                    elif a=='traf':
                        opt.graph='traf'
                elif a=='n' or a=='N':
                    opt.graph=False
            UI(opt)
            cont = False
            while(True):
                a=raw_input("Continue with another login [y/n]?")
                if a == 'y':
                    cont = True
                    break
                elif a== 'n':
                    cont = False
                    break
            if cont:
                continue
            else:
                break
    except Exception,e:
        print e
        sys.exit(1)

elif opt.check_list:
    try:
        list=open(opt.check_list,'rt')
        for line in list:
            lp=line.strip().partition(':')
            if lp[2]=='':
                continue
            print(lp[0].center(40,'*'))
            opt.login=lp[0]
            opt.password=lp[2]
            if opt.imagefilename:
                fname=opt.imagefilename
                # Заменим имя файла на логин
                basename=os.path.basename(fname)
                no_ext=basename.partition('.')[0]
                fname=fname.replace(no_ext,lp[0])
                show=False
            else:
                fname=None
                show=True
            opt.imagefilename=fname
            UI(opt)
            print("".center(40,'*')+'\n')
    except IOError,e:
        print "%s"%e
else:
    if not opt.login:
        sys.exit()
    if not opt.password:
        opt.password = PassFromDB(opt.login)
        if not opt.password:
            sys.exit()
    #command line
    UI(opt)
