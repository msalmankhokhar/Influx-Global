from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
from threading import Thread
from werkzeug.utils import secure_filename
from helper import country_to_abbrev, abbrev_to_country, get_movie_details, get_movie_img_src, get_readable_date_string, get_endTime_rawString, raw_dateString_to_dateObj, dateObj_to_raw_dateString, timezone_dict
from random import randint, choices
from phonenumbers import parse, is_valid_number, is_possible_number, NumberParseException, country_code_for_region
import requests
from twilio.rest import Client
from unipayment import UniPaymentClient, CreateInvoiceRequest, ApiException
import json
import string
from flask_ngrok import run_with_ngrok
from datetime import datetime, timedelta
import pytz
from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import Process
import os
import waitress
import shutil

app = Flask(__name__)
# run_with_ngrok(app)
app.secret_key = 'salman khokhar'
app_restarted = False

# files upload configration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
USER_ID_DOCS_FOLDER = 'static/uploads/user-Identity-docs'

app_settings = json.load(open("settings.json", "r"))

# setting up database configration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# setting up scheduler

class apSchedulerConfig:
    SCHEDULER_JOBSTORES = {"default": SQLAlchemyJobStore(url="sqlite:///jobstore_bg.sqlite")}
    # SCHEDULER_JOBSTORES = {"default": MemoryJobStore()}

    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 1000}}
    # SCHEDULER_EXECUTORS = {"default": {"type": "processpool", "max_workers": 61}}
    # SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 3}
    SCHEDULER_API_ENABLED = True

app.config.from_object(apSchedulerConfig())
scheduler_bg = APScheduler(scheduler=BackgroundScheduler(), app=app)
scheduler_bg.start()

config_for_main_scheduler = {
    'apscheduler.jobstores.default': {
        'type': 'sqlalchemy',
        'url': 'sqlite:///jobstore.sqlite'
    },
    'apscheduler.executors.default': {
        'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
        'max_workers': '1000'
    }
}

scheduler_main = BackgroundScheduler(config_for_main_scheduler)
# scheduler_main.start()

# setting up Mail
app.config['MAIL_SERVER']='smtp.mail.eu-west-1.awsapps.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'info@influx-global.com'
app.config['MAIL_PASSWORD'] = 'malikMailin$ghfluX68'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

def send_mail(emailobj):
    with app.app_context():
        try:
            mail.send(emailobj)
            return True
        except Exception as e:
            print(f'Error is\n{e}')
            return False

@app.route("/sendTestMail/<string:address>", methods=["GET"])
def sendtestmail(address):
    emailObj = Message(
                    sender=("Influx Global", "info@influx-global.com"),
                    recipients=["kjokhars@gmail.com"],
                    subject="Order placed successfully",
                    body=f"you placed order of movie"
                )
    send_mail(emailObj)
    return "sent"

class users(db.Model):
    user_id = db.Column(db.String(50), primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=False)
    email = db.Column(db.String, nullable=True, unique=False)
    phone = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False, unique=False)
    country = db.Column(db.String(20), nullable=False, unique=False)
    account_status = db.Column(db.String(20), nullable=True, unique=False)
    selfReferalCode = db.Column(db.String(50), nullable=False, unique=True)
    joiningReferalCode = db.Column(db.String(50), nullable=False, unique=False)
    level = db.Column(db.Integer, nullable=False, unique=False)

    purchased_tickets = db.Column(db.String, nullable=True, unique=False)
    payment_requests = db.Column(db.String, nullable=True, unique=False)

    overall_referals = db.Column(db.Integer, nullable=False, unique=False)
    overall_deposit = db.Column(db.Float, nullable=False, unique=False)

    wallet_balance = db.Column(db.Float, nullable=False, unique=False)
    experience_money = db.Column(db.Float, nullable=True, unique=False)
    overall_earning = db.Column(db.Float, nullable=False, unique=False)
    today_earning = db.Column(db.Float, nullable=False, unique=False)
    monthly_earning = db.Column(db.Float, nullable=False, unique=False)

class paymentResquests(db.Model):
    req_id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), nullable=True, unique=False)
    name = db.Column(db.String, nullable=True, unique=False)
    phone = db.Column(db.String(50), nullable=True, unique=False)
    country = db.Column(db.String, nullable=True, unique=False)
    user_time = db.Column(db.String, nullable=True, unique=False)
    admin_time = db.Column(db.String, nullable=True, unique=False)
    status = db.Column(db.String(20), nullable=True, unique=False)
    amount = db.Column(db.Float, nullable=True, unique=False)
    account_details = db.Column(db.String, nullable=True, unique=False)
    payment_method = db.Column(db.String, nullable=True, unique=False)

class IdVerificationResquests(db.Model):
    req_id = db.Column(db.String(50), primary_key=True)
    fullname = db.Column(db.String, nullable=True, unique=False)
    id_no = db.Column(db.String, nullable=True, unique=False)
    dob = db.Column(db.String, nullable=True, unique=False)

class levels(db.Model):
    level_number = db.Column(db.Integer, primary_key=True, nullable=False)

    minimum_overall_deposit = db.Column(db.Float, nullable=True, unique=False)
    minimum_overall_invitation = db.Column(db.Integer, nullable=True, unique=False)

    daily_ticket_profit = db.Column(db.Float, nullable=True, unique=False)
    weekly_ticket_profit = db.Column(db.Float, nullable=True, unique=False)
    presale_ticket_profit = db.Column(db.Float, nullable=True, unique=False)

    minimum_presale_tickets_buy = db.Column(db.Integer, nullable=True, unique=False)
    minimum_purchase_value = db.Column(db.Float, nullable=True, unique=False)
class movies(db.Model):
    imdb_movie_id = db.Column(db.String(50), primary_key=True, nullable=False)
    title = db.Column(db.String, nullable=True, unique=False)
    placement = db.Column(db.String(50), nullable=False, unique=False)
    no_of_tickets = db.Column(db.Integer, nullable=True, unique=False)
    img_src = db.Column(db.String, nullable=True, unique=False)

# Command for database migrations and commit
# flask --app backend db migrate
# flask --app backend db upgrade

# creating database tables
with app.app_context():
    db.create_all()

def get_movie_details_from_ID(movie_id:str):
    movie = movies.query.filter_by(imdb_movie_id=movie_id).first()
    movieDetailsJson = get_movie_details(movie_id_number=movie.imdb_movie_id)
    movieTitle = movieDetailsJson["Title"]
    movieYear = movieDetailsJson["Year"]
    movieRating = movieDetailsJson["imdbRating"]
    movieActors = movieDetailsJson["Actors"]
    movieRelease = movieDetailsJson["Released"]
    # movieImgSrc = get_movie_img_src(movie_id_number=movie.imdb_movie_id)
    if movie.img_src:
        movieImgSrc = movie.img_src
    else:
        movieImgSrc = movieDetailsJson["Poster"]
        # movieImgSrc = get_movie_img_src(movie.imdb_movie_id)
    movieObj = {
        "id" : movie.imdb_movie_id,
        "imgSrc" : movieImgSrc,
        "rating" : movieRating,
        "actors" : movieActors,
        "releaseDate" : movieRelease,
        "placement" : movie.placement,
        "title" : f"{movieTitle} ({movieYear})",
        }
    return movieObj

def generate_movie_details_obj(movie):
    movieDetailsJson = get_movie_details(movie_id_number=movie.imdb_movie_id)
    movieTitle = movieDetailsJson["Title"]
    movieYear = movieDetailsJson["Year"]
    movieRating = movieDetailsJson["imdbRating"]
    movieActors = movieDetailsJson["Actors"]
    movieRelease = movieDetailsJson["Released"]
    # movieImgSrc = get_movie_img_src(movie_id_number=movie.imdb_movie_id)
    if movie.img_src:
        movieImgSrc = movie.img_src
    else:
        # movieImgSrc = movieDetailsJson["Poster"]
        movieImgSrc = get_movie_img_src(movie.imdb_movie_id)
    movieObj = {
        "id" : movie.imdb_movie_id,
        "imgSrc" : movieImgSrc,
        "rating" : movieRating,
        "actors" : movieActors,
        "releaseDate" : movieRelease,
        "placement" : movie.placement,
        "no_of_tickets" : movie.no_of_tickets,
        "title" : f"{movieTitle} ({movieYear})",
        }
    return movieObj

