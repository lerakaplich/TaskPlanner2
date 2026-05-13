# windows/analytics/rating/rating_employee_card.py

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal


class RatingEmployeeCard(QFrame):
    """Карточка сотрудника для рейтинга с КПД"""

    clicked = pyqtSignal(int)

    def __init__(self, employee_data, position=0, parent=None):
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position
        self._init_ui()

    def _init_ui(self):
        # Стили
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                margin: 4px 0;
            }
            QFrame:hover {
                background-color: #FAFAFA;
                border-color: #ccab6e;
            }
        """)

        # Убираем фиксированную высоту
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(70)

        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)

        # Позиция (место)
        position_colors = {
            1: "#FFD700",  # Золото
            2: "#C0C0C0",  # Серебро
            3: "#CD7F32"  # Бронза
        }
        color = position_colors.get(self.position + 1, "#E0E0E0")
        font_size = "24px" if self.position < 3 else "18px"

        position_label = QLabel(f"{self.position + 1}")
        position_label.setFixedSize(50, 50)
        position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        position_label.setStyleSheet(f"""
            background-color: {color};
            border-radius: 25px;
            font-size: {font_size};
            font-weight: bold;
            color: {'#333' if self.position < 3 else '#666'};
        """)
        main_layout.addWidget(position_label)

        # Информация о сотруднике
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # Имя
        name_label = QLabel(self.employee_data.get('name', 'Без имени'))
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        # Должность и отдел
        position_text = self.employee_data.get('position', '—')
        department = self.employee_data.get('department', '')
        if department and department != '—':
            position_text += f" · {department}"
        subdivision = self.employee_data.get('subdivision', '')
        if subdivision and subdivision != '—':
            position_text += f" · {subdivision}"

        dept_label = QLabel(position_text)
        dept_label.setStyleSheet("color: #666; font-size: 11px;")
        dept_label.setWordWrap(True)
        info_layout.addWidget(dept_label)

        # Статистика (выполнено/всего задач)
        completed_tasks = self.employee_data.get('completed_tasks', 0)
        total_tasks = self.employee_data.get('total_tasks', 0)
        stats_label = QLabel(f"📊 Выполнено задач: {completed_tasks} из {total_tasks}")
        stats_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(stats_label)

        main_layout.addLayout(info_layout, stretch=1)

        # КПД с процентами (НОВЫЙ АЛГОРИТМ)
        kpd_layout = QVBoxLayout()
        kpd_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Получаем новый КПД из данных (рассчитанный по сложному алгоритму)
        kpd_percent = self.employee_data.get('kpd_percent', 0)
        weighted_kpd = self.employee_data.get('weighted_kpd', 0)

        # Данные для расчета (для тултипа)
        overtime_hours = self.employee_data.get('overtime_hours', 0)

        # Если нового КПД нет, используем старый простой расчет
        if kpd_percent == 0 and total_tasks > 0:
            kpd_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Основной процент КПД
        kpd_label = QLabel(f"{kpd_percent:.1f}%")
        kpd_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Цвет в зависимости от КПД
        if kpd_percent >= 80:
            kpd_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2ecc71;")
        elif kpd_percent >= 60:
            kpd_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #f1c40f;")
        elif kpd_percent >= 40:
            kpd_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e67e22;")
        else:
            kpd_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e74c3c;")
        kpd_layout.addWidget(kpd_label)

        # Взвешенный КПД (более точный, учитывает сложность и приоритет)
        if weighted_kpd > 0 and weighted_kpd != kpd_percent:
            weighted_label = QLabel(f"взв: {weighted_kpd:.1f}%")
            weighted_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            weighted_label.setStyleSheet("color: #888; font-size: 10px;")
            kpd_layout.addWidget(weighted_label)

        # Прогресс-бар (Цвет меняется в зависимости от процента)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(kpd_percent))
        progress_bar.setFixedWidth(120)
        progress_bar.setFixedHeight(8)
        progress_bar.setTextVisible(False)

        # Выбираем цвет градиента в зависимости от КПД
        if kpd_percent >= 80:
            gradient = "stop:0 #2ecc71, stop:1 #27ae60"
        elif kpd_percent >= 60:
            gradient = "stop:0 #f1c40f, stop:1 #f39c12"
        elif kpd_percent >= 40:
            gradient = "stop:0 #e67e22, stop:1 #d35400"
        else:
            gradient = "stop:0 #e74c3c, stop:1 #c0392b"

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    {gradient});
                border-radius: 4px;
            }}
        """)
        kpd_layout.addWidget(progress_bar)

        # Количество часов переработок (если есть)
        if overtime_hours > 0:
            overtime_label = QLabel(f"⏱️ +{overtime_hours:.1f} ч")
            overtime_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            if overtime_hours > 40:
                overtime_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            elif overtime_hours > 20:
                overtime_label.setStyleSheet("color: #e67e22; font-size: 11px;")
            else:
                overtime_label.setStyleSheet("color: #2ecc71; font-size: 11px;")
            kpd_layout.addWidget(overtime_label)

        main_layout.addLayout(kpd_layout)

        # Создаем тултип с пояснением алгоритма расчета КПД
        tooltip_text = self._generate_kpd_tooltip(
            kpd_percent, weighted_kpd, overtime_hours,
            total_tasks, completed_tasks
        )
        self.setToolTip(tooltip_text)

        # Сделать карточку кликабельной
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _generate_kpd_tooltip(self, kpd_percent, weighted_kpd, overtime_hours, total_tasks, completed_tasks):
        """Генерирует пояснение алгоритма расчета КПД"""

        # Формула расчета
        formula = """📐 ФОРМУЛА РАСЧЕТА КПД:

KPD = (Дедлайн × Приоритет × Прогресс × Сложность) / 2 × 100%

Где:
• Дедлайн = коэффициент соблюдения срока
  - Выполнено раньше срока: 1.1-1.5
  - Выполнено в срок: 1.0
  - Небольшое опоздание: 0.5-0.9
  - Просрочено: 0-0.4
  - Нет дедлайна: 0.8

• Приоритет = вес задачи
  - Низкий: 0.5
  - Средний: 1.0
  - Высокий: 1.5
  - Критический: 2.0

• Прогресс = коэф. выполнения (0-1.2)
  - 0%: 0.0
  - 50%: ~0.42
  - 100%: 1.2 (бонус)

• Сложность = вес задачи (0-1.5)
  - 0★: 0.5
  - 1★: 0.6
  - 2★: 0.8
  - 3★: 1.0
  - 4★: 1.2
  - 5★: 1.5"""

        # Статистика сотрудника
        stats = f"""
📊 ВАША СТАТИСТИКА:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Выполнено задач: {completed_tasks}
📋 Всего задач: {total_tasks}
⚡ Итоговый КПД: {kpd_percent:.1f}%
{'🎯 Взвешенный КПД: ' + str(weighted_kpd) + '%' if weighted_kpd > 0 else ''}
{'⏱️ Часы переработок: ' + str(overtime_hours) + ' ч.' if overtime_hours > 0 else ''}

💡 Штраф за переработки:
   Более 20ч: -5%
   Более 40ч: -10%
   Более 60ч: -15%"""

        # Интерпретация результата
        interpretation = ""
        if kpd_percent >= 80:
            interpretation = """
🏆 ИНТЕРПРЕТАЦИЯ: ОТЛИЧНО!
   Вы показываете высокую эффективность.
   Задачи выполняются качественно и в срок.
   Продолжайте в том же духе!"""
        elif kpd_percent >= 60:
            interpretation = """
👍 ИНТЕРПРЕТАЦИЯ: ХОРОШО!
   Хороший результат, но есть куда расти.
   Обратите внимание на соблюдение дедлайнов."""
        elif kpd_percent >= 40:
            interpretation = """
⚠️ ИНТЕРПРЕТАЦИЯ: СРЕДНЕ
   Результат ниже целевого.
   Рекомендуется улучшить планирование задач
   и соблюдение сроков выполнения."""
        else:
            interpretation = """
❌ ИНТЕРПРЕТАЦИЯ: ТРЕБУЕТ УЛУЧШЕНИЯ
   Низкая эффективность.
   Необходимо пересмотреть подход к работе:
   - Соблюдайте дедлайны
   - Повышайте приоритет важных задач
   - Старайтесь завершать начатые задачи"""

        return f"{formula}\n{stats}\n{interpretation}"

    def mousePressEvent(self, event):
        self.clicked.emit(self.employee_id)
        super().mousePressEvent(event)