# services/overtime_service/overtime_base_service.py

from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Dict
from PyQt6.QtCore import QDate, QTime


class OvertimeBaseService:
    """Базовый сервис с утилитами для работы с переработками"""

    @staticmethod
    def round_to_30_minutes_up(dt: datetime) -> datetime:
        minute = dt.minute
        if minute == 0 and dt.second == 0:
            return dt
        if minute < 30:
            return dt.replace(minute=30, second=0, microsecond=0)
        else:
            next_hour = dt.hour + 1
            return dt.replace(hour=next_hour if next_hour < 24 else 0, minute=0, second=0, microsecond=0)

    @staticmethod
    def round_to_30_minutes_down(dt: datetime) -> datetime:
        minute = dt.minute
        if minute < 30:
            return dt.replace(minute=0, second=0, microsecond=0)
        else:
            return dt.replace(minute=30, second=0, microsecond=0)

    def calculate_overtime_separate(self, start_time: time, end_time: time,
                                    shift_start: time, shift_end: time) -> list:
        from datetime import date
        shift_start_dt = datetime.combine(date.today(), shift_start)
        shift_end_dt = datetime.combine(date.today(), shift_end)
        actual_start_dt = datetime.combine(date.today(), start_time)
        actual_end_dt = datetime.combine(date.today(), end_time)
        rounded_start = self.round_to_30_minutes_up(actual_start_dt)
        rounded_end = self.round_to_30_minutes_down(actual_end_dt)
        results = []
        if rounded_start < shift_start_dt:
            early_minutes = (shift_start_dt - rounded_start).total_seconds() / 60.0
            early_hours = round(early_minutes / 60.0, 2)
            if early_hours > 0:
                results.append((early_hours, rounded_start.time(), shift_start_dt.time()))
        if rounded_end > shift_end_dt:
            late_minutes = (rounded_end - shift_end_dt).total_seconds() / 60.0
            late_hours = round(late_minutes / 60.0, 2)
            if late_hours > 0:
                results.append((late_hours, shift_end_dt.time(), rounded_end.time()))
        return results

    @staticmethod
    def calculate_duration(start_time: Optional[time], end_time: Optional[time]) -> float:
        if not start_time or not end_time:
            return 0.0
        start = datetime.combine(date.today(), start_time)
        end = datetime.combine(date.today(), end_time)
        if end < start:
            end = end + timedelta(days=1)
        return (end - start).total_seconds() / 3600

    @staticmethod
    def format_duration(hours: float) -> str:
        return f"{hours:.1f}".replace(".", ",")

    @staticmethod
    def format_time_period(start_time: Optional[time], end_time: Optional[time]) -> str:
        if not start_time or not end_time:
            return "--:-- - --:--"
        return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

    @staticmethod
    def parse_shift(shift_str: str) -> Tuple[time, time]:
        import re
        if not shift_str or not isinstance(shift_str, str) or shift_str == 'nan':
            return time(8, 0), time(16, 30)
        pattern = r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})'
        match = re.search(pattern, shift_str)
        if match:
            start_h, start_m = int(match.group(1)), int(match.group(2))
            end_h, end_m = int(match.group(3)), int(match.group(4))
            return time(start_h, start_m, 0), time(end_h, end_m, 0)
        return time(8, 0), time(16, 30)

    @staticmethod
    def parse_time_range(time_str: str) -> Tuple[Optional[time], Optional[time]]:
        import re
        if not time_str or not isinstance(time_str, str) or time_str == 'nan':
            return None, None
        pattern = r'(\d{1,2}):(\d{2})(?::\d{2})?\s*[-–]\s*(\d{1,2}):(\d{2})(?::\d{2})?'
        match = re.search(pattern, time_str)
        if match:
            start_h, start_m = int(match.group(1)), int(match.group(2))
            end_h, end_m = int(match.group(3)), int(match.group(4))
            return time(start_h, start_m, 0), time(end_h, end_m, 0)
        return None, None

    @staticmethod
    def parse_date(date_value) -> Optional[date]:
        from datetime import datetime
        if not date_value or str(date_value) == 'nan':
            return None
        try:
            if isinstance(date_value, (date, datetime)):
                return date_value.date() if isinstance(date_value, datetime) else date_value
            for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y', '%d.%m.%Y %H:%M:%S']:
                try:
                    return datetime.strptime(str(date_value).strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    @staticmethod
    def py_date_from_qdate(qdate: QDate) -> date:
        return qdate.toPyDate()

    @staticmethod
    def py_time_from_qtime(qtime: QTime) -> time:
        return time(qtime.hour(), qtime.minute())

    @staticmethod
    def qdate_from_string(date_str: str) -> Optional[QDate]:
        if not date_str:
            return None
        qdate = QDate.fromString(date_str, "dd.MM.yyyy")
        return qdate if qdate.isValid() else None

    @staticmethod
    def has_description(overtime_data: Dict) -> bool:
        """Проверяет, есть ли у переработки описание (проект, задача или текст)"""
        description = overtime_data.get('description', '')
        project_name = overtime_data.get('project')
        task_title = overtime_data.get('task')

        # ===== ИСПРАВЛЕНИЕ: "Без описания" считается как отсутствие описания =====
        if description and description.strip() and description.strip() != "Без описания":
            return True
        if project_name and str(project_name).strip():
            return True
        if task_title and str(task_title).strip():
            return True
        return False

    @staticmethod
    def get_display_description(overtime_data: Dict) -> str:
        """Возвращает текст для отображения в карточке"""
        description = overtime_data.get('description', '')
        project_name = overtime_data.get('project')
        task_title = overtime_data.get('task')

        # ===== ИСПРАВЛЕНИЕ: если описание "Без описания" - показываем стандартный текст =====
        if description and description.strip() and description.strip() != "Без описания":
            return description
        elif project_name and task_title:
            return f"{project_name} - {task_title}"
        elif project_name:
            return project_name
        elif task_title:
            return task_title
        return "Нет описания"