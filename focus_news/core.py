import datetime
import logging
import os
import subprocess
import traceback
import schedule


def do_wrapper(function, arguments=None):
    try:
        logging.info(f"starting {function.__name__} at {datetime.datetime.now().isoformat(sep=' ')}")
        if arguments is not None:
            function(*arguments)
        else:
            function()
        logging.info(f"successfully ran {function.__name__} at {datetime.datetime.now().isoformat(sep=' ')}")
    except Exception:
        logging.error(f"failed {function.__name__} at {datetime.datetime.now().replace(microsecond=0).isoformat(sep=' ')}\n"
                      f"{traceback.format_exc()}")


def do_command_wrapper(command):
    try:
        logging.info(f"starting {command} at {datetime.datetime.now().isoformat(sep=' ')}")
        subprocess.call(['python', command], cwd=os.path.dirname(os.path.realpath(__file__)))
        logging.info(f"successfully ran {command} at {datetime.datetime.now().isoformat(sep=' ')}")
    except Exception:
        logging.error(f"failed {command} at {datetime.datetime.now().replace(microsecond=0).isoformat(sep=' ')}\n"
                      f"{traceback.format_exc()}")


if __name__ == "__main__":
    logging.getLogger().setLevel('INFO')

    # on every deploy: read all news, generate new report
    do_command_wrapper('focus_news_get_news.py')
    do_command_wrapper('focus_news_write_summary.py')

    # read news for Focus News (server time)
    schedule.every().day.at('05:05').do(do_command_wrapper, command='focus_news_get_news.py')  # 8 утра по UTC
    schedule.every().day.at('11:05').do(do_command_wrapper, command='focus_news_get_news.py')  # 2 дня по UTC
    schedule.every().day.at('17:05').do(do_command_wrapper, command='focus_news_get_news.py')  # 8 вечера по UTC

    # send news report
    schedule.every().monday.at("05:35").do(do_command_wrapper, command='focus_news_write_summary.py') # 8:30 утра по UTC
    while True:
        schedule.run_pending()
