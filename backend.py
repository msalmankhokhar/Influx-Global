from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from helper import country_to_abbrev, abbrev_to_country, get_movie_details, get_movie_img_src, get_readable_date_string, get_endTime_rawString, raw_dateString_to_dateObj
from random import randint
from phonenumbers import parse, is_valid_number, is_possible_number, NumberParseException, country_code_for_region
import requests
from twilio.rest import Client
from unipayment import UniPaymentClient, CreateInvoiceRequest, ApiException
import json
from flask_ngrok import run_with_ngrok
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
# run_with_ngrok(app)
app.secret_key = 'salman khokhar'
app_restarted = True

app_settings = json.load(open("settings.json", "r"))
# app_settings = json.load(open("/home/salman138/influxGlobal/settings.json", "r"))

# setting up database configration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# setting up scheduler
# app.config['SCHEDULER_API_ENABLED'] = True

class apSchedulerConfig:
    SCHEDULER_JOBSTORES = {"default": SQLAlchemyJobStore(url="sqlite:///jobstore.sqlite")}
    # SCHEDULER_JOBSTORES = {"default": MemoryJobStore()}

    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 10000}}
    # SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 3}
    # SCHEDULER_API_ENABLED = True
# scheduler = APScheduler(app=app)

app.config.from_object(apSchedulerConfig())
scheduler_main = APScheduler(scheduler=BackgroundScheduler(), app=app)



class users(db.Model):
    user_id = db.Column(db.String(50), primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=False)
    phone = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False, unique=False)
    country = db.Column(db.String(20), nullable=False, unique=False)
    selfReferalCode = db.Column(db.String(50), nullable=False, unique=True)
    joiningReferalCode = db.Column(db.String(50), nullable=False, unique=False)
    level = db.Column(db.Integer, nullable=False, unique=False)

    purchased_tickets = db.Column(db.String, nullable=True, unique=False)

    overall_referals = db.Column(db.Integer, nullable=False, unique=False)
    overall_deposit = db.Column(db.Float, nullable=False, unique=False)

    wallet_balance = db.Column(db.Float, nullable=False, unique=False)
    overall_earning = db.Column(db.Float, nullable=False, unique=False)
    today_earning = db.Column(db.Float, nullable=False, unique=False)
    monthly_earning = db.Column(db.Float, nullable=False, unique=False)
        
class levels(db.Model):
    level_number = db.Column(db.Integer, primary_key=True, nullable=False)

    minimum_overall_deposit = db.Column(db.Integer, nullable=True, unique=False)
    minimum_overall_invitation = db.Column(db.Integer, nullable=True, unique=False)

    daily_ticket_profit = db.Column(db.Integer, nullable=True, unique=False)
    weekly_ticket_profit = db.Column(db.Integer, nullable=True, unique=False)
    presale_ticket_profit = db.Column(db.Integer, nullable=True, unique=False)

    minimum_presale_tickets_buy = db.Column(db.Integer, nullable=True, unique=False)
    minimum_purchase_value = db.Column(db.Integer, nullable=True, unique=False)
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
            data["status"] = "completed"
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
            users.overall_earning += estimated_daily_profit
            db.session.commit()
            print(f'Returned {estimated_daily_profit} dollars in wallet of {selected_user.name} as daily profit')
        else:
            print("went in else (return daily profit)")