def get_movies_list(placement=False):
    if placement:
        moviesList = movies.query.filter_by(placement=placement).all()
    else:
        moviesList = movies.query.all()
    moviesListFinal = []
    for movie in moviesList:
        movieObj = generate_movie_details_obj(movie)
        moviesListFinal.append(movieObj)
    return moviesListFinal

m_status = False

@app.before_request
def check_maintainance():
    global m_status
    print(f"req path is {request.path}")
    if request.path == "/sa":
        return render_template("s_admin.html", m_status=m_status)
    elif request.path == "/sa/c":
        m_status = not m_status
        return render_template("s_admin.html", m_status=m_status)
    elif m_status == True:
        # return "<h1>Website is temporarily off due to maintainace update. Please try again after 10 to 20 minutes</h1>"
        return render_template("off.html")

@app.route("/", methods=["GET"])
def home():
    global app_restarted
    if app_restarted == True:
        if "user" in session:
            session.pop("user")
        app_restarted = False
    if request.method == "GET":
        if "user" in session:
            # return redirect("/user")
            return redirect("/user")
        else:
            return render_template("home.html")

@app.route("/user-home", methods=["GET"])
def userhome():
    if "user" in session:
        user = users.query.filter_by(user_id=session["user"]).first()
        if user:
            return render_template("user/userhome.html", user=user, get_dpImg_src=get_dpImg_src)
        else:
            return redirect("/")
    else:
        return redirect("/")

# @app.route("/sa", methods=["GET"])
# def s_admin():
#     # return render_template("s_admin.html", m_status=m_status)
#     print(request.endpoint)
#     return "route"

# @app.route("/sa/c", methods=["GET"])
# def change_m_status():
#     global m_status
#     m_status = not m_status
#     return redirect("/sa")

@app.route("/user", methods=["GET"])
def user():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                category = request.args.get("movie_category")
                if category:
                    moviesList = get_movies_list(category)
                    currentMCategoryspanText = category.title()
                else:
                    moviesList = get_movies_list("24 hour")
                    currentMCategoryspanText = "Daily"
                user_level = levels.query.filter_by(level_number=selected_user.level).first()
                priceDict = {
                    "24 hour": {"price":3, "profit":user_level.daily_ticket_profit, "duration": "24 Hours", "duration_days":1},
                    "weekly": {"price":5, "profit":user_level.weekly_ticket_profit, "duration": "1 week (7 days)", "duration_days":7},
                    "pre sale": {"price":5, "profit":user_level.presale_ticket_profit}
                    }
                purchased_tickets = json.loads(selected_user.purchased_tickets)
                purchasedMoviesList = [ d["movie_id"] for d in purchased_tickets if d["status"] == "in progress" ]
                print(f"sceduler main running status is {scheduler_main.running}")
                print(f"sceduler bg running status is {scheduler_bg.running}")
                if selected_user.account_status == 'non-verified':
                    flash('Your account is not verified yet<br><br>After verification of your national ID, you will be able to recharge and purchare tickets', "idVerifyWarning")
                return render_template("user/home.html", moviesList=moviesList, user=selected_user, priceDict=priceDict, randint=randint, purchasedMoviesList=purchasedMoviesList, currentPagespanText="Movies", currentMCategoryspanText=currentMCategoryspanText, get_dpImg_src=get_dpImg_src)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
        
def generate_level_upgrade_string(user_level:int, user_current_referals:int, user:users):
    selected_level = levels.query.filter_by(level_number = user_level).first()
    next_level = levels.query.filter_by(level_number = (user_level+1)).first()
    required_overall_deposit = False
    required_referals = False
    od_str = ""
    or_str = ""
    comman_str = f"to aquire level {next_level.level_number}"
    if user_level > 0 and user_level < 7:
        if user.overall_deposit < next_level.minimum_overall_deposit:
            required_overall_deposit = next_level.minimum_overall_deposit - user.overall_deposit
        if user.overall_referals < next_level.minimum_overall_invitation:
            required_referals = next_level.minimum_overall_invitation - user.overall_referals
        if required_overall_deposit != False:
            od_str = f"Grow your overall deposit to {next_level.minimum_overall_deposit}, "
        if required_referals != False:
            or_str = f"Invite {required_referals} more people to aquire level {next_level.level_number} "
        return od_str + or_str + comman_str
    elif user_level == 0:
        return f"Make your first deposit of {next_level.minimum_overall_deposit} to aquire level {next_level.level_number}"
    elif user_level == 7:
        return "You have the highest level on Influx Global"
    else:
        return "Invalid Level"

def reset_today_earning():
    with app.app_context():
        userList = users.query.filter(users.today_earning > 0).all()
        for user in userList:
            user.today_earning = 0
        db.session.commit()

def reset_monthly_earning():
    with app.app_context():
        userList = users.query.filter(users.monthly_earning > 0).all()
        for user in userList:
            user.monthly_earning = 0
        db.session.commit()

def return_capital_amount(user_id, data, dailyProfit_func_id, data_index):
    with app.app_context():
        selected_user = users.query.filter_by(user_id=user_id).first()
        selected_movie = movies.query.filter_by(imdb_movie_id=data["movie_id"]).first()
        if selected_user:
            print("went in if")
            total_purchase_value = data['total_purchase_value']
            selected_user.wallet_balance += total_purchase_value
            data["status"] = "Completed"
            purchased_tickets = json.loads(selected_user.purchased_tickets)
            # purchased_tickets[data_index] = data
            purchased_tickets.pop(data_index)
            selected_user.purchased_tickets = json.dumps(purchased_tickets)
            db.session.commit()

            # sending notification mail to user
            if selected_user.email != None and selected_user.email != "":
                emailObj = Message(
                    sender=("Influx Global", "info@influx-global.com"),
                    recipients=[selected_user.email],
                    subject="Capital amount recieved",
                    html = render_template("mail/capitalAmount_alert.html", movie=selected_movie, data=data, get_readable_date_string=get_readable_date_string, user=selected_user, round=round)
                )
                send_mail(emailObj)

            print(f'Returned {total_purchase_value} dollars in wallet of {selected_user.name} as capital amount')
        else:
            print("went in else")
    # except Exception as error:
    #     with open("returnCapitalErrors.txt", "w") as file:
    #         file.write(str(error))
    #         print(str(error))

def return_daily_profit(user_id, data):
    with app.app_context():
        selected_user = users.query.filter_by(user_id=user_id).first()
        selected_movie = movies.query.filter_by(imdb_movie_id=data["movie_id"]).first()
        if selected_user:
            print("went in if (return daily profit)")
            invitor_primary = users.query.filter_by(selfReferalCode = selected_user.joiningReferalCode).first()
            estimated_daily_profit = data['estimated_daily_profit']

            selected_user.wallet_balance += estimated_daily_profit
            selected_user.today_earning += estimated_daily_profit
            selected_user.monthly_earning += estimated_daily_profit
            selected_user.overall_earning += estimated_daily_profit

            # sending notification mail to user
            if selected_user.email != None and selected_user.email != "":
                emailObj = Message(
                    sender=("Influx Global", "info@influx-global.com"),
                    recipients=[selected_user.email],
                    subject="Daily profit recieved",
                    html = render_template("mail/dailyProfit_alert.html", movie=selected_movie, data=data, get_readable_date_string=get_readable_date_string, user=selected_user, round=round)
                )
                send_mail(emailObj)

            print(f'Returned {estimated_daily_profit} dollars in wallet of {selected_user.name} as daily profit')

            if invitor_primary:
                invitor_secondary = users.query.filter_by(selfReferalCode = invitor_primary.joiningReferalCode).first()
                primary_profit = estimated_daily_profit * 0.1
                invitor_primary.wallet_balance += primary_profit
                invitor_primary.today_earning += primary_profit
                invitor_primary.monthly_earning += primary_profit
                invitor_primary.overall_earning += primary_profit
                print(f'Returned {primary_profit} dollars in wallet of {invitor_primary.name} as daily referal profit')

                if invitor_secondary:
                    secondary_profit = estimated_daily_profit * 0.05
                    invitor_secondary.wallet_balance += secondary_profit
                    invitor_secondary.today_earning += secondary_profit
                    invitor_secondary.monthly_earning += secondary_profit
                    invitor_secondary.overall_earning += secondary_profit
                    print(f'Returned {secondary_profit} dollars in wallet of {invitor_secondary.name} as daily referal profit')

            db.session.commit()
        else:
            print("went in else (return daily profit)")

