import datetime
import logging

import telegram
from telegram.ext import RegexHandler, MessageHandler, Filters, CommandHandler, Updater

import config
import locale
from SQLworker import SQL_worker

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    global chat_id
    chat_id = update.message.chat_id
    db_worker = SQL_worker(config.database_name)
    cur_user = (chat_id,)
    print(cur_user)
    exist = db_worker.searh_user()
    print(exist)
    if cur_user in exist:
        print("С возвращением!")
        bot.send_message(chat_id=update.message.chat_id,
                         text=locale.old_user)
    else:
        db_worker.new_user(update.message.chat_id)

    dp.remove_handler(not_started)
    markup = telegram.ReplyKeyboardMarkup(locale.start_keyboard)
    bot.send_message(chat_id=update.message.chat_id,
                     text=locale.welcome_message,
                     reply_markup=markup)

    dp.add_handler(RegexHandler("^(Settings)$", settings_handler))
    dp.add_handler(RegexHandler("^(Send Feedback)$", feedback_handler))
    dp.add_handler(RegexHandler("^(Add new Task)$", new_task))
    dp.add_handler(RegexHandler("^(Read my Tasks)$", read_task))
    dp.add_handler(RegexHandler("^(Read my Tasks)$",
                                read_task))
    dp.add_handler(RegexHandler("^(Start daemon)$", start_daemon, pass_job_queue=True, pass_chat_data=True))
    dp.add_handler(RegexHandler("^(My Stats)$", read_stats))


def settings_handler(bot, update):
    global cancel_work_handler
    settings_keyboard = locale.settings_keyboard
    markup = telegram.ReplyKeyboardMarkup(settings_keyboard)
    bot.send_message(update.message.chat_id,
                     text=locale.settings,
                     reply_markup=markup)
    dp.add_handler(RegexHandler("^(Set morning remind time)$", set_morning))
    dp.add_handler(RegexHandler("^(Set evening remind time)$", set_evening))
    cancel_work_handler = RegexHandler("^(Cancel)$", cancel_button)
    dp.add_handler(cancel_work_handler)


def set_morning(bot, update):
    global text_handler, cancel_work_handler
    cancel_work_handler = RegexHandler("^(Cancel)$", cancel_button)
    markup = telegram.ReplyKeyboardMarkup([["Cancel"]])
    dp.remove_handler(cancel_work_handler)
    bot.send_message(chat_id=update.message.chat_id, text="Write time in format 'hours:minutes'", reply_markup=markup)
    text_handler = MessageHandler(Filters.text, set_morning_write)
    dp.add_handler(text_handler)


def set_morning_write(bot, update):
    sql = SQL_worker(database=config.database_name)
    temp = str(update.message.text).split(":")
    try:
        int(temp[0])
        int(temp[1])
        time = ":".join([temp[0], temp[1]])
        print(time)
        if int(temp[0]) <= 23 or int(temp[1]) <= 59:
            sql.write_morning(user_id=update.message.chat_id, time=time)
            dp.remove_handler(text_handler)
            bot.send_message(chat_id=update.message.chat_id,
                             text=locale.done,
                             reply_markup=telegram.ReplyKeyboardMarkup(locale.start_keyboard))
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Wrong value")
    except ValueError:
        bot.send_message(chat_id=update.message.chat_id, text="Wrong value")


def set_evening(bot, update):
    global text_handler, cancel_work_handler
    cancel_work_handler = RegexHandler("^(Cancel)$", cancel_button)
    markup = telegram.ReplyKeyboardMarkup([["Cancel"]])
    dp.remove_handler(cancel_work_handler)
    bot.send_message(chat_id=update.message.chat_id, text="Write time in format 'hours:minutes'", reply_markup=markup)
    text_handler = MessageHandler(Filters.text, set_evening_write)
    dp.add_handler(text_handler)


