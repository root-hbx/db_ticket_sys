# -*- coding: utf-8 -*-
# @Author: XXG
# @Date:   2024-06-07 09:14:20
# @Last Modified by:   XXG
# @Last Modified time: 2024-06-07 10:52:40
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from .forms import PassengerInfoForm, UserForm
from .models import Flight, Order
from .classes import IncomeMetric
from .classes import Order as ClassOrder
from django.contrib.auth.models import Permission, User
import datetime, pytz
from operator import attrgetter
from django.utils import timezone

ADMIN_ID = 1


# 管理员后台财务管理
# 统计航空公司每周、每月，每年营业收入情况。
def admin_finance(request):
    all_Trains = Flight.objects.all()
    all_Trains = sorted(all_Trains, key=attrgetter('leave_time'))  # 将所有车次按照出发时间排序

    # 将车次每天的输入打上不同的时间标签 [周，月，日]
    week_day_incomes = []
    month_day_incomes = []
    year_day_incomes = []

    # 用set存储所有的 周，月，年
    week_set = set()
    month_set = set()
    year_set = set()
    for flight in all_Trains:
        if flight.income > 0:  # 只统计有收入的车次
            # 打上周标签
            this_week = flight.leave_time.strftime('%W')  # datetime获取周
            week_day_incomes.append((this_week, flight.income))  # 添加元组(week, income)
            week_set.add(this_week)
            # 打上月标签
            this_month = flight.leave_time.strftime('%m')  # datetime获取月
            month_day_incomes.append((this_month, flight.income))  # 添加元组(month, income)
            month_set.add(this_month)
            # 打上年标签
            this_year = flight.leave_time.strftime('%Y')  # datetime获取年
            year_day_incomes.append((this_year, flight.income))  # 添加元组(year, income)
            year_set.add(this_year)

    # 存储每周收入
    # 将每周的收入用 IncomeMetric 类型存储在 week_incomes List中
    week_incomes = []
    for week in week_set:
        income = sum(x[1] for x in week_day_incomes if x[0] == week)  # 同周次的income求和
        flight_sum = sum(1 for x in week_day_incomes if x[0] == week)  # 同周次的车次总数目
        week_income = IncomeMetric(week, flight_sum, income)  # 将数据存储到IncomeMetric类中，方便jinja语法
        week_incomes.append(week_income)
    week_incomes = sorted(week_incomes, key=attrgetter('metric'))  # 将List类型的 week_incomes 按周次升序排列

    # 存储每月收入
    # 将每月的收入用 IncomeMetric 类型存储在 month_incomes List中
    month_incomes = []
    for month in month_set:
        income = sum(x[1] for x in month_day_incomes if x[0] == month)
        flight_sum = sum(1 for x in month_day_incomes if x[0] == month)
        month_income = IncomeMetric(month, flight_sum, income)
        month_incomes.append(month_income)
    month_incomes = sorted(month_incomes, key=attrgetter('metric'))  # 将List类型的 month_incomes 按月份升序排列

    # 存储每年收入
    # 将每年的收入用 IncomeMetric 类型存储在 year_incomes List中
    year_incomes = []
    for year in year_set:
        income = sum(x[1] for x in year_day_incomes if x[0] == year)
        flight_sum = sum(1 for x in year_day_incomes if x[0] == year)
        year_income = IncomeMetric(year, flight_sum, income)
        year_incomes.append(year_income)
    year_incomes = sorted(year_incomes, key=attrgetter('metric'))  # 将List类型的 year_incomes 按年份升序排列

    # 存储order信息
    passengers = User.objects.exclude()  # 去掉管理员
    order_set = set()
    for p in passengers:
        # Trains = Flight.objects.filter(user=p)
        # for f in Trains:
        #     route = f.leave_city + ' → ' + f.arrive_city
        #     order = ClassOrder(p.username, f.name, route, f.leave_time, f.price)
        #     order_set.add(order)
        orders = Order.objects.filter(user=p)
        for o in orders:
            route = o.flight.leave_city + ' → ' + o.flight.arrive_city
            if o.is_pay:
                pay_information = '已支付'
            else :
                pay_information = '未支付'
            if o.is_fetch:
                fetch_information = '已取票'
            else :
                fetch_information = '未取票'
            if o.is_refund:
                refund_information = '已退票'
            else :
                refund_information = '未退票'
            order = ClassOrder(p.username, o.creat_time, o.flight.name, route, 
                o.flight.leave_time, o.flight.price,
                pay_information, fetch_information, refund_information)
            order_set.add(order)

    # 信息传给前端
    context = {
        'week_incomes': week_incomes,
        'month_incomes': month_incomes,
        'year_incomes': year_incomes,
        'order_set': order_set
    }
    return context


