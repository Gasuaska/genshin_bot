import threading, time, sqlite3, os
from datetime import datetime, timedelta
from telebot import TeleBot, types

bot = TeleBot(token=os.getenv('TOKEN'))

BUTTONS_CONFIG = {
    '/CrystalflyTrap': 7 * 24,
    '/ParametricTransformer': 7 * 24,
    '/20HoursExpedition': 20,
    '/15HoursExpedition': 15,
    '/80HoursTreasures': 80,
}

REMINDER_MESSAGES = {
    '/CrystalflyTrap': 'Зайди в ловушку',
    '/ParametricTransformer': 'Преобразователь снова доступен!',
    '/20HoursExpedition': '20-часовая экспедиция завершена!',
    '/15HoursExpedition': '15-часовая экспедиция завершена!',
    '/80HoursTreasures': 'Сокровищница скоро переполнится!'
}

now = datetime.now().isoformat()

def resin_reminder(resin):
    max_time = 1600
    my_time = resin * 8
    time_left = max_time - my_time
    return time_left


def init_db():
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (user_id INTEGER, message TEXT,
              remind_at TEXT, created_at TEXT,  reminder_type TEXT)''')
    conn.commit()
    conn.close()


def add_reminder(user_id, remind_at, message, reminder_type):
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO reminders (user_id, remind_at, message, reminder_type) VALUES (?, ?, ?, ?)',
        (user_id, remind_at.isoformat(), message, reminder_type))
    conn.commit()
    conn.close()


def get_due_reminders():
    now = datetime.now().isoformat()
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute(
        'SELECT rowid, user_id, remind_at, message, reminder_type FROM reminders WHERE remind_at <= ?',
        (now,))
    rows = c.fetchall()
    for row in rows:
        c.execute('DELETE FROM reminders WHERE rowid = ?', (row[0],))
    conn.commit()
    conn.close()
    return rows

def delete_reminder(reminder_type):
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute('DELETE FROM reminders WHERE reminder_type = ?', (reminder_type,))
    conn.commit()
    conn.close()


def reminder_checker():
    while True:
        due = get_due_reminders()
        for _, user_id, remind_at, message, reminder_type in due:
            bot.send_message(user_id, message)
            print(f'[{datetime.now().strftime("%H:%M:%S")}]'
                  f'Отправлено напоминание типа {reminder_type}')
        time.sleep(60)


def create_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        types.KeyboardButton('/CrystalflyTrap'),
        types.KeyboardButton('/ParametricTransformer'),
        types.KeyboardButton('/20HoursExpedition'),
        types.KeyboardButton('/15HoursExpedition'),
        types.KeyboardButton('/80HoursTreasures')
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    keyboard.add(buttons[4])

    return keyboard

@bot.message_handler(commands=['start'])
def wake_up(message):
    chat_id = message.chat.id
    keyboard = create_keyboard()
    bot.send_message(
        chat_id=chat_id, text=('Привет! Я бот-напоминалка для Геншина. Выбери действие '
                               'или введи количество смолы'),
        reply_markup=keyboard)

@bot.message_handler(func=lambda msg: msg.text.isdigit())
def handle_resin(message):
    chat_id = message.chat.id
    resin = int(message.text)
    if resin > 200 or resin < 0:
        bot.send_message(chat_id, 'Некорректное количество смолы')
        return
    delete_reminder('Resin')
    time_left = resin_reminder(resin)
    remind_at = datetime.now() + timedelta(minutes=time_left)
    full_text = 'Пора собирать смолу!'
    early_text = 'Через десять минут лимит смолы заполнится!'
    add_reminder(chat_id, remind_at, full_text, reminder_type='Resin')
    if time_left > 10:
        early_reminder = remind_at - timedelta(minutes=10)
        add_reminder(chat_id, early_reminder, early_text, reminder_type='Resin')
    days = remind_at.day
    time_str = remind_at.strftime('%H:%M')
    bot.send_message(chat_id, f'Смола полностью восстановится {days} числа в {time_str}.')


@bot.message_handler(commands=['CrystalflyTrap', 'ParametricTransformer',
                               '20HoursExpedition', '15HoursExpedition',])
def other_reminders(message):
    chat_id = message.chat.id
    cmd = message.text
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute('SELECT remind_at FROM reminders WHERE reminder_type = ?', (cmd,))
    row = c.fetchone()
    conn.close()
    if row:
        remind_at = datetime.fromisoformat(row[0])
        if remind_at > datetime.now():
            bot.send_message(chat_id, 'Еще не готово, подождите')
            return
    hours = BUTTONS_CONFIG[cmd]
    remind_at = datetime.now() + timedelta(hours=hours)
    text = REMINDER_MESSAGES[cmd]
    add_reminder(chat_id, remind_at, text, reminder_type=cmd)
    days = remind_at.day
    time_str = remind_at.strftime('%H:%M')
    bot.send_message(chat_id, f'Будет готово {days} числа в {time_str}')


@bot.message_handler(commands=['/80HoursTreasures',])
def treasure_reminder(message):
    chat_id = message.chat.id
    hours = BUTTONS_CONFIG['/80HoursTreasures']
    remind_at = datetime.now() + timedelta(hours=hours)
    early_reminder = remind_at - timedelta(minutes=10)
    text = REMINDER_MESSAGES['/80HoursTreasures']
    add_reminder(chat_id, remind_at, text, reminder_type='/80HoursTreasures')
    add_reminder(chat_id, early_reminder, text, reminder_type='/80HoursTreasures')
    days = remind_at.day
    time_str = remind_at.strftime('%H:%M')
    bot.send_message(chat_id, f'Сокровищница полностью заполнится {days} числа в {time_str}.')


if __name__ == '__main__':
    init_db()
    threading.Thread(target=reminder_checker, daemon=True).start()
    bot.polling(interval=20)
