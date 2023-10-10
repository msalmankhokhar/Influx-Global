from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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

app = Flask(__name__)
# run_with_ngrok(app)
app.secret_key = 'salman khokhar'
app_restarted = False

# files upload configration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
USER_ID_DOCS_FOLDER = 'static/uploads/user-Identity-docs'

try:
    app_settings = json.load(open("/home/salman138/influxGlobal/settings.json", "r"))
except:
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
scheduler_main.start()

class users(db.Model):
    user_id = db.Column(db.String(50), primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=False)
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

def get_movie_details_from_ID(movie_id):
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
        movieImgSrc = movieDetailsJson["Poster"]
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

@app.route("/", methods=["GET"])
def home():
    global app_restarted
    if app_restarted == True:
        if "user" in session:
            session.pop("user")
        app_restarted = False
    if request.method == "GET":
        if "user" in session:
            return redirect("/user")
        else:
            return render_template("home.html")

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
                return render_template("user/home.html", moviesList=moviesList, user=selected_user, priceDict=priceDict, randint=randint, purchasedMoviesList=purchasedMoviesList, currentPagespanText="Home", currentMCategoryspanText=currentMCategoryspanText)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")
        
def generate_level_upgrade_string(user_level:int):
    selected_level = levels.query.filter_by(level_number = user_level).first()
    next_level = levels.query.filter_by(level_number = (user_level+1)).first()
    if user_level > 0 and user_level < 7:
        return f"Grow your overall deposit to {next_level.minimum_overall_deposit} and invite {next_level.minimum_overall_invitation} people and get level {next_level.level_number}"
    elif user_level == 0:
        return f"Make your first deposit of {next_level.minimum_overall_deposit} and get level {next_level.level_number}"
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
        if selected_user:
            print("went in if")
            total_purchase_value = data['total_purchase_value']
            selected_user.wallet_balance += total_purchase_value
            data["status"] = "Completed"
            purchased_tickets = json.loads(selected_user.purchased_tickets)
            purchased_tickets[data_index] = data
            selected_user.purchased_tickets = json.dumps(purchased_tickets)
            db.session.commit()
            # scheduler_main.remove_job(id=dailyProfit_func_id)
            # print(f"successfully removed daily profit job for user {selected_user.name}")
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
        if selected_user:
            print("went in if (return daily profit)")
            estimated_daily_profit = data['estimated_daily_profit']
            selected_user.wallet_balance += estimated_daily_profit
            selected_user.today_earning += estimated_daily_profit
            selected_user.monthly_earning += estimated_daily_profit
            selected_user.overall_earning += estimated_daily_profit
            db.session.commit()
            print(f'Returned {estimated_daily_profit} dollars in wallet of {selected_user.name} as daily profit')
        else:
            print("went in else (return daily profit)")

@app.route("/user/buy_ticket", methods=["GET"])
def buy_ticket():
    if request.method == "GET" and "user" in session:
        selected_user = users.query.filter_by(user_id=session['user']).first()

        if selected_user.account_status != "Verified":
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
            "purchase_time" : purchase_time,
            "end_time" : end_time,
            "ticket_price" : ticket_price,
            "tickets_purchased" : tickets_purchased,
            "total_purchase_value" : total_purchase_value,
            # "estimated_total_profit" : tickets_purchased * ticket_price,
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
            return render_template("user/quantity.html", ticket_price=ticket_price, movie=movie, user=user, daily_profit_percent=daily_profit_percent, userLevel=userLevel, round=round)
            # return movie
        else:
            return redirect("/")
        
@app.route("/user/help", methods=["GET"])
def help():
    if request.method == "GET":
        if "user" in session:
            user = users.query.filter_by(user_id=session["user"]).first()
            return render_template("user/help.html", user=user)
        else:
            return redirect("/")

@app.route("/user/account", methods=["GET"])
def user_account():
    if request.method == "GET":
        if "user" in session:
            user_id = session["user"]
            selected_user = users.query.filter_by(user_id = user_id).first()
            if selected_user:
                level_upgrade_string = generate_level_upgrade_string(selected_user.level)
                return render_template("user/account.html", user=selected_user, level_upgrade_string=level_upgrade_string, currentPagespanText="Account", round=round)
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
                return render_template("user/orders.html", user=selected_user, moviesList=moviesListFiltered, get_movie_details_from_ID=get_movie_details_from_ID, priceDict=priceDict, get_readable_date_string=get_readable_date_string, currentPagespanText="Orders", round=round)
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
                return render_template("user/wallet.html", user=selected_user, currentPagespanText="Wallet", round=round)
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
                return render_template("user/verifyID.html", user=selected_user, currentPagespanText="", round=round)
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
        front = request.files['front']
        back = request.files['back']
        files = request.files
        for key in files:
            file = files[key]
            file_extention = os.path.splitext(file.filename)[1]
            filename = secure_filename(file.name + file_extention)
            file.save(os.path.join(uploads_folder_path, filename))
        # print(request.files)
        # return f"files saved successfully in folder {uploads_folder_path}"
        flash("Identity documents submitted successfully<br><br>Wait for admins to approve your account. Once your account gets verified, you can recharge credits and buy ticket. Approval may take 24 hours. In case of further delay, contact the customer support")
        selected_user.account_status = "Pending"
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
                return render_template("user/withdraw.html", user = selected_user, float_to_int=float_to_int)
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
                return render_template("user/getCryptoDetails.html", selected_amount=amount, payment_method=payment_method)
                # return f"Amount is {amount} and payment method is {payment_method}"
            elif payment_method == "Bank Transfer":
                # return f"Amount is {amount} and payment method is {payment_method}"
                return render_template("user/getBankDetails.html", user=selected_user, abbrev_to_country=abbrev_to_country, selected_amount=amount, payment_method=payment_method)
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
unipayment_client_id = 'bb6d66bc-b466-48a2-ae5c-f4002c9c3bc1'
unipayment_client_secret = 'F6EGZnmJTyY7Z1VQuJpwr864FV6D3eeRo'
unipayment_app_id = 'b52153b8-0c10-4350-b246-d27c6d5b1d85'
unipaymet_client = UniPaymentClient(unipayment_client_id, unipayment_client_secret)

