import sys
from PyQt6.QtWidgets import QApplication

from windows.projects.main_window import MainWindow
from database import test_connections


def main():

    # Проверка БД
    test_connections()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()