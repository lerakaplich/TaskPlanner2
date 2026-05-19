# windows/gantt/gantt_constants.py

from datetime import datetime

# Константы
PIXELS_PER_DAY = 40
TASK_HEIGHT = 28
TASK_VERTICAL_SPACING = 5
HEADER_HEIGHT = 50
ROW_HEIGHT = TASK_HEIGHT + TASK_VERTICAL_SPACING

# Цвета
COLOR_PRIMARY = "#D22730"      # Красный - активные задачи
COLOR_ACCENT = "#ccab6e"       # Золотистый - акценты
COLOR_BACKGROUND = "#1B232A"   # Темно-синий - фон
COLOR_SECONDARY = "#2C3640"    # Серо-синий - вторичный фон
COLOR_BORDER = "#3A4550"       # Границы
COLOR_COMPLETED = "#2E8B57"    # Зеленый - завершенные задачи
COLOR_OVERDUE = "#8B0000"      # Темно-красный - просроченные задачи
COLOR_TEXT = "#FFFFFF"         # Белый - текст
TODAY_COLOR = "#ccab6e"        # Золотистый - линия сегодня

TODAY = datetime.now().date()