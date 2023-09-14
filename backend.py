from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from helper import country_to_abbrev, abbrev_to_country, get_movie_details, get_movie_img_src
from random import randint
from phonenumbers import parse, is_valid_number, is_possible_number, NumberParseException
import requests
from twilio.rest import Client
from unipayment import UniPaymentClient, CreateInvoiceRequest, ApiException
import json
from flask_ngrok import run_with_ngrok

app = Flask(__name__)
# run_with_ngrok(app)
app.secret_key = 'salman khokhar'

# setting up database configration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class users(db.Model):
    user_id = db.Column(db.String(50), primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=False)
    phone = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False, unique=False)
    country = db.Column(db.String(20), nullable=False, unique=False)
    selfReferalCode = db.Column(db.String(50), nullable=False, unique=True)
    joiningReferalCode = db.Column(db.String(50), nullable=False, unique=False)

    overall_referals = db.Column(db.Integer, nullable=False, unique=False)
    overall_deposit = db.Column(db.Float, nullable=False, unique=False)

    wallet_balance = db.Column(db.Float, nullable=False, unique=False)
    overall_earning = db.Column(db.Float, nullable=False, unique=False)
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

# Command for database migrations and commit
# flask --app backend db migrate
# flask --app backend db upgrade

# creating database tables
with app.app_context():
    db.create_all()

def get_movies_list(placement=False):
    if placement:
        moviesList = movies.query.filter_by(placement=placement).all()
    else:
        moviesList = movies.query.all()
    moviesListFinal = []
    for movie in moviesList:
        movieDetailsJson = get_movie_details(movie_id_number=movie.imdb_movie_id)
        movieTitle = movieDetailsJson["Title"]
        movieYear = movieDetailsJson["Year"]
        movieRating = movieDetailsJson["imdbRating"]
        movieActors = movieDetailsJson["Actors"]
        movieRelease = movieDetailsJson["Released"]
        movieImgSrc = get_movie_img_src(movie_id_number=movie.imdb_movie_id)
        movieObj = {
            "id" : movie.imdb_movie_id,
            "imgSrc" : movieImgSrc,
            "rating" : movieRating,
            "actors" : movieActors,
            "releaseDate" : movieRelease,
            "placement" : movie.placement,
            "title" : f"{movieTitle} ({movieYear})",
            }
        moviesListFinal.append(movieObj)
    return moviesListFinal

@app.route("/", methods=["GET"])
def home():
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
                moviesList = get_movies_list()
                priceDict = {
                    "24 hour": {"price":3, "profit":2},
                    "weekly": {"price":5, "profit":2},
                    "pre sale": {"price":5, "profit":2}
                }
                return render_template("user/home.html", moviesList=moviesList, user=selected_user, priceDict=priceDict, randint=randint)
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
                return render_template("user/wallet.html", user=selected_user)
            else:
                session.pop("user")
                return redirect("/")
        else:
            return redirect("/")

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
            title='Confrim Purchase | Influx Global',
            lang='en-US',
            price_amount=amount,
            price_currency='USD',
            redirect_url='https://108d-59-103-141-51.ngrok-free.app/user/wallet',
            notify_url='https://108d-59-103-141-51.ngrok-free.app/user/wallet/verify_recharge',
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
    with open('transactions.json', 'a') as file:
        json.dump(notify, file)
    try:
        check_ipn_response = unipaymet_client.check_ipn(notify)
        if check_ipn_response.code == 'OK':
        # a = 1
        # b = 1
        # if a==b:
            # ipn is valid, we can handel status
            if notify['status'] == 'Complete':
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
            return "Please enter a valid mobile number"
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
auth_token = "7a74c9554b6204af402500a7a072bab7"
verify_sid = "VA5ce6d856cdcd9d51386fbd1a80f7f028"
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
                        wallet_balance = 0,
                        overall_earning = 0
                    )
            db.session.add(pending_user)
            db.session.commit()
            session.pop("pending_user")
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
    selfReferalCode = name.upper() + str(randint(1111, 9999))
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

        givenPhone = request.form.get('phone')
        country = request.form.get('country')
        parsedPhoneNumber = parse(givenPhone, region=country)

        if is_valid_number(parsedPhoneNumber) and is_possible_number(parsedPhoneNumber):
            phone = str(parsedPhoneNumber.country_code) + str(parsedPhoneNumber.national_number)
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
                return redirect(f'/verify/user_phone/{phone}')
            else:
                return "phone number is invalid"
        else:
            return "phone number is invalid"
        
@app.route("/admin", methods=["GET"])
def admin():
    if request.method == "GET":
        return redirect("/admin/all_movies")
    
@app.route("/admin/all_movies", methods=["GET"])
def admin_all_movies():
    if request.method == "GET":
        moviesList = get_movies_list()
        return render_template('admin/movies.html', moviesList=moviesList)
    
@app.route("/admin/all_users", methods=["GET"])
def admin_all_users():
    if request.method == "GET":
        usersList = users.query.all()
        return render_template('admin/users.html', usersList=usersList)
    
@app.route("/admin/all_levels", methods=["GET"])
def admin_all_levels():
    if request.method == "GET":
        levelList = levels.query.all()
        return render_template('admin/levels.html', levelList=levelList)

@app.route("/admin/add_new_movie", methods=["GET", "POST"])
def admin_add_new_movie():
    if request.method == "GET":
        return render_template('admin/add_new_movie.html')
    elif request.method == "POST":
        movieId = request.form.get('movieId')
        placement = request.form.get('placement')
        new_movie = movies(imdb_movie_id=movieId, placement=placement)
        db.session.add(new_movie)
        db.session.commit()
        return redirect("/admin")
    
@app.route("/admin/delete_movie/<string:movieId>", methods=["GET"])
def admin_delete_movie(movieId):
    if request.method == "GET":
        selected_movie = movies.query.filter_by(imdb_movie_id=movieId).first()
        db.session.delete(selected_movie)
        db.session.commit()
        return redirect('/admin')
    
if __name__ == "__main__":
    app.run(host='localhost', port=5000, debug=True)