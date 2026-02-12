from PyQt6.QtWidgets import QWidget, QListWidgetItem, QGraphicsScene
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import QRectF
from PyQt6.uic import loadUi
import psycopg2
from datetime import datetime


class GanttPage(QWidget):
    def __init__(self, project_id, db_conn):
        super().__init__()

        loadUi("ui/gantt_page.ui", self)

        self.project_id = project_id
        self.conn = db_conn

        self.scene = QGraphicsScene()
        self.ganttView.setScene(self.scene)

        self.load_tasks()
        self.draw_gantt()

    def load_tasks(self):
        self.tasks = []

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, created_at, due_date, priority
                FROM tasks
                WHERE project_id = %s
                  AND due_date IS NOT NULL
                ORDER BY created_at
            """, (self.project_id,))

            for row in cur.fetchall():
                self.tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "start": row[2],
                    "end": row[3],
                    "priority": row[4]
                })

                item = QListWidgetItem(row[1])
                self.taskList.addItem(item)

    def draw_gantt(self):
        self.scene.clear()

        if not self.tasks:
            return

        start_date = min(t["start"] for t in self.tasks)
        px_per_day = 20
        row_height = 35

        for index, task in enumerate(self.tasks):
            duration = (task["end"] - task["start"]).days + 1
            x = (task["start"] - start_date).days * px_per_day
            y = index * row_height

            color = self.get_priority_color(task["priority"])

            rect = QRectF(x, y, duration * px_per_day, 24)
            self.scene.addRect(rect, brush=QBrush(color))

            self.scene.addText(task["title"]).setPos(x + 5, y)

        self.scene.setSceneRect(self.scene.itemsBoundingRect())

    def get_priority_color(self, priority):
        return {
            "low": QColor("#7a6a50"),
            "medium": QColor("#ccab6e"),
            "high": QColor("#D22730"),
            "critical": QColor("#862633")
        }.get(priority, QColor("#999999"))
