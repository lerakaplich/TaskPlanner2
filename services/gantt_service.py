# services/gantt_service.py
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

from docx.shared import Inches, Pt
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_

from models.tasks import Task, TaskDependency
from models.projects import Project
from models.schemas.projects_dto import ProjectDTO


@dataclass
class TaskGanttData:
    """Данные задачи для отображения на диаграмме Ганта"""
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    executor_name: str
    executor_initials: str
    executor_id: Optional[int]
    color: str
    priority: str
    progress: float
    dependencies: List[Dict]
    project_id: int
    project_name: str
    status: str

    @property
    def duration_days(self) -> int:
        return max(1, (self.end_date - self.start_date).days + 1)


class GanttService:
    """Сервис для работы с диаграммой Ганта - реальные данные из БД"""

    # Константы для отрисовки
    DAY_WIDTH = 30
    ROW_HEIGHT = 50
    HEADER_HEIGHT = 55
    LEFT_PADDING = 0

    # Цвета для приоритетов
    PRIORITY_COLORS = {
        "critical": "#D22730",  # Красный
        "high": "#ccab6e",  # Золотой
        "medium": "#1B232A",  # Темно-синий
        "low": "#998664"  # Коричневый
    }

    def __init__(self, session: Session, current_user_id: int = None, project_service=None):
        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service
        self._cached_tasks: List[TaskGanttData] = []
        self._cached_projects: List[ProjectDTO] = []

    def create_task_via_service(self, form_data: Dict) -> Optional[Dict]:
        """
        Создаёт задачу через сервис задач.

        Args:
            form_data: данные формы задачи

        Returns:
            Dict: созданная задача или None
        """
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        try:
            task_service = TasksService(
                db_session=self.session,
                current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
                mode="others",
                column_service=ColumnService(self.session)
            )

            # Добавляем created_by если нет
            if "created_by" not in form_data:
                form_data["created_by"] = self.current_user_id

            new_task = task_service.create_task(form_data)
            print(f"✅ Задача создана: {new_task.get('id')}")
            return new_task

        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_to_image(self, canvas_widget) -> Optional[str]:
        """
        Экспортирует диаграмму Ганта в файл PNG.

        Args:
            canvas_widget: виджет с диаграммой (GanttCanvas)

        Returns:
            Optional[str]: путь к сохранённому файлу или None при ошибке
        """
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime

        if not canvas_widget:
            return None

        try:
            # Генерируем имя файла по умолчанию
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"gantt_chart_{timestamp}.png"

            # Диалог сохранения файла
            file_path, _ = QFileDialog.getSaveFileName(
                canvas_widget,
                "Сохранить диаграмму Ганта",
                default_name,
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)"
            )

            if not file_path:
                return None

            # Создаём pixmap с размерами виджета
            pixmap = canvas_widget.grab()

            # Сохраняем в файл
            success = pixmap.save(file_path)

            if success:
                print(f"✅ Диаграмма экспортирована: {file_path}")
                return file_path
            else:
                print(f"❌ Ошибка сохранения диаграммы")
                return None

        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_to_docx(self, tasks: List[TaskGanttData], start_date: datetime = None, end_date: datetime = None) -> \
    Optional[str]:
        """
        Экспортирует диаграмму Ганта в файл Word (DOCX).

        Args:
            tasks: список задач для экспорта
            start_date: начало периода (опционально)
            end_date: конец периода (опционально)

        Returns:
            Optional[str]: путь к сохранённому файлу или None при ошибке
        """
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime

        if not tasks:
            return None

        try:
            # Пробуем импортировать необходимые библиотеки
            try:
                from docx import Document
                from docx.shared import Inches, Pt, RGBColor
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                from docx.enum.table import WD_TABLE_ALIGNMENT
            except ImportError:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    None,
                    "Ошибка экспорта",
                    "Для экспорта в Word необходима библиотека python-docx.\n"
                    "Установите её командой:\npip install python-docx"
                )
                return None

            # Генерируем имя файла по умолчанию
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"gantt_report_{timestamp}.docx"

            # Диалог сохранения файла
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Экспорт диаграммы Ганта в Word",
                default_name,
                "Word Documents (*.docx);;All Files (*.*)"
            )

            if not file_path:
                return None

            # Создаём документ
            doc = Document()

            # Настройка стилей
            style = doc.styles['Normal']
            style.font.name = 'Arial'
            style.font.size = Pt(11)

            # Заголовок
            title = doc.add_heading('Диаграмма Ганта', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Информация о документе
            doc.add_paragraph(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            if start_date and end_date:
                doc.add_paragraph(
                    f"Период экспорта: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            doc.add_paragraph(f"Всего задач: {len(tasks)}")
            doc.add_paragraph()

            # Статистика по приоритетам
            doc.add_heading('Статистика по задачам', level=1)

            priority_stats = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
            status_stats = {}
            executor_stats = {}

            for task in tasks:
                priority_stats[task.priority] = priority_stats.get(task.priority, 0) + 1
                status_stats[task.status] = status_stats.get(task.status, 0) + 1
                if task.executor_name:
                    executor_stats[task.executor_name] = executor_stats.get(task.executor_name, 0) + 1

            # Таблица статистики по приоритетам
            doc.add_heading('Приоритеты задач:', level=2)
            table_priority = doc.add_table(rows=len([c for c in priority_stats.values() if c > 0]) + 1, cols=2)
            table_priority.style = 'Light Grid Accent 1'

            # Заголовки
            header_cells = table_priority.rows[0].cells
            header_cells[0].text = 'Приоритет'
            header_cells[1].text = 'Количество'
            self._set_cell_font(header_cells[0], bold=True)
            self._set_cell_font(header_cells[1], bold=True)

            # Данные
            priority_names = {
                "critical": "Критический",
                "high": "Высокий",
                "medium": "Средний",
                "low": "Низкий"
            }
            row_idx = 1
            for priority, count in priority_stats.items():
                if count > 0:
                    cells = table_priority.rows[row_idx].cells
                    cells[0].text = priority_names.get(priority, priority)
                    cells[1].text = str(count)
                    row_idx += 1

            # Статистика по исполнителям
            if executor_stats:
                doc.add_heading('Нагрузка на исполнителей:', level=2)
                table_executors = doc.add_table(rows=len(executor_stats) + 1, cols=2)
                table_executors.style = 'Light Grid Accent 1'

                header_cells = table_executors.rows[0].cells
                header_cells[0].text = 'Исполнитель'
                header_cells[1].text = 'Количество задач'
                self._set_cell_font(header_cells[0], bold=True)
                self._set_cell_font(header_cells[1], bold=True)

                row_idx = 1
                for executor, count in sorted(executor_stats.items()):
                    cells = table_executors.rows[row_idx].cells
                    cells[0].text = executor
                    cells[1].text = str(count)
                    row_idx += 1

            doc.add_page_break()

            # Детальная таблица задач
            doc.add_heading('Детальный список задач', level=1)

            # Создаём таблицу задач
            headers = ['ID', 'Задача', 'Проект', 'Исполнитель', 'Приоритет', 'Статус', 'Прогресс', 'Дата начала',
                       'Дата окончания', 'Длительность']
            table_tasks = doc.add_table(rows=1, cols=len(headers))
            table_tasks.style = 'Light Grid Accent 1'

            # Заголовки
            header_cells = table_tasks.rows[0].cells
            for i, header in enumerate(headers):
                header_cells[i].text = header
                self._set_cell_font(header_cells[i], bold=True)
                header_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Данные задач
            priority_names = {
                "critical": "Критический",
                "high": "Высокий",
                "medium": "Средний",
                "low": "Низкий"
            }

            for task in tasks:
                row_cells = table_tasks.add_row().cells
                row_cells[0].text = str(task.id)
                row_cells[1].text = task.name
                row_cells[2].text = task.project_name
                row_cells[3].text = task.executor_name or "Не назначен"
                row_cells[4].text = priority_names.get(task.priority, task.priority)
                row_cells[5].text = task.status
                row_cells[6].text = f"{task.progress}%"
                row_cells[7].text = task.start_date.strftime("%d.%m.%Y")
                row_cells[8].text = task.end_date.strftime("%d.%m.%Y")
                row_cells[9].text = str(task.duration_days)

                # Цвет для приоритета
                if task.priority == "critical":
                    self._set_cell_font(row_cells[4], color="D22730", bold=True)
                elif task.priority == "high":
                    self._set_cell_font(row_cells[4], color="ccab6e", bold=True)

            # Настройка ширины колонок таблицы
            self._auto_fit_table_columns(table_tasks)

            # Добавляем информацию о связях, если они есть
            links = self.get_all_links()
            if links:
                # Фильтруем связи только по задачам в экспорте
                task_ids = {t.id for t in tasks}
                filtered_links = {}
                for from_id, to_ids in links.items():
                    if from_id in task_ids:
                        filtered_to_ids = [tid for tid in to_ids if tid in task_ids]
                        if filtered_to_ids:
                            filtered_links[from_id] = filtered_to_ids

                if filtered_links:
                    doc.add_page_break()
                    doc.add_heading('Связи между задачами', level=1)

                    link_text = ""
                    for from_id, to_ids in filtered_links.items():
                        from_task = self.get_task_by_id(from_id)
                        if from_task:
                            for to_id in to_ids:
                                to_task = self.get_task_by_id(to_id)
                                if to_task:
                                    link_text += f"• {from_task.name} → {to_task.name}\n"

                    if link_text:
                        p = doc.add_paragraph(link_text)
                        p.style.font.size = Pt(11)
                    else:
                        doc.add_paragraph("Нет связей между задачами")

            # Сохраняем документ
            doc.save(file_path)
            print(f"✅ Word документ экспортирован: {file_path}")
            return file_path

        except Exception as e:
            print(f"❌ Ошибка экспорта в Word: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _set_cell_font(self, cell, bold=False, color=None, size=None):
        """Устанавливает шрифт для ячейки таблицы"""
        try:
            paragraph = cell.paragraphs[0]
            run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()

            if bold:
                run.bold = True
            if color:
                run.font.color.rgb = self._hex_to_rgb(color)
            if size:
                run.font.size = Pt(size)
        except Exception as e:
            # Если не удалось установить стиль, просто игнорируем
            pass

    def _hex_to_rgb(self, hex_color):
        """Преобразует HEX цвет в RGB объект python-docx"""
        from docx.shared import RGBColor
        hex_color = hex_color.lstrip('#')
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))

    def _auto_fit_table_columns(self, table):
        """Автоматически подбирает ширину колонок таблицы"""
        # Простой метод - устанавливаем примерную ширину
        # В python-docx нет автоматической подгонки, но можно установить предпочтительные ширины
        widths = [0.7, 3.0, 2.0, 2.0, 1.2, 1.5, 1.0, 1.2, 1.2, 1.0]  # в дюймах
        for i, cell in enumerate(table.columns):
            try:
                cell.width = Inches(widths[i] if i < len(widths) else 1.0)
            except:
                pass

    def export_to_excel(self, tasks: List[TaskGanttData], start_date: datetime = None, end_date: datetime = None) -> \
    Optional[str]:
        """
        Экспортирует диаграмму Ганта в Excel с визуальным отображением.

        Args:
            tasks: список задач для экспорта
            start_date: начало периода (опционально)
            end_date: конец периода (опционально)

        Returns:
            Optional[str]: путь к сохранённому файлу или None при ошибке
        """
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime, timedelta
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        if not tasks:
            return None

        try:
            # Если период не указан, определяем по задачам
            if start_date is None or end_date is None:
                all_dates = []
                for task in tasks:
                    all_dates.append(task.start_date)
                    all_dates.append(task.end_date)

                if all_dates:
                    start_date = min(all_dates).replace(day=1)
                    end_date = max(all_dates) + timedelta(days=14)
                else:
                    start_date = datetime.now().replace(day=1)
                    end_date = start_date + timedelta(days=30)

            # Генерируем список всех дат в периоде
            current_date = start_date
            dates_list = []
            while current_date <= end_date:
                dates_list.append(current_date)
                current_date += timedelta(days=1)

            # Генерируем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"gantt_chart_{timestamp}.xlsx"

            # Диалог сохранения
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Экспорт диаграммы Ганта в Excel",
                default_name,
                "Excel Files (*.xlsx);;All Files (*.*)"
            )

            if not file_path:
                return None

            # Создаём книгу Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "Диаграмма Ганта"

            # Стили
            border = Border(
                left=Side(style='thin', color='E0E0E0'),
                right=Side(style='thin', color='E0E0E0'),
                top=Side(style='thin', color='E0E0E0'),
                bottom=Side(style='thin', color='E0E0E0')
            )

            header_fill = PatternFill(start_color="1B232A", end_color="1B232A", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)

            # Заголовки приоритетов
            priority_colors = {
                "critical": "D22730",
                "high": "ccab6e",
                "medium": "1B232A",
                "low": "998664"
            }

            # ==================== ШАПКА ТАБЛИЦЫ ====================

            # Строка 1: Информация о документе
            ws.merge_cells('A1:B1')
            ws['A1'] = f'Диаграмма Ганта'
            ws['A1'].font = Font(bold=True, size=14)

            ws.merge_cells('C1:E1')
            ws['C1'] = f'Период: {start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}'
            ws['C1'].font = Font(size=10)

            ws.merge_cells('F1:H1')
            ws['F1'] = f'Задач в периоде: {len(tasks)}'
            ws['F1'].font = Font(size=10)

            # Строка 2: Заголовки колонок
            headers = ['ID', 'Задача', 'Проект', 'Исполнитель', 'Приоритет', 'Прогресс']

            # Добавляем заголовки для каждой даты
            col_idx = 1
            for header in headers:
                cell = ws.cell(row=3, column=col_idx)
                cell.value = header
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                col_idx += 1

            # Заголовки с датами (месяцы и дни)
            current_month = None
            month_start_col = col_idx

            for i, date_obj in enumerate(dates_list):
                # Заголовок с днём
                cell = ws.cell(row=3, column=col_idx + i)
                cell.value = date_obj.day
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border

                # Название месяца (объединяем ячейки)
                month_name = date_obj.strftime("%B %Y")
                if current_month != month_name:
                    if current_month is not None:
                        # Объединяем ячейки месяца
                        ws.merge_cells(
                            start_row=2, start_column=month_start_col,
                            end_row=2, end_column=col_idx + i - 1
                        )
                        month_cell = ws.cell(row=2, column=month_start_col)
                        month_cell.value = current_month
                        month_cell.fill = header_fill
                        month_cell.font = header_font
                        month_cell.alignment = Alignment(horizontal='center', vertical='center')
                        month_cell.border = border

                    current_month = month_name
                    month_start_col = col_idx + i

            # Последний месяц
            if current_month:
                ws.merge_cells(
                    start_row=2, start_column=month_start_col,
                    end_row=2, end_column=col_idx + len(dates_list) - 1
                )
                month_cell = ws.cell(row=2, column=month_start_col)
                month_cell.value = current_month
                month_cell.fill = header_fill
                month_cell.font = header_font
                month_cell.alignment = Alignment(horizontal='center', vertical='center')
                month_cell.border = border

            # ==================== ЗАДАЧИ ====================

            row_num = 4

            # Сортируем задачи по проектам
            tasks_by_project = {}
            for task in tasks:
                if task.project_name not in tasks_by_project:
                    tasks_by_project[task.project_name] = []
                tasks_by_project[task.project_name].append(task)

            for project_name, project_tasks in tasks_by_project.items():
                # Заголовок проекта
                ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num,
                               end_column=col_idx + len(dates_list) - 1)
                project_cell = ws.cell(row=row_num, column=1)
                project_cell.value = f'📁 {project_name}'
                project_cell.font = Font(bold=True, size=12)
                project_cell.fill = PatternFill(start_color="E8E8E8", end_color="E8E8E8", fill_type="solid")
                project_cell.alignment = Alignment(horizontal='left', vertical='center')
                row_num += 1

                # Задачи проекта
                for task in project_tasks:
                    # Информационные колонки
                    ws.cell(row=row_num, column=1, value=task.id)
                    ws.cell(row=row_num, column=2, value=task.name)
                    ws.cell(row=row_num, column=3, value=task.project_name)
                    ws.cell(row=row_num, column=4, value=task.executor_name or "Не назначен")

                    # Приоритет с цветом
                    priority_cell = ws.cell(row=row_num, column=5)
                    priority_name = self._translate_priority(task.priority)
                    priority_cell.value = priority_name
                    if task.priority in priority_colors:
                        priority_cell.fill = PatternFill(
                            start_color=priority_colors[task.priority],
                            end_color=priority_colors[task.priority],
                            fill_type="solid"
                        )
                        priority_cell.font = Font(color="FFFFFF", bold=True)

                    # Прогресс
                    progress_cell = ws.cell(row=row_num, column=6)
                    progress_cell.value = f"{task.progress}%"
                    progress_cell.alignment = Alignment(horizontal='center')

                    # Вычисляем позиции для полосы задачи
                    start_offset = (task.start_date - start_date).days
                    duration = task.duration_days

                    # Ограничиваем duration в пределах периода
                    end_offset = (task.end_date - start_date).days
                    visible_start = max(0, start_offset)
                    visible_end = min(len(dates_list) - 1, end_offset)
                    visible_duration = max(0, visible_end - visible_start + 1)

                    # Цвет задачи
                    task_color = priority_colors.get(task.priority, "1B232A")
                    task_fill = PatternFill(start_color=task_color, end_color=task_color, fill_type="solid")

                    # Рисуем полосу задачи (только видимую часть)
                    for i in range(visible_start, visible_start + visible_duration):
                        if 0 <= i < len(dates_list):
                            col_idx_task = 7 + i
                            cell = ws.cell(row=row_num, column=col_idx_task)
                            cell.fill = task_fill
                            cell.alignment = Alignment(horizontal='center', vertical='center')

                            # Добавляем текст на полосу
                            if i == visible_start:  # Первый видимый день
                                cell.value = task.name[:10]  # Обрезаем длинные названия
                                cell.font = Font(color="FFFFFF", bold=True, size=7)
                            elif i == visible_end and visible_duration > 2:  # Последний видимый день
                                if task.executor_initials:
                                    cell.value = task.executor_initials
                                    cell.font = Font(color="FFFFFF", bold=True, size=7)

                    row_num += 1

                # Отступ между проектами
                row_num += 1

            # ==================== НАСТРОЙКА ВНЕШНЕГО ВИДА ====================

            # Устанавливаем ширину колонок
            ws.column_dimensions['A'].width = 8  # ID
            ws.column_dimensions['B'].width = 35  # Задача
            ws.column_dimensions['C'].width = 25  # Проект
            ws.column_dimensions['D'].width = 20  # Исполнитель
            ws.column_dimensions['E'].width = 15  # Приоритет
            ws.column_dimensions['F'].width = 10  # Прогресс

            # Устанавливаем ширину для колонок с датами (фиксированная)
            for i in range(len(dates_list)):
                col_letter = get_column_letter(7 + i)
                ws.column_dimensions[col_letter].width = 4

            # Замораживаем панель
            ws.freeze_panes = 'G4'

            # Добавляем фильтры
            ws.auto_filter.ref = f"A3:{get_column_letter(6)}{row_num - 1}"

            # ==================== ЛЕГЕНДА ====================

            # Создаём новый лист для легенды
            ws_legend = wb.create_sheet("Легенда")

            # Заголовок легенды
            ws_legend['A1'] = 'Легенда диаграммы Ганта'
            ws_legend['A1'].font = Font(bold=True, size=14)

            # Информация о периоде
            ws_legend['A3'] = f'Период экспорта: {start_date.strftime("%d.%m.%Y")} - {end_date.strftime("%d.%m.%Y")}'
            ws_legend['A3'].font = Font(bold=True)

            # Приоритеты
            ws_legend['A5'] = 'Приоритеты:'
            ws_legend['A5'].font = Font(bold=True)

            priority_names = {
                "critical": "Критический",
                "high": "Высокий",
                "medium": "Средний",
                "low": "Низкий"
            }

            row = 6
            for priority, name in priority_names.items():
                color = priority_colors.get(priority, "1B232A")
                cell = ws_legend.cell(row=row, column=1)
                cell.value = name
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True)
                row += 1

            # Исполнители (уникальные)
            unique_executors = set()
            for task in tasks:
                if task.executor_name:
                    unique_executors.add(task.executor_name)

            if unique_executors:
                ws_legend.cell(row=row + 2, column=1, value="Исполнители:")
                ws_legend.cell(row=row + 2, column=1).font = Font(bold=True)

                for executor in sorted(unique_executors):
                    row += 1
                    ws_legend.cell(row=row, column=1, value=f"• {executor}")

            # Настройка ширины колонок легенды
            ws_legend.column_dimensions['A'].width = 50

            # Сохраняем файл
            wb.save(file_path)
            print(f"✅ Excel диаграмма Ганта экспортирована: {file_path}")
            return file_path

        except ImportError as e:
            print(f"❌ Не установлена библиотека: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "Ошибка экспорта",
                "Для экспорта в Excel необходима библиотека openpyxl.\n"
                "Установите её командой:\npip install openpyxl"
            )
            return None
        except Exception as e:
            print(f"❌ Ошибка экспорта в Excel: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _translate_priority(self, priority: str) -> str:
        """Переводит код приоритета в читаемое название"""
        priority_map = {
            "critical": "Критический",
            "high": "Высокий",
            "medium": "Средний",
            "low": "Низкий"
        }
        return priority_map.get(priority, priority)

    def update_task_dates_with_linked(self, task_id: int, new_start: datetime, new_end: datetime) -> bool:
        """
        Обновляет даты задачи и всех зависимых задач.

        Args:
            task_id: ID задачи
            new_start: новая дата начала
            new_end: новая дата окончания

        Returns:
            bool: успех операции
        """
        try:
            # Обновляем основную задачу
            if not self.update_task_dates(task_id, new_start, new_end):
                return False

            # Обновляем зависимые задачи
            old_task = None
            for t in self._cached_tasks:
                if t.id == task_id:
                    old_start = t.start_date
                    old_end = t.end_date
                    break

            if old_task:
                delta = (new_start - old_start).days
                linked_ids = self.get_linked_tasks_for_update(task_id)

                for linked_id in linked_ids:
                    for t in self._cached_tasks:
                        if t.id == linked_id:
                            new_linked_start = t.start_date + timedelta(days=delta)
                            new_linked_end = t.end_date + timedelta(days=delta)
                            self.update_task_dates(linked_id, new_linked_start, new_linked_end)
                            break

            return True
        except Exception as e:
            print(f"❌ Ошибка обновления дат с зависимостями: {e}")
            return False

    def get_all_data(self) -> Dict:
        """
        Возвращает все данные для UI.

        Returns:
            Dict: словарь с проектами, задачами, связями
        """
        return {
            "projects": self._cached_projects,
            "tasks": self._cached_tasks,
            "links": self.get_all_links(),
            "executors": self.get_unique_executors()
        }

    def get_task_by_id(self, task_id: int) -> Optional[TaskGanttData]:
        """
        Возвращает задачу по ID.

        Args:
            task_id: ID задачи

        Returns:
            TaskGanttData или None
        """
        for task in self._cached_tasks:
            if task.id == task_id:
                return task
        return None

    def validate_project_selected(self, project_filter: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Проверяет, выбран ли проект.

        Args:
            project_filter: текущий фильтр проекта ("all" или "project_{id}")

        Returns:
            Tuple[bool, Optional[int], Optional[str]]: (is_valid, project_id, error_message)
        """
        if project_filter == "all":
            return False, None, "Пожалуйста, сначала выберите проект из списка проектов"

        try:
            project_id = int(project_filter.split("_")[1])
            return True, project_id, None
        except (ValueError, IndexError):
            return False, None, "Неверный формат фильтра проекта"

    def get_tasks_for_tree(self) -> List[Tuple[ProjectDTO, List[TaskGanttData]]]:
        """
        Возвращает проекты с их задачами для дерева.

        Returns:
            List[Tuple[ProjectDTO, List[TaskGanttData]]]: список (проект, задачи проекта)
        """
        result = []
        for project in self._cached_projects:
            tasks = self.get_tasks_for_project(project.id)
            result.append((project, tasks))
        return result

    def load_data(self, project_id: Optional[int] = None) -> None:
        """Загружает данные из БД"""
        print(f"📊 GanttService.load_data(project_id={project_id})")

        # Загружаем проекты
        self._load_projects()

        # Загружаем задачи
        self._load_tasks(project_id)

    def create_task_from_dialog(self, form_data: Dict, current_user_id: int) -> Optional[Dict]:
        """
        Создаёт задачу из данных диалога.

        Args:
            form_data: данные формы задачи
            current_user_id: ID текущего пользователя

        Returns:
            Dict: созданная задача или None
        """
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        try:
            task_service = TasksService(
                db_session=self.session,
                current_user={"id": current_user_id, "last_name": "", "first_name": ""},
                mode="others",
                column_service=ColumnService(self.session)
            )

            # Добавляем created_by если нет
            if "created_by" not in form_data:
                form_data["created_by"] = current_user_id

            new_task = task_service.create_task(form_data)
            print(f"✅ Задача создана: {new_task.get('id')}")
            return new_task

        except Exception as e:
            print(f"❌ Ошибка создания задачи: {e}")
            import traceback
            traceback.print_exc()
            return None

    def refresh_all_data(self, project_id: Optional[int] = None) -> None:
        """
        Полностью перезагружает все данные.

        Args:
            project_id: опциональный ID проекта для фильтрации
        """
        self._cached_tasks = []
        self._cached_projects = []
        self.load_data(project_id)

    def get_project_name(self, project_id: int) -> str:
        """
        Возвращает имя проекта по ID.

        Args:
            project_id: ID проекта

        Returns:
            str: имя проекта или пустая строка
        """
        for project in self._cached_projects:
            if project.id == project_id:
                return project.name
        return ""

    def get_filtered_tasks(self, project_filter: str, executor_filter: str) -> List[TaskGanttData]:
        """
        Возвращает задачи с применением фильтров.

        Args:
            project_filter: "all" или "project_{id}"
            executor_filter: "all" или имя исполнителя

        Returns:
            List[TaskGanttData]: отфильтрованные задачи
        """
        all_tasks = self.get_all_tasks()

        # Фильтр по проекту
        if project_filter != "all":
            project_id = int(project_filter.split("_")[1])
            filtered = [t for t in all_tasks if t.project_id == project_id]
        else:
            filtered = all_tasks.copy()

        # Фильтр по исполнителю
        if executor_filter != "all":
            filtered = [t for t in filtered if t.executor_name == executor_filter]

        return filtered

    def get_date_range_for_tasks(self, tasks: List[TaskGanttData], padding_days: int = 14) -> Tuple[datetime, datetime]:
        """
        Возвращает диапазон дат для списка задач с отступом.

        Args:
            tasks: список задач
            padding_days: количество дней отступа (увеличено до 14 для лучшего отображения)

        Returns:
            Tuple[datetime, datetime]: (start_date, end_date)
        """
        if not tasks:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today.replace(day=1), today.replace(day=28) + timedelta(days=30)

        start = min(t.start_date for t in tasks)
        end = max(t.end_date for t in tasks)

        # Начинаем с первого дня месяца
        start = start.replace(day=1)

        # Добавляем отступ в начале и конце
        start = start - timedelta(days=padding_days)
        end = end + timedelta(days=padding_days)

        # Убеждаемся, что start - первый день месяца
        start = start.replace(day=1)

        # Добавляем запасной месяц в конце, если нужно
        if (end - start).days < 60:  # Если диапазон меньше 2 месяцев, расширяем
            end = end + timedelta(days=30)

        return start, end

    def get_unique_executors(self) -> List[str]:
        """
        Возвращает список уникальных имён исполнителей.

        Returns:
            List[str]: отсортированный список имён исполнителей
        """
        executors = set()
        for task in self.get_all_tasks():
            if task.executor_name:
                executors.add(task.executor_name)
        return sorted(executors)

    def _load_projects(self) -> None:
        """Загружает проекты из БД"""
        try:
            stmt = select(Project).where(Project.is_archived == False).order_by(Project.name)
            projects = self.session.scalars(stmt).all()
            self._cached_projects = [ProjectDTO.model_validate(p) for p in projects]
            print(f"   ✅ Загружено {len(self._cached_projects)} проектов")
        except Exception as e:
            print(f"   ❌ Ошибка загрузки проектов: {e}")
            self._cached_projects = []

    def _load_tasks(self, project_id: Optional[int] = None) -> None:
        """Загружает задачи из БД"""
        try:
            stmt = select(Task).where(
                Task.is_archived == False
            ).options(
                joinedload(Task.column),
                joinedload(Task.dependencies_as_predecessor),
                joinedload(Task.dependencies_as_successor)
            )

            if project_id:
                stmt = stmt.where(Task.project_id == project_id)

            tasks = self.session.scalars(stmt).unique().all()
            print(f"   ✅ Загружено {len(tasks)} задач")

            self._cached_tasks = []
            for task in tasks:
                gantt_task = self._convert_to_gantt_data(task)
                if gantt_task:
                    self._cached_tasks.append(gantt_task)

        except Exception as e:
            print(f"   ❌ Ошибка загрузки задач: {e}")
            import traceback
            traceback.print_exc()
            self._cached_tasks = []

    def _convert_to_gantt_data(self, task: Task) -> Optional[TaskGanttData]:
        """Конвертирует Task в TaskGanttData"""
        try:
            # Получаем даты
            start_date = task.created_at if task.created_at else datetime.now()
            end_date = task.deadline if task.deadline else start_date + timedelta(days=7)

            # Нормализуем даты (без времени)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Корректируем если start > end
            if start_date > end_date:
                start_date, end_date = end_date, start_date + timedelta(days=1)

            # Получаем имя исполнителя
            executor_name = ""
            executor_initials = ""
            if task.assigned_to and self.project_service:
                user = self.project_service.get_user_by_id(task.assigned_to)
                if user:
                    executor_name = f"{user.get('last_name', '')} {user.get('first_name', '')}"
                    executor_initials = self._get_initials(user)

            # Получаем цвет по приоритету
            priority_value = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            color = self.PRIORITY_COLORS.get(priority_value, self.PRIORITY_COLORS["medium"])

            # Получаем зависимости
            dependencies = []
            for dep in task.dependencies_as_predecessor:
                dependencies.append({
                    "successor_id": dep.successor_id,
                    "lag": dep.lag,
                    "type": dep.type
                })

            # Получаем имя проекта
            project_name = ""
            if task.project_id:
                for p in self._cached_projects:
                    if p.id == task.project_id:
                        project_name = p.name
                        break

            return TaskGanttData(
                id=task.id,
                name=task.title,
                start_date=start_date,
                end_date=end_date,
                executor_name=executor_name,
                executor_initials=executor_initials,
                executor_id=task.assigned_to,
                color=color,
                priority=priority_value,
                progress=task.progress_percent,
                dependencies=dependencies,
                project_id=task.project_id,
                project_name=project_name,
                status=task.column.name if task.column else "unknown"
            )
        except Exception as e:
            print(f"   ⚠️ Ошибка конвертации задачи {task.id}: {e}")
            return None

    def _get_initials(self, user: Dict) -> str:
        """Получает инициалы пользователя"""
        first = user.get('first_name', '')
        last = user.get('last_name', '')
        if last and first:
            return f"{last[0]}{first[0]}".upper()
        return "??"

    def get_projects(self) -> List[ProjectDTO]:
        """Возвращает список проектов"""
        return self._cached_projects

    def get_all_tasks(self) -> List[TaskGanttData]:
        """Возвращает все задачи"""
        return self._cached_tasks

    def get_tasks_for_project(self, project_id: int) -> List[TaskGanttData]:
        """Возвращает задачи для конкретного проекта"""
        return [t for t in self._cached_tasks if t.project_id == project_id]

    def get_all_links(self) -> Dict[int, List[int]]:
        """Возвращает все связи между задачами"""
        links = {}
        for task in self._cached_tasks:
            for dep in task.dependencies:
                links[task.id] = links.get(task.id, [])
                links[task.id].append(dep["successor_id"])
        return links

    def get_linked_tasks_for_update(self, task_id: int) -> List[int]:
        """Возвращает ID задач, которые зависят от данной"""
        linked = []
        for task in self._cached_tasks:
            for dep in task.dependencies:
                if dep["successor_id"] == task_id:
                    linked.append(task.id)
        return linked

    def calculate_bar_position(self, task: TaskGanttData, start_date: datetime) -> Tuple[float, float]:
        """Вычисляет позицию и ширину полосы задачи"""
        total_days = max(1, (task.end_date - task.start_date).days + 1)
        offset_days = max(0, (task.start_date - start_date).days)

        x = self.LEFT_PADDING + offset_days * self.DAY_WIDTH
        width = total_days * self.DAY_WIDTH

        return float(x), float(width)

    def get_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """Возвращает диапазон дат для выбранного периода"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "Месяц":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            return start, end
        elif period == "Квартал":
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            if quarter == 3:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 3, day=1) - timedelta(days=1)
            return start, end
        elif period == "Год":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            return start, end
        else:  # "Неделя" или по умолчанию
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end

    def update_task_dates(self, task_id: int, start_date: datetime, end_date: datetime) -> bool:
        """Обновляет даты задачи в БД"""
        try:
            task = self.session.get(Task, task_id)
            if task:
                task.created_at = start_date
                task.deadline = end_date
                self.session.commit()

                # Обновляем в кэше
                for t in self._cached_tasks:
                    if t.id == task_id:
                        t.start_date = start_date
                        t.end_date = end_date
                        break

                print(f"✅ Задача {task_id}: даты обновлены на {start_date.date()} - {end_date.date()}")
                return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка обновления дат: {e}")
        return False

    def add_dependency(self, predecessor_id: int, successor_id: int, lag: int = 0, dep_type: str = "FS") -> bool:
        """Добавляет связь между задачами"""
        try:
            # Проверяем, существует ли уже такая связь
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                return False

            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.commit()

            # Обновляем кэш
            for t in self._cached_tasks:
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                    break

            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка создания связи: {e}")
            return False