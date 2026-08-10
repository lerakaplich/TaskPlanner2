# windows/profile/edit_profile.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog, QLabel, QFrame, QGridLayout  # ✅ ДОБАВЛЕН QGridLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainterPath, QPainter

from windows.profile.avatar_crop_dialog import AvatarCropDialog


class EditProfileDialog(QDialog):
    """Диалог редактирования профиля (только UI)"""

    def __init__(self, parent=None, employee_data=None, profile_service=None):
        super().__init__(parent)

        self.employee_data = employee_data or {}
        self.profile_service = profile_service
        self.employee_id = self.employee_data.get('id')
        self._avatar_path = None
        self._avatar_data = None
        self._avatar_label = None
        self._original_pixmap = None  # Сохраняем оригинал для обрезки

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
        uic.loadUi(os.path.join(ui_path, "edit_profile.ui"), self)

        self._setup_avatar_placeholder()
        self._fill_fields()
        self._load_avatar()
        self._connect_signals()

    def _choose_avatar(self):
        """Выбор фото для аватара с обрезкой"""
        if not self.profile_service:
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите фото для профиля",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*.*)"
        )

        if not file_path:
            return

        try:
            # Загружаем изображение
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
                return

            # Сохраняем оригинал
            self._original_pixmap = pixmap

            # Показываем диалог обрезки
            print("🖼️ Открываем диалог обрезки...")
            crop_dialog = AvatarCropDialog(pixmap, self)
            if crop_dialog.exec() == QDialog.DialogCode.Accepted:
                cropped_pixmap = crop_dialog.get_cropped_pixmap()
                if cropped_pixmap and not cropped_pixmap.isNull():
                    print("✅ Изображение обрезано успешно")
                    # Показываем обрезанное изображение
                    self._set_avatar_pixmap(cropped_pixmap)

                    # ✅ ИСПРАВЛЕНО: используем QBuffer вместо QIODevice
                    from PyQt6.QtCore import QByteArray, QBuffer
                    ba = QByteArray()
                    buffer = QBuffer(ba)
                    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
                    cropped_pixmap.save(buffer, "PNG")
                    buffer.close()
                    self._avatar_data = ba.data()
                    self._avatar_filename = os.path.basename(file_path).rsplit('.', 1)[0] + '.png'
                    print(f"   Сохранено {len(self._avatar_data)} байт")
                else:
                    print("❌ Обрезка не удалась, используем оригинал")
                    # Если обрезка не удалась, используем оригинал
                    self._set_avatar_pixmap(pixmap)
                    with open(file_path, "rb") as f:
                        self._avatar_data = f.read()
                    self._avatar_filename = os.path.basename(file_path)
            else:
                print("❌ Пользователь отменил обрезку")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить изображение: {e}")
            import traceback
            traceback.print_exc()

    def _setup_avatar_placeholder(self):
        """Создаёт QLabel внутри photoContainer для отображения фото"""
        photo_container = getattr(self, 'photoContainer', None)
        if not photo_container:
            return

        # Проверяем, есть ли уже QLabel в контейнере
        existing_label = None
        for child in photo_container.children():
            if isinstance(child, QLabel):
                existing_label = child
                break

        if existing_label:
            self._avatar_label = existing_label
            # Убеждаемся, что настройки правильные
            self._avatar_label.setScaledContents(False)
            self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return

        # Создаём новый QLabel
        self._avatar_label = QLabel(photo_container)
        self._avatar_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setScaledContents(False)  # Важно: выключаем авто-масштабирование

        # Добавляем QLabel в QGridLayout контейнера
        layout = photo_container.layout()
        if layout and isinstance(layout, QGridLayout):
            # Добавляем QLabel на всю область
            layout.addWidget(self._avatar_label, 0, 0, 1, 1)
            # Устанавливаем растяжение
            layout.setRowStretch(0, 1)
            layout.setColumnStretch(0, 1)

            # Перемещаем кнопку в правый нижний угол
            btn_edit = getattr(self, 'btnEditPhoto', None)
            if btn_edit:
                layout.removeWidget(btn_edit)
                layout.addWidget(btn_edit, 0, 0, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
                # Поднимаем кнопку на передний план
                btn_edit.raise_()

        # Устанавливаем аватар по умолчанию
        self._set_default_avatar()

    def _set_default_avatar(self):
        """Устанавливает аватар по умолчанию (инициалы)"""
        if not self._avatar_label:
            return

        # Получаем инициалы
        first = self.employee_data.get('first_name', '')[:1].upper()
        last = self.employee_data.get('last_name', '')[:1].upper()
        initials = f"{last}{first}" if last and first else "??"

        # Создаём цветной круг с инициалами
        from PyQt6.QtGui import QPainter, QColor, QFont

        size = 160
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Цвет фона (на основе ID)
        colors = ["#D22730", "#ccab6e", "#1B232A", "#862633", "#4CAF50"]
        color = colors[self.employee_id % len(colors)] if self.employee_id else colors[0]

        # Рисуем круг
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Рисуем инициалы
        painter.setPen(QColor("white"))
        font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()

        self._avatar_label.setPixmap(pixmap)
        self._avatar_label.setScaledContents(True)  # Включаем масштабирование
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _fill_fields(self):
        """Заполняет поля формы данными через сервис"""
        if not self.profile_service:
            return

        data = self.profile_service.get_edit_form_data(self.employee_data)

        if hasattr(self, 'lineEditPhone'):
            self.lineEditPhone.setText(data["phone_number"])
        if hasattr(self, 'lineEditEmail'):
            self.lineEditEmail.setText(data["email"])
        if hasattr(self, 'dateEditBirth') and data["birth_date"]:
            self.dateEditBirth.setDate(data["birth_date"])

    def _load_avatar(self):
        """Загружает текущий аватар"""
        if not self.profile_service or not self.employee_id:
            return

        pixmap = self.profile_service.get_avatar_pixmap(self.employee_id, 160)
        if pixmap:
            self._set_avatar_pixmap(pixmap)
        else:
            self._set_default_avatar()

    def _set_avatar_pixmap(self, pixmap: QPixmap):
        """Устанавливает пиксельную карту аватара в UI"""
        if not self._avatar_label:
            return

        # Размер контейнера
        container_size = 160

        # Создаём квадратное изображение нужного размера
        result = QPixmap(container_size, container_size)
        result.fill(Qt.GlobalColor.transparent)

        # Масштабируем изображение с сохранением пропорций, чтобы оно вписалось в круг
        scaled = pixmap.scaled(
            container_size, container_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Вычисляем позицию для центрирования
        x = (container_size - scaled.width()) // 2
        y = (container_size - scaled.height()) // 2

        # Рисуем с круглой маской
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Создаём круглую маску
        path = QPainterPath()
        path.addEllipse(0, 0, container_size, container_size)
        painter.setClipPath(path)

        # Рисуем изображение по центру
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self._avatar_label.setPixmap(result)
        self._avatar_label.setScaledContents(True)  # Включаем масштабирование
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _connect_signals(self):
        if hasattr(self, 'btnSave'):
            self.btnSave.clicked.connect(self._save_profile)
        if hasattr(self, 'btnCancel'):
            self.btnCancel.clicked.connect(self.reject)

        # Используем btnEditPhotoLabel как основную кнопку выбора фото
        if hasattr(self, 'btnEditPhotoLabel'):
            self.btnEditPhotoLabel.clicked.connect(self._choose_avatar)
        elif hasattr(self, 'btnEditPhoto'):
            self.btnEditPhoto.clicked.connect(self._choose_avatar)

        if hasattr(self, 'btnDeletePhoto'):
            self.btnDeletePhoto.clicked.connect(self._delete_avatar)

    def _delete_avatar(self):
        """Удаление аватара"""
        if not self.profile_service:
            return

        reply = QMessageBox.question(
            self,
            "Удаление фото",
            "Вы уверены, что хотите удалить фото профиля?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Очищаем превью и показываем аватар по умолчанию
            self._set_default_avatar()

            # Помечаем для удаления
            self._avatar_data = None
            self._avatar_filename = None

            # Удаляем в БД при сохранении
            self._delete_avatar_on_save = True

    def _save_profile(self):
        """Сохраняет изменения через сервис"""
        if not self.profile_service:
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        # Сохраняем основные данные
        updates = self.profile_service.build_update_data(
            phone=self.lineEditPhone.text() if hasattr(self, 'lineEditPhone') else None,
            email=self.lineEditEmail.text() if hasattr(self, 'lineEditEmail') else None,
            birth_date=self.dateEditBirth.date() if hasattr(self, 'dateEditBirth') else None
        )

        success = self.profile_service.update_profile(self.employee_id, updates)

        if not success:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изменения в базе данных")
            return

        # Сохраняем аватар (только в БД)
        if hasattr(self, '_avatar_data') and self._avatar_data:
            success, _ = self.profile_service.save_avatar(
                self.employee_id,
                self._avatar_data,
                self._avatar_filename if hasattr(self, '_avatar_filename') else None
            )
            if not success:
                QMessageBox.warning(self, "Предупреждение", "Не удалось сохранить фото профиля")
            else:
                # ✅ Явно обновляем аватар в UI
                self._load_avatar()
        elif hasattr(self, '_delete_avatar_on_save') and self._delete_avatar_on_save:
            self.profile_service.delete_avatar(self.employee_id)
            # ✅ Показываем аватар по умолчанию
            self._set_default_avatar()

        self.accept()