def set_evening_write(bot, update):
    sql = SQL_worker(database=config.database_name)
    temp = str(update.message.text).split(":")
    try:
        int(temp[0])
        int(temp[1])
        time = ":".join([temp[0], temp[1]])
        print(time)
        if int(temp[0]) <= 23 or int(temp[1]) <= 59:
            sql.write_evening(user_id=update.message.chat_id, time=time)
            dp.remove_handler(text_handler)
            bot.send_message(chat_id=update.message.chat_id,
                             text=locale.done,
                             reply_markup=telegram.ReplyKeyboardMarkup(locale.start_keyboard))
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Wrong value")
    except ValueError:
        bot.send_message(chat_id=update.message.chat_id, text="Wrong value")


def read_stats(bot, update):
    sql = SQL_worker(database=config.database_name)
    stats = (str(sql.select_stats(chat_id))
             .replace("('", '').replace("',)", '')).split('/')
    bot.send_message(chat_id=update.message.chat_id,
                     text="You done " + stats[0]
                          + " tasks of " + stats[1]
                          + "\nPercentage of completed tasks: "
                          + str(int(stats[0]) / int(stats[1])) + "%.")


def start_daemon(bot, update, job_queue, chat_data):
    markup = telegram.ReplyKeyboardMarkup(locale.main_keyboard)
    bot.send_message(chat_id=update.message.chat_id, text="A new day was started.", reply_markup=markup)
    sql = SQL_worker(database=config.database_name)
    morning_time = str(sql.select_morning_time(user_id=update.message.chat_id)).replace("('", '').replace("',)",
                                                                                                          '').split(":")
    future = (datetime.datetime.now() + datetime.timedelta(days=0)).replace(hour=int(morning_time[0]),
                                                                            minute=int(morning_time[1]))
    delta = future - datetime.datetime.now()
    job = job_queue.run_once(new_day, delta, context=update.message.chat_id)
    chat_data['job'] = job

    evening_time = str(sql.select_evening_time(user_id=update.message.chat_id)).replace("('", '').replace("',)",
                                                                                                          '').split(":")
    future = (datetime.datetime.now() + datetime.timedelta(days=0)).replace(hour=int(evening_time[0]),
                                                                            minute=int(evening_time[1]))
    delta = future - datetime.datetime.now()
    job = job_queue.run_once(day_end, delta, context=update.message.chat_id)
    chat_data['job'] = job


def day_end(bot, job):
    """Send the alarm message."""
    global text_handler, none_work_handler
    none_work_handler = RegexHandler("^(None)$", cancel_button)
    sql = SQL_worker(database=config.database_name)
    current_tasks = (str(sql.select_task(chat_id))
                     .replace("('", '').replace("',)", '')).split(' ^$^ ')
    none = telegram.ReplyKeyboardMarkup([["None"]])
    bot.send_message(job.context,
                     text="You had " + str(len(current_tasks)) + " tasks today\nHow many of them have you done?",
                     reply_markup=none)
    text_handler = MessageHandler(Filters.text, write_stats)
    dp.add_handler(text_handler)


def write_stats(bot, update):
    dp.remove_handler(text_handler)
    dp.remove_handler(none_work_handler)
    sql = SQL_worker(database=config.database_name)
    current_tasks = len((str(sql.select_task(chat_id))
                         .replace("('", '').replace("',)", '')).split(' ^$^ '))
    stats = (str(sql.select_stats(chat_id))
             .replace("('", '').replace("',)", '')).split('/')
    try:
        temp = int(update.message.text)
        if current_tasks < temp:
            bot.send_message(chat_id=update.message.chat_id, text="Wrong value")
        stats[0] = str(int(stats[0]) + temp)
        stats[1] = str(int(stats[1]) + current_tasks)
        stats = "/".join(stats)
        sql.write_new_stats(stats=stats, user_id=update.message.chat_id)
        sql.write_new_task(task=locale.no_tasks, user_id=update.message.chat_id)
        bot.send_message(chat_id=update.message.chat_id, text=locale.done)
    except Exception:
        bot.send_message(chat_id=update.message.chat_id, text="Something went wrong. I don't understand you.")


