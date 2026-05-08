# services/overtime_service/overtime_import_service.py

import os
import re
import traceback
from datetime import datetime, date, time
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd

from repositories.overtime_repo import OvertimeRepo
from repositories.employee_repo import EmployeeRepo
from .overtime_base_service import OvertimeBaseService


class OvertimeImportService:
    """Сервис для импорта переработок из Excel-файла"""

    def __init__(self, session: Session, employees_session: Session):
        self.session = session
        self.employees_session = employees_session
        self.overtime_repo = OvertimeRepo(session)
        self.employee_repo = EmployeeRepo(employees_session)
        self.base = OvertimeBaseService()
        self.employees_cache = {}

    def _load_employees_cache(self):
        """Загружает всех сотрудников в кэш для быстрого поиска"""
        try:
            employees = self.employee_repo.get_all()
            print(f"[IMPORT] Загружено сотрудников из БД: {len(employees)}")

            for emp in employees:
                full_name = self._normalize_name(f"{emp.last_name} {emp.first_name} {emp.middle_name or ''}".strip())
                if full_name:
                    self.employees_cache[full_name] = emp.id

                short_name = f"{emp.last_name} {emp.first_name[0]}."
                if emp.middle_name:
                    short_name += f"{emp.middle_name[0]}."
                self.employees_cache[short_name] = emp.id

                very_short = f"{emp.last_name} {emp.first_name[0]}."
                self.employees_cache[very_short] = emp.id

            print(f"[IMPORT] Всего загружено {len(self.employees_cache)} записей в кэш")
        except Exception as e:
            print(f"[IMPORT ERROR] Ошибка загрузки кэша сотрудников: {e}")

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not name:
            return ""
        return ' '.join(name.split()).lower()

    def _find_employee_by_name(self, full_name: str) -> Optional[int]:
        """Находит ID сотрудника по ФИО"""
        if not full_name or full_name == 'nan':
            return None

        if not self.employees_cache:
            self._load_employees_cache()

        normalized = self._normalize_name(full_name)

        if normalized in self.employees_cache:
            return self.employees_cache[normalized]

        words = normalized.split()
        if words:
            last_name = words[0]
            for cached_name, emp_id in self.employees_cache.items():
                if cached_name.startswith(last_name):
                    return emp_id

        return None

    def check_duplicate(self, employee_id: int, overtime_date: date,
                        start_time: time, end_time: time) -> bool:
        try:
            existing_notes = self.overtime_repo.get_by_employee(employee_id)
            for note in existing_notes:
                if note.overtime_date == overtime_date:
                    if note.overtime_start and note.overtime_end:
                        if (note.overtime_start.hour == start_time.hour and
                            note.overtime_start.minute == start_time.minute and
                            note.overtime_end.hour == end_time.hour and
                            note.overtime_end.minute == end_time.minute):
                            return True
            return False
        except Exception:
            return False

    def import_from_excel(self, file_path: str, progress_callback=None) -> Dict:
        """Импортирует переработки из Excel-файла"""
        result = {
            'total_rows': 0,
            'imported': 0,
            'duplicates': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }

        try:
            print(f"[IMPORT] Начало импорта из файла: {file_path}")
            self._load_employees_cache()

            df = pd.read_excel(file_path, header=None, dtype=str)
            print(f"[IMPORT] Файл прочитан, строк: {len(df)}")

            # Поиск начала данных
            data_start_row = 0
            for idx, row in df.iterrows():
                first_cell = str(row.iloc[0]) if len(row) > 0 else ""
                if first_cell.isdigit() and int(first_cell) > 0:
                    data_start_row = idx
                    print(f"[IMPORT] Начало данных найдено на строке {idx}")
                    break

            data_rows = []
            for idx in range(data_start_row, len(df)):
                row = df.iloc[idx]
                first_cell = str(row.iloc[0]) if len(row) > 0 else ""
                if first_cell.isdigit():
                    data_rows.append(row)

            result['total_rows'] = len(data_rows)
            print(f"[IMPORT] Найдено строк с данными: {result['total_rows']}")

            # Определение колонок
            if data_rows:
                sample_row = data_rows[0]
                name_col = None
                date_col = None
                time_col = None
                shift_col = None

                for col_idx in range(min(len(sample_row), 15)):
                    val = str(sample_row.iloc[col_idx]) if col_idx < len(sample_row) else ""

                    if re.search(r'[а-яА-Я]', val) and ' ' in val and len(val) > 5:
                        if name_col is None:
                            name_col = col_idx
                            print(f"[IMPORT] Определена колонка ФИО: {col_idx} ('{val}')")

                    if re.match(r'\d{2}\.\d{2}\.\d{4}', val):
                        if date_col is None:
                            date_col = col_idx
                            print(f"[IMPORT] Определена колонка ДАТА: {col_idx} ('{val}')")

                    if ':' in val and '-' in val:
                        if time_col is None:
                            time_col = col_idx
                            print(f"[IMPORT] Определена колонка ВРЕМЯ: {col_idx} ('{val}')")

                    if re.search(r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}', val):
                        if shift_col is None and col_idx != time_col:
                            shift_col = col_idx
                            print(f"[IMPORT] Определена колонка СМЕНА: {col_idx} ('{val}')")

                name_col = name_col if name_col is not None else 7
                date_col = date_col if date_col is not None else 10
                time_col = time_col if time_col is not None else 11
                shift_col = shift_col if shift_col is not None else 12
            else:
                name_col, date_col, time_col, shift_col = 7, 10, 11, 12

            print(f"[IMPORT] Итоговые колонки: ФИО={name_col}, Дата={date_col}, Время={time_col}, Смена={shift_col}")

            for i, row in enumerate(data_rows):
                try:
                    full_name = str(row.iloc[name_col]) if len(row) > name_col else ""
                    if not full_name or full_name == 'nan':
                        result['skipped'] += 1
                        continue

                    date_value = row.iloc[date_col] if len(row) > date_col else None
                    overtime_date = self.base.parse_date(date_value)
                    if not overtime_date:
                        result['skipped'] += 1
                        continue

                    time_range = str(row.iloc[time_col]) if len(row) > time_col else ""
                    start_time, end_time = self.base.parse_time_range(time_range)
                    if not start_time or not end_time:
                        result['skipped'] += 1
                        continue

                    shift_str = str(row.iloc[shift_col]) if len(row) > shift_col else ""
                    shift_start, shift_end = self.base.parse_shift(shift_str)

                    employee_id = self._find_employee_by_name(full_name)
                    if not employee_id:
                        result['skipped'] += 1
                        continue

                    overtime_records = self.base.calculate_overtime_separate(
                        start_time, end_time, shift_start, shift_end
                    )

                    if not overtime_records:
                        result['skipped'] += 1
                        continue

                    for hours, ot_start, ot_end in overtime_records:
                        if self.check_duplicate(employee_id, overtime_date, ot_start, ot_end):
                            result['duplicates'] += 1
                            continue

                        note = self.overtime_repo.create(
                            employee_id=employee_id,
                            overtime_date=overtime_date,
                            note_text="",
                            overtime_start=ot_start,
                            overtime_end=ot_end
                        )
                        result['imported'] += 1

                    self.session.commit()

                    if progress_callback and (i + 1) % 100 == 0:
                        progress_callback(int((i + 1) / len(data_rows) * 100),
                                          f"Обработано {i + 1} из {result['total_rows']}")

                except Exception as e:
                    result['errors'] += 1
                    result['error_details'].append(f"Строка {i + 1}: {str(e)}")
                    self.session.rollback()

            print(f"[IMPORT] Импорт завершён. Результат: импортировано={result['imported']}")
            return result

        except Exception as e:
            result['errors'] += 1
            result['error_details'].append(f"Ошибка при чтении файла: {str(e)}")
            return result