# 显示用户订单信息
# 车次信息，退票管理
def user_operation(request):
    if request.user.is_authenticated:
        # 如果用户是管理员，render公司车次收入统计信息页面 admin_finance
        # if request.user.id == ADMIN_ID:
        #     #context = admin_finance(request)  # 获取要传入前端的数据
        #     context = admin_finance(request)
        #     return render(request, 'booksystem/admin_finance.html', context)
        # 如果用户是普通用户，render用户的车票信息 user_info
        # else:
            booked_Trains = Flight.objects.filter(user=request.user)  # 从 booksystem_flight_user 表过滤出该用户订的车次
            context = {
                'booked_Trains': booked_Trains,
                'username': request.user.username,  # 导航栏信息更新
            }
            return render(request, 'booksystem/user_operation.html', context)
    return render(request, 'booksystem/login.html')  # 用户如果没登录，render登录页面

#个人账单
def user_bill(request):
    if request.user.is_authenticated:
        # 如果用户是管理员，render公司车次收入统计信息页面 admin_finance
        if request.user.id == ADMIN_ID:
            #context = admin_finance(request)  # 获取要传入前端的数据
            context = admin_finance(request)
            return render(request, 'booksystem/admin_finance.html', context)
        # 如果用户是普通用户，render用户的车票信息 user_info
        else:
            order_set = set()
            # Trains = Flight.objects.filter(user=request.user)
            orders = Order.objects.filter(user=request.user)
            for o in orders:
                route = o.flight.leave_city + ' → ' + o.flight.arrive_city
                if o.is_pay:
                    pay_information = '已支付'
                else :
                    pay_information = '未支付'
                if o.is_fetch:
                    fetch_information = '已取票'
                else :
                    fetch_information = '未取票'
                if o.is_refund:
                    refund_information = '已退票'
                else :
                    refund_information = '未退票'
                order = ClassOrder(request.user.username, o.creat_time, o.flight.name, route, 
                    o.flight.leave_time, o.flight.price,
                    pay_information, fetch_information, refund_information)
                order_set.add(order)
            # booked_Trains = Flight.objects.filter(user=request.user)  # 从 booksystem_flight_user 表过滤出该用户订的车次
            context = {
                'order_set': order_set,
                'username': request.user.username,  # 导航栏信息更新
            }
            return render(request, 'booksystem/user_bill.html', context)
    return render(request, 'booksystem/login.html')  # 用户如果没登录，render登录页面

# 主页
# 欢迎页面性质的订票页面
def index(request):
    return render(request, 'booksystem/index.html')


# 免除csrf
@csrf_exempt
def book_ticket(request, flight_id):
    if not request.user.is_authenticated:  # 如果没登录就render登录页面
        return render(request, 'booksystem/login.html')
    else:
        flight = Flight.objects.get(pk=flight_id)
        # 查看乘客已经订购的Trains
        booked_Trains = Flight.objects.filter(user=request.user)  # 返回 QuerySet

        if flight in booked_Trains:
            return render(request, 'booksystem/book_conflict.html')

        # book_flight.html 点确认之后，request为 POST 方法，虽然没有传递什么值，但是传递了 POST 信号
        # 确认订票，flight数据库改变

        # 验证一下，同样的车票只能订一次
        if request.method == 'POST':
            if flight.capacity > flight.book_sum:
                flight.book_sum += 1
                # flight.capacity -= 1
                flight.income += flight.price
                flight.user.add(request.user)
                flight.save()  # 一定要记着save
                order = Order()
                order.user = request.user
                order.flight = flight
                order.save()
        # 传递更改之后的票务信息
        context = {
            'flight': flight,
            'username': request.user.username,
            'surplus' : flight.capacity - flight.book_sum
        }
        return render(request, 'booksystem/book_flight.html', context)


# 退票
def refund_ticket(request, flight_id):
    flight = Flight.objects.get(pk=flight_id)
    order = Order.objects.filter(user = request.user)
    for o in order:
        if o.can_modify == True and o.flight == flight and o.is_refund != True and o.is_fetch != True:
            flight.book_sum -= 1
            # flight.capacity += 1
            flight.income -= flight.price
            flight.user.remove(request.user)
            flight.save()
            o.is_refund = True
            o.can_modify = False
            o.refund_time = timezone.now()
            o.save()
            return HttpResponseRedirect('/booksystem/user_operation')
    # order = Order.objects.get(user = request.user, flight = flight)
    # order.is_refund
    return render(request, 'booksystem/refund_failure.html')

def fetch_ticket(request, flight_id):
    flight = Flight.objects.get(pk=flight_id)
    surplus = (flight.leave_time - timezone.now()).days
    order = Order.objects.filter(user = request.user)
    for o in order:
        if o.can_modify == True and o.flight == flight and o.is_refund != True and o.is_fetch != True and o.is_pay == True:
            if surplus <= 1:
                o.is_fetch = True
                o.can_modify = False
                o.fetch_time = timezone.now()
                o.save()
                return render(request, 'booksystem/fetch_success.html')
            else:
                return render(request, 'booksystem/fetch_time_failure.html')
    return render(request, 'booksystem/fetch_no_pay.html')