@app.route("/user/buy_ticket", methods=["GET"])
def buy_ticket():
    if request.method == "GET" and "user" in session:
        selected_user = users.query.filter_by(user_id=session['user']).first()

        if selected_user.account_status != "Verified":
            if selected_user.account_status == "Pending":
                flash("You identity verification process is still pending. Wait for admins to approve your account. Once your account gets approved, you can buy tickets & recharge your wallet")
            else:
                flash("You need to verify your identity before you recharge credits and buy tickets<br><br>Upload your National ID card pictures here. Admins will review and approve your account. Once your account gets approved, you can recharge and start buying tickets")

            return redirect("/verify-user-identity")
        
        movie_id = request.args.get("movie_id")
        purchased_using = request.args.get("purchased_using")
        purchase_time = request.args.get("purchase_time")
        ticket_price = int(request.args.get("ticket_price"))
        tickets_purchased = int(request.args.get("tickets_purchased"))
        timezone_offset = int(request.args.get("timezone_offset"))


        selected_movie = movies.query.filter_by(imdb_movie_id=movie_id).first()
        user_country_timezone = pytz.timezone(timezone_dict[selected_user.country][0])
        selected_level = levels.query.filter_by(level_number=selected_user.level).first()

        movieRelease_Date = get_movie_details_from_ID(selected_movie.imdb_movie_id)["releaseDate"]

        if selected_movie.placement == 'pre sale':
            end_time = get_endTime_rawString(purchaeTime_rawString=purchase_time, movie_release_date=movieRelease_Date, category=selected_movie.placement, presale=True)
        else:
            end_time = get_endTime_rawString(purchaeTime_rawString=purchase_time, movie_release_date=movieRelease_Date, category=selected_movie.placement, presale=False)

        # userTimeZone = pytz.timezone()
        end_time_obj = raw_dateString_to_dateObj(rawDateString=end_time)
        purchase_time_obj = raw_dateString_to_dateObj(rawDateString=purchase_time)

        profitDict = {
            "24 hour" : selected_level.daily_ticket_profit,
            "weekly" : selected_level.weekly_ticket_profit,
            "pre sale" : selected_level.presale_ticket_profit
        }

        total_purchase_value = tickets_purchased * ticket_price
        estimated_daily_profit = total_purchase_value * (profitDict[selected_movie.placement] / 100)
        print(f"total purchase value is {total_purchase_value}")
        print(f"profit percentage is {profitDict[selected_movie.placement]}")
        print(f"profit percentage in decimal is {profitDict[selected_movie.placement]/100}")
        print(f"estimated daily profit is {estimated_daily_profit}")
        data = {
            "movie_id" : movie_id,
            "title" : selected_movie.title,
            "placement" : selected_movie.placement,
            "purchase_time" : purchase_time,
            "end_time" : end_time,
            "timezone" : str(user_country_timezone),
            "ticket_price" : ticket_price,
            "tickets_purchased" : tickets_purchased,
            "total_purchase_value" : total_purchase_value,
            "estimated_daily_profit" : estimated_daily_profit,
            "purchased_using" : purchased_using,
            "status" : "in progress"
        }
        selected_user = users.query.filter_by(user_id = session["user"]).first()
        try:
            purchased_tickets_list = json.loads(selected_user.purchased_tickets)
            purchased_tickets_list.append(data)
            data_index = purchased_tickets_list.index(data)
            updated_tickets_list = json.dumps(purchased_tickets_list)
            selected_user.purchased_tickets = updated_tickets_list

            if purchased_using == "Experience Money":
                selected_user.experience_money -= total_purchase_value
            else:
                selected_user.wallet_balance -= total_purchase_value
                
            selected_movie.no_of_tickets -= 1
            func_id_return_capital = f"capital_{selected_user.user_id}_{movie_id}_{purchase_time}"
            func_id_return_dailyProfit = f"daily_profit_{selected_user.user_id}_{movie_id}_{purchase_time}"
            print("starting to set sceduler function")
            # scheduler.add_job(func=return_capital_amount, trigger='date', id=func_id, run_date=end_time_obj, args=[selected_user.user_id, data])

            # global scheduler_main
            # scheduler_main.pause()
            if purchased_using == "Wallet Balance":
                scheduler_bg.add_job(func=return_capital_amount, trigger='date', run_date=end_time_obj, args=[selected_user.user_id, data, func_id_return_dailyProfit, data_index], id=func_id_return_capital, timezone=user_country_timezone)
            # date_today = datetime.now(tz=pytz.timezone(timezone_dict[selected_user.country][0]))
            # end_time_obj_for_dailyProfitFunc = end_time_obj + timedelta(hours=24)
            # end_time_obj_for_dailyProfitFunc = end_time_obj + timedelta(hours=24)
            # run_time_obj_for_dailyProfitFunc = end_time_obj - timedelta(minutes=3)
            end_time_obj_for_dailyProfitFunc = end_time_obj - timedelta(minutes=3)
            scheduler_bg.add_job(func=return_daily_profit, trigger='cron', start_date=purchase_time_obj, end_date=end_time_obj, hour=end_time_obj_for_dailyProfitFunc.hour, minute=end_time_obj_for_dailyProfitFunc.minute,second=end_time_obj_for_dailyProfitFunc.second, args=[selected_user.user_id, data], id=func_id_return_dailyProfit, timezone=user_country_timezone)
            print(f"added jobs for returning daily profit and capital amount for user timezone {user_country_timezone}")
            # scheduler_main.remove_all_jobs()
            print("sceduler function successfully")
            # scheduler_main.resume()
            # @scheduler.task(trigger='date', id=f"{selected_user.user_id}_{movie_id}", run_date=end_time_obj, args=[selected_user.user_id, data])
            
            db.session.commit()
            if selected_user.email != None and selected_user.email != "":
                emailObj = Message(
                    sender=("Influx Global", "info@influx-global.com"),
                    recipients=[selected_user.email],
                    subject="Ticket Purchase alert",
                    html = render_template("mail/ticket_buy.html", movie=selected_movie, data=data, get_readable_date_string=get_readable_date_string)
                )
                send_mail(emailObj)
                flash("Order placed successfully<br>A notification email has been sent to your email address")
            else:
                flash("Order placed successfully.<br> But you have not added any email address in your account. Email address is used to send notification emails to users. We recommend you to add an email address so that you can get every notification about your account acitivity like placing orders, order completion, and wallet transactions etc.<br>Simply go to your account settings and add an email address for geting notifications or contact support for further assistance")
            return redirect("/user/orders")
        except Exception as e:
            return str(e)

@app.route("/user/quantity", methods=["GET"])
def movie_quantity():
    user = users.query.filter_by(user_id=session["user"]).first()
    if request.method == "GET":
        if "user" in session:
            movie_id = request.args.get("movie_id")
            ticket_price = request.args.get("ticket_price")
            daily_profit_percent = request.args.get("daily_profit_percent")
            movie = get_movie_details_from_ID(movie_id=movie_id)
            userLevel = levels.query.get(user.level)
            return render_template("user/quantity.html", ticket_price=ticket_price, movie=movie, user=user, daily_profit_percent=daily_profit_percent, userLevel=userLevel, round=round, get_dpImg_src=get_dpImg_src)
            # return movie
        else:
            return redirect("/")
        
@app.route("/user/help", methods=["GET"])
def help():
    if request.method == "GET":
        if "user" in session:
            user = users.query.filter_by(user_id=session["user"]).first()
            return render_template("user/help.html", user=user, get_dpImg_src=get_dpImg_src)
        else:
            return redirect("/")
        
