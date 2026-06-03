import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8842282443:AAFvXwa1LfGeAX3eWp23a-gubQo4etDu_Dc"

DATA_FILE = "data.json"
FILES_DIR = "files"

# ===== ИНИЦИАЛИЗАЦИЯ =====
os.makedirs(FILES_DIR, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "objects": {},  # { "объект": { "address": "", "invoices": {}, "dopusk": [] } }
        "current_user": {}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== КНОПКИ =====
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton("📦 Мои объекты", callback_data="my_objects")],
        [InlineKeyboardButton("➕ Создать объект", callback_data="create_object")],
        [InlineKeyboardButton("📄 Дозаказы", callback_data="dopusk_menu")],
        [InlineKeyboardButton("📊 Общая сводка", callback_data="global_summary")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_object_keyboard(obj_name):
    buttons = [
        [InlineKeyboardButton("🧾 Список счетов", callback_data=f"invoices_{obj_name}")],
        [InlineKeyboardButton("➕ Добавить счёт", callback_data=f"add_invoice_{obj_name}")],
        [InlineKeyboardButton("📁 Все файлы объекта", callback_data=f"files_{obj_name}")],
        [InlineKeyboardButton("📊 Статус объекта", callback_data=f"status_{obj_name}")],
        [InlineKeyboardButton("◀ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_invoice_keyboard(obj_name, invoice_name):
    buttons = [
        [InlineKeyboardButton("📄 Показать файл", callback_data=f"view_file_{obj_name}_{invoice_name}")],
        [InlineKeyboardButton("📋 Список позиций", callback_data=f"positions_{obj_name}_{invoice_name}")],
        [InlineKeyboardButton("➕ Добавить позицию", callback_data=f"add_position_{obj_name}_{invoice_name}")],
        [InlineKeyboardButton("🚦 Статус счёта", callback_data=f"invoice_status_{obj_name}_{invoice_name}")],
        [InlineKeyboardButton("🗑 Удалить счёт", callback_data=f"delete_invoice_{obj_name}_{invoice_name}")],
        [InlineKeyboardButton("◀ К объекту", callback_data=f"to_object_{obj_name}")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_status_keyboard(obj_name, invoice_name):
    statuses = ["в оплате", "оплачено", "в пути", "на складе", "на объекте"]
    buttons = []
    for status in statuses:
        buttons.append([InlineKeyboardButton(status, callback_data=f"set_status_{obj_name}_{invoice_name}_{status}")])
    buttons.append([InlineKeyboardButton("◀ Назад", callback_data=f"back_to_invoice_{obj_name}_{invoice_name}")])
    return InlineKeyboardMarkup(buttons)

# ===== ОСНОВНЫЕ КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["objects"]:
        data["objects"] = {}
        save_data(data)
    
    await update.message.reply_text(
        "🏗 *Бот-комплектатор* (вентиляция и кондиционирование)\n\n"
        "Что хочешь сделать?",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# ===== ОБЪЕКТЫ =====
async def my_objects(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    data = load_data()
    objects = list(data["objects"].keys())
    
    if not objects:
        text = "📭 Нет ни одного объекта. Создай первый через ➕ Создать объект"
        if query:
            await query.edit_message_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return
    
    buttons = []
    for obj in objects:
        buttons.append([InlineKeyboardButton(f"🏠 {obj}", callback_data=f"open_object_{obj}")])
    buttons.append([InlineKeyboardButton("◀ Назад", callback_data="back_to_main")])
    
    if query:
        await query.edit_message_text("📦 *Выбери объект:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.message.reply_text("📦 *Выбери объект:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def create_object(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    context.user_data["waiting_for_object_name"] = True
    text = "✏️ *Напиши название нового объекта:*\n\nНапример: `Коттедж Лесная 15`"
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def open_object(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, query=None):
    data = load_data()
    if obj_name not in data["objects"]:
        data["objects"][obj_name] = {"address": "", "invoices": {}, "dopusk": []}
        save_data(data)
    
    address = data["objects"][obj_name].get("address", "")
    text = f"🏠 *{obj_name}*\n📍 {address if address else 'адрес не указан'}\n\nЧто хочешь сделать?"
    
    if query:
        await query.edit_message_text(text, reply_markup=get_object_keyboard(obj_name), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_object_keyboard(obj_name), parse_mode="Markdown")

# ===== СЧЕТА =====
async def add_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, query=None):
    context.user_data["waiting_for_invoice"] = {"obj_name": obj_name}
    text = f"✏️ *Добавление счёта для {obj_name}*\n\n1. *Сначала напиши название счёта* (например: `Счёт №123 от 10.06`)\n\nПосле этого я попрошу загрузить файл и указать поставщика."
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def show_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, query=None):
    data = load_data()
    invoices = data["objects"].get(obj_name, {}).get("invoices", {})
    
    if not invoices:
        text = "📭 Нет ни одного счёта. Добавь через ➕ Добавить счёт"
        if query:
            await query.edit_message_text(text, reply_markup=get_object_keyboard(obj_name))
        return
    
    buttons = []
    for inv_name, inv_data in invoices.items():
        status = inv_data.get("status", "нет статуса")
        supplier = inv_data.get("supplier", "?")
        buttons.append([InlineKeyboardButton(f"🧾 {inv_name} [{status}]", callback_data=f"open_invoice_{obj_name}_{inv_name}")])
    buttons.append([InlineKeyboardButton("◀ Назад", callback_data=f"to_object_{obj_name}")])
    
    if query:
        await query.edit_message_text(f"🧾 *Счета для {obj_name}:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def open_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    data = load_data()
    invoice = data["objects"].get(obj_name, {}).get("invoices", {}).get(invoice_name, {})
    
    text = f"🧾 *{invoice_name}*\n"
    text += f"📦 Поставщик: {invoice.get('supplier', 'не указан')}\n"
    text += f"🚦 Статус: {invoice.get('status', 'нет статуса')}\n"
    text += f"📅 Создан: {invoice.get('date', 'неизвестно')}\n"
    text += f"📁 Файл: {'есть' if invoice.get('file_path') else 'нет'}\n"
    text += f"📋 Позиций: {len(invoice.get('positions', {}))}"
    
    if query:
        await query.edit_message_text(text, reply_markup=get_invoice_keyboard(obj_name, invoice_name), parse_mode="Markdown")

async def set_invoice_status(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    if query:
        await query.edit_message_text(f"🚦 *Выбери статус для {invoice_name}:*", reply_markup=get_status_keyboard(obj_name, invoice_name), parse_mode="Markdown")

async def save_invoice_status(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, status: str, query=None):
    data = load_data()
    if obj_name in data["objects"] and invoice_name in data["objects"][obj_name]["invoices"]:
        data["objects"][obj_name]["invoices"][invoice_name]["status"] = status
        save_data(data)
        
        if query:
            await query.edit_message_text(f"✅ Статус счёта *{invoice_name}* изменён на: *{status}*", parse_mode="Markdown")
            await open_invoice(update, context, obj_name, invoice_name, query)

# ===== ПОЗИЦИИ =====
async def show_positions(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    data = load_data()
    positions = data["objects"].get(obj_name, {}).get("invoices", {}).get(invoice_name, {}).get("positions", {})
    
    if not positions:
        text = "📭 Нет позиций. Добавь через ➕ Добавить позицию"
        if query:
            await query.edit_message_text(text, reply_markup=get_invoice_keyboard(obj_name, invoice_name))
        return
    
    text = f"📋 *Позиции в {invoice_name}:*\n\n"
    for pos_name, pos_data in positions.items():
        text += f"• {pos_name}\n"
        text += f"  └ кол-во: {pos_data.get('qty', '?')} | статус: {pos_data.get('status', '⏳')} | цена: {pos_data.get('price', '?')}\n\n"
    
    buttons = [[InlineKeyboardButton("◀ Назад", callback_data=f"back_to_invoice_{obj_name}_{invoice_name}")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def add_position(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    context.user_data["waiting_for_position"] = {"obj_name": obj_name, "invoice_name": invoice_name}
    text = "✏️ *Добавление позиции*\n\nНапиши в формате:\n`Название | количество | поставщик | цена`\n\nПример:\n`Вентилятор VKO-200 | 2 шт | Техноклимат | 12500`"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

# ===== ФАЙЛЫ =====
async def view_file(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    data = load_data()
    file_path = data["objects"].get(obj_name, {}).get("invoices", {}).get(invoice_name, {}).get("file_path")
    
    if file_path and os.path.exists(file_path):
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, "rb"))
        if query:
            await query.answer("📁 Файл отправлен")
    else:
        if query:
            await query.edit_message_text("❌ Файл не найден", reply_markup=get_invoice_keyboard(obj_name, invoice_name))

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, query=None):
    data = load_data()
    invoices = data["objects"].get(obj_name, {}).get("invoices", {})
    
    text = f"📁 *Файлы объекта {obj_name}:*\n\n"
    has_files = False
    for inv_name, inv_data in invoices.items():
        if inv_data.get("file_path"):
            has_files = True
            text += f"• {inv_name} — есть файл\n"
        else:
            text += f"• {inv_name} — ❌ нет файла\n"
    
    if not has_files:
        text = "📭 Нет загруженных файлов"
    
    buttons = [[InlineKeyboardButton("◀ Назад", callback_data=f"to_object_{obj_name}")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# ===== СТАТУСЫ =====
async def object_status(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, query=None):
    data = load_data()
    obj_data = data["objects"].get(obj_name, {})
    invoices = obj_data.get("invoices", {})
    
    total_items = 0
    ordered = 0
    in_warehouse = 0
    on_site = 0
    
    for inv_name, inv_data in invoices.items():
        for pos_name, pos_data in inv_data.get("positions", {}).items():
            total_items += 1
            status = pos_data.get("status", "")
            if "заказано" in status.lower() or "в пути" in inv_data.get("status", "").lower():
                ordered += 1
            if "склад" in inv_data.get("status", "").lower():
                in_warehouse += 1
            if "объект" in inv_data.get("status", "").lower():
                on_site += 1
    
    text = f"📊 *Статус объекта: {obj_name}*\n\n"
    text += f"📦 Всего позиций: {total_items}\n"
    text += f"🚚 В заказе/пути: {ordered}\n"
    text += f"🏚 На складе: {in_warehouse}\n"
    text += f"✅ На объекте: {on_site}\n"
    
    buttons = [[InlineKeyboardButton("◀ Назад", callback_data=f"to_object_{obj_name}")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# ===== ДОЗАКАЗЫ =====
async def dopusk_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    data = load_data()
    all_dopusk = []
    
    for obj_name, obj_data in data["objects"].items():
        for req in obj_data.get("dopusk", []):
            all_dopusk.append(f"🏠 {obj_name}: {req}")
    
    if not all_dopusk:
        text = "📝 Нет активных заявок на дозаказ"
    else:
        text = "📝 *Заявки на дозаказ:*\n\n" + "\n".join(all_dopusk[-10:])
    
    buttons = [[InlineKeyboardButton("➕ Добавить дозаказ", callback_data="add_dopusk")],
               [InlineKeyboardButton("◀ Назад", callback_data="back_to_main")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def add_dopusk(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    context.user_data["waiting_for_dopusk"] = True
    text = "✏️ *Напиши заявку на дозаказ*\n\nПример: `Коттедж Лесная — не хватает 4 хомута 250 мм`"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

# ===== ОБЩАЯ СВОДКА =====
async def global_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    data = load_data()
    objects = data["objects"]
    
    text = "📊 *Общая сводка по всем объектам*\n\n"
    for obj_name, obj_data in objects.items():
        invoices = obj_data.get("invoices", {})
        total_positions = 0
        for inv_data in invoices.values():
            total_positions += len(inv_data.get("positions", {}))
        text += f"🏠 *{obj_name}* — {len(invoices)} счетов, {total_positions} позиций\n"
    
    buttons = [[InlineKeyboardButton("◀ Назад", callback_data="back_to_main")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# ===== УДАЛЕНИЕ =====
async def delete_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, obj_name: str, invoice_name: str, query=None):
    data = load_data()
    file_path = data["objects"].get(obj_name, {}).get("invoices", {}).get(invoice_name, {}).get("file_path")
    
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    del data["objects"][obj_name]["invoices"][invoice_name]
    save_data(data)
    
    await query.edit_message_text(f"✅ Счёт *{invoice_name}* удалён", parse_mode="Markdown")
    await show_invoices(update, context, obj_name, query)

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = load_data()
    
    # Создание объекта
    if context.user_data.get("waiting_for_object_name"):
        obj_name = text.strip()
        if obj_name not in data["objects"]:
            data["objects"][obj_name] = {"address": "", "invoices": {}, "dopusk": []}
            save_data(data)
        context.user_data["waiting_for_object_name"] = False
        await update.message.reply_text(f"✅ Объект *{obj_name}* создан!", parse_mode="Markdown")
        await open_object(update, context, obj_name)
        return
    
    # Добавление счёта
    if context.user_data.get("waiting_for_invoice"):
        invoice_name = text.strip()
        context.user_data["invoice_temp"] = invoice_name
        obj_name = context.user_data["waiting_for_invoice"]["obj_name"]
        context.user_data["waiting_for_invoice_supplier"] = {"obj_name": obj_name, "invoice_name": invoice_name}
        context.user_data["waiting_for_invoice"] = False
        await update.message.reply_text(f"✏️ Хорошо, счёт будет называться *{invoice_name}*\n\nТеперь напиши *название поставщика*", parse_mode="Markdown")
        return
    
    if context.user_data.get("waiting_for_invoice_supplier"):
        supplier = text.strip()
        obj_name = context.user_data["waiting_for_invoice_supplier"]["obj_name"]
        invoice_name = context.user_data["waiting_for_invoice_supplier"]["invoice_name"]
        context.user_data["waiting_for_invoice_file"] = {"obj_name": obj_name, "invoice_name": invoice_name, "supplier": supplier}
        context.user_data["waiting_for_invoice_supplier"] = False
        await update.message.reply_text(f"✅ Поставщик: {supplier}\n\n📎 *Теперь отправь файл счёта* (PDF, фото или Excel)", parse_mode="Markdown")
        return
    
    # Добавление позиции
    if context.user_data.get("waiting_for_position"):
        parts = text.split("|")
        if len(parts) >= 2:
            name = parts[0].strip()
            qty = parts[1].strip() if len(parts) > 1 else "?"
            supplier = parts[2].strip() if len(parts) > 2 else ""
            price = parts[3].strip() if len(parts) > 3 else ""
            
            obj_name = context.user_data["waiting_for_position"]["obj_name"]
            invoice_name = context.user_data["waiting_for_position"]["invoice_name"]
            
            if obj_name in data["objects"] and invoice_name in data["objects"][obj_name]["invoices"]:
                data["objects"][obj_name]["invoices"][invoice_name].setdefault("positions", {})
                data["objects"][obj_name]["invoices"][invoice_name]["positions"][name] = {
                    "qty": qty,
                    "status": "ожидает",
                    "supplier": supplier,
                    "price": price,
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                save_data(data)
                context.user_data["waiting_for_position"] = False
                await update.message.reply_text(f"✅ Добавлена позиция: {name} ({qty})", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Ошибка: счёт не найден")
        else:
            await update.message.reply_text("❌ Неправильный формат. Используй:\n`Название | количество | поставщик | цена`")
        return
    
    # Дозаказ
    if context.user_data.get("waiting_for_dopusk"):
        # Попробуем определить объект из текста
        text_lower = text.lower()
        matched_obj = None
        for obj_name in data["objects"].keys():
            if obj_name.lower() in text_lower:
                matched_obj = obj_name
                break
        
        if matched_obj:
            data["objects"][matched_obj].setdefault("dopusk", []).append(text)
            save_data(data)
            await update.message.reply_text(f"📝 Заявка на дозаказ добавлена для объекта *{matched_obj}*", parse_mode="Markdown")
        else:
            # Если объект не определился, спросим
            context.user_data["dopusk_text"] = text
            await update.message.reply_text("❓ К какому объекту относится этот дозаказ?\n\nНапиши название объекта из списка:")
            objects_list = list(data["objects"].keys())
            if objects_list:
                await update.message.reply_text("\n".join(objects_list))
            context.user_data["waiting_for_dopusk_object"] = True
            return
        
        context.user_data["waiting_for_dopusk"] = False
        return
    
    if context.user_data.get("waiting_for_dopusk_object"):
        obj_name = text.strip()
        data = load_data()
        dopusk_text = context.user_data.get("dopusk_text", "")
        if obj_name in data["objects"]:
            data["objects"][obj_name].setdefault("dopusk", []).append(dopusk_text)
            save_data(data)
            await update.message.reply_text(f"📝 Заявка на дозаказ добавлена для объекта *{obj_name}*", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Объект *{obj_name}* не найден", parse_mode="Markdown")
        context.user_data["waiting_for_dopusk_object"] = False
        context.user_data["dopusk_text"] = None
        return
    
    await update.message.reply_text("Используй кнопки 👇", reply_markup=get_main_keyboard())

# ===== ОБРАБОТЧИК ФАЙЛОВ =====
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_invoice_file"):
        obj_name = context.user_data["waiting_for_invoice_file"]["obj_name"]
        invoice_name = context.user_data["waiting_for_invoice_file"]["invoice_name"]
        supplier = context.user_data["waiting_for_invoice_file"]["supplier"]
        
        file = update.message.document or update.message.photo[-1] if update.message.photo else None
        if not file:
            await update.message.reply_text("❌ Пожалуйста, отправь файл (PDF, фото или Excel)")
            return
        
        # Сохраняем файл
        obj_dir = os.path.join(FILES_DIR, obj_name)
        os.makedirs(obj_dir, exist_ok=True)
        
        file_ext = "jpg" if update.message.photo else file.file_name.split(".")[-1] if hasattr(file, 'file_name') else "file"
        safe_invoice_name = invoice_name.replace("/", "_").replace(" ", "_")
        file_path = os.path.join(obj_dir, f"{safe_invoice_name}.{file_ext}")
        
        if update.message.document:
            new_file = await context.bot.get_file(file.file_id)
            await new_file.download_to_drive(file_path)
        else:
            new_file = await context.bot.get_file(file.file_id)
            await new_file.download_to_drive(file_path)
        
        # Сохраняем в data.json
        data = load_data()
        if obj_name not in data["objects"]:
            data["objects"][obj_name] = {"address": "", "invoices": {}, "dopusk": []}
        
        data["objects"][obj_name]["invoices"][invoice_name] = {
            "supplier": supplier,
            "status": "в оплате",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "file_path": file_path,
            "positions": {}
        }
        save_data(data)
        
        context.user_data["waiting_for_invoice_file"] = False
        await update.message.reply_text(f"✅ Счёт *{invoice_name}* создан!\n📦 Поставщик: {supplier}\n📁 Файл сохранён", parse_mode="Markdown")
        await open_invoice(update, context, obj_name, invoice_name)
        return
    
    await update.message.reply_text("Я ждал файл для счёта, но что-то пошло не так. Попробуй заново через Добавить счёт")

# ===== ОБРАБОТЧИК КНОПОК =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Главное меню
    if data == "back_to_main":
        await query.edit_message_text("🏗 *Главное меню*", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return
    
    if data == "my_objects":
        await my_objects(update, context, query)
        return
    
    if data == "create_object":
        await create_object(update, context, query)
        return
    
    if data == "dopusk_menu":
        await dopusk_menu(update, context, query)
        return
    
    if data == "add_dopusk":
        await add_dopusk(update, context, query)
        return
    
    if data == "global_summary":
        await global_summary(update, context, query)
        return
    
    # Открытие объекта
    if data.startswith("open_object_"):
        obj_name = data.replace("open_object_", "")
        await open_object(update, context, obj_name, query)
        return
    
    if data.startswith("to_object_"):
        obj_name = data.replace("to_object_", "")
        await open_object(update, context, obj_name, query)
        return
    
    # Счета
    if data.startswith("invoices_"):
        obj_name = data.replace("invoices_", "")
        await show_invoices(update, context, obj_name, query)
        return
    
    if data.startswith("add_invoice_"):
        obj_name = data.replace("add_invoice_", "")
        await add_invoice(update, context, obj_name, query)
        return
    
    if data.startswith("open_invoice_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await open_invoice(update, context, obj_name, invoice_name, query)
        return
    
    if data.startswith("back_to_invoice_"):
        parts = data.split("_", 4)
        if len(parts) >= 5:
            obj_name = parts[3]
            invoice_name = parts[4]
            await open_invoice(update, context, obj_name, invoice_name, query)
        return
    
    if data.startswith("invoice_status_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await set_invoice_status(update, context, obj_name, invoice_name, query)
        return
    
    if data.startswith("set_status_"):
        parts = data.split("_", 4)
        if len(parts) >= 5:
            obj_name = parts[2]
            invoice_name = parts[3]
            status = parts[4]
            await save_invoice_status(update, context, obj_name, invoice_name, status, query)
        return
    
    # Позиции
    if data.startswith("positions_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await show_positions(update, context, obj_name, invoice_name, query)
        return
    
    if data.startswith("add_position_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await add_position(update, context, obj_name, invoice_name, query)
        return
    
    # Файлы
    if data.startswith("files_"):
        obj_name = data.replace("files_", "")
        await list_files(update, context, obj_name, query)
        return
    
    if data.startswith("view_file_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await view_file(update, context, obj_name, invoice_name, query)
        return
    
    # Статус объекта
    if data.startswith("status_"):
        obj_name = data.replace("status_", "")
        await object_status(update, context, obj_name, query)
        return
    
    # Удаление
    if data.startswith("delete_invoice_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            obj_name = parts[2]
            invoice_name = parts[3]
            await delete_invoice(update, context, obj_name, invoice_name, query)
        return

# ===== ЗАПУСК =====
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, file_handler))
    
    print("🚀 Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()