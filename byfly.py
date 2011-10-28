#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        byfly.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр 2011
#-------------------------------------------------------------------------------
#To install MatPlotLib in Debian/Ubuntu Linux run
# > sudo apt-get install python-matplotlib
try:
    import plotinfo
    Has_Matplot=True
except:
    print ("Warning: MatPlotlib not installed - Plotting not working.")
    Has_Matplot=False
import optparse
import time
import ByFlyUser
import sys
import sqlite3 as db
import getpass
import os.path
__VERSION__='2.0'
__FIGURE_FORMATS__=['png', 'pdf', 'svg','eps','ps']

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
p.set_defaults(
                interactive=False,
                graph=None,
                imagefilename=None
                )
if len(sys.argv)==1:
    p.print_help()
    sys.exit()
opt,args=p.parse_args()
if opt.interactive:
    try:
        a=True
        while a:
            a=raw_input("Login:")
            if a=='':
                print "Incorrect data"
                sys.exit(1)
            opt.login=a
            try:
                c=db.connect("users.db")
                c.row_factory = db.Row
                cu=c.cursor()
                cu.execute('SELECT * FROM USERS WHERE login=? or alias=?',[a,a])
                row=cu.fetchone()
                if row!=None:
                    print (u'Пароль взят из БД')
                    a=row['pass']
                    try:
                        ## если введенный логин не число то это алиас в базе данных
                        k=int(opt.login)
                    except:
                        opt.login=row['login']
                else:
                    a=None
            except Exception,e:
                print e.message
            finally:
                c.close()
            if a==None:
                a=getpass.getpass("Password:")
            if a=='':
                print "Incorrect data"
                sys.exit(1)
            opt.password=a
            if Has_Matplot:
                a=raw_input("Plot graph? [y/n]")
                if a=='y' or a=='Y':
                    opt.graph=True
                elif a=='n' or a=='N':
                    opt.graph=False
            user=ByFlyUser.ByFlyUser(opt.login,opt.password)
            if user.Login():
                user.PrintInfo()
                if opt.graph and Has_Matplot:
                    plt=plotinfo.Plotter()
                    plt.PlotTrafAllocation(user.GetLog(),title=user.info)
            else:
                print "Can't Log: "+user.LastError()
            a=raw_input("Print something if you want to continue")
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
            print("*"*40)
            user=ByFlyUser.ByFlyUser(lp[0],lp[2])
            if user.Login():
                user.PrintInfo()
                if opt.graph and Has_Matplot:
                    if opt.imagefilename:
                        fname=opt.imagefilename
                        # Заменим имя файла на логин
                        basename=os.path.basename(fname)
                        no_ext=basename.partition('.')[0]
                        fname=fname.replace(no_ext,lp[0])
                        show=False
                    else:
                        fname=False
                        show=True
                    plt=plotinfo.Plotter()
                    if opt.graph=='time':
                        plt.PlotTimeAllocation(user.GetLog(),title=user.info,fname=fname,show=show)
                    elif opt.graph=='traf':
                        plt.PlotTrafAllocation(user.GetLog(),title=user.info,fname=fname,show=show)
            else:
                print('%s- %s'%(lp[0],user.LastError()))
            print("*"*40+'\n')
    except IOError,e:
        print "%s"%e
else:
    if not opt.login:
        sys.exit()
    if not opt.password:
        sys.exit()
    user=ByFlyUser.ByFlyUser(opt.login,opt.password)
    if user.Login():
        user.PrintInfo()
        if opt.graph and Has_Matplot:
            if opt.imagefilename:
                fname=opt.imagefilename
                show=False
            else:
                fname=False
                show=true
            plt=plotinfo.Plotter()
            if opt.graph=='time':
                plt.PlotTimeAllocation(user.GetLog(),title=user.info,fname=fname,show=show)
            elif opt.graph=='traf':
                plt.PlotTrafAllocation(user.GetLog(),title=user.info,fname=fname,show=show)
    else:
        print "Can't Log: "+user.LastError()