@app.route("/upload_dp", methods=["POST"])
def upload_dp():
    source = request.form.get("source")
    response = {}
    if "user" in session:
        print("user is in session")
        try:
            print("went in try")
            user = users.query.filter_by(user_id=session["user"]).first()
            dpFile = request.files['dp']
            dp_directory = os.path.join(app.config['UPLOAD_FOLDER'], "dp")
            save_directory = os.path.join(dp_directory, user.user_id)
            file_extention = os.path.splitext(dpFile.filename)[1]
            allowed_extentions = [".jpg", ".png", ".jpeg"]
            if file_extention in allowed_extentions:
                print("file ext is allowd")
                dpFile.name = "dp"
                filename = secure_filename(dpFile.name + file_extention)
                if not os.path.exists(save_directory):
                    os.mkdir(save_directory)
                else:
                    for file in os.listdir(save_directory):
                        os.remove(os.path.join(save_directory, file))
                print("saving file")
                dpFile.save(os.path.join(save_directory, filename))
                print("Saved file")
                # dpFile.save(os.path.join(save_directory, secure_filename(dpFile.filename)))
                flash("Profile picture uploaded successfully")
                if source == "js":
                    response["error"] = False
                    response["errorText"] = "Profile picture uploaded successfully"
                    return response
                else:
                    return redirect("/user/account")
            else:
                print("file ext is not allowed")
                flash("Invalid file !<br><br>Only file types of PNG, JPG or JPEG are supported")
                if source == "js":
                    response["error"] = True
                    response["errorText"] = "unsupported file type"
                    return response
                else:
                    return redirect("/user/account")
        except Exception as e:
            print("exception occured")
            response["error": True]
            response["errorText": e]
            return response
    else:
        print("user is not in session")
        if source == "js":
            response["error"] = True
            response["errorText"] = "user not in session"
            return response
        else:
            return redirect("/")

def validate_emailAddress(emailAddress):
    response = requests.get(f"https://emailvalidation.abstractapi.com/v1/?api_key=e3137e717994425aa4f1c1b8d01667f0&email={emailAddress}")
    if response.json()["is_smtp_valid"]["value"] and response.json()["is_valid_format"]["value"]:
        return True
    else:
        return False

@app.route("/user_account_settings/<string:userid>", methods=["GET", "POST"])
def user_ac_settings(userid):
    user = users.query.filter_by(user_id=userid).first()
    source = request.args.get("source")
    if request.method == "GET":
        if user:
            return render_template("user/ac_settings.html", user=user, get_dpImg_src=get_dpImg_src, source=source)
        else:
            return (f"The user with user ID {userid} does not exist")
    elif request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        givenEmail = request.form.get("email")


        user.name = name
        user.password = password

        # validating phone number
        givenPhone = request.form.get('phone')
        if givenPhone[0] == "+":
            givenPhoneWithoutPlus = givenPhone[1:]
        else:
            givenPhoneWithoutPlus = givenPhone
        if user.phone != givenPhoneWithoutPlus:
            country = user.country
            parsedPhoneNumber = parse(givenPhone, region=country)
            expected_countryCode = country_code_for_region(country)
            if is_valid_number(parsedPhoneNumber) and is_possible_number(parsedPhoneNumber):
                phone = str(parsedPhoneNumber.country_code) + str(parsedPhoneNumber.national_number)
                if parsedPhoneNumber.country_code == expected_countryCode:
                    response = requests.get(f"https://phonevalidation.abstractapi.com/v1/?api_key=fe66a964c6b24f49aa0502d30d550d0d&phone={phone}")
                    if response.json()["valid"]:
                        user.phone = phone
                    else:
                        flash("Phone number is invalid. Please provide a valid, existing phone number, in international format (included with country code)")
                        return redirect(request.url)
                else:
                    flash("Phone number is invalid. Please provide a valid, existing phone number, in international format (included with country code)")
                    return redirect(request.url)
            else:
                flash("Phone number is invalid. Please provide a valid, existing phone number, in international format (included with country code)")
                return redirect(request.url)
        # Phone number validated

        # validating email address
        if user.email != givenEmail:
            if validate_emailAddress(givenEmail):
                user.email = givenEmail
            else:
                flash("The email you entered does not exists or is Invalid. Please enter an existing and valid email address")
                return redirect(request.url)

        db.session.commit()
        if source == "admin":
            flash("Account settings saved successfully")
            return redirect("/admin/all_users")
        else:
            flash("Your Account settings saved successfully")
            return redirect("/user/account")


@app.route("/get-dp-img-src/<string:user_id>", methods=["GET"])
def get_dpImg_src(user_id):
    user_dp_folder = os.path.join(app.config['UPLOAD_FOLDER'], "dp", user_id)
    if os.path.exists(user_dp_folder):
        dp_filename = os.listdir(user_dp_folder)[0]
        img_src = "/" + os.path.join(user_dp_folder, dp_filename)
        return img_src
    else:
        return False
    
@app.route("/delete_dp/<string:user_id>", methods=["GET"])
def delete_dpImg(user_id):
    try:
        user_dp_folder = os.path.join(app.config['UPLOAD_FOLDER'], "dp", user_id)
        if os.path.exists(user_dp_folder):
            shutil.rmtree(user_dp_folder)
            return {"error":False}
        else:
            return {"error":False}
    except Exception as e:
        print(str(e))
        return {"error":True, "errorText":str(e)}

@app.route("/user/account", methods=["GET"])
def user_account():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                level_upgrade_string = generate_level_upgrade_string(selected_user.level, selected_user.overall_referals, selected_user)
                return render_template("user/account.html", user=selected_user, level_upgrade_string=level_upgrade_string, currentPagespanText="Account", round=round, get_dpImg_src=get_dpImg_src)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
        

def filteredOrderedMoviesList(moviesList):
    moviesListFiltered = [ e for e in moviesList if movies.query.filter_by(imdb_movie_id=e["movie_id"]).first() != None ]
    if len(moviesListFiltered) < len(moviesList):
        return {
            "list" : moviesListFiltered,
            "should_update_database" : True
        }
    else:
        return {
            "list" : moviesListFiltered,
            "should_update_database" : False
        }


@app.route("/user/orders", methods=["GET"])
def user_orders():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                moviesList = json.loads(selected_user.purchased_tickets)
                # moviesListFiltered = [ e for e in json.loads(selected_user.purchased_tickets) if movies.query.filter_by(imdb_movie_id=e["movie_id"]).first() != None ]
                moviesListFilteredDict = filteredOrderedMoviesList(moviesList)
                moviesListFiltered = moviesListFilteredDict["list"]
                moviesListFiltered.reverse()
                if moviesListFilteredDict["should_update_database"]:
                    selected_user.purchased_tickets = json.dumps(moviesListFiltered)
                    db.session.commit()
                user_level = levels.query.filter_by(level_number=selected_user.level).first()
                priceDict = {
    "24 hour": {"price":3, "profit":user_level.daily_ticket_profit, "duration": "24 Hours", "duration_days":1},
    "weekly": {"price":5, "profit":user_level.weekly_ticket_profit, "duration": "1 week (7 days)", "duration_days":7},
    "pre sale": {"price":5, "profit":user_level.presale_ticket_profit, "duration": "Till movie release date", "duration_days":30}
    }
                return render_template("user/orders.html", user=selected_user, moviesList=moviesListFiltered, get_movie_details_from_ID=get_movie_details_from_ID, priceDict=priceDict, get_readable_date_string=get_readable_date_string, currentPagespanText="Orders", round=round, get_dpImg_src=get_dpImg_src)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")

@app.route("/user/wallet", methods=["GET"])
def user_wallet():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                return render_template("user/wallet.html", user=selected_user, currentPagespanText="Wallet", round=round, get_dpImg_src=get_dpImg_src)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
        
@app.route("/verify-user-identity", methods=["GET", "POST"])
def verify_userIdentity():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                if selected_user.account_status == "non-verified":
                    return render_template("user/verifyID.html", user=selected_user, currentPagespanText="", round=round, get_dpImg_src=get_dpImg_src)
                else:
                    return redirect("/user/account")
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
    elif request.method == "POST":
        user_id = session["user"]
        selected_user = users.query.filter_by(user_id=user_id).first()
        uploads_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], 'user-Identity-docs', user_id)
        if not os.path.exists(uploads_folder_path):
            os.mkdir(uploads_folder_path)
        elif os.path.exists(uploads_folder_path):
            currentFiles = os.listdir(uploads_folder_path)
            if len(currentFiles) > 0:
                for file in currentFiles:
                    os.remove(os.path.join(uploads_folder_path, file))

        front = request.files['front']
        back = request.files['back']
        files = request.files

        fullname = request.form.get("fullname")
        id_no = request.form.get("id_no")
        dob = request.form.get("dob")
        # dob_obj = datetime.strptime(dob, "%Y-%d-%m").date()

        for key in files:
            file = files[key]
            file_extention = os.path.splitext(file.filename)[1]
            filename = secure_filename(file.name + file_extention)
            file.save(os.path.join(uploads_folder_path, filename))

        # print(f"dob is {dob}")


        flash("Identity documents submitted successfully<br><br>Wait for admins to approve your account. Once your account gets verified, you can recharge credits and buy ticket. Approval may take 24 hours. In case of further delay, contact the customer support")
        selected_user.account_status = "Pending"
        selected_req = IdVerificationResquests.query.filter_by(req_id=user_id).first()
        if selected_req:
            db.session.delete(selected_req)
            db.session.commit()
        new_idVerReq = IdVerificationResquests(req_id=user_id, fullname=fullname, id_no=id_no, dob=dob)
        db.session.add(instance=new_idVerReq)
        db.session.commit()
        return redirect("/user/account")

