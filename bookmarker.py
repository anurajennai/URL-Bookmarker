import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QComboBox,
    QCalendarWidget,
    QDialog,
)
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QColor
import sqlite3
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import datetime
import webbrowser


class BookmarkApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bookmarking App")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()  # Single widget for both functionalities

        self.init_ui()

        self.setCentralWidget(self.central_widget)

    def init_ui(self):
        layout = QVBoxLayout()

        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL")
        self.url_input.textChanged.connect(self.on_text_changed)

        # Calendar widget for selecting due date
        self.calendar = QCalendarWidget()
        self.calendar.hide()

        # Due date button to set the due date from the calendar
        self.due_date_button = QPushButton("Select Due Date")
        self.due_date_button.clicked.connect(self.toggle_calendar)

        # Save button to save the bookmark
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_bookmark)

        # ComboBox for selecting sorting criteria
        self.sort_criteria_combo = QComboBox()
        self.sort_criteria_combo.addItems(["Due Date", "Stored Date"])
        self.sort_criteria_combo.currentIndexChanged.connect(self.refresh_display)

        # Table for displaying bookmarks
        self.table = QTableWidget()
        self.table.setColumnCount(8)  # Add one more column for buttons
        self.table.setHorizontalHeaderLabels(
            ["ID", "URL", "Title", "Summary", "Stored Date", "Due Date", "", ""]
        )  # Added two empty headers for buttons

        # Set column widths and enable text wrap
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 200)

        # Add vertical scroll bar to the table
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        # Add widgets to the layout
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_input)
        layout.addWidget(QLabel("Due Date:"))
        layout.addWidget(self.calendar)
        layout.addWidget(self.due_date_button)
        layout.addWidget(self.save_button)
        layout.addWidget(QLabel("Sort by:"))
        layout.addWidget(self.sort_criteria_combo)
        layout.addWidget(self.table)

        self.refresh_display()

        self.central_widget.setLayout(layout)

    def save_bookmark(self):
        # Save a bookmark to the database
        url = self.url_input.text().strip()
        due_date = self.calendar.selectedDate().toString("yyyy-MM-dd")

        if not url:
            self.show_error("URL cannot be empty.")
            return

        try:
            title, summary = self.extract_info(url)
        except Exception as e:
            self.show_error(f"Error fetching URL info: {e}")
            return

        try:
            # Connect to the database and insert bookmark data
            conn = sqlite3.connect("bookmarks.db")
            c = conn.cursor()
            c.execute(
                "INSERT INTO bookmarks (url, title, summary, stored_date, due_date) VALUES (?, ?, ?, ?, ?)",
                (url, title, summary, datetime.datetime.now(), due_date),
            )
            conn.commit()
            conn.close()
            self.show_success("Bookmark saved successfully.")
            self.refresh_display()  # Refresh the display after saving
            self.url_input.clear()  # Clear URL input field after saving
            self.save_button.setStyleSheet("background-color: lightgreen")  # Change save button color
        except sqlite3.Error as e:
            self.show_error(f"Database error: {e}")

    def extract_info(self, url):
        # Extract title and summary from a given URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "No title found"
        summary = soup.find("meta", attrs={"name": "description"})
        if summary:
            summary = summary["content"]
        else:
            summary = "No summary found"
        return title, summary

    def refresh_display(self):
        # Refresh the display of bookmarks in the table
        try:
            sort_criteria = self.sort_criteria_combo.currentText()

            conn = sqlite3.connect("bookmarks.db")
            c = conn.cursor()
            c.execute(
                "CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY, url TEXT, title TEXT, summary TEXT, stored_date TEXT, due_date TEXT)"
            )

            if sort_criteria == "Due Date":
                c.execute("SELECT * FROM bookmarks ORDER BY due_date")
            else:
                c.execute("SELECT * FROM bookmarks ORDER BY stored_date")

            bookmarks = c.fetchall()
            conn.close()

            self.table.setRowCount(0)
            for row, bookmark in enumerate(bookmarks):
                self.table.insertRow(row)
                for col, data in enumerate(bookmark):
                    item = QTableWidgetItem(str(data))
                    # Set item flags for URL, title, and summary columns
                    if col in [1, 2, 3]:
                        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, item)

                # Highlight due date column if the due date has expired
                due_date_item = self.table.item(row, 5)
                if due_date_item:
                    due_date = datetime.datetime.strptime(due_date_item.text(), "%Y-%m-%d")
                    if due_date < datetime.datetime.now():
                        due_date_item.setForeground(QtGui.QColor("red"))

                # Add Read, Delete, and Update Due Date buttons to each row
                read_button = QPushButton("Read")
                read_button.clicked.connect(
                    lambda _, url=bookmark[1]: self.open_url(url)
                )
                self.table.setCellWidget(row, 6, read_button)

                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(
                    lambda _, id=bookmark[0]: self.delete_bookmark(id)
                )
                self.table.setCellWidget(row, 7, delete_button)

                update_due_date_button = QPushButton("Update Due Date")
                update_due_date_button.clicked.connect(
                    lambda _, id=bookmark[0]: self.update_due_date(id)
                )
                self.table.setCellWidget(row, 8, update_due_date_button)

        except sqlite3.Error as e:
            self.show_error(f"Database error: {e}")

    def toggle_calendar(self):
        # Show or hide the calendar widget
        if self.calendar.isVisible():
            self.calendar.hide()
        else:
            self.calendar.show()

    def on_text_changed(self):
        # Change save button color when text in URL field changes
        self.save_button.setStyleSheet("background-color: None")

    def open_url(self, url):
        # Open a URL in the default web browser
        webbrowser.open(url)

    def delete_bookmark(self, id):
        # Delete a bookmark from the database
        try:
            conn = sqlite3.connect("bookmarks.db")
            c = conn.cursor()
            c.execute("DELETE FROM bookmarks WHERE id=?", (id,))
            conn.commit()
            conn.close()
            self.show_success("Bookmark deleted successfully.")
            self.refresh_display()  # Refresh the display after deletion
        except sqlite3.Error as e:
            self.show_error(f"Database error: {e}")

    def update_due_date(self, id):
        # Update the due date of a bookmark in the database
        new_due_date, ok = self.get_new_due_date()
        if ok:
            try:
                conn = sqlite3.connect("bookmarks.db")
                c = conn.cursor()
                c.execute(
                    "UPDATE bookmarks SET due_date=? WHERE id=?", (new_due_date, id)
                )
                conn.commit()
                conn.close()
                self.show_success("Due date updated successfully.")
                self.refresh_display()  # Refresh the display after update
            except sqlite3.Error as e:
                self.show_error(f"Database error: {e}")

    def get_new_due_date(self):
        # Open a dialog to get a new due date from the user
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Due Date")
        layout = QVBoxLayout()
        calendar = QCalendarWidget()
        layout.addWidget(calendar)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        dialog.setLayout(layout)
        if dialog.exec_() == QDialog.Accepted:
            return calendar.selectedDate().toString("yyyy-MM-dd"), True
        return "", False

    def show_error(self, message):
        # Display an error message dialog
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        # Display a success message dialog
        QMessageBox.information(self, "Success", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BookmarkApp()
    window.show()
    sys.exit(app.exec_())