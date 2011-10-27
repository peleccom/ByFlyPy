# -*- coding: utf-8 -*-
try:
    import plotinfo
    Has_Matplot=True
except:
    Has_Matplot=False
import optparse
import time
import ByFlyUser
import sys
import sqlite3 as db
import getpass
p=optparse.OptionParser()
#
##u=ByFlyUser.ByFlyUser('','')
##sessions=u.GetLog(fromfile='c:\\tmp\\1.csv')
##plt=plotinfo.Plotter()
##plt.PlotTimeAllocation(sessions[::-1],title=u'Всякая фигня')
##print u.LastError()
##sys.exit()
#
p.add_option("-i",action="store_true",dest="interactive",help="Enable interactive mode")
p.add_option("-l","--login",action="store",type="string",dest="login")
p.add_option("--list",type="string",dest="check_list",metavar='<filename>',help="Check accounts in file. Each line of file must be login:password")
p.add_option("-p","--p",action="store",type="string",dest="password")
p.add_option("-g","--graph",action="store_true",dest="graph",help="Plot a graph")
p.set_defaults(
                interactive=False,
                graph=False
                )
if len(sys.argv)==1:
    p.print_help()
    sys.exit()
opt,args=p.parse_args()
dir(opt)
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
                if opt.graph:
                    plt=plotinfo.Plotter()
                    plt.PlotTrafAllocation(user.GetLog(),title=user.info)
            else:
                print "Can't Log: "+user.LastError()
            a=raw_input("Print something if you want to continue")
    except Exception,e:
        print e
        sys.exit(1)
else:
    if not opt.login:
        sys.exit()
    if not opt.password:
        sys.exit()
    user=ByFlyUser.ByFlyUser(opt.login,opt.password)
    if user.Login():
        user.PrintInfo()
        if opt.graph:
            plt=plotinfo.Plotter()
            plt.PlotTimeAllocation(user.GetLog(),title=user.info)
            print plt._get_traf_peaks(user.GetLog())
            #plt.PlotTrafAllocation(user.GetLog())
    else:
        print "Can't Log: "+user.LastError()