# -*- coding: utf-8 -*-
import sqlite3


class SQL_worker:

    def __init__(self, database):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    def select_task(self, user_id):
        """ Получаем один элемент из БД """
        with self.connection:
            return self.cursor.execute('SELECT upcoming_tasks FROM user_data where user_id = ?',
                                       (user_id,)).fetchone()

    def select_stats(self, user_id):
        """ Получаем один элемент из БД """
        with self.connection:
            return self.cursor.execute('SELECT completed_tasks FROM user_data where user_id = ?',
                                       (user_id,)).fetchone()

    def select_morning_time(self, user_id):
        with self.connection:
            return self.cursor.execute('SELECT morning_remind FROM user_data WHERE user_id = ?', (user_id,)).fetchone()

    def select_evening_time(self, user_id):
        with self.connection:
            return self.cursor.execute('SELECT evening_remind FROM user_data WHERE user_id = ?', (user_id,)).fetchone()

    def new_user(self, user_id):
        """ Создание нового пользователя """
        with self.connection:
            self.cursor.execute('INSERT INTO user_data VALUES (?, ?, ?, ?, ?)',
                                (user_id, "No actual tasks", "0/0", "8:00", "21:00"))

    def searh_user(self):
        """ Поиск среди все пользователей """
        with self.connection:
            return self.cursor.execute('SELECT user_id FROM user_data').fetchall()

    def write_new_task(self, task, user_id):
        """ Запись заданий """
        with self.connection:
            self.cursor.execute('UPDATE user_data SET upcoming_tasks = ? WHERE user_id = ?',
                                (task, user_id,))

    def write_new_stats(self, stats, user_id):
        with self.connection:
            self.cursor.execute('UPDATE user_data SET completed_tasks = ? WHERE user_id = ?',
                                (stats, user_id,))

    def close(self):
        """ Закрываем текущее соединение с БД """
        self.connection.close()
