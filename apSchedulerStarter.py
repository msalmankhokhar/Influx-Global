from multiprocessing import Process
from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from backend import scheduler_main
# from backend import app

# def start_scheduler():
#     print("starting scheduler")
#     scheduler_main.start()
#     print("started scheduler successfully")

# schedular_start_process = Process(target=start_scheduler, name="schedular_starter_process", daemon=True)

# schedular_start_process = Process(target=scheduler_main.start(), name="schedular_starter_process")
# schedular_start_process.start()

# class apSchedulerConfig:
#     SCHEDULER_JOBSTORES = {"default": SQLAlchemyJobStore(url="sqlite:///jobstore.sqlite")}
#     # SCHEDULER_JOBSTORES = {"default": MemoryJobStore()}

#     SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 1000}}
#     # SCHEDULER_EXECUTORS = {"default": {"type": "processpool", "max_workers": 61}}
#     # SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 3}
#     SCHEDULER_API_ENABLED = True
# # scheduler = APScheduler(app=app)

# app.config.from_object(apSchedulerConfig())
# scheduler_main = APScheduler(scheduler=BackgroundScheduler(), app=app)

if __name__ == "__main__":
    # schedular_start_process.start()
    scheduler_main.start()