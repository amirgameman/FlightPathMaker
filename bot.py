import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import json
import os
import heapq
from PIL import Image, ImageDraw, ImageFont
import io

# Загрузка данных из JSON (аналогично вашему коду)
with open(os.path.join(os.path.dirname(__file__), 'flight_graph.json'), encoding='utf-8') as f:
    flight_graph = json.load(f)

with open(os.path.join(os.path.dirname(__file__), 'city_coords.json'), encoding='utf-8') as f:
    city_coords = json.load(f)

# Преобразуем координаты к tuple, так как json сохраняет списки
city_coords = {k: tuple(v) for k, v in city_coords.items()}

# Токен вашего бота (замените на свой)
BOT_TOKEN = "BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# Using a dictionary to store user data
user_data = {}

print("Работаем аааааа")

# Функции для поиска пути
def find_all_routes(start, end, max_depth=5):
    def dfs(current, path, total_distance, total_price, total_comfort, path_details):
        if len(path) > max_depth + 1:
            return
        if current == end:
            routes.append({
                "path": path[:],
                "distance": total_distance,
                "price": total_price,
                "comfort": total_comfort / (len(path) - 1) if len(path) > 1 else 0,
                "details": path_details[:]
            })
            return
        for neighbor, data in flight_graph.get(current, {}).items():
            if neighbor not in path:  # избегаем циклов
                path.append(neighbor)
                path_details.append({
                    "from": current,
                    "to": neighbor,
                    "distance": data["distance"],
                    "price": data["price"],
                    "comfort": data["comfort"]
                })
                dfs(neighbor, path,
                    total_distance + data["distance"],
                    total_price + data["price"],
                    total_comfort + data["comfort"],
                    path_details)
                path.pop()
                path_details.pop()

    routes = []
    dfs(start, [start], 0, 0, 0, [])
    return routes


def dijkstra(start, end, criteria="distance"):
    """Поиск кратчайшего пути по различным критериям"""
    if criteria == "distance":
        queue = [(0, start, [start], 0, 0)]  # (distance, current, path, price, comfort)
    elif criteria == "price":
        queue = [(0, start, [start], 0, 0)]  # (price, current, path, distance, comfort)
    elif criteria == "comfort":
        queue = [(-0, start, [start], 0, 0)]  # (-comfort, current, path, distance, price)

    visited = set()

    while queue:
        if criteria == "distance":
            dist, current, path, total_price, total_comfort = heapq.heappop(queue)
        elif criteria == "price":
            total_price, current, path, dist, total_comfort = heapq.heappop(queue)
        elif criteria == "comfort":
            neg_comfort, current, path, dist, total_price = heapq.heappop(queue)
            total_comfort = -neg_comfort

        if current == end:
            avg_comfort = total_comfort / (len(path) - 1) if len(path) > 1 else 0
            return {
                "path": path,
                "distance": dist,
                "price": total_price,
                "comfort": avg_comfort,
                "details": get_route_details(path)
            }
        if current in visited:
            continue
        visited.add(current)

        for neighbor, data in flight_graph.get(current, {}).items():
            if neighbor not in visited:
                new_dist = dist + data["distance"]
                new_price = total_price + data["price"]
                new_comfort = total_comfort + data["comfort"]

                if criteria == "distance":
                    heapq.heappush(queue, (new_dist, neighbor, path + [neighbor], new_price, new_comfort))
                elif criteria == "price":
                    heapq.heappush(queue, (new_price, neighbor, path + [neighbor], new_dist, new_comfort))
                elif criteria == "comfort":
                    heapq.heappush(queue, (-new_comfort, neighbor, path + [neighbor], new_dist, new_price))

    return None


def get_route_details(route):
    details = []
    for i in range(len(route) - 1):
        from_city = route[i]
        to_city = route[i + 1]
        data = flight_graph[from_city][to_city]
        details.append({
            "from": from_city,
            "to": to_city,
            "distance": data["distance"],
            "price": data["price"],
            "comfort": data["comfort"]
        })
    return details


