import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QLabel, QFrame
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QPainterPath


class CropGraphicsView(QGraphicsView):
    """Кастомный GraphicsView для обрезки изображения с круглой областью"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background-color: #1B232A;")

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = None
        self.zoom_factor = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 5.0

        # Переменные для перемещения
        self._drag_start = QPointF()
        self._is_dragging = False

        # Размер области обрезки (круг)
        self.crop_size = 400

    def set_pixmap(self, pixmap: QPixmap):
        """Устанавливает изображение для обрезки"""
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        # РАСШИРЯЕМ СЦЕНУ: добавляем отступы вокруг картинки,
        # чтобы её можно было свободно двигать влево/вправо и вверх/вниз
        w, h = pixmap.width(), pixmap.height()
        margin_w = w * 1.5
        margin_h = h * 1.5
        self.scene.setSceneRect(-margin_w, -margin_h, w + margin_w * 2, h + margin_h * 2)

        # Центрируем камеру на самой картинке
        self.centerOn(self.pixmap_item)
        self.zoom_factor = 1.0

        # Определяем размер обрезки
        self._update_crop_size()

    def _update_crop_size(self):
        """Обновляет размер области обрезки"""
        if self.pixmap_item:
            view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            self.crop_size = min(view_rect.width(), view_rect.height()) * 0.75

    def wheelEvent(self, event):
        """Масштабирование колесиком мыши"""
        delta = event.angleDelta().y()
        factor = 1.25 if delta > 0 else 0.8

        new_zoom = self.zoom_factor * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom_factor = new_zoom
            self.scale(factor, factor)
            self._update_crop_size()
            self.scene.update()

    def resizeEvent(self, event):
        """Обновляет размер обрезки при изменении размера виджета"""
        super().resizeEvent(event)
        self._update_crop_size()
        self.scene.update()

    def mousePressEvent(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position()
            self._is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Перетаскивание изображения"""
        if self._is_dragging:
            delta = event.position() - self._drag_start
            self._drag_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            self.scene.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Конец перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.scene.update()
        super().mouseReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Рисует затемнение вне круглой области обрезки"""
        if not self.pixmap_item:
            return

        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        center = view_rect.center()
        radius = self.crop_size / 2

        full_path = QPainterPath()
        full_path.addRect(view_rect)

        circle_path = QPainterPath()
        circle_path.addEllipse(center, radius, radius)

        mask_path = full_path.subtracted(circle_path)

        # Маска
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(mask_path)

        # Белая рамка
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(255, 255, 255, 220), 3)
        painter.setPen(pen)
        painter.drawEllipse(center, radius, radius)

        # Перекрестие
        pen = QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        cx, cy, r = int(center.x()), int(center.y()), int(radius)
        painter.drawLine(cx - int(r * 0.6), cy, cx + int(r * 0.6), cy)
        painter.drawLine(cx, cy - int(r * 0.6), cx, cy + int(r * 0.6))

        # Уголки
        corner_size = int(r * 0.08)
        pen = QPen(QColor(255, 255, 255, 200), 2)
        painter.setPen(pen)
        corners = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        for dx, dy in corners:
            x = cx + dx * r
            y = cy + dy * r
            painter.drawLine(x - dx * corner_size, y, x, y)
            painter.drawLine(x, y - dy * corner_size, x, y)

    def get_cropped_pixmap(self) -> QPixmap:
        """Получает обрезанное изображение в круге с корректным захватом сцены"""
        if not self.pixmap_item:
            return QPixmap()

        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        center = view_rect.center()
        radius = self.crop_size / 2

        # Запрашиваем рендеринг ровно той области, что находится внутри круга
        target_size = int(radius * 2)
        result = QPixmap(target_size, target_size)
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Создаем круглую маску
        path = QPainterPath()
        path.addEllipse(0, 0, target_size, target_size)
        painter.setClipPath(path)

        # Рендерим нужный участок сцены
        source_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        self.scene.render(painter, QRectF(0, 0, target_size, target_size), source_rect)
        painter.end()

        return result


class AvatarCropDialog(QDialog):
    """Диалог для обрезки аватара с круглой областью"""

    crop_finished = pyqtSignal(QPixmap)

    def __init__(self, original_pixmap: QPixmap, parent=None, crop_size: int = 400):
        super().__init__(parent)
        self.original_pixmap = original_pixmap
        self.cropped_pixmap = None
        self.crop_size = crop_size

        self.setWindowTitle("Обрезка фото для профиля")
        self.setMinimumSize(600, 700)
        self.setModal(True)

        self._setup_ui()
        self._connect_signals()

        self.crop_view.set_pixmap(original_pixmap)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Выберите область для аватара")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1B232A;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("Перетаскивайте изображение и используйте колёсико мыши для масштабирования")
        hint.setStyleSheet("font-size: 12px; color: #666;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.crop_view = CropGraphicsView()
        self.crop_view.setMinimumHeight(400)
        layout.addWidget(self.crop_view)

        controls = QHBoxLayout()

        self.btn_reset = QPushButton("Сбросить")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #1B232A;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0C0C0;
            }
        """)
        controls.addWidget(self.btn_reset)

        controls.addStretch()

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 30px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        controls.addWidget(self.btn_save)

        layout.addLayout(controls)
        self.setStyleSheet("QDialog { background-color: white; }")

    def _connect_signals(self):
        self.btn_reset.clicked.connect(self._reset_view)
        if hasattr(self, 'btn_cancel'):
            self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save_cropped)

    def _reset_view(self):
        if self.crop_view.pixmap_item:
            self.crop_view.resetTransform()
            self.crop_view.centerOn(self.crop_view.pixmap_item)
            self.crop_view.zoom_factor = 1.0
            self.crop_view._update_crop_size()
            self.crop_view.scene.update()

    def _save_cropped(self):
        cropped = self.crop_view.get_cropped_pixmap()
        self.cropped_pixmap = cropped
        self.crop_finished.emit(cropped)
        self.accept()

    def get_cropped_pixmap(self) -> QPixmap:
        return self.cropped_pixmap