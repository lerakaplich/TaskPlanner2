import sys
import traceback
from PyQt6.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QWidget, QApplication
from PyQt6.QtCore import Qt


def setup_exception_hook():
    """Настройка глобального перехвата исключений"""
    sys.excepthook = exception_hook


def exception_hook(exctype, value, tb):
    """Функция, которая вызывается при любой ошибке"""
    # Печатаем в консоль (на всякий случай)
    traceback_formated = "".join(traceback.format_exception(exctype, value, tb))
    print(traceback_formated)

    # Если приложение еще живо, показываем окно
    app = QApplication.instance()
    if app:
        show_error_window(traceback_formated, str(value))

    # Не закрываем приложение принудительно,
    # чтобы можно было скопировать текст
    # sys.exit(1) # Раскомментируй, если хочешь, чтобы приложение всё же падало


def show_error_window(traceback_text, error_message):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Произошла ошибка")
    msg_box.setText(f"Критическая ошибка: {error_message}")
    msg_box.setInformativeText("Текст ошибки представлен ниже. Вы можете скопировать его для отладки.")

    # Создаем поле с текстом, который можно копировать
    error_details = QTextEdit()
    error_details.setPlainText(traceback_text)
    error_details.setReadOnly(True)
    error_details.setMinimumHeight(200)
    error_details.setMinimumWidth(500)

    # Добавляем его в раскрывающуюся секцию "Show Details"
    msg_box.layout().addWidget(error_details, 1, 0, 1, msg_box.layout().columnCount())

    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()