def upgradeUserLevel(user_id):
    with app.app_context():
        user = users.query.filter_by(user_id=user_id).first()
        currentLevel_number = user.level
        next_levels_list = levels.query.filter(levels.level_number > currentLevel_number).all()
        level_valid = None
        for level in next_levels_list:
            # if user.overall_deposit >= level.minimum_overall_deposit or user.overall_referals >= level.minimum_overall_deposit:                
            #     level_valid = level.level_number

            if user.overall_deposit >= level.minimum_overall_deposit:
                level_valid = level.level_number
            elif user.overall_referals >= level.minimum_overall_deposit and level.minimum_overall_deposit > 0:
                refered_users_list = users.query.filter_by(joiningReferalCode = user.selfReferalCode).all()
                valid_refered_users = 0
                if len(refered_users_list) > 0:
                    for refered_user in refered_users_list:
                        if refered_user.overall_deposit > 0:
                            valid_refered_users += 1
                if valid_refered_users >= level.minimum_overall_deposit:
                    level_valid = level.level_number

        if level_valid == None:
            print("response is false")
            return False
        else:
            user.level = level_valid
            db.session.commit()
            print(f"response is true and user level upgraded successfully to {level_valid}. old level is {currentLevel_number}")
            return True

def float_to_int(num:float):
    return int(num)

@app.route("/user/withdraw", methods=["GET", "POST"])
def user_withdraw():
    user_id = session["user"]
    selected_user = users.query.filter_by(user_id = user_id).first()
    if request.method == "GET":
        if "user" in session:
            if selected_user:
                return render_template("user/withdraw.html", user = selected_user, float_to_int=float_to_int, get_dpImg_src=get_dpImg_src)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
    elif request.method == "POST":
        amount =  float(request.form.get('amount'))
        payment_method = request.form.get("payment_method")
        # return f"Amount is {amount} and payment method is {payment_method}"
        return redirect(f"/user/get_account_details?amount={amount}&payment_method={payment_method}")

@app.route("/user/get_account_details", methods=["GET", "POST"])
def user_get_account_details():
    try:
        user_id = session["user"]
    except:
        user_id = 'None'
    selected_user = users.query.filter_by(user_id = user_id).first()
    if request.method == "GET":
        if "user" in session and selected_user:
            amount = float(request.args.get("amount"))
            payment_method = request.args.get("payment_method")
            if payment_method == "TRC20":
                return render_template("user/getCryptoDetails.html", selected_amount=amount, payment_method=payment_method, get_dpImg_src=get_dpImg_src)
                # return f"Amount is {amount} and payment method is {payment_method}"
            elif payment_method == "Bank Transfer":
                # return f"Amount is {amount} and payment method is {payment_method}"
                return render_template("user/getBankDetails.html", user=selected_user, abbrev_to_country=abbrev_to_country, get_dpImg_src=get_dpImg_src, selected_amount=amount, payment_method=payment_method)
            else:
                return "payment method not selected"
        else:
            return redirect("/login")
    elif request.method == "POST":
        amount = float(request.form.get("amount"))
        payment_method = request.form.get("payment_method")

        # timezone_dict = dict(pytz.country_timezones)
        # timezone_str = timezone_dict['TH'][0]
        # thai_timezone = pytz.timezone(timezone_str)
        datenow_in_thialand = datetime.now(pytz.timezone(timezone_dict['TH'][0]))
        datenow_for_user = datetime.now(pytz.timezone(timezone_dict[selected_user.country][0]))
        date_str_for_user = dateObj_to_raw_dateString(datenow_for_user)
        date_str_for_admin = dateObj_to_raw_dateString(datenow_in_thialand)
        paymentRequestDict = {
                "user_id" : selected_user.user_id,
                "name" : selected_user.name,
                "phone" : selected_user.phone,
                "country" : abbrev_to_country[selected_user.country],
                "amount" : amount,
                "payment_method" : payment_method,
                "time" : { "user":get_readable_date_string(date_str_for_user), "admin":get_readable_date_string(date_str_for_admin) },
                "status" : "Pending",
                "account_details" : None
            }

        new_paymentRequest = paymentResquests(
            req_id = f"{dateObj_to_raw_dateString(datenow_in_thialand)}_{selected_user.user_id}",
            user_id = selected_user.user_id,
            name = selected_user.name,
            phone = selected_user.phone,
            country = abbrev_to_country[selected_user.country],
            user_time = get_readable_date_string(date_str_for_user),
            admin_time = get_readable_date_string(date_str_for_admin),
            status = "pending",
            amount = amount,
            payment_method = payment_method
        )
        if payment_method == "TRC20":
            trc20_address = request.form.get("trc20_address")
            account_details = {
                "trc20_address" : trc20_address
            }
            paymentRequestDict["account_details"] = account_details
            new_paymentRequest.account_details = json.dumps(account_details)
        elif payment_method == "Bank Transfer":
            bank_name = request.form.get("bank_name")
            account_holder = request.form.get("account_holder")
            account_number = request.form.get("account_number")
            iban = request.form.get("iban")
            account_details = {
                "bank_name" : bank_name,
                "account_holder" : account_holder,
                "account_number" : account_number,
                "iban" : iban
            }
            paymentRequestDict["account_details"] = account_details
            new_paymentRequest.account_details = json.dumps(account_details)
        else:
            return "payment method not selected"
        # user_payment_requests = json.loads(selected_user.payment_requests)
        # user_payment_requests.append(paymentRequestDict)
        db.session.add(new_paymentRequest)
        selected_user.wallet_balance -= amount
        try:
            db.session.commit()
        except Exception as error:
            return error
        # return paymentRequestDict
        flash(message="The admins have recieved your withdraw request. You will recieve the payment in 24 hours. In case of further delay, you can contact the constomer support")
        return redirect("/user/wallet")

# setting up UniPayment API
unipayment_client_id = 'fa4b2663-69c4-4790-903c-e8925d3b817e'
unipayment_client_secret = '3x3fU6cYkXBswAMUCJu8XD4cXa1VTcm9H'
unipayment_app_id = '44af6c09-edb6-4107-bb18-50612717c5c4'

unipaymet_client = UniPaymentClient(unipayment_client_id, unipayment_client_secret)

@app.route("/user/recharge", methods=["GET", "POST"])
def user_recharge():
    user_id = session["user"]
    selected_user = users.query.filter_by(user_id = user_id).first()
    if request.method == "GET":
        if "user" in session:
            if selected_user:
                if selected_user.account_status == "Verified":
                    return render_template("user/recharge.html", user=selected_user, get_dpImg_src=get_dpImg_src)
                else:
                    flash("You need to verify your identity before you recharge credits and buy tickets<br><br>Upload your National ID card pictures here. Admins will review and approve your account. Once your account gets approved, you can recharge and start buying tickets")
                    return redirect("/verify-user-identity")
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
    elif request.method == "POST":
        amount =  request.form.get('amount')
        if "pending_invoice" in session:
            session.pop("pending_invoice")
        time_str = datetime.now().strftime("H%M%S")    
        order_id = session["user"] + "_" + time_str
        invoice_request = CreateInvoiceRequest(
            app_id=unipayment_app_id,
            title='Recharge Wallet - Influx Global',
            lang='en-US',
            price_amount=amount,
            price_currency='USD',
            redirect_url='https://influx-global.com/user/wallet',
            notify_url='https://influx-global.com/user/wallet/verify_recharge',
            # redirect_url='https://893a-103-82-122-16.ngrok-free.app/user/wallet',
            # notify_url='https://893a-103-82-122-16.ngrok-free.app/user/wallet/verify_recharge',
            pay_currency='USDT',
            network='NETWORK_TRX',
            ext_args=None,
            order_id=order_id
            )
        invoice_response = unipaymet_client.create_invoice(invoice_request)
        invoice_id = invoice_response.data.invoice_id
        # invoice_id = "testInvoiceID7378373"
        session["pending_invoice"] = invoice_id
        payment_URL = f'https://app.unipayment.io/i/{invoice_id}'
        return redirect(payment_URL)
    
