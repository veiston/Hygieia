import sys
import logging
import markdown
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QFileDialog, QProgressBar, QHBoxLayout, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, pyqtSlot, QEvent
from PyQt6.QtGui import QKeyEvent, QDragEnterEvent, QDropEvent

logging.basicConfig(level=logging.INFO)

QSS_PATH = "style.qss"
HTML_PATH = "main.html"

class ChatbotUI(QMainWindow):
    sendMessage = pyqtSignal(str)
    sendImage = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hygieia - Medical AI Chatbot")
        self.setGeometry(100, 100, 600, 500)
        self.setMinimumSize(400, 400)
        self.messages = []
        self._is_sending = False
        self._message_history = []
        self._history_index = -1
        self.main_layout = QVBoxLayout()
        central = QWidget()
        central.setLayout(self.main_layout)
        self.setCentralWidget(central)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setAcceptRichText(True)
        self.chat_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.chat_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_display.customContextMenuRequested.connect(self.show_context_menu)
        self.chat_display.setAcceptDrops(True)
        self.main_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.installEventFilter(self)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_text)
        input_layout.addWidget(self.send_button)

        self.attach_button = QPushButton("Attach Image")
        self.attach_button.clicked.connect(self.attach_image)
        input_layout.addWidget(self.attach_button)

        self.import_button = QPushButton("Import File")
        self.import_button.clicked.connect(self.import_file)
        input_layout.addWidget(self.import_button)

        self.main_layout.addLayout(input_layout)

        self.clear_button = QPushButton("Clear Conversation")
        self.clear_button.clicked.connect(self.clear_conversation)
        self.main_layout.addWidget(self.clear_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        self.input_field.setFocus()
        self._load_stylesheet()
        self._load_html_template()

    def _load_stylesheet(self):
        try:
            with open(QSS_PATH, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

    def _load_html_template(self):
        try:
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                self.bubble_template = f.read()
        except Exception:
            self.bubble_template = None

    def eventFilter(self, a0, a1):
        # handle key events on the input field
        watched = a0
        event = a1
        if watched == self.input_field and isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return False
                self.send_text()
                return True
            elif event.key() == Qt.Key.Key_L and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.clear_conversation()
                return True
            elif event.key() == Qt.Key.Key_Up and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.navigate_history(-1)
                return True
            elif event.key() == Qt.Key.Key_Down and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.navigate_history(1)
                return True
        return super().eventFilter(a0, a1)
    def navigate_history(self, direction):
        # move through typed messages
        if not self._message_history:
            return
        self._history_index += direction
        self._history_index = max(-1, min(self._history_index, len(self._message_history) - 1))
        if self._history_index == -1:
            self.input_field.clear()
        else:
            self.input_field.setText(self._message_history[self._history_index])
    def dragEnterEvent(self, a0):
        event = a0
        # allow file drops with URLs
        if isinstance(event, QDragEnterEvent):
            md = event.mimeData()
            if md is not None and hasattr(md, 'hasUrls') and md.hasUrls():
                event.acceptProposedAction()
                return
        return

    def dropEvent(self, a0):
        event = a0
        if not isinstance(event, QDropEvent):
            return
        md = event.mimeData()
        if md is None or not hasattr(md, 'urls'):
            return
        for url in md.urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                self.add_user_image_message(file_path)
                self.sendImage.emit(file_path)
            elif file_path.lower().endswith((".pdf", ".docx", ".pptx")):
                self.import_file_dialog(file_path)
            else:
                self.display_error("Unsupported file type dropped.")
        event.acceptProposedAction()
    def import_file_dialog(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Import File", "", "Documents (*.pdf *.docx *.pptx)")
        if file_path:
            try:
                from anyFileRead import anyReader
                content = anyReader(file_path)
                if content:
                    self.add_system_message("Imported File Content:")
                    self.add_bot_message(str(content))
                else:
                    self.add_system_message("No content imported.")
            except Exception as e:
                self.display_error(f"Error importing file: {e}")
    def open_link(self, url):
        import webbrowser
        webbrowser.open(url.toString())
    def _render_messages(self):
        html = "\n".join(self.messages)
        self.chat_display.setHtml(html)
        vsb = self.chat_display.verticalScrollBar()
        if vsb is not None:
            vsb.setValue(vsb.maximum())
    def _format_message(self, message: str, align: str) -> str:
        import re
        converted = markdown.markdown(message, extensions=['extra', 'sane_lists', 'smarty'])
        url_pattern = r"((https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+))"
        converted = re.sub(url_pattern, r'<a href="\1">\1</a>', converted)
        cls = {"right": "user-message", "left": "bot-message", "center": "system-message"}.get(align, "user-message")
        t = datetime.datetime.now().strftime("%H:%M")
        justify = {
            "right": "flex-end",
            "left": "flex-start",
            "center": "center"
        }[align]
        if self.bubble_template:
            return self.bubble_template.format(
                align=align,
                cls=cls,
                style=self._bubble_style(cls),
                converted=converted,
                t=t,
                justify=justify
            )
        # fallback
        return f"""
        <div class=\"message-container\" style=\"width:100%; display:flex; justify-content:{justify};\">
            <div class=\"message-bubble {cls}\" style=\"{self._bubble_style(cls)}\">
                {converted}<br>
                <span style=\"font-size:10px; color:#999;\">{t}</span>
            </div>
        </div>
        """
    def _bubble_style(self, cls):
        styles = {
            "user-message": "border-radius: 22px 22px 22px 8px; background: #92D050; padding: 12px 18px; margin: 8px 0 8px 25%; max-width: 70%; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: right; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;",
            "bot-message": "border-radius: 22px 22px 8px 22px; background: #E8F5E9; padding: 12px 18px; margin: 8px 25% 8px 0; max-width: 70%; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: left; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;",
            "system-message": "border-radius: 20px; background: #E0E0E0; padding: 10px 16px; margin: 6px auto; max-width: 60%; text-align: center; color: #666; font-size: 13px; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;"
        }
        return styles[cls]
    def add_user_message(self, message: str) -> None:
        f = self._format_message(message, align='right')
        if not self.messages or self.messages[-1] != f:
            self.messages.append(f)
            self._render_messages()
        self._message_history.append(message)
        self._history_index = -1
    def add_bot_message(self, message: str) -> None:
        f = self._format_message(message, align='left')
        self.messages.append(f)
        self._render_messages()
    def add_system_message(self, message: str) -> None:
        f = self._format_message(message, align='center')
        self.messages.append(f)
        self._render_messages()
    def add_user_image_message(self, image_path: str) -> None:
        p = Path(image_path).absolute()
        img_src = f"file:///{p.as_posix()}"
        img_tag = f'<img src="{img_src}" style="max-width:80%; border-radius:10px;">'
        t = datetime.datetime.now().strftime("%H:%M")
        html = f"""
        <div class=\"message-container\">\n            <div class=\"message-bubble user-message\">\n                {img_tag}<br>\n                <span style=\"font-size:10px; border-radius: 45px; color:#999;\">{t}</span>\n            </div>\n        </div>\n        """
        self.messages.append(html)
        self._render_messages()
    def update_last_bot_message(self, message: str) -> None:
        if self.messages:
            self.messages[-1] = self._format_message(message, align='left')
            self._render_messages()
    def send_text(self):
        if self._is_sending:
            return
        self._is_sending = True
        user_input = self.input_field.text().strip()
        if user_input:
            if not self.messages or self.messages[-1] != self._format_message(user_input, align='right'):
                self.add_user_message(user_input)
            self.input_field.clear()
            self.sendMessage.emit(user_input)
        self.input_field.setFocus()
        self._is_sending = False
    def attach_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Attach Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.add_user_image_message(file_path)
            self.sendImage.emit(file_path)
    def import_file(self):
        self.import_file_dialog()
    def clear_conversation(self):
        self.messages.clear()
        self.chat_display.clear()
        self.input_field.setFocus()
    def set_input_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)
        self.import_button.setEnabled(enabled)
        if enabled:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(0)
    def display_error(self, error_message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", error_message)
    def show_context_menu(self, pos):
        cursor = self.chat_display.cursorForPosition(pos)
        cursor.select(cursor.SelectionType.LineUnderCursor)
        selected_text = cursor.selectedText()
        menu = QMenu(self)
        copy_action = menu.addAction("Copy Message")
        open_link_action = menu.addAction("Open Link")
        action = menu.exec(self.chat_display.mapToGlobal(pos))
        if action == copy_action:
            if selected_text:
                cb = QApplication.clipboard()
                if cb is not None and hasattr(cb, 'setText'):
                    cb.setText(selected_text)
        elif action == open_link_action:
            # try to open selected text as URL
            txt = selected_text.strip()
            if txt.startswith("http://") or txt.startswith("https://"):
                import webbrowser
                webbrowser.open(txt)
            else:
                # nothing to open
                pass