#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 26 21:19:53 2021

@author: liufeng
"""
# 各种要用到的地址
Normal_URL = 'https://authserver.hhu.edu.cn/authserver/login'
EasyPW_URL = 'http://ids.hhu.edu.cn/amserver/UI/Login?goto=http://form.hhu.edu.cn/pdc/form/list&gx_charset=UTF-8'
Healthy_List_URL = 'http://dailyreport.hhu.edu.cn/pdc/form/list'
LoginOut_URL = 'http://my.hhu.edu.cn/portal-web/oauth/logout'

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pymysql
import pytz,datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from time import sleep
##selenium判断某个元素是否存在
def isElementHere(Xpath,bro):
    isHere= True
    try:
        element = bro.find_element_by_xpath(Xpath)
    except:
        isHere = False
    return isHere
##SQL命令执行函数
def SQL_CMD(cursor,cmd):
    sqlcmd = cmd
    a = cursor.execute(sqlcmd)
    cursor.connection.commit()
    return
###########################################
# #isRightPW字段为1：正确密码
#isRightPW字段为2：错误密码
#EasyPW字段为0：不是简单密码
#EasyPW字段为1：是简单密码，但可以登录旧版门户
#EasyPW字段为2：是简单密码，不能登录旧版门户
###########################################
def Login(bro,user,passwd,cursor):
    # 先注销一次
    bro.get(LoginOut_URL)
    sleep(1)
    #######################################开始
    bro.get(Normal_URL)
    # 冻结ip处理
    if isElementHere('// *[ @ id = "msg"] / p', bro):
        print('IP has benn killed!')
        sleep(5 * 60)
        bro.get(Normal_URL)
    try:
        # 尝试正常密码登录
        name_text = WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="username"]')))
        name_text.send_keys(user)
        code_text = WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]')))
        code_text.send_keys(passwd)
        btn = WebDriverWait(bro, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="casLoginForm"]/p[5]/button')))
        btn.click()
        # 密码错误处理
        if (isElementHere('//*[@id="msg"]', bro) or isElementHere('//*[@id="captchaResponse"]', bro)):
            print('Wrong Password!')
            SQL_CMD(cursor, "update stu_info set isRightPW=2 where user=" + "\'" + user + "\';")
            return None
        else:
            SQL_CMD(cursor, "update stu_info set isRightPW=1 where user=" + "\'" + user + "\';")
        # 登陆成功打开打卡界面
        bro.get(Healthy_List_URL)
        # 判断是否是简单密码，是简单密码，需要去老版系统登录，但是错误多了会有验证码，所以先在新版系统试验密码是否正确，正确后直接就可以打卡。
        if isElementHere('/html/body/section/div/div/div[1]/div[2]/div/div/a', bro):
            bro.get(LoginOut_URL)
            print('Easy Password!')
            SQL_CMD(cursor, "update stu_info set isEasyPW=1 where user=" + "\'" + user + "\';")
            bro.get(EasyPW_URL)
            name_text = WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="IDToken1"]')))
            name_text.send_keys(user)
            code_text = WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="IDToken2"]')))
            code_text.send_keys(passwd)
            code_text.send_keys(Keys.ENTER)
            print('Login Success!')
            if isElementHere('/html/body/table/tbody/tr[2]/th/table[2]/tbody/tr[2]/td[2]/table/tbody/tr[2]/td/div/p/a',bro):
                SQL_CMD(cursor, "update stu_info set isEasyPW=2 where user=" + "\'" + user + "\';")
        else:
            # 正常登录，向数据率录入正确密码且不是简单密码
            SQL_CMD(cursor, "update stu_info set isEasyPW=0 where user=" + "\'" + user + "\';")
        return bro
    except Exception as e:
        print(e)
        return None

def ClockIn(bro,user,passwd,cursor):
    try:
        bro = Login(bro,user,passwd,cursor)
        if(bro):
            #防止超时，尝试五次
            #进行打卡
            times = 5
            while(times):
                try:
                    WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//section/section/div/a'))).click()
                    sleep(1)
                    WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="saveBtn"]'))).send_keys(Keys.ENTER)
                    times=0
                except Exception as e:
                    times = times -1
                    bro.get(EasyPW_URL)
                    print(times)
                    print(e)
            #检测是否打卡成功
            # 录入打卡时间
            sleep(1)
            if (WebDriverWait(bro, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="successSubmit"]/div[2]/h5')))):
                isOK = bro.find_element_by_xpath('//*[@id="successSubmit"]/div[2]/h5').text
                print(isOK)
                if(isOK=="你已成功提交，谢谢参与！"):
                    tz = pytz.timezone('Asia/Shanghai')
                    time = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
                    cmd = "update stu_info set time="+"\'"+time+"\'"+" where user="+"\'"+user+"\';"
                    SQL_CMD(cursor, cmd)
                    print('success')
                else:
                    print('failed')
            # 注销登录
            bro.get(LoginOut_URL)
    except Exception as e:
        print(e)




##设置chorme
options = Options()
options.add_argument("--headless")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
prefs = {
            'profile.default_content_setting_values': {
                'images': 2,
            }
        }
options.add_experimental_option('prefs', prefs)
bro = webdriver.Chrome(options=options)
bro.set_page_load_timeout(8)
bro.set_script_timeout(8)

#mysql参数

SQL_HOST='localhost'
SQL_USER = '******'
SQL_PWD = '*****'
SQL_DB = '************'
#打卡函数游标
connection1 = pymysql.connect(host=SQL_HOST,user=SQL_USER,password=SQL_PWD,db=SQL_DB,port=3306,charset='utf8')
cursor1 = connection1.cursor()

#获取全部数据

times =  10
while(times):
    times=times-1
    # 主函数游标
    connection = pymysql.connect(host=SQL_HOST, user=SQL_USER, password=SQL_PWD, db=SQL_DB, port=3306, charset='utf8')
    cursor = connection.cursor()
    count = cursor.execute('select * from stu_info;')
    cursor.connection.commit()
    #遍历数据
    NO = 1
    for i in range(count):
        results=cursor.fetchone()
        print('NO.'+str(NO)+':')
        print(results)
        NO=NO+1
        try:
            #当天打卡成功则不再打卡
            tz = pytz.timezone('Asia/Shanghai')
            if(results[3]==2 or results[4]==2):
                continue
            #以前打卡成功过
            if(results[2] is not None):
                recenttime = datetime.datetime.now(tz).strftime('%Y-%m-%d')
                lastesttime = results[2].strftime('%Y-%m-%d')
                if(lastesttime != recenttime):
                    sleep(10)
                    ClockIn(bro,results[0], results[1], cursor1)
            #第一次打卡
            if(results[2] is None):
                print(results)
                cursor.execute("delete from stu_info where user='"+results[0]+"' and passwd='"+results[1]+"';")
                cursor.connection.commit()
                cursor.execute("insert into stu_info (user,passwd)values('"+results[0].replace(" ","")+"','"+results[1].replace(" ","")+"');")
                cursor.connection.commit()
                sleep(10)
                ClockIn(bro,results[0].replace(" ", ""), results[1].replace(" ", ""), cursor1)
        except Exception as e:
            continue
    print('finish!')
#释放资源
connection.close()
connection1.close()
bro.quit()