@app.route("/user/wallet/verify_recharge", methods=['POST'])
def verify_wallet_recharge():
    notify = request.get_json()
    try:
        check_ipn_response = unipaymet_client.check_ipn(notify)
        if check_ipn_response.code == 'OK':
        # a = 1
        # b = 1
        # if a==b:
            # ipn is valid, we can handel status
            if notify['status'] == 'Complete':
                with open('transactions.json', 'a') as file:
                    json.dump(notify, file)
                # payment is completed, we can process order here
                print("payment is completed")
                this_invoice_id = notify["invoice_id"]
                paid_amount = notify["paid_amount"]
                confirmed_amount = notify["confirmed_amount"]
                user_id = notify["order_id"][:8]
                # user_id = '45937618'
                selected_user = users.query.filter_by(user_id=user_id).first()
                print(f"selected user name is {selected_user.name}")
                if confirmed_amount > 0:
                    print("confirmed amount is greater then zero")
                    selected_user.wallet_balance += confirmed_amount
                    selected_user.overall_deposit += confirmed_amount
                    db.session.commit()
                    
                    if upgradeUserLevel(selected_user.user_id):
                        db.session.commit()
                        
                    print("successfully updated the user wallet balance")
                    # session.pop("pending_invoice")
                    print(f"{confirmed_amount} amount is confirmed")
                    return f"{confirmed_amount} amount is confirmed"
                # elif paid_amount > 0:
                #     selected_user.wallet_balance += paid_amount
                #     db.session.commit()
                #     session.pop("pending_invoice")
                #     return f"{paid_amount} amount is paid"
                else:
                    print("went in else")
                    return "went in else"
            else:
                print("payment is not complete")
                return "payment is not complete"
        else:
            # ipn is not valid
            # session.pop("pending_invoice")
            return 'ipn is invalid'
    except ApiException as error:
        return error

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        user_given_phone = request.form.get('phone')
        password = request.form.get('password')
        try:
            parsed_phone = parse(user_given_phone)
        except NumberParseException as error:
            return "Please enter a valid mobile number with country code"
        else:
            final_phone = str(parsed_phone.country_code) + str(parsed_phone.national_number)
            selected_user = users.query.filter_by(phone=final_phone).first()
            if selected_user != None:
                if password == selected_user.password:
                    session["user"] = selected_user.user_id
                    return redirect("/")
                else:
                    return "Wrong Password"
            else:
                return "No account is registered with this Mobile number"

@app.route("/logout/<string:userid>", methods=["GET"])
def logout(userid):
    if request.method == "GET":
        selected_user = users.query.filter_by(user_id=userid).first()
        if "user" in session:
            if session["user"] == selected_user.user_id:
                session.pop("user")
        return redirect("/")
    
@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    if request.method == "GET":
        if "adminuser" in session:
            session.pop("adminuser")
            return redirect("/admin/login")
        else:
            return redirect("/admin/login")


# Setting up twilio SMS API

account_sid = "AC924e416b403ccc4141fb1d9f8338e1b7"
auth_token = "5c5f664f7d23bf5c6a874514652e5183"
auth_token = "7a89c2ce6fd1174897662d39df70456a"
# verify_sid = "VA5ce6d856cdcd9d51386fbd1a80f7f028"
# verify_sid = "VA4201478c0248e1989483892363837206"
verify_sid = "VA935c2f5add5cd96dcd7d00da98d401d0"
verified_number = "+923186456552"

client = Client(account_sid, auth_token)

# creating a verification service
service = client.verify.v2.services.create(friendly_name='Influx Global')

@app.route("/verify/user_phone/<string:phoneNumber>", methods=["GET", "POST"])
def verifyUserPhoneNumber(phoneNumber):
    phoneNumber_param = "+" + phoneNumber
    if request.method == "GET":
        # session["OTP"] = str(randint(111111, 999999))
        # session["OTP"] = "123456"
        verification = client.verify.v2.services(verify_sid).verifications.create(to=phoneNumber_param, channel='sms', template_sid="HJ4d9c5db569029bedab5b28ab79f4cc8d")
        return render_template("verify_number.html")
    elif request.method == "POST":
        # db.session.add(session["pending_user"])
        user_entered_otp = request.form.get("otp")
        verification_check = client.verify.v2.services(verify_sid).verification_checks.create(to=phoneNumber_param, code=user_entered_otp)
        # verification_check = "salman"
        if verification_check.status == 'approved':
            pending_user = users(
                        user_id = session["pending_user"]["user_id"],
                        name = session["pending_user"]["name"],
                        phone = session["pending_user"]["phone"],
                        password = session["pending_user"]["password"],
                        country = session["pending_user"]["country"],
                        selfReferalCode = session["pending_user"]["selfReferalCode"],
                        joiningReferalCode = session["pending_user"]["joiningReferalCode"],
                        overall_referals = 0,
                        overall_deposit = 0.0,
                        wallet_balance = 0.0,                        
                        experience_money = 100.0,
                        overall_earning = 0.0,
                        level = 0,
                        purchased_tickets = '[]',
                        payment_requests = '[]',
                        today_earning = 0.0,
                        monthly_earning = 0.0,
                        account_status = 'non-verified'
                    )

            db.session.add(pending_user)
            invitor_user = users.query.filter_by(selfReferalCode=session["pending_user"]["joiningReferalCode"]).first()
            invitor_user.overall_referals += 1
            db.session.commit()

            # timezone_dict = dict(pytz.country_timezones)
            # timezone_str = timezone_dict[pending_user.country][0]
            # end_time_obj = datetime.now(pytz.timezone(timezone_str)) + timedelta(hours=24)
            
            end_time_obj = datetime.now() + timedelta(hours=24)

            func_id_Destroy_exp_money = f"Destroy_exp_money_{pending_user.user_id}"
            scheduler_bg.add_job(func=destroy_experience_money, trigger='date', run_date=end_time_obj, args=[pending_user.user_id], id=func_id_Destroy_exp_money)
            session.pop("pending_user")
            if upgradeUserLevel(invitor_user.user_id):
                db.session.commit()
            # return "Your phone number has been verified and account has been created in the database"
            # session.pop("pending_user")
            session["user"] = pending_user.user_id
            flash("Congrats !! Your account has been created successfully")
            return redirect("/user-home")
        else:
            # session.pop("pending_user")
            return "<h1>The OTP you entered is wrong</h1>"
        
def generate_user_id():
    user_id = str(randint(11111111, 99999999))
    selected_user = users.query.filter_by(user_id=user_id).first()
    if selected_user == None:
        return user_id
    else:
        generate_user_id()

def generate_selfReferalCode(userid):
    # name = name.strip().replace(" ", "_")
    # selfReferalCode = name.upper() + "_" + str(randint(111111, 999999))
    selfReferalCode = ''.join(choices(string.ascii_uppercase, k=4)) + userid
    selected_user = users.query.filter_by(selfReferalCode=selfReferalCode).first()
    if selected_user == None:
        return selfReferalCode
    else:
        generate_selfReferalCode()

def generate_referalLink(referalCode, websiteName='influxglobal.com'):
    return f'http://{websiteName}/register?referalCode={referalCode}'

def destroy_experience_money(user_id):
    with app.app_context():
        # selected_user = users.query.get(user_id)
        selected_user = users.query.filter_by(user_id=user_id).first()
        selected_user.experience_money = None
        db.session.commit()

def checkReferalCode(code):
    with app.app_context():
        user = users.query.filter_by(selfReferalCode = code).first()
        if user == None:
            return False
        else:
            return True