@app.route("/user/recharge", methods=["GET", "POST"])
def user_recharge():
    user_id = session["user"]
    selected_user = users.query.filter_by(user_id = user_id).first()
    if request.method == "GET":
        if "user" in session:
            if selected_user:
                if selected_user.account_status == "Verified":
                    return render_template("user/recharge.html", user=selected_user)
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
        order_id = session["user"]
        invoice_request = CreateInvoiceRequest(
            app_id=unipayment_app_id,
            title='Recharge Wallet - Influx Global',
            lang='en-US',
            price_amount=amount,
            price_currency='USD',
            redirect_url='https://influx-global.com/user/wallet',
            notify_url='https://influx-global.com/user/wallet/verify_recharge',
            # redirect_url='http://127.0.0.1:5000/user/wallet',
            # notify_url='http://127.0.0.1:5000/user/wallet/verify_recharge',
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
                user_id = notify["order_id"]
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
            session.pop("user")
            return redirect("/admin/login")
        else:
            return redirect("/admin/login")


# Setting up twilio SMS API

account_sid = "AC924e416b403ccc4141fb1d9f8338e1b7"
auth_token = "5c5f664f7d23bf5c6a874514652e5183"
# verify_sid = "VA5ce6d856cdcd9d51386fbd1a80f7f028"
verify_sid = "VA4201478c0248e1989483892363837206"
verified_number = "+923186456552"

client = Client(account_sid, auth_token)

# creating a verification service
service = client.verify.v2.services.create(friendly_name='My First Verify Service')

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
            session.pop("pending_user")
            return redirect("/login")
        else:
            session.pop("pending_user")
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
    selected_user = users.query.get(user_id)
    selected_user.experience_money = None
    db.session.commit()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        referalCode = request.args.get('referalCode')
        if referalCode == None:
            return render_template("register.html")
        elif referalCode == "":
            return render_template("register.html")
        elif referalCode:
            return render_template("register.html", referalCode=referalCode)
    elif request.method == "POST":
        name = request.form.get('name')
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
                    session["pending_user"] = {
                        "user_id" : user_id,
                        "name" : name,
                        "phone" : phone,
                        "password" : password,
                        "country" : country,
                        "selfReferalCode" : selfReferalCode,
                        "joiningReferalCode" : joiningReferalCode
                    }
                    if invitor_user:
                        return redirect(f'/verify/user_phone/{phone}')
                    else:
                        return "Referal code is not valid. Please enter a valid referal/invitation code"
                else:
                    return "phone number is invalid"
            else:
                return f"Invalid phone number. This is not a {abbrev_to_country[country]} based phone number. Please enter your valid {abbrev_to_country[country]} phone number"
        else:
            return "phone number is invalid"

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
    
@app.route("/admin/all_users", methods=["GET"])
def admin_all_users():
    if request.method == "GET":
        if "adminuser" in session:
            usersList = users.query.all()
            return render_template('admin/users.html', usersList=usersList, round=round, currentNavlinkSpanText="Users", abbrev_to_country=abbrev_to_country)
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

@app.route("/admin/ID-Verification", methods=["GET"])
def id_verifications():
    if request.method == "GET":
        if "adminuser" in session:
            usersList = users.query.filter_by(account_status="Pending").all()
            return render_template('admin/idVerification.html', usersList=usersList, round=round, currentNavlinkSpanText="ID Verification", abbrev_to_country=abbrev_to_country, get_id_docsImg_srcList=get_id_docsImg_srcList)
        else:
            return redirect("/admin/login")
        
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


# adding scheduled jobs for reseting users daily and monthly earning
# scheduler_main.add_job(func=reset_today_earning, trigger='cron', hour=0, minute=0, id="reset_todayEarning_job", timezone = pytz.utc, replace_existing=True)
# scheduler_main.add_job(func=reset_monthly_earning, trigger='cron', day=1, hour=0, minute=0, id="reset_monthlyEarning_job", timezone = pytz.utc, replace_existing=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)