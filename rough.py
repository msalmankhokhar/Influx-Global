from phonenumbers import parse, geocoder, carrier, is_valid_number, is_possible_number

phoneNumber = parse("0372 7777 000", region="PK")

# formats:
# +66 653520884
# +880 1885208429

# print(phoneNumber.country_code)
# print(phoneNumber.national_number)

Carrier = carrier.name_for_number(phoneNumber, 'en')

Region = geocoder.description_for_number(phoneNumber, 'en')

# Validating a phone number
valid = is_valid_number(phoneNumber)
  
# Checking possibility of a number
possible = is_possible_number(phoneNumber)

# print(valid)
# print(possible)

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

response = requests.post(url='http://localhost:5000/user/wallet/verify_recharge', json=payload)

print(response.text)

# ngrok_path = "C:\Windows\System32\\ngrok.exe"

# print(ngrok_path)