def pay_ticket(request, flight_id):
    flight = Flight.objects.get(pk=flight_id)
    order = Order.objects.filter(user = request.user)
    for o in order:
        if o.can_modify == True and o.flight == flight and o.is_pay != True:
            o.is_pay = True
            o.pay_time = timezone.now()
            o.save()
            return render(request, 'booksystem/pay_success.html')
    return render(request, 'booksystem/pay_failure.html')

# 退出登录
def logout_user(request):
    logout(request)
    form = UserForm(request.POST or None)
    context = {
        "form": form,
    }
    return render(request, 'booksystem/login.html', context)


# 登录
def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        user = authenticate(username=username, password=password)
        if user is not None:  # 登录成功
            if user.is_active:  # 加载订票页面
                login(request, user)
                context = {
                    'username': request.user.username
                }
                if user.id == ADMIN_ID:
                    context = admin_finance(request)  # 获取要传入前端的数据
                    return render(request, 'booksystem/admin_finance.html', context)
                else:
                    return render(request, 'booksystem/result.html', context)
            else:
                return render(request, 'booksystem/login.html', {'error_message': 'Your account has been disabled'})
        else:  # 登录失败
            return render(request, 'booksystem/login.html', {'error_message': 'Invalid login'})
    return render(request, 'booksystem/login.html')


# 注册
def register(request):
    form = UserForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                context = {
                    'username': request.user.username
                }
                return render(request, 'booksystem/result.html', context)  # 注册成功直接render result页面
    context = {
        "form": form,
    }
    return render(request, 'booksystem/register.html', context)


# 搜索结果页面
def result(request):
    if request.method == 'POST':
        form = PassengerInfoForm(request.POST)  # 绑定数据至表单
        if form.is_valid():
            passenger_lcity = form.cleaned_data.get('leave_city')
            passenger_acity = form.cleaned_data.get('arrive_city')
            passenger_ldate = form.cleaned_data.get('leave_date')
            # print(type(passenger_ldate))

            # 全设为naive比较
            # china_tz = pytz.timezone('Asia/Shanghai')
            # passenger_ltime = datetime.datetime(
            #     year=passenger_ldate.year,
            #     month=passenger_ldate.month,
            #     day=passenger_ldate.day,
            #     hour=0, minute=0, second=0,
            #     tzinfo=china_tz
            # )

            # 全设为aware比较
            passenger_ltime = datetime.datetime.combine(passenger_ldate, datetime.time())
            print(passenger_ltime)

            # filter 可用车次
            all_Trains = Flight.objects.filter(leave_city=passenger_lcity, arrive_city=passenger_acity)
            usable_Trains = []
            for flight in all_Trains:  # off-set aware
                flight.leave_time = flight.leave_time.replace(tzinfo=None)  # replace方法必须要赋值。。笑哭
                if flight.leave_time.date() == passenger_ltime.date():  # 只查找当天的车次
                    usable_Trains.append(flight)

            # 按不同的key排序
            usable_Trains_by_ltime = sorted(usable_Trains, key=attrgetter('leave_time'))  # 出发时间从早到晚
            usable_Trains_by_atime = sorted(usable_Trains, key=attrgetter('arrive_time'))
            usable_Trains_by_price = sorted(usable_Trains, key=attrgetter('price'))  # 价格从低到高

            # 转换时间格式
            time_format = '%H:%M'
            # for flight in usable_Trains_by_ltime:
            #     flight.leave_time = flight.leave_time.strftime(time_format)  # 转成了str
            #     flight.arrive_time = flight.arrive_time.strftime(time_format)
            #
            # for flight in usable_Trains_by_atime:
            #     flight.leave_time = flight.leave_time.strftime(time_format)  # 转成了str
            #     flight.arrive_time = flight.arrive_time.strftime(time_format)

            # 虽然只转换了一个list，其实所有的都转换了
            for flight in usable_Trains_by_price:
                flight.leave_time = flight.leave_time.strftime(time_format)  # 转成了str
                flight.arrive_time = flight.arrive_time.strftime(time_format)

            # 决定 search_head , search_failure 是否显示
            dis_search_head = 'block'
            dis_search_failure = 'none'
            if len(usable_Trains_by_price) == 0:
                dis_search_head = 'none'
                dis_search_failure = 'block'
            context = {
                # 搜多框数据
                'leave_city': passenger_lcity,
                'arrive_city': passenger_acity,
                'leave_date': str(passenger_ldate),
                # 搜索结果
                'usable_Trains_by_ltime': usable_Trains_by_ltime,
                'usable_Trains_by_atime': usable_Trains_by_atime,
                'usable_Trains_by_price': usable_Trains_by_price,
                # 标记
                'dis_search_head': dis_search_head,
                'dis_search_failure': dis_search_failure
            }
            if request.user.is_authenticated:
                context['username'] = request.user.username
            return render(request, 'booksystem/result.html', context)  # 最前面如果加了/就变成根目录了，url错误
        else:
            return render(request, 'booksystem/index.html')  # 在index界面提交的表单无效，就保持在index界面
    else:
        context = {
            'dis_search_head': 'none',
            'dis_search_failure': 'none'
        }
    return render(request, 'booksystem/result.html', context)
