import asyncio
import os
import sqlite3
from enum import Enum
from functools import wraps
from typing import Optional, List

import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder, \
    MessageHandler


class UserState(Enum):
    START = "start"
    AFTER_START = "after_start"
    AFTER_NAME = "after_name"
    BLACK = 'black'
    CHOOSE_NAME = "choose_name"
    COMMON = "common"
    DICT = "dict"
    END = "end"
    FAULTS = "faults"
    FIRE = "fire"
    FIRST_DAY = "first_day"
    GRAY = "gray"
    HOW_TO_FIRE = "how_to_fire"
    MC1 = "mc1"
    MC2 = "mc2"
    MC3 = "mc3"
    MC_START = "mc_start"
    NIGHT = "night"
    RED = "red"
    TEST_END = "test_end"
    TEST_Q1 = "test_q1"
    TEST_Q2 = "test_q2"
    TEST_Q3 = "test_q3"
    VOTING = "voting"
    WHERE = "where"
    WHO = "who"
    YELLOW = "yellow"
    ZERO_NIGHT = "zero_night"


STAGES = [
    UserState.START,
    UserState.AFTER_START,
    UserState.CHOOSE_NAME,
    UserState.AFTER_NAME,
    UserState.COMMON,
    UserState.RED,
    UserState.YELLOW,
    UserState.BLACK,
    UserState.GRAY,
    UserState.HOW_TO_FIRE,
    UserState.FIRST_DAY,
    UserState.VOTING,
    UserState.FIRE,
    UserState.NIGHT,
    UserState.FAULTS,
    UserState.WHO,
    UserState.DICT,
    UserState.TEST_Q1,
    UserState.TEST_Q2,
    UserState.TEST_Q3,
    UserState.TEST_END,
    UserState.MC_START,
    UserState.MC1,
    UserState.MC2,
    UserState.MC3,
    UserState.WHERE,
    UserState.END,
]


