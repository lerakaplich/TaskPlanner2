# services/projects_service/projects_statistics_service.py

from typing import Dict


class ProjectsStatisticsService:
    """Статистика проектов"""

    def __init__(self, session, employee_repo):
        self.session = session
        self.employee_repo = employee_repo

    def get_project_card_data(self, project_card_dto) -> Dict:
        """
        Преобразует ProjectCardDTO в данные для отображения в карточке
        Возвращает словарь с готовыми строками для UI
        """
        # Прогресс
        if project_card_dto.tasks_total > 0:
            progress = int((project_card_dto.tasks_done / project_card_dto.tasks_total) * 100)
        else:
            progress = 0

        # Информационная строка (владелец и куратор)
        owner_name = getattr(project_card_dto, 'owner_name', 'Не назначен')
        manager_name = getattr(project_card_dto, 'manager_name', None)

        if manager_name:
            info_text = f"Владелец: {owner_name} | Куратор: {manager_name}"
        else:
            info_text = f"Владелец: {owner_name}"

        # Дата создания
        created_at = getattr(project_card_dto, 'created_at', None)
        start_date_text = f"Создан: {created_at}" if created_at else ""

        # Участники
        member_count = getattr(project_card_dto, 'member_count', 0)
        participants_text = f"Участники: {member_count} чел."

        # Администраторы
        admin_count = getattr(project_card_dto, 'admin_count', 0)
        admins_text = f"Админы: {admin_count} чел."

        # Задачи
        tasks_total = getattr(project_card_dto, 'tasks_total', 0)
        tasks_done = getattr(project_card_dto, 'tasks_done', 0)

        if tasks_total > 0:
            tasks_text = f"Задачи: {tasks_done} / {tasks_total} выполнено"
        else:
            tasks_text = "Задачи: 0"

        # Цвет для задач (зеленый если все выполнены)
        tasks_style = "color: #4CAF50;" if (tasks_total > 0 and tasks_done == tasks_total) else "color: #1B232A;"

        # Колонки
        columns_count = getattr(project_card_dto, 'columns_count', 0)
        columns_text = f"Колонок: {columns_count}"

        return {
            'name': project_card_dto.name if project_card_dto.name else '',
            'progress': progress,
            'info_text': info_text,
            'start_date_text': start_date_text,
            'participants_text': participants_text,
            'admins_text': admins_text,
            'tasks_text': tasks_text,
            'tasks_style': tasks_style,
            'columns_text': columns_text
        }