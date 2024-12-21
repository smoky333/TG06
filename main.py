import asyncio
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
import sqlite3
import aiohttp
import logging

# Логирование
logging.basicConfig(level=logging.INFO)

# Настройка бота
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Кнопки клавиатуры

button_registr = KeyboardButton(text='Регистрация')
button_exchange_rates = KeyboardButton(text='Курсы валют')
button_tips = KeyboardButton(text='Подсказки')
button_finances = KeyboardButton(text='Финансы')

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button_registr, button_exchange_rates],
        [button_tips, button_finances]
    ],
    resize_keyboard=True
)


# Настройка базы данных
conn = sqlite3.connect('user.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    name TEXT,
    category1 TEXT,
    category2 TEXT,
    category3 TEXT,
    expences1 REAL,
    expences2 REAL,
    expences3 REAL  
)
''')
conn.commit()

# Состояния для FinancesForm
class FinancesForm(StatesGroup):
    category1 = State()
    category2 = State()
    category3 = State()
    expences1 = State()
    expences2 = State()
    expences3 = State()

# Обработчики команд
@dp.message(CommandStart())
async def send_start(message: Message):
    await message.answer(
        text='Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:',
        reply_markup=keyboard
    )

# Регистрация
@dp.message(F.text == "Регистрация")
async def handle_registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name

    try:
        c.execute(
            "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name)
        )
        conn.commit()
        await message.answer("Вы успешно зарегистрированы!")
    except sqlite3.IntegrityError:
        await message.answer("Вы уже зарегистрированы.")

# Курсы валют
@dp.message(F.text == "Курсы валют")
async def handle_exchange_rates(message: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.exchangerate-api.com/v4/latest/USD") as response:
            if response.status == 200:
                data = await response.json()
                rates = data.get("rates", {})
                text = "Курсы валют относительно USD:\n"
                for currency, rate in rates.items():
                    text += f"{currency}: {rate:.2f}\n"
                await message.answer(text[:4000])  # Ограничиваем длину сообщения
            else:
                await message.answer("Не удалось получить курсы валют.")

# Подсказки
@dp.message(F.text == "Подсказки")
async def handle_tips(message: Message):
    tips = [
        "Ведите учет своих расходов.",
        "Старайтесь экономить 10% от дохода.",
        "Избегайте импульсивных покупок.",
        "Инвестируйте в свое образование.",
        "Создайте резервный фонд на черный день."
    ]
    await message.answer("\n".join(tips))

# Финансы
@dp.message(F.text == "Финансы")
async def handle_finances(message: Message, state: FSMContext):
    await message.answer("Введите название первой категории расходов:")
    await state.set_state(FinancesForm.category1)

@dp.message(FinancesForm.category1)
async def handle_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await message.answer("Введите название второй категории расходов:")
    await state.set_state(FinancesForm.category2)

@dp.message(FinancesForm.category2)
async def handle_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await message.answer("Введите название третьей категории расходов:")
    await state.set_state(FinancesForm.category3)

@dp.message(FinancesForm.category3)
async def handle_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await message.answer("Введите сумму расходов по первой категории:")
    await state.set_state(FinancesForm.expences1)

@dp.message(FinancesForm.expences1)
async def handle_expences1(message: Message, state: FSMContext):
    await state.update_data(expences1=float(message.text))
    await message.answer("Введите сумму расходов по второй категории:")
    await state.set_state(FinancesForm.expences2)

@dp.message(FinancesForm.expences2)
async def handle_expences2(message: Message, state: FSMContext):
    await state.update_data(expences2=float(message.text))
    await message.answer("Введите сумму расходов по третьей категории:")
    await state.set_state(FinancesForm.expences3)

@dp.message(FinancesForm.expences3)
async def handle_expences3(message: Message, state: FSMContext):
    try:
        # Пробуем преобразовать введенное значение в число
        expences3 = float(message.text)

        # Сохраняем значение в данные состояния
        await state.update_data(expences3=expences3)

        # Получаем все данные из состояния
        data = await state.get_data()
        telegram_id = message.from_user.id

        # Сохраняем данные в базу данных
        c.execute("""
            UPDATE users 
            SET category1 = ?, category2 = ?, category3 = ?, 
                expences1 = ?, expences2 = ?, expences3 = ?
            WHERE telegram_id = ?
        """, (
            data["category1"], data["category2"], data["category3"],
            data["expences1"], data["expences2"], data["expences3"],
            telegram_id
        ))
        conn.commit()

        await message.answer("Ваши данные успешно сохранены!")
        # Очищаем состояние
        await state.clear()
    except ValueError:
        # Обработка некорректного ввода (не число)
        await message.answer("Пожалуйста, введите корректное число.")
    except Exception as e:
        # Логируем и отправляем пользователю сообщение об ошибке
        logging.error(f"Ошибка сохранения данных: {e}")
        await message.answer("Произошла ошибка при сохранении данных. Попробуйте позже.")



async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