# Функции для генерации картинки (переработаны для telebot)
def generate_map_image(route):
    """Генерирует картинку с маршрутом"""
    if not route:
        return None

    # Размеры изображения
    img_width = 800
    img_height = 600
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    # Цветовая схема
    ROUTE_COLOR = (230, 57, 70)  # Красный
    CITY_COLOR = (29, 53, 87)
    LINE_COLOR = (168, 218, 220)
    TEXT_COLOR = (0, 0, 0)

    # Шрифт (замените на свой путь к шрифту, если нужно)
    try:
        # Explicitly use UTF-8 for text encoding in font loading
        font = ImageFont.truetype("arial.ttf", size=12, encoding="utf-8")  # or another font path
    except IOError:
        print("arial.ttf not found. Using default font.")
        font = ImageFont.load_default()


    def transform_coords(x, y):
        """Преобразует координаты для масштабирования"""
        scale = 0.8  # adjust scale as needed
        offset_x = 50
        offset_y = 50
        return (
            int(x * scale + offset_x),
            int(y * scale + offset_y)
        )

    # Рисуем связи между городами
    for city, neighbors in flight_graph.items():
        if city in city_coords:
            x1, y1 = transform_coords(*city_coords[city])
            for neighbor in neighbors:
                if neighbor in city_coords:
                    x2, y2 = transform_coords(*city_coords[neighbor])
                    draw.line((x1, y1, x2, y2), fill=LINE_COLOR, width=1)

    # Рисуем города и подписи
    for city, (x, y) in city_coords.items():
        tx, ty = transform_coords(x, y)
        draw.ellipse((tx - 5, ty - 5, tx + 5, ty + 5), fill=CITY_COLOR, outline="black")
        try:
           draw.text((tx, ty - 10), city, fill=TEXT_COLOR, font=font, anchor="ms") # Adjusted anchor
        except UnicodeEncodeError as e:
            print(f"Skipping city label {city} due to encoding error: {e}")
            # Если ошибка кодировки, можно заменить текст на что-то нейтральное или пропустить его.
            # Например:
            # draw.text((tx, ty - 10), "???", fill=TEXT_COLOR, font=font, anchor="ms")
            # Или просто пропустить строку:
            pass  # or continue

    # Рисуем маршрут
    for i in range(len(route) - 1):
        start_city = route[i]
        end_city = route[i + 1]

        if start_city in city_coords and end_city in city_coords:
            x1, y1 = transform_coords(*city_coords[start_city])
            x2, y2 = transform_coords(*city_coords[end_city])
            draw.line((x1, y1, x2, y2), fill=ROUTE_COLOR, width=3, joint="curve")

    # Convert image to bytes for telebot
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0) # Reset the stream position to the beginning

    return img_bytes


# Handler для /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}  # Initialize user data for this chat
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in flight_graph.keys():
        markup.add(KeyboardButton(city))
    bot.send_message(chat_id, "Выберите город отправления:", reply_markup=markup)
    bot.register_next_step_handler(message, get_destination_city)


# Handler для выбора города отправления
def get_destination_city(message):
    chat_id = message.chat.id
    start_city = message.text
    if start_city not in flight_graph:
        bot.send_message(chat_id, "Город отправления не найден. Пожалуйста, начните заново /start.")
        return

    user_data[chat_id]['start_city'] = start_city  # Save start city
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in flight_graph.keys():
        markup.add(KeyboardButton(city))
    bot.send_message(chat_id, "Выберите город назначения:", reply_markup=markup)
    bot.register_next_step_handler(message, get_criteria)


# Handler для выбора города назначения
def get_criteria(message):
    chat_id = message.chat.id
    end_city = message.text
    start_city = user_data[chat_id]['start_city']  # Retrieve start city

    if end_city not in flight_graph:
        bot.send_message(chat_id, "Город назначения не найден. Пожалуйста, начните заново /start.")
        return

    user_data[chat_id]['end_city'] = end_city  # Save end city
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Кратчайший путь"))
    markup.add(KeyboardButton("Самый удобный путь"))
    markup.add(KeyboardButton("Самый дешевый путь"))
    bot.send_message(chat_id, "Выберите критерий поиска:", reply_markup=markup)
    bot.register_next_step_handler(message, find_route)


# Handler для поиска пути
def find_route(message):
    chat_id = message.chat.id
    criteria_text = message.text
    start_city = user_data[chat_id]['start_city']
    end_city = user_data[chat_id]['end_city']

    if criteria_text == "Кратчайший путь":
        criteria = "distance"
        criterion_description = "кратчайший"
    elif criteria_text == "Самый удобный путь":
        criteria = "comfort"
        criterion_description = "самый удобный"
    elif criteria_text == "Самый дешевый путь":
        criteria = "price"
        criterion_description = "самый дешевый"
    else:
        bot.send_message(chat_id, "Неверный критерий выбора. Пожалуйста, начните заново /start.")
        return

    result = dijkstra(start_city, end_city, criteria)

    if result:
        # Format the route details
        path_str = " → ".join(result["path"])
        details_str = "\n".join([
            f"  {detail['from']} → {detail['to']}: {detail['distance']} км, {detail['price']} руб, удобство: {detail['comfort']}/10"
            for detail in result.get("details",[])
        ])
        message_text = (
            f"Найден {criterion_description} путь из {start_city} в {end_city}:\n"
            f"  Маршрут: {path_str}\n"
            f"  Общее расстояние: {result['distance']} км\n"
            f"  Общая стоимость: {result['price']} руб\n"
            f"  Среднее удобство: {result.get('comfort', 0):.1f}/10\n"
            f"\nДетали:\n{details_str}"
        )
        bot.send_message(chat_id, message_text)

        # Generate and send the map image
        image = generate_map_image(result["path"])
        if image:
            bot.send_photo(chat_id, photo=image)
        else:
            bot.send_message(chat_id, "Не удалось сгенерировать изображение карты.")
    else:
        bot.send_message(chat_id, f"Не удалось найти путь из {start_city} в {end_city} по критерию {criteria_text.lower()}.")

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("/start"))
    bot.send_message(chat_id, "Вы можете начать новый поиск", reply_markup=markup)


# Запуск бота
bot.infinity_polling()