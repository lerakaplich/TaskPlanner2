# windows/analytics/rating/rating_employee_card.py

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal


class RatingEmployeeCard(QFrame):
    """Карточка сотрудника для рейтинга с КПД (использует новые поля)"""

    clicked = pyqtSignal(int)

    def __init__(self, employee_data, position=0, parent=None):
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_id = employee_data.get('id')
        self.position = position

        # Логирование получения данных
        self._log_employee_data()

        self._init_ui()

    def _log_employee_data(self):
        """Логирует полученные данные сотрудника для отладки"""
        print(f"\n{'=' * 60}")
        print(f"📊 РАСЧЕТ КПД ДЛЯ СОТРУДНИКА #{self.position + 1}")
        print(f"{'=' * 60}")
        print(f"👤 Сотрудник: {self.employee_data.get('name', 'Неизвестно')}")
        print(f"📋 Должность: {self.employee_data.get('position', '—')}")
        print(f"📁 Отдел: {self.employee_data.get('department', '—')}")
        print(f"{'-' * 40}")

        # Базовые метрики
        completed_tasks = self.employee_data.get('completed_tasks', 0)
        total_tasks = self.employee_data.get('total_tasks', 0)
        overdue_tasks = self.employee_data.get('overdue_tasks', 0)

        print(f"📊 Базовые метрики:")
        print(f"   ✅ Выполнено задач: {completed_tasks}")
        print(f"   📋 Всего задач: {total_tasks}")
        print(f"   ⏰ Просрочено: {overdue_tasks}")

        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100
            print(f"   📈 Процент выполнения: {completion_rate:.1f}%")

        # Данные из EmployeeData (рассчитанные в БД)
        kpd_rating = self.employee_data.get('kpd_rating', 0)
        on_time_rate = self.employee_data.get('on_time_rate', 0)
        tasks_completed_total = self.employee_data.get('tasks_completed_total', 0)
        tasks_completed_on_time = self.employee_data.get('tasks_completed_on_time', 0)
        avg_completion_days = self.employee_data.get('avg_task_completion_days', 0)

        print(f"\n📊 Данные из EmployeeData (рассчитанные в БД):")
        print(f"   ⭐ КПД рейтинг: {kpd_rating:.1f}%")
        print(f"   🎯 Процент в срок: {on_time_rate:.1f}%")
        print(f"   ✅ Выполнено (БД): {tasks_completed_total}")
        print(f"   🎯 В срок (БД): {tasks_completed_on_time}")
        print(f"   📅 Среднее время выполнения: {avg_completion_days:.1f} дн.")

        # Данные из analytics (рассчитанные в реальном времени)
        kpd_percent = self.employee_data.get('kpd_percent', 0)
        weighted_kpd = self.employee_data.get('weighted_kpd', 0)
        overtime_hours = self.employee_data.get('overtime_hours', 0)

        print(f"\n📊 Данные из Analytics (рассчитанные в real-time):")
        print(f"   ⚡ КПД процент: {kpd_percent:.1f}%")
        print(f"   🎯 Взвешенный КПД: {weighted_kpd:.1f}%")
        print(f"   ⏱️ Часы переработок: {overtime_hours:.1f} ч.")

        # Формула расчета
        print(f"\n📐 ФОРМУЛА РАСЧЕТА КПД ЗАДАЧИ:")
        print(f"   KPD = Сложность × Приоритет × Эффективность × Готовность")
        print(f"   ")
        print(f"   где:")
        print(f"   • Сложность: 1★=0.6, 2★=0.8, 3★=1.0, 4★=1.2, 5★=1.5")
        print(f"   • Приоритет: low=0.8, medium=1.0, high=1.2, critical=1.5")
        print(f"   • Эффективность = Плановые_дни / Фактические_дни")
        print(f"   • Готовность: 1.0 для выполненных задач")

        # Итоговый КПД
        final_kpd = kpd_percent if kpd_percent > 0 else kpd_rating
        if final_kpd == 0 and total_tasks > 0:
            final_kpd = (completed_tasks / total_tasks * 100)

        print(f"\n🎯 ИТОГОВЫЙ КПД: {final_kpd:.1f}%")

        # Оценка
        if final_kpd >= 80:
            print(f"🏆 ОЦЕНКА: Отлично! Высокая эффективность")
        elif final_kpd >= 60:
            print(f"👍 ОЦЕНКА: Хорошо! Есть куда расти")
        elif final_kpd >= 40:
            print(f"⚠️ ОЦЕНКА: Средне! Требуется улучшение")
        else:
            print(f"❌ ОЦЕНКА: Низкая эффективность! Требует внимания")

        print(f"{'=' * 60}\n")

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

        # Используем новые поля из EmployeeData если есть
        kpd_rating = self.employee_data.get('kpd_rating', 0)
        on_time_rate = self.employee_data.get('on_time_rate', 0)

        stats_text = f"📊 Задач: {completed_tasks} из {total_tasks}"
        if on_time_rate > 0:
            stats_text += f" · В срок: {on_time_rate:.0f}%"
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(stats_label)

        main_layout.addLayout(info_layout, stretch=1)

        # КПД с процентами
        kpd_layout = QVBoxLayout()
        kpd_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Получаем КПД - приоритет новым полям
        kpd_percent = self.employee_data.get('kpd_percent', 0)
        if kpd_percent == 0:
            kpd_percent = self.employee_data.get('kpd_rating', 0)
        if kpd_percent == 0 and total_tasks > 0:
            kpd_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        weighted_kpd = self.employee_data.get('weighted_kpd', 0)
        overtime_hours = self.employee_data.get('overtime_hours', 0)

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

        # Взвешенный КПД
        if weighted_kpd > 0 and weighted_kpd != kpd_percent:
            weighted_label = QLabel(f"взв: {weighted_kpd:.1f}%")
            weighted_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            weighted_label.setStyleSheet("color: #888; font-size: 10px;")
            kpd_layout.addWidget(weighted_label)

        # Прогресс-бар
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(kpd_percent))
        progress_bar.setFixedWidth(120)
        progress_bar.setFixedHeight(8)
        progress_bar.setTextVisible(False)

        # Выбираем цвет градиента
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

        # Часы переработок
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

        # Тултип
        tooltip_text = self._generate_kpd_tooltip(
            kpd_percent, weighted_kpd, overtime_hours,
            total_tasks, completed_tasks, on_time_rate
        )
        self.setToolTip(tooltip_text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _generate_kpd_tooltip(self, kpd_percent, weighted_kpd, overtime_hours,
                              total_tasks, completed_tasks, on_time_rate):
        """Генерирует пояснение расчета КПД"""

        formula = """📐 ФОРМУЛА РАСЧЕТА КПД ЗАДАЧИ:

KPD = Сложность × Приоритет × Эффективность × Готовность

Где коэффициенты:
• Сложность (difficulty): 1★=0.6, 2★=0.8, 3★=1.0, 4★=1.2, 5★=1.5
• Приоритет: low=0.8, medium=1.0, high=1.2, critical=1.5
• Эффективность = Плановые_дни / Фактические_дни
  - Раньше срока: >1.0
  - В срок: 1.0
  - Просрочка: <1.0
• Готовность: 1.0 для выполненных задач

Итоговый КПД сотрудника = среднее арифметическое КПД всех задач"""

        # Статистика сотрудника
        stats = f"""
📊 ВАША СТАТИСТИКА:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Выполнено задач: {completed_tasks}
📋 Всего задач: {total_tasks}
🎯 Процент в срок: {on_time_rate:.0f}%
⚡ Итоговый КПД: {kpd_percent:.1f}%
{'🎯 Взвешенный КПД: ' + str(weighted_kpd) + '%' if weighted_kpd > 0 else ''}
{'⏱️ Часы переработок: ' + str(overtime_hours) + ' ч.' if overtime_hours > 0 else ''}"""

        # Интерпретация
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