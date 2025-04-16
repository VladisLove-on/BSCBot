import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import asyncio
import nest_asyncio
from datetime import datetime, time

# Применяем nest_asyncio для разрешения вложенных циклов
nest_asyncio.apply()

# Токен вашего бота
TOKEN = '6072615655:AAHQh3BVU3HNHd3p7vfvE3JsBzfHiG-hNMU'
# ID канала
CHANNEL_ID = '-1001949728514'

# Состояния пользователя
user_data = {}
last_selection = {}

async def start(update, context):
    chat_id = update.message.chat_id
    keyboard = [[InlineKeyboardButton("Приступить", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Вы можете уведомить заводские подразделения о вновь прибывших материалах.", reply_markup=reply_markup)

async def transport_selection(chat_id, context):
    now = datetime.now()
    keyboard = [
        [InlineKeyboardButton("🚛 Автомобилем", callback_data='transport_car'), InlineKeyboardButton("🚂 Вагонами", callback_data='transport_train')]
    ]
    # Проверка времени и добавление кнопки с последним выбором
    if now.hour == 12 and chat_id in last_selection:
        last_cargo = last_selection[chat_id].get('cargo', '')
        last_sender = last_selection[chat_id].get('sender', '')
        if last_cargo and last_sender:
            keyboard.append([InlineKeyboardButton(f"{last_cargo}/{last_sender}", callback_data='last_selection')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Выберите способ транспортировки.", reply_markup=reply_markup)

async def button(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    # Подтверждаем обработку callback, чтобы старые кнопки не работали
    await query.answer()

    if data == 'start':
        await transport_selection(chat_id, context)
        return

    if chat_id not in user_data:
        user_data[chat_id] = {}

    if data == 'transport_car':
        user_data[chat_id]['transport'] = "Автомобилем"
        sender_keyboard = [
            [InlineKeyboardButton("Кривой рог цемент", callback_data='sender_krc'), InlineKeyboardButton("СпецКарьер", callback_data='sender_sk')],
            [InlineKeyboardButton("Баловские пески", callback_data='sender_bp'), InlineKeyboardButton("Любимовський карьер", callback_data='sender_lk')],
            [InlineKeyboardButton("ТОВ МКК №3", callback_data='sender_mkk'), InlineKeyboardButton("Новатор", callback_data='sender_nov')],
            [InlineKeyboardButton("Свой вариант", callback_data='sender_custom')]
        ]
        await context.bot.send_message(chat_id=chat_id, text="Выберите отправителя:", reply_markup=InlineKeyboardMarkup(sender_keyboard))

    elif data == 'transport_train':
        user_data[chat_id]['transport'] = "Вагонами"
        sender_keyboard = [
            [InlineKeyboardButton("Кривой рог цемент", callback_data='sender_krc'), InlineKeyboardButton("ТОВ МКК №3", callback_data='sender_mkk')],
            [InlineKeyboardButton("Новатор", callback_data='sender_nov'), InlineKeyboardButton("Свой вариант", callback_data='sender_custom')]
        ]
        await context.bot.send_message(chat_id=chat_id, text="Выберите отправителя:", reply_markup=InlineKeyboardMarkup(sender_keyboard))

    elif data.startswith('sender_'):
        senders = {
            'sender_krc': 'Кривой рог цемент',
            'sender_sk': 'СпецКарьер',
            'sender_bp': 'Баловские пески',
            'sender_lk': 'Любимовський карьер',
            'sender_mkk': 'ТОВ МКК №3',
            'sender_nov': 'Новатор',
        }
        sender = senders.get(data)
        if sender == 'custom':
            await context.bot.send_message(chat_id=chat_id, text="Введите своего отправителя:")
            return
        user_data[chat_id]['sender'] = sender
        await cargo_selection(chat_id, context)

    elif data.startswith('cargo_'):
        cargos = {
            'cargo_sand': 'Песок',
            'cargo_cement400': 'Цемент М400',
            'cargo_cement500': 'Цемент М500',
            'cargo_gravel5x10': 'Щебень 5х10',
            'cargo_gravel5x20': 'Щебень 5х20',
            'cargo_gravel10x20': 'Щебень 10х20',
            'cargo_gravel20x40': 'Щебень 20х40'
        }
        user_data[chat_id]['cargo'] = cargos.get(data)
        if user_data[chat_id]['transport'] == "Автомобилем":
            # Сохраняем последний выбор
            last_selection[chat_id] = {'cargo': user_data[chat_id]['cargo'], 'sender': user_data[chat_id]['sender']}
            await quantity_selection(chat_id, context)
        else:
            await status_selection(chat_id, context)

    elif data == 'last_selection':
        user_data[chat_id]['transport'] = "Автомобилем"
        user_data[chat_id]['cargo'] = last_selection[chat_id]['cargo']
        user_data[chat_id]['sender'] = last_selection[chat_id]['sender']
        await quantity_selection(chat_id, context)

    elif data.startswith('quantity_'):
        user_data[chat_id]['quantity'] = data.split('_')[1]
        await preview_message_car(chat_id, context)

    elif data.startswith('status_'):
        statuses = {'status_unloaded': '🟢 Разгружено', 'status_not_unloaded': '🟡 Не Разгружено'}
        user_data[chat_id]['status'] = statuses.get(data)
        await preview_message_train(chat_id, context)

    elif data == 'send':
        if user_data[chat_id]['transport'] == "Автомобилем":
            message = f"🚛Новое поступление🔔\nТранспортировка: {user_data[chat_id]['transport']}\nОтправитель: {user_data[chat_id]['sender']}\nГруз: {user_data[chat_id]['cargo']}\nКоличество машин: {user_data[chat_id]['quantity']}"
        else:
            message = f"🚂Новое поступление🔔\nТранспортировка: {user_data[chat_id]['transport']}\nОтправитель: {user_data[chat_id]['sender']}\nГруз: {user_data[chat_id]['cargo']}\nСтатус разгрузки: {user_data[chat_id]['status']}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
        await transport_selection(chat_id, context)
        user_data[chat_id].clear()

    elif data == 'cancel':
        await transport_selection(chat_id, context)
        user_data[chat_id].clear()

async def cargo_selection(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("Песок", callback_data='cargo_sand'), InlineKeyboardButton("Цемент М400", callback_data='cargo_cement400')],
        [InlineKeyboardButton("Цемент М500", callback_data='cargo_cement500'), InlineKeyboardButton("Щебень 5х10", callback_data='cargo_gravel5x10')],
        [InlineKeyboardButton("Щебень 5х20", callback_data='cargo_gravel5x20'), InlineKeyboardButton("Щебень 10х20", callback_data='cargo_gravel10x20')],
        [InlineKeyboardButton("Щебень 20х40", callback_data='cargo_gravel20x40')]
    ]
    await context.bot.send_message(chat_id=chat_id, text="Выберите груз:", reply_markup=InlineKeyboardMarkup(keyboard))

async def quantity_selection(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("1", callback_data='quantity_1'), InlineKeyboardButton("2", callback_data='quantity_2')],
        [InlineKeyboardButton("3", callback_data='quantity_3'), InlineKeyboardButton("4", callback_data='quantity_4')],
        [InlineKeyboardButton("5", callback_data='quantity_5'), InlineKeyboardButton("Свой вариант", callback_data='quantity_custom')]
    ]
    await context.bot.send_message(chat_id=chat_id, text="Укажите количество:", reply_markup=InlineKeyboardMarkup(keyboard))

async def status_selection(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("🟢 Разгружено", callback_data='status_unloaded'), InlineKeyboardButton("🟡 Не Разгружено", callback_data='status_not_unloaded')]
    ]
    await context.bot.send_message(chat_id=chat_id, text="Укажите статус разгрузки:", reply_markup=InlineKeyboardMarkup(keyboard))

async def preview_message_car(chat_id, context):
    message = f"🚛Новое поступление🔔\nТранспортировка: {user_data[chat_id]['transport']}\nОтправитель: {user_data[chat_id]['sender']}\nГруз: {user_data[chat_id]['cargo']}\nКоличество машин: {user_data[chat_id]['quantity']}"
    keyboard = [
        [InlineKeyboardButton("✉️ Отправить", callback_data='send'), InlineKeyboardButton("❌ Отменить", callback_data='cancel')]
    ]
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))

async def preview_message_train(chat_id, context):
    message = f"🚂Новое поступление🔔\nТранспортировка: {user_data[chat_id]['transport']}\nОтправитель: {user_data[chat_id]['sender']}\nГруз: {user_data[chat_id]['cargo']}\nСтатус разгрузки: {user_data[chat_id]['status']}"
    keyboard = [
        [InlineKeyboardButton("✉️ Отправить", callback_data='send'), InlineKeyboardButton("❌ Отменить", callback_data='cancel')]
    ]
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_custom_input(update, context):
    chat_id = update.message.chat_id
    text = update.message.text
    if chat_id in user_data and 'sender' not in user_data[chat_id]:
        user_data[chat_id]['sender'] = text
        await cargo_selection(chat_id, context)
    elif chat_id in user_data and 'quantity' not in user_data[chat_id]:
        user_data[chat_id]['quantity'] = text
        await preview_message_car(chat_id, context)

async def home(update, context):
    chat_id = update.message.chat_id
    user_data[chat_id].clear()
    await transport_selection(chat_id, context)

async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("home", home))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_input))

    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
