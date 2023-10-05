from phonenumbers import parse, geocoder, carrier, is_valid_number, is_possible_number, country_code_for_region

expected_region = "BD"
phoneNumber = parse("+92 318 6456552", _check_region=True)

# print(country_code_for_region(expected_region))

# formats:
# +66 653520884
# +880 1885208429

# print(phoneNumber.country_code)
# print(phoneNumber.national_number)

# Carrier = carrier.name_for_number(phoneNumber, 'en')

# Region = geocoder.description_for_number(phoneNumber, 'en')

# Validating a phone number
# valid = is_valid_number(phoneNumber)
  
# Checking possibility of a number
# possible = is_possible_number(phoneNumber)

# print(valid)
# print(possible)
# print(phoneNumber)

from random import randint

# print(randint(111111, 999999))
name = "salman"
# print(name.capitalize() + "566")


# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

# Set environment variables for your credentials
# Read more at http://twil.io/secure
account_sid = "AC924e416b403ccc4141fb1d9f8338e1b7"
auth_token = "7a74c9554b6204af402500a7a072bab7"
verify_sid = "VA5ce6d856cdcd9d51386fbd1a80f7f028"
verified_number = "+923186456552"

client = Client(account_sid, auth_token)

# verification = client.verify.v2.services(verify_sid).verifications.create(to=verified_number, channel="sms")
# print(verification.status)

# otp_code = input("Please enter the OTP:")

# verification_check = client.verify.v2.services(verify_sid).verification_checks.create(to=verified_number, code=otp_code)
# print(verification_check.status)


# curl -X POST https://verify.twilio.com/v2/Services/VAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/Verifications--data-urlencode "To=+15017122661"--data-urlencode "Channel=sms"--data-urlencode "TemplateSid=HJXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"-u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN

# templates = client.verify.v2.templates.list(limit=20)

# for template in templates:
#     print(f"\nThe sid is {template.sid}\nThe friendly name is {template.friendly_name}\nThe text is {template.translations['en']['text']}\nIts status is {template.translations['en']['status']}")

import requests

payload = {
    "ipn_type": "invoice",
    "event": "invoice_completed",
    "app_id": "b52153b8-0c10-4350-b246-d27c6d5b1d85",
    "invoice_id": "GR1xu9wPsdiwnXUgLrRDQq",
    "order_id": "45937618",
    "price_amount": 9.0,
    "price_currency": "USD",
    "network": "NETWORK_TRX",
    "address": "TBrfPan2bLFYAG1MqD2ux1Xs2NcJPFFys8",
    "pay_currency": "USDT",
    "pay_amount": 9.0,
    "exchange_rate": 1.0,
    "paid_amount": 9.0,
    "confirmed_amount": 9.0,
    "refunded_price_amount": 0.0,
    "create_time": "2023-09-13T14:51:07",
    "expiration_time": "2023-09-13T15:11:07",
    "status": "Complete",
    "error_status": "None",
    "ext_args": None,
    "transactions": None,
    "notify_id": "648d5c43-2db4-4424-bca0-c8a6485d58d9",
    "notify_time": "2023-09-13T14:57:46.8003133Z"
}

# response = requests.post(url='http://localhost:5000/user/wallet/verify_recharge', json=payload)

# print(response.text)

# ngrok_path = "C:\Windows\System32\\ngrok.exe"

# print(ngrok_path)

from datetime import datetime, timedelta, timezone
from helper import raw_dateString_to_dateObj, get_readable_date_string, dateObj_to_raw_dateString, get_endTime_rawString
# from apscheduler.schedulers.blocking import BlockingScheduler

# scheduler = BlockingScheduler()

# def test_func(name):
#     print(name)

# dateObj = raw_dateString_to_dateObj('2023-9-16-18-59')

# scheduler.add_job(func=test_func, trigger='date', run_date=dateObj, args=['salman khokhar'], id=)
# scheduler.start()
# print(f'successfully set scheduler on {dateObj}')

def movie_R_date_string_todate_obj(relaseDateString):
    movieReleaseDateformat = "%d %b %Y"
    dateObj = datetime.strptime(relaseDateString, movieReleaseDateformat)
    return dateObj


# print(movie_R_date_string_todate_obj("25 Jan 2008").date())

# print(datetime.today())
name = "salman"
l = ["salman", "eman", "imran"]
# # l.remove(name)
# print(l[name])

mydictList = [
    {
    "name" : "salman",
    "class" : 9
},
    {
    "name" : "imran",
    "class" : 10
}
]

list_of_names = [ d["name"] for d in mydictList ]

# print(list_of_names)

def generate_selfReferalCode(name):
    name = name.strip().replace(" ", "_")
    selfReferalCode = name.upper() + "_" + str(randint(111111, 999999))
    return selfReferalCode

name = "Salman Khokhar"

# print(generate_selfReferalCode(name))

import math

balance = 25.006

# print(round(float(balance), 2))

import string
from random import choices
selfReferalCode = ''.join(choices(string.ascii_uppercase, k=4)) + '234568'
# print(selfReferalCode)

import pytz
UCTTimeZone = pytz.utc
fixedOffsetObj = pytz._FixedOffset(-240)
# pytz.u
dateObj = datetime.now()
# dateObjWithTZ = timezone.localize(dateObj)

# print(datetime.now())
# print(datetime.now(tz=timezone(timedelta(minutes=-240))))
# print(dateObjWithTZ)
# print(dateObjWithTZ.tzinfo())

# print(timezone)

num = 240

num = -num

# print(num)

# dateObje = raw_dateString_to_dateObj("2023-9-28-14-50")

# print(dateObje)
# year = dateObje.year
# month = dateObje.month                    
# day = dateObje.day               
# hour = dateObje.hour                    
# minute = dateObje.minute                    

# dateObjeWithTimeZone = datetime(year=year, month=month, day=day, hour=hour, minute=minute, tzinfo=timezone(timedelta(minutes=-240)) )
# dateObjeWithTimeZone = fixedOffsetObj.localize(dateObje)
# dateObjeWithTimeZone = fixedOffsetObj.normalize(dateObje)

# print(dateObjeWithTimeZone)
# print(dateObjeWithTimeZone.now(dateObjeWithTimeZone.tzinfo))

# trying how to get the timezone from country name
from helper import abbrev_to_country, timezone_dict
country_name = abbrev_to_country['TH']

# print(pytz.country_timezones)
# timezone_dict = dict(pytz.country_timezones)

# timezone_str = timezone_dict['TH'][0]

# thai_timezone = pytz.timezone(timezone_str)

# datenow_in_thialand = datetime.now(pytz.timezone(timezone_str))

# # print(str(datenow_in_thialand.tzinfo))

# mydict = { "name":"salman", "class":6 }

# for key in mydict:
#     print(f"Key is {key} and value is {mydict[key]}")
timezone = pytz.timezone(timezone_dict['TH'][0])
# print(datetime.now(tz=timezone))
# print(f"timezone is {timezone}")
print(datetime.strptime("20 Dec 2023", "%d %b %Y"))