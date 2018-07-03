ByFlyPy
================
[![Build Status](https://travis-ci.org/peleccom/ByFlyPy.svg?branch=master)](https://travis-ci.org/peleccom/ByFlyPy)
[![codecov](https://codecov.io/gh/peleccom/ByFlyPy/branch/master/graph/badge.svg)](https://codecov.io/gh/peleccom/ByFlyPy)

Tiny program and class to check ByFly (*The belarus biggest ICS provider*) account balance, get user information, plot some information

Маленькая программа и класс для проверки баланса аккаунта ByFly, получения информации и построения некоторых графиков

Class usage:

        from byflyuser import ByFlyUser

        user = ByFlyUser("login", "password")

        # connect to server and login
        user.login()

        info = user.get_account_info_page()

        #  print account info
        print(info.full_name)
        print(info.balance)
        

CLI usage:

        python byfly.py -l <your_login_number> -p <your_password>