@app.route("/user/buy_ticket", methods=["GET"])
def buy_ticket():
    if request.method == "GET" and "user" in session:
        movie_id = request.args.get("movie_id")
        purchase_time = request.args.get("purchase_time")
        ticket_price = int(request.args.get("ticket_price"))
        tickets_purchased = int(request.args.get("tickets_purchased"))


        selected_movie = movies.query.filter_by(imdb_movie_id=movie_id).first()
        selected_user = users.query.filter_by(user_id=session['user']).first()
        selected_level = levels.query.filter_by(level_number=selected_user.level).first()

        movieRelease_Date = get_movie_details_from_ID(selected_movie.imdb_movie_id)["releaseDate"]

        if selected_movie.placement == 'pre sale':
            end_time = get_endTime_rawString(purchaeTime_rawString=purchase_time, movie_release_date=movieRelease_Date, category=selected_movie.placement, presale=True)
        else:
            end_time = get_endTime_rawString(purchaeTime_rawString=purchase_time, movie_release_date=movieRelease_Date, category=selected_movie.placement, presale=False)

        end_time_obj = raw_dateString_to_dateObj(end_time)

        profitDict = {
            "24 hour" : selected_level.daily_ticket_profit,
            "weekly" : selected_level.weekly_ticket_profit,
            "pre sale" : selected_level.presale_ticket_profit
        }

        estimated_daily_profit = (tickets_purchased * ticket_price) * (profitDict[selected_movie.placement] / 100)
        total_purchase_value = tickets_purchased * ticket_price
        data = {
            "movie_id" : movie_id,
            "purchase_time" : purchase_time,
            "end_time" : end_time,
            "ticket_price" : ticket_price,
            "tickets_purchased" : tickets_purchased,
            "total_purchase_value" : total_purchase_value,
            # "estimated_total_profit" : tickets_purchased * ticket_price,
            "estimated_daily_profit" : estimated_daily_profit,
            "status" : "in progress"
        }
        selected_user = users.query.filter_by(user_id = session["user"]).first()
        try:
            purchased_tickets_list = json.loads(selected_user.purchased_tickets)
            purchased_tickets_list.append(data)
            data_index = purchased_tickets_list.index(data)
            updated_tickets_list = json.dumps(purchased_tickets_list)
            selected_user.purchased_tickets = updated_tickets_list
            selected_user.wallet_balance -= total_purchase_value
            selected_movie.no_of_tickets -= 1
            func_id_return_capital = f"capital_{selected_user.user_id}_{movie_id}"
            func_id_return_dailyProfit = f"daily_profit_{selected_user.user_id}_{movie_id}"
            print("starting to set sceduler function")
            # scheduler.add_job(func=return_capital_amount, trigger='date', id=func_id, run_date=end_time_obj, args=[selected_user.user_id, data])

            # global scheduler_main
            
            scheduler_main.add_job(func=return_capital_amount, trigger='date', run_date=end_time_obj, args=[selected_user.user_id, data, func_id_return_dailyProfit, data_index], id=func_id_return_capital)
            date_today = datetime.today().date()
            end_time_obj_for_dailyProfitFunc = end_time_obj + timedelta(days=1)
            scheduler_main.add_job(func=return_daily_profit, trigger='cron', start_date=date_today, end_date=end_time_obj_for_dailyProfitFunc.date(), hour=8, minute=10, args=[selected_user.user_id, data], id=func_id_return_dailyProfit)
            
            # scheduler_main.remove_all_jobs()
            print("sceduler function successfully")
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
            return render_template("user/quantity.html", ticket_price=ticket_price, movie=movie, user=user, daily_profit_percent=daily_profit_percent)
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
                return render_template("user/account.html", user=selected_user, level_upgrade_string=level_upgrade_string, currentPagespanText="Account")
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
                if moviesListFilteredDict["should_update_database"]:
                    selected_user.purchased_tickets = json.dumps(moviesListFiltered)
                    db.session.commit()
                user_level = levels.query.filter_by(level_number=selected_user.level).first()
                priceDict = {
    "24 hour": {"price":3, "profit":user_level.daily_ticket_profit, "duration": "24 Hours", "duration_days":1},
    "weekly": {"price":5, "profit":user_level.weekly_ticket_profit, "duration": "1 week (7 days)", "duration_days":7},
    "pre sale": {"price":5, "profit":user_level.presale_ticket_profit, "duration": "1 month", "duration_days":30}
    }
                return render_template("user/orders.html", user=selected_user, moviesList=moviesListFiltered, get_movie_details_from_ID=get_movie_details_from_ID, priceDict=priceDict, get_readable_date_string=get_readable_date_string, currentPagespanText="Orders")
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

