# windows/profile/profile_page.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidgetItem,
                             QMessageBox, QFrame, QLabel, QProgressBar, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QFont

from services.analytics_service.analytics_service import AnalyticsService
from services.profile_service import ProfileService
from windows.profile.chart_widget import ChartWidget
from windows.profile.edit_profile import EditProfileDialog
from windows.profile.projects_page import ProjectsPage


class ProfilePage(QWidget):
    """Страница профиля сотрудника (только UI)"""

    edit_profile_requested = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, employee_id=None, parent=None, current_user=None, service=None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.main_window = parent
        self.current_user = current_user
        self.projects_page = None

        if not self.employee_id and current_user:
            self.employee_id = current_user.get('id')

        from server_app.database import get_tasks_session
        session = get_tasks_session()
        self.profile_service = service or ProfileService(session=session)

        if current_user:
            self.profile_service.set_current_user_id(current_user.get('id'))

        self.employee_data = {}

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
        uic.loadUi(os.path.join(ui_path, "profile_page.ui"), self)

        self._init_chart_widget()
        self._connect_signals()

        if self.employee_id:
            self.load_employee()

    def _connect_signals(self):
        if hasattr(self, 'btnEditProfile'):
            self.btnEditProfile.clicked.connect(self._open_edit_profile)
        if hasattr(self, 'btnCompletedProjects'):
            self.btnCompletedProjects.clicked.connect(self._show_completed_projects)
        if hasattr(self, 'btnRefresh'):
            self.btnRefresh.clicked.connect(self.refresh_data)
        if hasattr(self, 'btnExit'):
            self.btnExit.clicked.connect(self._on_logout)

    def showEvent(self, event):
        """Срабатывает при каждом показе страницы"""
        super().showEvent(event)
        print("👤 ProfilePage.showEvent - обновляем содержимое")
        if self.employee_id:
            QTimer.singleShot(100, self.load_employee)

    def load_employee(self):
        """Загружает данные через сервис и обновляет UI"""
        print(f"\n🔍 [DEBUG] ProfilePage.load_employee, employee_id={self.employee_id}")

        if not self.profile_service:
            print("   ❌ profile_service отсутствует!")
            return

        # Загружаем основные данные
        self.employee_data = self.profile_service.get_employee_profile(self.employee_id)
        print(f"   Загружены данные сотрудника: {self.employee_data.get('full_name')}")

        # ✅ Проверяем наличие аватара в БД
        avatar_data = self.profile_service.employee_data_repo.get_avatar_data(self.employee_id)
        if avatar_data:
            print(f"   ✅ Аватар в БД: {len(avatar_data)} байт")
        else:
            print("   ❌ Аватар в БД отсутствует")

        # Загружаем статистику и проекты
        stats = self.profile_service.get_employee_statistics(self.employee_id)
        projects = self.profile_service.get_employee_projects(self.employee_id)
        print(f"   Статистика: {stats}")

        # Обогащаем данные
        self.employee_data.update(stats)
        self.employee_data["active_projects"] = projects

        analytics = AnalyticsService(self.profile_service.session)
        emp_analytics = analytics.get_employee_card_data(self.employee_id)
        self.employee_data["tag_analytics"] = emp_analytics.get("tag_analytics", [])
        print(f"   tag_analytics: {len(self.employee_data['tag_analytics'])} записей")

        # Обновляем UI
        self._update_ui()
        print("   UI обновлен")

        # Применяем права доступа
        self._apply_permissions()

    def  _apply_permissions(self):
        """Применяет права доступа к кнопкам профиля"""
        # Определяем, свой ли это профиль
        is_own_profile = False
        if self.current_user and self.employee_id:
            is_own_profile = (self.employee_id == self.current_user.get('id'))

        # Если профиль чужой - скрываем кнопки редактирования и выхода
        if not is_own_profile:
            # Скрываем кнопку редактирования
            if hasattr(self, 'btnEditProfile'):
                self.btnEditProfile.setVisible(False)
                self.btnEditProfile.hide()

            # Скрываем кнопку выхода
            if hasattr(self, 'btnExit'):
                self.btnExit.setVisible(False)
                self.btnExit.hide()

            # Меняем заголовок
            if hasattr(self, 'label_3'):
                employee_name = self.employee_data.get('full_name', 'Сотрудник')
                self.label_3.setText(f"Профиль сотрудника: {employee_name}")
        else:
            # Свой профиль - показываем все кнопки
            if hasattr(self, 'btnEditProfile'):
                self.btnEditProfile.setVisible(True)
                self.btnEditProfile.show()

            if hasattr(self, 'btnExit'):
                self.btnExit.setVisible(True)
                self.btnExit.show()

            if hasattr(self, 'label_3'):
                self.label_3.setText("Профиль сотрудника")

    def _set_round_avatar(self, pixmap: QPixmap):
        """Устанавливает круглый аватар"""
        if not hasattr(self, 'labelPhoto'):
            return

        if pixmap.isNull():
            self._set_default_avatar()
            return

        # 150px (ширина фрейма) - 8px (две рамки по 4px) = 142px
        size = 142

        # Создаём прозрачный холст
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Вырезаем круг под размер
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)

        # Масштабируем изображение с сохранением пропорций (Crop / Fill)
        scaled = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        # Центрируем изображение перед отрисовкой
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        # Настраиваем labelPhoto
        self.labelPhoto.setFixedSize(size, size)
        self.labelPhoto.setScaledContents(False)
        self.labelPhoto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelPhoto.setStyleSheet("""
            QLabel#labelPhoto {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        self.labelPhoto.setPixmap(rounded)
        self.labelPhoto.update()

    def _set_default_avatar(self):
        """Устанавливает аватар по умолчанию (инициалы)"""
        if not hasattr(self, 'labelPhoto'):
            return

        size = 142

        self.labelPhoto.setFixedSize(size, size)
        self.labelPhoto.setScaledContents(False)
        self.labelPhoto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.labelPhoto.setStyleSheet("""
            QLabel#labelPhoto {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        # Получаем инициалы
        data = self.employee_data
        first = data.get('first_name', '')[:1].upper()
        last = data.get('last_name', '')[:1].upper()
        initials = f"{last}{first}" if last and first else "?"

        # Создаём круг с инициалами
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        colors = ["#D22730", "#ccab6e", "#1B232A", "#862633", "#4CAF50"]
        color = colors[self.employee_id % len(colors)] if self.employee_id else colors[0]

        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        painter.setPen(QColor("white"))
        font_size = size // 3
        font = QFont("Arial", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()

        self.labelPhoto.setPixmap(pixmap)
        self.labelPhoto.update()

    def _update_ui(self):
        """Обновляет UI из self.employee_data"""
        data = self.employee_data

        # ✅ Загружаем аватар
        if hasattr(self, 'labelPhoto'):
            print(f"\n🔍 [AVATAR DEBUG] _update_ui")
            print(f"   frameAvatar.size: {self.frameAvatar.size()}")
            print(f"   labelPhoto.size ДО: {self.labelPhoto.size()}")

            # ПРИНУДИТЕЛЬНО обновляем геометрию перед установкой аватара
            self.frameAvatar.updateGeometry()
            self.labelPhoto.updateGeometry()

            if self.profile_service and self.employee_id:
                print(f"🖼️ Загрузка аватара для сотрудника {self.employee_id}")
                pixmap = self.profile_service.get_avatar_pixmap(self.employee_id, 400)
                if pixmap:
                    print(f"   ✅ Аватар загружен: {pixmap.width()}x{pixmap.height()}")
                    self._set_round_avatar(pixmap)
                else:
                    print("   ❌ Аватар не найден, показываем по умолчанию")
                    self._set_default_avatar()
            else:
                self._set_default_avatar()

         # ФИО
        if hasattr(self, 'labelFullName'):
            middle = f" {data.get('middle_name', '')}" if data.get('middle_name') else ""
            self.labelFullName.setText(f"{data.get('last_name', '')} {data.get('first_name', '')}{middle}")

        # Должность и отдел
        if hasattr(self, 'labelPosition'):
            self.labelPosition.setText(data.get('position', ''))
        if hasattr(self, 'labelDepartment'):
            self.labelDepartment.setText(data.get('department_name', '—'))

        # Контакты
        if hasattr(self, 'labelPhone'):
            self.labelPhone.setText(data.get('phone_number', ''))
        if hasattr(self, 'labelEmail'):
            self.labelEmail.setText(data.get('email', ''))

        # Дата рождения
        if hasattr(self, 'labelBirthDate'):
            birth = data.get('birth_date')
            if birth:
                try:
                    date = QDate.fromString(birth, "yyyy-MM-dd")
                    if date.isValid():
                        self.labelBirthDate.setText(date.toString("dd.MM.yyyy"))
                except:
                    pass

        # Статистика
        if hasattr(self, 'labelCompletedTasks'):
            self.labelCompletedTasks.setText(str(data.get('completed_tasks', 0)))
        if hasattr(self, 'labelActiveProjects'):
            self.labelActiveProjects.setText(str(data.get('projects_count', 0)))

        # Рейтинг
        rating = self.profile_service.calculate_rating(self.employee_data)
        if hasattr(self, 'labelKPD'):
            self.labelKPD.setText(f"КПД: {rating:.1f}%")
        self._update_rating_stars(rating)

        # Таблица навыков
        self._setup_skills_table()

        # Проекты
        self._create_projects_widgets()

        # График
        if hasattr(self, 'chart_widget'):
            tag_analytics = data.get('tag_analytics', [])
            self.chart_widget.update_chart_from_analytics(tag_analytics)

    def _update_rating_stars(self, rating: float):
        """Обновляет звёзды рейтинга"""
        stars = self.profile_service.calculate_rating_stars(rating)
        for i in range(1, 6):
            star_attr = f"star{i}"
            if hasattr(self, star_attr):
                star = getattr(self, star_attr)
                if i <= stars:
                    star.setStyleSheet("font-size: 24px; color: #FFD700;")
                else:
                    star.setStyleSheet("font-size: 24px; color: #E0E0E0;")

    def _setup_skills_table(self):
        """Заполняет таблицу навыков"""
        skills = self.employee_data.get('tag_analytics', [])
        table = getattr(self, 'tableSkills', None)
        if not table:
            return

        table.setRowCount(len(skills))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Тема", "КПД", "Задач"])

        for row, skill in enumerate(skills):
            table.setItem(row, 0, QTableWidgetItem(skill.get("tag", "")))
            table.setItem(row, 1, QTableWidgetItem(f"{skill.get('kpd', 0):.2f}"))
            table.setItem(row, 2, QTableWidgetItem(str(skill.get("count", 0))))

        table.horizontalHeader().setStretchLastSection(True)

    def _create_projects_widgets(self):
        """Создаёт виджеты проектов"""
        projects = self.employee_data.get("active_projects", [])
        container = getattr(self, 'projectsContainer', None)
        if not container:
            return

        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            container.setLayout(layout)

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not projects:
            label = QLabel("Нет активных проектов")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; padding: 20px; border: none;")
            layout.addWidget(label)
            return

        for project in projects:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame { background-color: white; border-radius: 8px; border: 1px solid #E0E0E0;
                         padding: 10px; margin: 5px; }
            """)
            v = QVBoxLayout(frame)
            v.setSpacing(8)

            name = QLabel(project.get("name", "Без названия"))
            name.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")

            progress = project.get("progress", 0)
            percent = QLabel(f"{progress}%")
            percent.setStyleSheet("color: #ccab6e; font-weight: bold; border: none;")

            h = QHBoxLayout()
            h.addWidget(name)
            h.addStretch()
            h.addWidget(percent)
            v.addLayout(h)

            bar = QProgressBar()
            bar.setValue(progress)
            bar.setStyleSheet("""
                QProgressBar { border: 1px solid #E0E0E0; border-radius: 4px; height: 10px; }
                QProgressBar::chunk { background-color: #D22730; border-radius: 4px; }
            """)
            v.addWidget(bar)

            tasks_label = QLabel(f"Задачи {project.get('completed_tasks', 0)}/{project.get('total_tasks', 0)}")
            tasks_label.setStyleSheet("color: #666; font-size: 12px; border: none;")
            v.addWidget(tasks_label)

            layout.addWidget(frame)

        layout.addStretch()

    def _init_chart_widget(self):
        """Инициализирует виджет графика"""
        if not hasattr(self, "frameChart"):
            return

        layout = self.frameChart.layout()
        if layout is None:
            layout = QVBoxLayout(self.frameChart)
            layout.setContentsMargins(0, 0, 0, 0)

        self.chart_widget = ChartWidget()
        self.chart_widget.set_profile_service(self.profile_service)
        layout.addWidget(self.chart_widget)

    def _on_logout(self):
        """Обработчик нажатия кнопки выхода из профиля"""

        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти из системы?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def _open_edit_profile(self):
        """Открывает диалог редактирования профиля"""
        edit_data = {
            'id': self.employee_id,
            'last_name': self.employee_data.get('last_name', ''),
            'first_name': self.employee_data.get('first_name', ''),
            'middle_name': self.employee_data.get('middle_name', ''),
            'position': self.employee_data.get('position', ''),
            'phone_number': self.employee_data.get('phone_number', ''),
            'work_number': self.employee_data.get('work_number', ''),
            'email': self.employee_data.get('email', ''),
            'birth_date': self.employee_data.get('birth_date', ''),
            'department_id': self.employee_data.get('department_id'),
            'division_id': self.employee_data.get('division_id'),
            'role': self.employee_data.get('role', 'user')
        }

        dialog = EditProfileDialog(self, employee_data=edit_data, profile_service=self.profile_service)
        if dialog.exec():
            self.load_employee()
            QMessageBox.information(self, "Профиль обновлен", "Данные профиля успешно обновлены")

    def _show_completed_projects(self):
        """Показать окно выполненных проектов"""
        try:
            projects = self.profile_service.get_employee_projects(self.employee_id)

            if self.projects_page is None:
                self.projects_page = ProjectsPage(
                    employee_id=self.employee_id,
                    mode="all",
                    projects_data=projects,
                    profile_service=self.profile_service
                )
                self.projects_page.back_requested.connect(self._hide_completed_projects)
            else:
                self.projects_page.update_data(projects_data=projects, employee_id=self.employee_id)

            self.projects_page.show()
            self.projects_page.raise_()
            self.projects_page.activateWindow()
        except Exception as e:
            print(f"Ошибка при открытии окна проектов: {e}")

    def _hide_completed_projects(self):
        if self.projects_page:
            self.projects_page.hide()

    def refresh_data(self):
        """Обновляет данные профиля"""
        self.load_employee()