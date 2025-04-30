import tkinter as tk
from tkinter import ttk
from tkinter import font
import json
import os
import heapq

# Загрузка данных из JSON
with open(os.path.join(os.path.dirname(__file__), 'flight_graph.json'), encoding='utf-8') as f:
    flight_graph = json.load(f)

with open(os.path.join(os.path.dirname(__file__), 'city_coords.json'), encoding='utf-8') as f:
    city_coords = json.load(f)

# Преобразуем координаты к tuple, так как json сохраняет списки
city_coords = {k: tuple(v) for k, v in city_coords.items()}


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


# Цветовая схема
BG_COLOR = "#f0f0f0"
BUTTON_COLOR = "#4a7a8c"
BUTTON_TEXT = "#ffffff"
TEXT_COLOR = "#333333"
ROUTE_COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261"]
CITY_COLOR = "#1d3557"
LINE_COLOR = "#a8dadc"
MAP_BG = "#ffffff"
ECONOMY_COLOR = "#2a9d8f"
BUSINESS_COLOR = "#e63946"


class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Авиамаршруты с ценами")
        self.root.geometry("1200x800")
        self.root.configure(bg=BG_COLOR)

        # Масштаб и смещение карты
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_data = {"x": 0, "y": 0, "item": None}

        # Выбранный класс обслуживания
        self.flight_class = tk.StringVar(value="economy")
        self.sort_criteria = tk.StringVar(value="distance")

        self.setup_ui()
        self.draw_map()

    def setup_ui(self):
        # Стили
        style = ttk.Style()
        style.configure("TCombobox", padding=5)
        style.configure("TButton", padding=5, background=BUTTON_COLOR, foreground=BUTTON_TEXT)
        style.configure("TRadiobutton", background=BG_COLOR)

        # Главный фрейм
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Панель управления
        control_frame = tk.Frame(main_frame, bg=BG_COLOR)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Выбор городов
        tk.Label(control_frame, text="Откуда:", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, padx=5)
        self.start_combobox = ttk.Combobox(control_frame, values=list(flight_graph.keys()), width=20)
        self.start_combobox.grid(row=0, column=1, padx=5)

        tk.Label(control_frame, text="Куда:", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=2, padx=5)
        self.end_combobox = ttk.Combobox(control_frame, values=list(flight_graph.keys()), width=20)
        self.end_combobox.grid(row=0, column=3, padx=5)

        # Выбор критерия сортировки
        tk.Label(control_frame, text="Сортировать по:", bg=BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=4, padx=5)
        ttk.Radiobutton(control_frame, text="Расстоянию", variable=self.sort_criteria, value="distance").grid(row=0, column=5, padx=2)
        ttk.Radiobutton(control_frame, text="Цене", variable=self.sort_criteria, value="price").grid(row=0, column=6, padx=2)
        ttk.Radiobutton(control_frame, text="Удобству", variable=self.sort_criteria, value="comfort").grid(row=0, column=7, padx=2)

        # Кнопки
        ttk.Button(control_frame, text="Найти маршруты", command=self.show_routes).grid(row=0, column=8, padx=10)
        ttk.Button(control_frame, text="Сбросить", command=self.reset_map).grid(row=0, column=9, padx=5)

        # Фрейм для карты и информации
        content_frame = tk.Frame(main_frame, bg=BG_COLOR)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Холст для карты
        self.canvas = tk.Canvas(content_frame, bg=MAP_BG, bd=2, relief=tk.GROOVE)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Информационная панель
        info_frame = tk.Frame(content_frame, width=350, bg=BG_COLOR)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Прокрутка для текста
        scrollbar = tk.Scrollbar(info_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.routes_text = tk.Text(
            info_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=('Arial', 10)
        )
        self.routes_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.routes_text.yview)

        # Привязка событий
        self.canvas.bind("<MouseWheel>", self.zoom_map)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_map)
        self.routes_text.bind("<Button-1>", self.on_route_select)

        # Настройка текстовых тегов
        self.routes_text.tag_config("header", font=('Arial', 12, 'bold'), foreground="#1d3557")
        self.routes_text.tag_config("subheader", font=('Arial', 10, 'bold'), foreground="#457b9d")
        self.routes_text.tag_config("distance", font=('Arial', 10, 'italic'), foreground="#2a9d8f")
        self.routes_text.tag_config("price", font=('Arial', 10, 'italic'), foreground="#e63946")

    def draw_map(self):
        """Рисует карту с городами и связями"""
        self.canvas.delete("all")

        # Рисуем связи между городами
        for city, neighbors in flight_graph.items():
            if city in city_coords:
                x1, y1 = self.transform_coords(*city_coords[city])
                for neighbor in neighbors:
                    if neighbor in city_coords:
                        x2, y2 = self.transform_coords(*city_coords[neighbor])
                        self.canvas.create_line(
                            x1, y1, x2, y2,
                            fill=LINE_COLOR,
                            width=1,
                            dash=(2, 2),
                            tags="line"
                        )

        # Рисуем города (точки)
        for city, (x, y) in city_coords.items():
            tx, ty = self.transform_coords(x, y)
            self.canvas.create_oval(
                tx - 5, ty - 5, tx + 5, ty + 5,
                fill=CITY_COLOR,
                outline="black",
                tags=("city", city)
            )
            self.canvas.create_text(
                tx, ty - 15,
                text=city,
                font=('Arial', 8),
                anchor="center",
                tags=("city_label", city)
            )

    def transform_coords(self, x, y):
        """Преобразует координаты с учетом масштаба и смещения"""
        return (
            x * self.zoom_level + self.offset_x,
            y * self.zoom_level + self.offset_y
        )

    def zoom_map(self, event):
        """Масштабирование карты"""
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= factor

        # Масштабируем относительно курсора
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        self.offset_x = x - (x - self.offset_x) * factor
        self.offset_y = y - (y - self.offset_y) * factor

        self.draw_map()

    def start_drag(self, event):
        """Начало перетаскивания карты"""
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def drag_map(self, event):
        """Перетаскивание карты"""
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        self.offset_x += dx
        self.offset_y += dy

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        self.draw_map()

    def reset_map(self):
        """Сброс карты к исходному виду"""
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.draw_map()
        self.routes_text.delete(1.0, tk.END)

    def show_routes(self):
        """Отображает все найденные маршруты"""
        start_city = self.start_combobox.get()
        end_city = self.end_combobox.get()
        sort_criteria = self.sort_criteria.get()

        if not start_city or not end_city:
            tk.messagebox.showwarning("Ошибка", "Пожалуйста, выберите города отправления и назначения")
            return

        if start_city not in flight_graph or end_city not in flight_graph:
            tk.messagebox.showerror("Ошибка", "Один из городов не найден в базе данных")
            return

        self.routes_text.delete(1.0, tk.END)

        # Поиск всех маршрутов
        all_routes = find_all_routes(start_city, end_city)

        if not all_routes:
            self.routes_text.insert(tk.END, f"Нет маршрутов из {start_city} в {end_city}.")
            return

        # Сортировка маршрутов по выбранному критерию
        if sort_criteria == "distance":
            all_routes.sort(key=lambda x: x["distance"])
            sort_text = "по расстоянию"
        elif sort_criteria == "price":
            all_routes.sort(key=lambda x: x["price"])
            sort_text = "по цене"
        elif sort_criteria == "comfort":
            all_routes.sort(key=lambda x: -x["comfort"])
            sort_text = "по удобству"

        # Отображение кратчайших маршрутов
        self.routes_text.insert(tk.END, f"Маршруты из {start_city} в {end_city} (сортировка {sort_text}):\n\n", "header")

        # Кратчайший по расстоянию
        shortest_by_dist = dijkstra(start_city, end_city, "distance")
        if shortest_by_dist:
            self.routes_text.insert(tk.END, "\nСамый короткий маршрут:\n", "subheader")
            self.format_route_text(shortest_by_dist, 0)
            self.draw_route(shortest_by_dist["path"], 0)

        # Самый дешевый
        cheapest = dijkstra(start_city, end_city, "price")
        if cheapest:
            self.routes_text.insert(tk.END, "\nСамый дешевый маршрут:\n", "subheader")
            self.format_route_text(cheapest, 1)

        # Самый удобный
        most_comfortable = dijkstra(start_city, end_city, "comfort")
        if most_comfortable:
            self.routes_text.insert(tk.END, "\nСамый удобный маршрут:\n", "subheader")
            self.format_route_text(most_comfortable, 2)

        # Отображение всех маршрутов
        self.routes_text.insert(tk.END, "\nВсе маршруты:\n", "header")
        for i, route in enumerate(all_routes, 1):
            self.routes_text.insert(tk.END, f"\nМаршрут #{i}:\n", "subheader")
            self.format_route_text(route, i)

    def draw_route(self, route, color_index=0):
        """Подсвечивает выбранный маршрут на карте"""
        if not route:
            return

        # Сначала рисуем базовую карту
        self.draw_map()

        # Выбираем цвет из палитры
        color = ROUTE_COLORS[color_index % len(ROUTE_COLORS)]

        # Рисуем маршрут
        for i in range(len(route) - 1):
            start_city = route[i]
            end_city = route[i + 1]

            if start_city in city_coords and end_city in city_coords:
                x1, y1 = self.transform_coords(*city_coords[start_city])
                x2, y2 = self.transform_coords(*city_coords[end_city])

                # Рисуем линию маршрута
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=color,
                    width=3,
                    arrow=tk.LAST,
                    smooth=True,
                    tags="route"
                )

                # Подсвечиваем города маршрута
                self.canvas.create_oval(
                    x1 - 8, y1 - 8, x1 + 8, y1 + 8,
                    fill=color,
                    outline="black",
                    tags="route"
                )
                self.canvas.create_text(
                    x1, y1 - 20,
                    text=start_city,
                    font=('Arial', 9, 'bold'),
                    fill=color,
                    tags="route"
                )

        # Рисуем последний город
        last_city = route[-1]
        if last_city in city_coords:
            x, y = self.transform_coords(*city_coords[last_city])
            self.canvas.create_oval(
                x - 8, y - 8, x + 8, y + 8,
                fill=color,
                outline="black",
                tags="route"
            )
            self.canvas.create_text(
                x, y - 20,
                text=last_city,
                font=('Arial', 9, 'bold'),
                fill=color,
                tags="route"
            )

    def format_route_text(self, route, route_num):
        """Форматирует текст маршрута с подсветкой"""
        if not route:
            return

        path = route["path"]
        total_distance = route["distance"]
        total_price = route["price"]
        total_comfort = route.get("comfort", 0)

        # Определяем цвет для этого маршрута
        route_color = ROUTE_COLORS[route_num % len(ROUTE_COLORS)]

        # Отображаем каждый сегмент маршрута
        for j in range(len(path) - 1):
            from_city = path[j]
            to_city = path[j + 1]
            data = flight_graph[from_city][to_city]

            # Формируем текст сегмента
            segment_text = (f"{from_city} → {to_city} "
                           f"({data['distance']} км, "
                           f"{data['price']} руб, "
                           f"удобство: {data['comfort']}/10)")

            # Добавляем тег для возможности выбора маршрута
            tag_name = f"route_{route_num}_{j}"
            self.routes_text.insert(tk.END, segment_text, tag_name)

            # Если не последний сегмент, добавляем стрелку
            if j < len(path) - 2:
                self.routes_text.insert(tk.END, " → ", tag_name)

            # Настраиваем тег
            self.routes_text.tag_config(tag_name, foreground=route_color)
            self.routes_text.tag_bind(tag_name, "<Button-1>",
                                      lambda e, r=path: self.draw_route(r, route_num))

        # Добавляем итоговую информацию
        self.routes_text.insert(tk.END, f"\nОбщее расстояние: {total_distance} км\n", "distance")
        self.routes_text.insert(tk.END, f"Общая стоимость: {total_price} руб\n", "price")
        self.routes_text.insert(tk.END, f"Среднее удобство: {total_comfort:.1f}/10\n\n", "price")

    def on_route_select(self, event):
        """Обработчик выбора маршрута из текста"""
        index = self.routes_text.index(f"@{event.x},{event.y}")

        # Ищем все теги в позиции клика
        tags = self.routes_text.tag_names(index)

        # Ищем тег маршрута
        for tag in tags:
            if tag.startswith("route_"):
                parts = tag.split("_")
                route_num = int(parts[1])

                # Находим маршрут по номеру
                all_routes = find_all_routes(
                    self.start_combobox.get(),
                    self.end_combobox.get()
                )

                if all_routes and 0 < route_num <= len(all_routes):
                    route = all_routes[route_num - 1]["path"]
                    self.draw_route(route, route_num)
                break


if __name__ == "__main__":
    root = tk.Tk()
    app = MapApp(root)
    root.mainloop()