# Инициализация базы данных
def init_db() -> None:
    with sqlite3.connect('users.db') as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                state TEXT
            )
        ''')
        db.commit()


# Функция для добавления пользователя в базу данных
async def add_user(user_id: int, username: str) -> None:
    async with aiosqlite.connect('users.db') as db:
        await db.execute('INSERT OR IGNORE INTO users (id, username, state) VALUES (?, ?, ?)',
                         (user_id, username, UserState.START.value))
        await db.commit()


# Функция для обновления состояния пользователя в базе данных
async def update_user_state(user_id: int, state: UserState) -> None:
    async with aiosqlite.connect('users.db') as db:
        await db.execute('UPDATE users SET state = ? WHERE id = ?', (state.value, user_id))
        await db.commit()


# Функция для получения состояния пользователя из базы данных
async def get_user_state(user_id: int) -> Optional[UserState]:
    async with aiosqlite.connect('users.db') as db:
        async with db.execute('SELECT state FROM users WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return UserState(row[0]) if row else None


# Чтение текстов из файлов
def load_text(filename: str) -> str:
    with open(os.path.join('texts', filename), 'r', encoding='utf-8') as file:
        return file.read()


def load_stage_text(stage: UserState, suffix: str = "") -> str:
    return load_text(stage.value + suffix + ".txt")


def send_action(action: ChatAction):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context, *args, **kwargs)

        return command_func

    return decorator


# Отправка картинок из папки
async def send_image(update: Update, context: ContextTypes.DEFAULT_TYPE, image_path: str, text: Optional[str] = None,
                     reply_markup: Optional[ReplyKeyboardMarkup] = None) -> None:
    with open(os.path.join('pics', image_path), 'rb') as file:
        await context.bot.send_photo(chat_id=update.effective_chat.id,
                                     caption=text,
                                     photo=file,
                                     reply_markup=reply_markup)


async def send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str, text: Optional[str] = None,
                     reply_markup: Optional[ReplyKeyboardMarkup] = None) -> None:
    with open(os.path.join('pics', video_path), 'rb') as file:
        await context.bot.send_video(chat_id=update.effective_chat.id,
                                     caption=text,
                                     video=file,
                                     reply_markup=reply_markup)


# Обработчик нажатия на кнопки
@send_action(ChatAction.TYPING)
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    chat_id = update.message.chat.id
    state = await get_user_state(user.id)
    if update.message.text == "/start" or state is None:
        state = UserState.START
        await add_user(user.id, user.username)
        await context.bot.send_message(chat_id=chat_id,
                                       text=load_stage_text(state),
                                       reply_markup=keyboard_from_messages(["Да"]))
        await send_image(update, context, "start.jpg")
    else:
        match state:
            case UserState.AFTER_START:
                await  common_stage_process(chat_id, context, state, "Да!")
            case UserState.CHOOSE_NAME:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state),
                                               reply_markup=None)
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state, "2"),
                                               reply_markup=keyboard_from_messages([""])
                                               )
            case UserState.AFTER_NAME:
                await  common_stage_process(chat_id, context, state, "Готов")
            case UserState.COMMON:
                await  common_stage_process(chat_id, context, state, "Теперь хочу узнать про роли!")
            case UserState.RED:
                await role_stage_process(chat_id, context, state, update, "Так, а комиссар тоже мирный житель? 🕵️")
            case UserState.YELLOW:
                await role_stage_process(chat_id, context, state, update, "А теперь про мафию 😈")
            case UserState.BLACK:
                await role_stage_process(chat_id, context, state, update, "А кто такой дон мафии? 👀")
            case UserState.GRAY:
                await role_stage_process(chat_id, context, state, update, "Так-так-так, а как понять куда стрелять?😅")
            case UserState.HOW_TO_FIRE:
                await  common_stage_process(chat_id, context, state, "Вроде понятно. Что дальше? ☀️")
            case UserState.FIRST_DAY:
                await common_stage_process(chat_id, context, state, "Так-так, а как голосовать? 🤔")
            case UserState.VOTING:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state, "1"),
                                               reply_markup=None)
                await send_video(update, context,
                                 video_path="voting.gif",
                                 text=load_stage_text(state, "2"),
                                 reply_markup=keyboard_from_messages(["А потом что? 🤓"])
                                 )
            case UserState.FIRE:
                await common_stage_process(chat_id, context, state, "А дон мафии и комиссар? 🕵️")
            case UserState.NIGHT:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state, "1"),
                                               reply_markup=None)
                await send_video(update, context,
                                 video_path="night.gif",
                                 text=load_stage_text(state, "2"),
                                 reply_markup=keyboard_from_messages(["Это все? Уже можно играть?😝"])
                                 )
            case UserState.FAULTS:
                await common_stage_process(chat_id, context, state, "То есть, не в свою минуту нельзя общаться? 😧️")
            case UserState.WHO:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state))
                await send_image(update, context, "who.jpg", load_stage_text(state, "2"),
                                 keyboard_from_messages(["А есть еще что-то важное, чтобы сейчас узнать?"]))
            case UserState.DICT:
                await common_stage_process(chat_id, context, state, "️Теперь проверка знаний!")
            case UserState.TEST_Q1:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state),
                                               reply_markup=keyboard_from_messages(
                                                   ["Дон мафии", "Маньяк", "Мафия", "Шериф", "Мирный житель"]))
            case UserState.TEST_Q2:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state),
                                               reply_markup=keyboard_from_messages(["Игрок № 5 - мафия",
                                                                                    "Игрок № 5 - мирный житель",
                                                                                    "Вы мафия",
                                                                                    "Игрок № 1 - шериф"]))
            case UserState.TEST_Q3:
                await context.bot.send_message(chat_id=chat_id,
                                               text=load_stage_text(state),
                                               reply_markup=keyboard_from_messages(
                                                   ["Стреляем в первую ночь и в 1, и в 6, и в 4",
                                                    "Первой ночью стреляем в игрока 1, следующей в 6, потом в 4.",
                                                    "Нужно проснуться ночью: когда назовут 1", ]))
            case UserState.TEST_END:
                await common_stage_process(chat_id, context, state, "Я уже поиграл! 😎")
            case UserState.MC_START:
                await common_stage_process(chat_id, context, state, "Да 😁")
            case UserState.MC1:
                await common_stage_process(chat_id, context, state, "Так, а что еще посмотреть? 🤔")
            case UserState.MC2:
                await common_stage_process(chat_id, context, state, "Супер! 😍")
            case UserState.MC3:
                await common_stage_process(chat_id, context, state, "А где можно поиграть? 😇")
            case UserState.WHERE:
                await common_stage_process(chat_id, context, state, "😋😋😋")
            case UserState.END:
                await common_stage_process(chat_id, context, state, "Пока-пока! 😊")
                pass

    next_stage = STAGES[(STAGES.index(state) + 1) % len(STAGES)]
    await update_user_state(user.id, next_stage)


async def common_stage_process(chat_id, context, state, reply_str="Так-так, а как голосовать? 🤔"):
    await context.bot.send_message(chat_id=chat_id,
                                   text=load_stage_text(state),
                                   reply_markup=keyboard_from_messages([reply_str]))


async def role_stage_process(chat_id, context, state, update, reply_str):
    await context.bot.send_message(chat_id=chat_id,
                                   text=load_stage_text(state, "1"),
                                   reply_markup=None)
    await send_image(update, context, state.value + ".jpg", load_stage_text(state, "2"),
                     keyboard_from_messages([reply_str]))


def keyboard_from_messages(messages: List[str]) -> ReplyKeyboardMarkup:
    keyboard = list(map(lambda it: [it], messages))
    return ReplyKeyboardMarkup(keyboard)


# Основная функция
def main() -> Application:
    init_db()

    app = ApplicationBuilder().token("").build()

    app.add_handler(MessageHandler(None, button))

    return app


if __name__ == '__main__':
    main().run_polling()