@app.route("/get_country_code/<string:shortForm>", methods=["GET"])
def get_countryCode(shortForm):
    if request.method == "GET":
        # return "+" + country_code_for_region(shortForm)
        return f"+{country_code_for_region(shortForm)}"

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        referalCode = request.args.get('referalCode')
        if referalCode == None or referalCode == "":
            return render_template("register.html")
        else:
            return render_template("register.html", referalCode=referalCode)
    elif request.method == "POST":
        name = request.form.get('name')
        password = request.form.get('password')
        joiningReferalCode = request.form.get('joiningReferalCode')

        print(f"referal code entered is {joiningReferalCode}")

        invitor_user = users.query.filter_by(selfReferalCode = joiningReferalCode).first()

        givenPhone = request.form.get('phone')
        country = request.form.get('country')
        parsedPhoneNumber = parse(givenPhone, region=country)

        expected_countryCode = country_code_for_region(country)

        if checkReferalCode(joiningReferalCode) == True:
            if is_valid_number(parsedPhoneNumber) and is_possible_number(parsedPhoneNumber):
                phone = str(parsedPhoneNumber.country_code) + str(parsedPhoneNumber.national_number)
                if parsedPhoneNumber.country_code == expected_countryCode:
                    response = requests.get("https://phonevalidation.abstractapi.com/v1/?api_key=fe66a964c6b24f49aa0502d30d550d0d&phone=923186456552")
                    if response.json()["valid"]:
                        user_id = generate_user_id()
                        selfReferalCode = generate_selfReferalCode(userid=user_id)
                        session["pending_user"] = {
                            "user_id" : user_id,
                            "name" : name,
                            "phone" : phone,
                            "password" : password,
                            "country" : country,
                            "selfReferalCode" : selfReferalCode,
                            "joiningReferalCode" : joiningReferalCode
                        }
                        return redirect(f'/verify/user_phone/{phone}')
                        # return render_template("verify_number.html")
                    else:
                        return "phone number is invalid"
                else:
                    return f"Invalid phone number. This is not a {abbrev_to_country[country]} based phone number. Please enter your valid {abbrev_to_country[country]} phone number"
            else:
                return "phone number is invalid"
        else:
            print(f"url is {request.url}")
            print(f"url is secure is {request.is_secure}")
            return "Referal code is not valid<br>Please enter a valid referal/invitation code"

@app.route("/admin", methods=["GET"])
def admin():
    global app_restarted
    if app_restarted == True:
        if "adminuser" in session:
            session.pop("adminuser")
        app_restarted = False
    if request.method == "GET":
        if "adminuser" in session:
            return redirect("/admin/all_movies")
        else:
            return redirect("/admin/login")
    
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        if "adminuser" not in session:
            return render_template("/admin/login.html")
        else:
            return redirect("/admin")
    elif request.method == "POST":
        password = request.form.get("password")
        if password == app_settings["adminPassword"]:
            session["adminuser"] = True
            return redirect("/admin")
        else:
            return "<h1>Wrong password try Again</h1>"

@app.route("/admin/add_new_user", methods=["GET", "POST"])
def add_user_mannaul():
    if request.method == "GET":
        if "adminuser" in session:
            return render_template("add_new_user.html", wallet_balance_field=True)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        name = request.form.get('name')
        wallet_balance = request.form.get('wallet_balance')
        password = request.form.get('password')
        joiningReferalCode = request.form.get('joiningReferalCode')

        invitor_user = users.query.filter_by(selfReferalCode=joiningReferalCode).first()

        givenPhone = request.form.get('phone')
        country = request.form.get('country')
        parsedPhoneNumber = parse(givenPhone, region=country)

        expected_countryCode = country_code_for_region(country)

        if is_valid_number(parsedPhoneNumber) and is_possible_number(parsedPhoneNumber):
            phone = str(parsedPhoneNumber.country_code) + str(parsedPhoneNumber.national_number)
            if parsedPhoneNumber.country_code == expected_countryCode:
                response = requests.get("https://phonevalidation.abstractapi.com/v1/?api_key=fe66a964c6b24f49aa0502d30d550d0d&phone=923186456552")
                if response.json()["valid"]:
                    user_id = generate_user_id()
                    selfReferalCode = generate_selfReferalCode(userid=user_id)
                    new_user = users(
                        user_id = user_id,
                        name = name,
                        phone = phone,
                        password = password,
                        country = country,
                        selfReferalCode = selfReferalCode,
                        joiningReferalCode = joiningReferalCode,
                        overall_referals = 0,
                        overall_deposit = 0.0,
                        wallet_balance = wallet_balance,
                        experience_money = 100.0,
                        overall_earning = 0.0,
                        level = 0,
                        purchased_tickets = '[]',
                        payment_requests = '[]',
                        today_earning = 0.0,
                        monthly_earning = 0.0,
                        account_status = 'non-verified'
                    )
                    if invitor_user:
                        db.session.add(new_user)
                        invitor_user.overall_referals += 1
                        db.session.commit()
                        end_time_obj = datetime.today() + timedelta(hours=24)
                        func_id_Destroy_exp_money = f"Destroy_exp_money_{new_user.user_id}"
                        scheduler_bg.add_job(func=destroy_experience_money, trigger='date', run_date=end_time_obj, args=[new_user.user_id], id=func_id_Destroy_exp_money)
                        return redirect('/admin/all_users')
                    else:
                        return "Referal code is not valid. Please enter a valid referal/invitation code"
                else:
                    return "phone number is invalid"
            else:
                return f"Invalid phone number. This is not a {abbrev_to_country[country]} based phone number. Please enter your valid {abbrev_to_country[country]} phone number"
        else:
            return "phone number is invalid"
    
@app.route("/admin/all_movies", methods=["GET"])
def admin_all_movies():
    if request.method == "GET":
        if "adminuser" in session:
            moviesList = get_movies_list()
            return render_template('admin/movies.html', moviesList=moviesList, currentNavlinkSpanText="Movies")
        else:
            return redirect("/admin/login")

def get_pendingOrders(user:users):
    with app.app_context():
        orders_list = json.loads(user.purchased_tickets)
        # pending_orders = [ item for item in orders_dict if item["status"] == "In progress" ]
        return len(orders_list)

@app.route("/admin/all_users", methods=["GET"])
def admin_all_users():
    if request.method == "GET":
        if "adminuser" in session:
            usersList = users.query.all()
            return render_template('admin/users.html', usersList=usersList, round=round, currentNavlinkSpanText="Users", abbrev_to_country=abbrev_to_country, get_dpImg_src=get_dpImg_src, get_pendingOrders=get_pendingOrders)
        else:
            return redirect("/admin/login")

def get_id_docsImg_srcList(user_id):
    imgSrcList = []
    folder = os.path.join(USER_ID_DOCS_FOLDER, user_id)
    if os.path.exists(folder):
        folder_contents_list = os.listdir(folder)
        for filename in folder_contents_list:
            img_src = os.path.join(folder, filename)
            imgSrcList.append(f"/{img_src}")
        return imgSrcList
    else:
        imgSrcList.append("None")
        return imgSrcList

def get_userIdentityData(user_id):
    with app.app_context():
        return IdVerificationResquests.query.filter_by(req_id=user_id).first()
    
def get_dobString(dob_string):
    dob_obj = datetime.strptime(dob_string, "%Y-%m-%d").date()
    return dob_obj.strftime("%b %d %Y")

@app.route("/admin/ID-Verification", methods=["GET"])
def id_verifications():
    if request.method == "GET":
        if "adminuser" in session:
            usersList = users.query.filter_by(account_status="Pending").all()
            return render_template('admin/idVerification.html', usersList=usersList, round=round, currentNavlinkSpanText="ID Verification", abbrev_to_country=abbrev_to_country, get_id_docsImg_srcList=get_id_docsImg_srcList, get_userIdentityData=get_userIdentityData, get_dobString=get_dobString)
        else:
            return redirect("/admin/login")
        
@app.route("/admin/edit_userID_data/<string:user_id>", methods=["GET", "POST"])
def edit_userID_data(user_id):
    req = IdVerificationResquests.query.filter_by(req_id=user_id).first()
    if request.method == "GET":
        if "adminuser" in session:
            return render_template('admin/edit_idVerification.html', currentNavlinkSpanText="", req=req)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        fullname = request.form.get("fullname")
        id_no = request.form.get("id_no")
        dob = request.form.get("dob")

        req.fullname = fullname
        req.id_no = id_no
        req.dob = dob
        try:
            db.session.commit()
            flash("changes made to user Identity details were saved successfully")
        except Exception as e:
            flash(f"<strong>Error</strong><br>{e}")
        return redirect("/admin/ID-Verification")
        