def read_task(bot, update):
    sql = SQL_worker(database=config.database_name)
    current_tasks = (str(sql.select_task(update.message.chat_id))
                     .replace("('", '').replace("',)", '')).split(' ^$^ ')
    temp = "My tasks for today: \n"
    for i in current_tasks:
        print(i)
        temp += '- ' + i + '\n'
    print(temp)
    bot.send_message(chat_id=update.message.chat_id, text=temp)


def new_day(bot, job):
    sql = SQL_worker(database=config.database_name)
    current_tasks = (str(sql.select_task(chat_id))
                     .replace("('", '').replace("',)", '')).split(' ^$^ ')
    temp = "My tasks for today: \n"
    for i in current_tasks:
        print(i)
        temp += '- ' + i + '\n'
    print("It's a new day!\n" + temp)
    bot.send_message(job.context, text="It's a new day!\n" + temp)


def new_task(bot, update):
    global cancel_work_handler, new_task_handler
    cancel_work_handler = RegexHandler("^(Cancel)$", cancel_button)
    markup = telegram.ReplyKeyboardMarkup([["Cancel"]])
    bot.send_message(chat_id=update.message.chat_id,
                     text="Введи новую задачу", reply_markup=markup)
    dp.add_handler(cancel_work_handler)
    new_task_handler = MessageHandler(Filters.text, task_writer)
    dp.add_handler(new_task_handler)


def task_writer(bot, update):
    sql = SQL_worker(database=config.database_name)
    current_tasks = (str(sql.select_task(update.message.chat_id))
                     .replace("('", '').replace("',)", '')).split(' ^$^ ')
    temp = str(update.message.text)
    if current_tasks[0] == "No actual tasks" or current_tasks[0] == "You haven't any tasks yet.":
        current_tasks = temp
    else:
        current_tasks = current_tasks + [temp]
        current_tasks = " ^$^ ".join(current_tasks)
    sql.write_new_task(current_tasks, update.message.chat_id)
    sql.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text=locale.done,
                     reply_markup=telegram.ReplyKeyboardMarkup(locale.start_keyboard))
    dp.remove_handler(cancel_work_handler)
    dp.remove_handler(new_task_handler)


def cancel_button(bot, update):
    try:
        dp.remove_handler(text_handler)
    except NameError:
        pass
    bot.send_message(update.message.chat_id,
                     text=locale.cancel,
                     reply_markup=telegram.ReplyKeyboardMarkup(locale.start_keyboard))


def feedback_handler(bot, update):
    """Catch user feedback"""
    global text_handler
    dp.add_handler(RegexHandler("^(Cancel)$", cancel_button))
    markup = telegram.ReplyKeyboardMarkup([[locale.cancel]])
    bot.send_message(update.message.chat_id,
                     text=locale.ask_feedback,
                     reply_markup=markup)
    text_handler = MessageHandler(Filters.text, send_feedback,
                                  pass_user_data=True)
    dp.add_handler(text_handler)


def send_feedback(bot, update, user_data):
    """Send feedback to admins"""
    markup = telegram.ReplyKeyboardMarkup(locale.start_keyboard)
    bot.send_message(chat_id=update.message.chat_id,
                     text=locale.done, reply_markup=markup)
    for guy in config.admins:
        bot.send_message(guy, str(update.message.from_user.username) +
                         locale.fb_mes + update.message.text)
    dp.remove_handler(text_handler)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def dummy(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=locale.not_started)


def debug(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=locale.debug)
    config.admins.add(update.message.chat_id)
    print(config.admins)


def cancel_debug(bot, update):
    try:
        config.admins.remove(update.message.chat_id)
        bot.send_message(update.message.chat_id, 'success')
    except KeyError:
        pass


def main():
    """Run bot."""
    global dp, not_started

    updater = Updater(config.token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("__debug", debug))
    dp.add_handler(CommandHandler("__cancel_debug", cancel_debug))
    not_started = MessageHandler(Filters.text, dummy)
    dp.add_handler(not_started)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
