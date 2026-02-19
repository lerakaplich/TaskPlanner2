from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

class EmployeesStatsView(QWidget):
    def __init__(self, theme_name, tasks, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.tasks = tasks  # все задачи с этим тегом
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Поиск
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по сотруднику...")
        self.search_edit.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_edit)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(7)  # Сотрудник | КПД (ср) | Выполнено | Low | Medium | High | Critical
        self.table.setHorizontalHeaderLabels([
            "Сотрудник", "Ср. КПД", "Выполнено",
            "Low", "Medium", "High", "Critical"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.all_stats = self.compute_stats()
        self.refresh_table()

    def parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    def calculate_kpi(self, created, completed, due):
        """КПД = (due - created) / (completed - created), если выполнено."""
        if not (created and completed and due):
            return None
        planned = (due - created).days
        actual = (completed - created).days
        if actual <= 0:
            return float('inf')
        return planned / actual

    def compute_stats(self):
        """Сбор статистики по сотрудникам на основе задач с этим тегом."""
        # Словарь: id сотрудника -> данные
        stats = {}
        # Для сопоставления id и имени используем временный справочник
        # В реальном проекте нужно получать из БД. Здесь для теста зададим вручную.
        employee_names = {
            1: "Иван Иванов",
            2: "Анна Петрова",
            3: "Алексей Сидоров"
        }

        for task in self.tasks:
            assigned = task.get("assigned_to")
            if not assigned:
                continue
            # Если assigned строка, используем как есть, иначе преобразуем id в имя
            if isinstance(assigned, int):
                employee = employee_names.get(assigned, f"ID {assigned}")
            else:
                employee = assigned

            if employee not in stats:
                stats[employee] = {
                    "kpi_sum": 0.0,
                    "kpi_count": 0,
                    "completed": 0,
                    "priority_count": {"low": 0, "medium": 0, "high": 0, "critical": 0}
                }

            # Приоритет
            prio = task.get("priority", "medium").lower()
            if prio in stats[employee]["priority_count"]:
                stats[employee]["priority_count"][prio] += 1

            # Статус выполнено
            status = task.get("status", "").lower()
            if status in ("completed", "archived", "выполнено"):
                stats[employee]["completed"] += 1
                # КПД для выполненной задачи
                created = self.parse_date(task.get("created_at"))
                completed_date = self.parse_date(task.get("completed_at"))
                due = self.parse_date(task.get("due_date"))
                kpi = self.calculate_kpi(created, completed_date, due)
                if kpi is not None:
                    stats[employee]["kpi_sum"] += kpi
                    stats[employee]["kpi_count"] += 1

        # Преобразуем в список для таблицы
        result = []
        for employee, data in stats.items():
            avg_kpi = data["kpi_sum"] / data["kpi_count"] if data["kpi_count"] > 0 else 0
            result.append({
                "employee": employee,
                "avg_kpi": avg_kpi,
                "completed": data["completed"],
                "low": data["priority_count"]["low"],
                "medium": data["priority_count"]["medium"],
                "high": data["priority_count"]["high"],
                "critical": data["priority_count"]["critical"]
            })
        return result

    def refresh_table(self, filter_text=""):
        self.table.setRowCount(0)
        for row, stat in enumerate(self.all_stats):
            if filter_text.lower() not in stat["employee"].lower():
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(stat["employee"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{stat['avg_kpi']:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(str(stat["completed"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(stat["low"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(stat["medium"])))
            self.table.setItem(row, 5, QTableWidgetItem(str(stat["high"])))
            self.table.setItem(row, 6, QTableWidgetItem(str(stat["critical"])))

    def filter_table(self, text):
        self.refresh_table(text)