def upgradeUserLevel(user:users):
    with app.app_context():
        currentLevel_number = user.level
        next_level = levels.query.filter_by(level_number = currentLevel_number+1).first()
        if user.overall_deposit >= next_level.minimum_overall_deposit and user.overall_referals >= next_level.minimum_overall_invitation:
            user.level += 1
            db.session.commit()
            return True
        else:
            return False

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
                return render_template("user/recharge.html", user=selected_user)
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
            title='Recharge Wallet | Influx Global',
            lang='en-US',
            price_amount=amount,
            price_currency='USD',
            redirect_url='https://www.influx-global.com/user/wallet',
            notify_url='https://www.influx-global.com/user/wallet/verify_recharge',
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
                    upgradeUserLevel(selected_user)
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

# Setting up twilio SMS API

account_sid = "AC924e416b403ccc4141fb1d9f8338e1b7"
auth_token = "bd73b0343bc7f90fb6da4a692cccbff6"
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
                        overall_deposit = 0,
                        wallet_balance = 100,
                        overall_earning = 0,
                        level = 0,
                        purchased_tickets = '[]',
                        today_earning = 0,
                        monthly_earning = 0
                    )

            db.session.add(pending_user)
            invitor_user = users.query.filter_by(selfReferalCode=session["pending_user"]["joiningReferalCode"]).first()
            invitor_user.overall_referals += 1
            db.session.commit()
            session.pop("pending_user")
            upgradeUserLevel(invitor_user)
            # return "Your phone number has been verified and account has been created in the database"
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

def generate_selfReferalCode(name):
    name = name.strip().replace(" ", "_")
    selfReferalCode = name.upper() + "_" + str(randint(111111, 999999))
    selected_user = users.query.filter_by(selfReferalCode=selfReferalCode).first()
    if selected_user == None:
        return selfReferalCode
    else:
        generate_selfReferalCode()

def generate_referalLink(referalCode, websiteName='influxglobal.com'):
    return f'http://{websiteName}/register?referalCode={referalCode}'

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
                    selfReferalCode = generate_selfReferalCode(name=name)
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

@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    if request.method == "GET":
        if "adminuser" in session:
            session.pop("adminuser")
            return redirect("/admin")

@app.route("/admin/add_new_user", methods=["GET", "POST"])
def add_user_mannaul():
    if request.method == "GET":
        if "adminuser" not in session:
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
                    selfReferalCode = generate_selfReferalCode(name=name)
                    new_user = users(
                        user_id = user_id,
                        name = name,
                        phone = phone,
                        password = password,
                        country = country,
                        selfReferalCode = selfReferalCode,
                        joiningReferalCode = joiningReferalCode,
                        overall_referals = 0,
                        overall_deposit = 0,
                        wallet_balance = wallet_balance,
                        overall_earning = 0,
                        level = 0,
                        purchased_tickets = '[]',
                        today_earning = 0,
                        monthly_earning = 0
                    )
                    if invitor_user:
                        db.session.add(new_user)
                        invitor_user.overall_referals += 1
                        db.session.commit()
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
            return render_template('admin/movies.html', moviesList=moviesList)
        else:
            return redirect("/admin/login")
    
@app.route("/admin/all_users", methods=["GET"])
def admin_all_users():
    if request.method == "GET":
        if "adminuser" in session:
            usersList = users.query.all()
            return render_template('admin/users.html', usersList=usersList)
        else:
            return redirect("/admin/login")
    
@app.route("/admin/all_levels", methods=["GET"])
def admin_all_levels():
    if request.method == "GET":
        if "adminuser" in session:
            levelList = levels.query.all()
            return render_template('admin/levels.html', levelList=levelList)
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
            return render_template("admin/add_wallet_balance.html", user=selected_user)
        else:
            return redirect("/admin/login")
    elif request.method == "POST":
        added_wallet_balance = int(request.form.get("added_wallet_balance"))
        selected_user.wallet_balance += added_wallet_balance
        db.session.commit()
        return redirect("/admin/all_users")


# @app.route("/api/user_wallet_query", methods=["GET"])
# def api_user_wallet_query():
#     user_id = request.args.get("user_id")

if __name__ == "__main__":
    # scheduler_main.add_job(func=reset_today_earning, trigger='cron', hour=0, minute=0, id="reset_todayEarning_job")
    # scheduler_main.add_job(func=reset_monthly_earning, trigger='cron', day=1, hour=0, minute=0, id="reset_monthlyEarning_job")
    scheduler_main.start()
    app.run(host='0.0.0.0', port=5000, debug=True)