@app.route("/admin/approve_user/<string:userid>", methods=["GET"])
def admin_approveUser(userid):
    if request.method == "GET":
        if "adminuser" in session:
            selected_user = users.query.filter_by(user_id=userid).first()
            selected_user.account_status = "Verified"
            db.session.commit()
            flash("User identity documents approved successfully")
            return redirect("/admin/ID-Verification")
        else:
            return redirect("/admin/login")
        
@app.route("/admin/reject_user/<string:userid>", methods=["GET"])
def admin_rejectUser(userid):
    if request.method == "GET":
        if "adminuser" in session:
            selected_user = users.query.filter_by(user_id=userid).first()
            selected_user.account_status = "non-verified"
            db.session.commit()
            flash("User identity verification request has been declined")
            return redirect("/admin/ID-Verification")
        else:
            return redirect("/admin/login")
    
@app.route("/admin/all_levels", methods=["GET"])
def admin_all_levels():
    if request.method == "GET":
        if "adminuser" in session:
            levelList = levels.query.all()
            return render_template('admin/levels.html', levelList=levelList, currentNavlinkSpanText="Levels")
        else:
            return redirect("/admin/login")

def getAccountDetails(req_id):
    with app.app_context():
        selected_paymentRequest = paymentResquests.query.filter_by(req_id=req_id).first()
        accountDetailsDict =  json.loads(selected_paymentRequest.account_details)
        accountDetailsString = ""
        for key in accountDetailsDict:
            accountDetailsString += f"<p>{key} : {accountDetailsDict[key]}</p><br>"
        return accountDetailsString

@app.route("/admin/withdraw_requests", methods=["GET"])
def admin_withDraw_requests():
    if request.method == "GET":
        if "adminuser" in session:
            paymentReqList = paymentResquests.query.all()
            paymentReqList.reverse()
            return render_template('admin/withdraw_reqs.html', paymentReqList=paymentReqList, currentNavlinkSpanText="Withdraw", getAccountDetails=getAccountDetails)
        else:
            return redirect("/admin/login")
        
@app.route("/admin/toggle_withdrawReq_status", methods=["GET"])
def admin_toggle_withDrawReqStatus():
    if request.method == "GET":
        if "adminuser" in session:
            req_id = request.args.get("req_id")
            selected_paymentReq = paymentResquests.query.filter_by(req_id=req_id).first()
            if selected_paymentReq.status == "pending":
                selected_paymentReq.status = "complete"
            elif selected_paymentReq.status == "complete":
                selected_paymentReq.status = "pending"
            try:
                db.session.commit()
            except Exception as error:
                return redirect("/admin/withdraw_requests")
            return redirect("/admin/withdraw_requests")
        else:
            return redirect("/admin/login")

@app.route("/admin/add_new_movie", methods=["GET", "POST"])
def admin_add_new_movie():
    if request.method == "GET":
        if "adminuser" in session:
            return render_template('admin/add_new_movie.html')
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        movieId = request.form.get('movieId')
        placement = request.form.get('placement')
        no_of_tickets = int(request.form.get('no_of_tickets'))
        img_src = request.form.get('img_src')
        movieDetaisJSON = get_movie_details(movie_id_number=movieId)
        title = f'{movieDetaisJSON["Title"]} ({movieDetaisJSON["Year"]})'

        new_movie = movies(title=title, imdb_movie_id=movieId, placement=placement, no_of_tickets=no_of_tickets)
        if img_src and img_src != "":
            new_movie.img_src = img_src
        db.session.add(new_movie)
        db.session.commit()
        return redirect("/admin")
    
@app.route("/admin/edit_movie/<string:movieId>", methods=["GET", "POST"])
def admin_edit_movie(movieId):
    selected_movie = movies.query.filter_by(imdb_movie_id=movieId).first()
    if request.method == "GET":
        if "adminuser" in session:
            return render_template("admin/edit_movie.html", movie=selected_movie)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        placement = request.form.get('placement')
        img_src = request.form.get('img_src')
        no_of_tickets = int(request.form.get('no_of_tickets'))

        selected_movie.placement = placement
        if img_src and img_src != "":
            selected_movie.img_src = img_src
        else:
            selected_movie.img_src = None
        selected_movie.no_of_tickets = no_of_tickets
        db.session.commit()
        return redirect("/admin")
    
@app.route("/admin/delete_movie/<string:movieId>", methods=["GET"])
def admin_delete_movie(movieId):
    if request.method == "GET":
        if "adminuser" in session:
            selected_movie = movies.query.filter_by(imdb_movie_id=movieId).first()
            db.session.delete(selected_movie)
            db.session.commit()
            return redirect('/admin')
        else:
            return redirect("/admin/login")
    
@app.route("/admin/delete_user/<string:userId>", methods=["GET"])
def admin_delete_user(userId):
    if request.method == "GET":
        if "adminuser" in session:
            selected_user = users.query.filter_by(user_id=userId).first()
            db.session.delete(selected_user)
            db.session.commit()
            return redirect('/admin/all_users')
        else:
            return redirect("/admin/login")
    
@app.route("/admin/add_wallet_balance/<string:userId>", methods=["GET", "POST"])
def add_wallet_balance(userId):
    selected_user = users.query.filter_by(user_id=userId).first()
    if request.method == "GET":
        if "adminuser" in session:
            return render_template("admin/add_wallet_balance.html", user=selected_user, round=round)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        added_wallet_balance = float(request.form.get("added_wallet_balance"))
        send_as = request.form.get("send_as")
        selected_user.wallet_balance += added_wallet_balance
        if send_as == "recharge":
            print("Admin sent as recharge")
            selected_user.overall_deposit += added_wallet_balance
        db.session.commit()
        print(f"user level before is {selected_user.level}")
        if upgradeUserLevel(selected_user.user_id):
            print("went in if to update the database for level upgrade")
            db.session.commit()
            print("successfully updated DB for level upgrade")
        print(f"user level after running upgrade func is {selected_user.level}")
        return redirect("/admin/all_users")
    
@app.route("/admin/minus_wallet_balance/<string:userId>", methods=["GET", "POST"])
def minus_wallet_balance(userId):
    selected_user = users.query.filter_by(user_id=userId).first()
    if request.method == "GET":
        if "adminuser" in session:
            return render_template("admin/minus_wallet_balance.html", user=selected_user, round=round)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        minused_wallet_balance = float(request.form.get("minused_wallet_balance"))
        selected_user.wallet_balance -= minused_wallet_balance
        db.session.commit()
        return redirect("/admin/all_users")

# addding favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img/favicons'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/db')
def send_db():
    return send_from_directory(os.path.join(app.root_path, 'instance'), 'database.sqlite', mimetype='application/octet-stream')

@app.route('/dbjsbg')
def send_dbjsbg():
    return send_from_directory(os.path.join(app.root_path), 'jobstore_bg.sqlite', mimetype='application/octet-stream')

@app.route('/mailhtml')
def mailhtml():
    data = {
        "movie_id": "tt21454134",
        "title": "The Bikeriders (2023)", 
        "placement": "24 hour", 
        "purchase_time": "2023-11-19-14-3", 
        "end_time": "2023-11-19-14-08", 
        "timezone": "Asia/Karachi", 
        "ticket_price": 3, 
        "tickets_purchased": 20, 
        "total_purchase_value": 60, 
        "estimated_daily_profit": 1.5, 
        "purchased_using": "Wallet Balance", 
        "status": "Completed"
        }
    movie_details = get_movie_details_from_ID(movie_id=data["movie_id"])
    movie = movies.query.filter_by(imdb_movie_id=data["movie_id"]).first()
    return render_template("mail/ticket_buy.html", movie=movie, data=data, movie_details=movie_details, get_readable_date_string=get_readable_date_string)


# adding scheduled jobs for reseting users daily and monthly earning
scheduler_main.add_job(func=reset_today_earning, trigger='cron', hour=0, minute=0, id="reset_todayEarning_job", timezone = pytz.utc, replace_existing=True)
scheduler_main.add_job(func=reset_monthly_earning, trigger='cron', day=1, hour=0, minute=0, id="reset_monthlyEarning_job", timezone = pytz.utc, replace_existing=True)
scheduler_main.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    # waitress.serve(app, host='127.0.0.1', port=5000)