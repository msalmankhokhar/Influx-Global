# from backend import scheduler_main, app, db, users
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

# config_for_main_scheduler = {
#     'apscheduler.jobstores.default': {
#         'type': 'sqlalchemy',
#         'url': 'sqlite:///jobstore_bg.sqlite'
#     },
#     'apscheduler.executors.default': {
#         'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
#         'max_workers': '1000'
#     }
# }

# scheduler_main = BackgroundScheduler(config_for_main_scheduler)

# @scheduler_main.task(trigger='cron', hour=0, minute=0, id="reset_todayEarning_job", timezone = pytz.utc)
# def reset_today_earning():
#     with app.app_context():
#         userList = users.query.filter(users.today_earning > 0).all()
#         for user in userList:
#             user.today_earning = 0
#         db.session.commit()

# @scheduler_main.task(trigger='cron', day=1, hour=0, minute=0, id="reset_monthlyEarning_job", timezone = pytz.utc)
# def reset_monthly_earning():
#     with app.app_context():
#         userList = users.query.filter(users.monthly_earning > 0).all()
#         for user in userList:
#             user.monthly_earning = 0
#         db.session.commit()

# if __name__ == "__main__":
    # scheduler_main.start()
