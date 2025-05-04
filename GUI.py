import sys
import logging
import markdown
import datetime
import anyFileRead
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QFileDialog, QProgressBar, QHBoxLayout, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, pyqtSlot

logging.basicConfig(level=logging.INFO)

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    @pyqtSlot(str)
    def process_text(self, text):
        try:
            logging.info(f"Processing text: {text}")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @pyqtSlot(str)
    def process_image(self, image_path):
        try:
            logging.info(f"Processing image: {image_path}")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

class ChatbotUI(QMainWindow):
    sendMessage = pyqtSignal(str)
    sendImage = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hygieia - Medical AI Chatbot")
        self.setGeometry(100, 100, 600, 500)
        self.setMinimumSize(400, 400)
        self.setStyleSheet("""
            QMainWindow { background-color: #2E2E2E; }
            QTextEdit {
                background-color: #3B3B3B;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                color: #EEE;
            }
            QLineEdit {
                background-color: #3B3B3B;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                color: #EEE;
            }
            QPushButton {
                background-color: #28a745;
                border: none;
                color: white;
                padding: 8px 16px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #218838; }
            QPushButton#clearButton {
                background-color: #444;
                color: #ccc;
                font-size: 12px;
                margin-top: 8px;
            }
            QPushButton#clearButton:hover { background-color: #666; color: #fff; }
            QProgressBar {
                background-color: #555;
                border: 1px solid #444;
                border-radius: 10px;
                text-align: center;
                color: #EEE;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 10px;
            }
        """)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.messages = []
        self._is_sending = False
        self._message_history = []  # For keyboard navigation
        self._history_index = -1
        self.layout = QVBoxLayout(self.central_widget)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setAcceptRichText(True)
        self.chat_display.setOpenExternalLinks(True)  # Make links clickable
        self.chat_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_display.customContextMenuRequested.connect(self.show_context_menu)
        self.chat_display.setAcceptDrops(True)  # Enable drag-and-drop
        self.chat_display.document().setDefaultStyleSheet("""
            .message-container { margin: 0; padding: 0; }
            .message-bubble {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                color: #333;
                animation: fadeIn 0.4s;
            }
            .user-message {
                background-color: #92D050;
                border-radius: 30px;
                padding: 10px 15px;
                margin: 5px 0 5px 20%;
                max-width: 80%;
                word-wrap: break-word;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 20px;
                text-align: right;
            }
            .bot-message {
                background-color: #E8F5E9;
                border-radius: 30px;
                padding: 10px 15px;
                margin: 5px 20% 5px 0;
                max-width: 80%;
                word-wrap: break-word;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 5px;
                text-align: left;
            }
            .system-message {
                background-color: #E0E0E0;
                border-radius: 15px;
                padding: 8px 12px;
                margin: 4px auto;
                max-width: 80%;
                font-size: 13px;
                color: #666;
                animation: fadeIn 0.3s ease-in;
                text-align: center;
            }
            .user-message:hover, .bot-message:hover, .system-message:hover {
                filter: brightness(95%);
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        """)
        self.chat_display.anchorClicked.connect(self.open_link)
        self.layout.addWidget(self.chat_display)
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_text)
        self.input_field.installEventFilter(self)  # For keyboard shortcuts
        input_layout.addWidget(self.input_field)
        self.send_button = QPushButton("Send")
        self.send_button.setToolTip("Send your message")
        self.send_button.clicked.connect(self.send_text)
        input_layout.addWidget(self.send_button)
        self.attach_button = QPushButton("Attach Image")
        self.attach_button.setToolTip("Attach an image file")
        self.attach_button.clicked.connect(self.attach_image)
        input_layout.addWidget(self.attach_button)
        self.import_button = QPushButton("Import File")
        self.import_button.setToolTip("Import a file (PDF, DOCX, PPTX)")
        self.import_button.clicked.connect(self.import_file)
        input_layout.addWidget(self.import_button)
        self.layout.addLayout(input_layout)
        self.clear_button = QPushButton("Clear Conversation")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.setToolTip("Clear all messages")
        self.clear_button.clicked.connect(self.clear_conversation)
        self.layout.addWidget(self.clear_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.start()
        self.sendMessage.connect(self.worker.process_text)
        self.sendImage.connect(self.worker.process_image)
        self.worker.error.connect(self.display_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.input_field.setFocus()

    def eventFilter(self, obj, event):
        # Keyboard shortcuts for input field
        if obj == self.input_field:
            if event.type() == event.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if event.modifiers() & Qt.ShiftModifier:
                        return False  # Allow newline
                    self.send_text()
                    return True
                elif event.key() == Qt.Key_L and event.modifiers() & Qt.ControlModifier:
                    self.clear_conversation()
                    return True
                elif event.key() == Qt.Key_Up and event.modifiers() & Qt.ControlModifier:
                    self.navigate_history(-1)
                    return True
                elif event.key() == Qt.Key_Down and event.modifiers() & Qt.ControlModifier:
                    self.navigate_history(1)
                    return True
        return super().eventFilter(obj, event)

    def navigate_history(self, direction):
        if not self._message_history:
            return
        self._history_index += direction
        self._history_index = max(-1, min(self._history_index, len(self._message_history) - 1))
        if self._history_index == -1:
            self.input_field.clear()
        else:
            self.input_field.setText(self._message_history[self._history_index])

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                self.add_user_image_message(file_path)
                self.sendImage.emit(file_path)
            elif file_path.lower().endswith((".pdf", ".docx", ".pptx")):
                try:
                    file_content = anyFileRead.anyReader()
                    if file_content:
                        self.add_system_message("Imported File Content:")
                        self.add_bot_message(str(file_content))
                    else:
                        self.add_system_message("No content imported.")
                except Exception as e:
                    self.display_error(f"Error importing file: {e}")
            else:
                self.display_error("Unsupported file type dropped.")
        event.acceptProposedAction()

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url.toString())

    def _render_messages(self):
        conversation_html = "\n".join(self.messages)
        self.chat_display.setHtml(conversation_html)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _format_message(self, message: str, align: str) -> str:
        # WhatsApp-style bubble with timestamp, improved rounded look
        converted = markdown.markdown(message, extensions=['extra', 'sane_lists', 'smarty'])
        # Make URLs clickable if not already
        import re
        url_pattern = r'(https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+)'
        converted = re.sub(url_pattern, r'<a href="\1">\1</a>', converted)
        message_class = {"right": "user-message", "left": "bot-message", "center": "system-message"}.get(align, "user-message")
        timestamp = datetime.datetime.now().strftime("%H:%M")
        bubble_style = {
            "user-message": "border-radius: 22px 22px 22px 8px; background: #92D050; padding: 12px 18px; margin: 8px 0 8px 25%; max-width: 70%; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: right; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;",
            "bot-message": "border-radius: 22px 22px 8px 22px; background: #E8F5E9; padding: 12px 18px; margin: 8px 25% 8px 0; max-width: 70%; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: left; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;",
            "system-message": "border-radius: 20px; background: #E0E0E0; padding: 10px 16px; margin: 6px auto; max-width: 60%; text-align: center; color: #666; font-size: 13px; display: inline-block; min-width: 40px; min-height: 28px; word-break: break-word;"
        }[message_class]
        return f"""
        <div class=\"message-container\" style=\"width:100%; display:flex; justify-content:{{'flex-end' if align=='right' else ('flex-start' if align=='left' else 'center')}};\">
            <div class=\"message-bubble {message_class}\" style=\"{bubble_style}\">
                {converted}<br>
                <span style=\"font-size:10px; color:#999;\">{timestamp}</span>
            </div>
        </div>
        """

    def add_user_message(self, message: str) -> None:
        formatted = self._format_message(message, align='right')
        if not self.messages or self.messages[-1] != formatted:
            self.messages.append(formatted)
            self._render_messages()
            logging.info(f"User message added: {message}")
        self._message_history.append(message)
        self._history_index = -1

    def add_bot_message(self, message: str) -> None:
        formatted = self._format_message(message, align='left')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"Bot message added: {message}")

    def add_system_message(self, message: str) -> None:
        formatted = self._format_message(message, align='center')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"System message added: {message}")

    def add_user_image_message(self, image_path: str) -> None:
        # Show attached image as a user message bubble
        img_tag = f'<img src="file:///{image_path}" style="max-width:80%; border-radius:10px;">'
        timestamp = datetime.datetime.now().strftime("%H:%M")
        message_html = f"""
        <div class=\"message-container\">
            <div class=\"message-bubble user-message\">
                {img_tag}<br>
                <span style=\"font-size:10px; border-radius: 45px; color:#999;\">{timestamp}</span>
            </div>
        </div>
        """
        self.messages.append(message_html)
        self._render_messages()

    def update_last_bot_message(self, message: str) -> None:
        # Update the last bot message (for streaming responses)
        if self.messages:
            self.messages[-1] = self._format_message(message, align='left')
            self._render_messages()

    def send_text(self):
        if self._is_sending:
            return
        self._is_sending = True
        user_input = self.input_field.text().strip()
        if user_input:
            logging.info(f"User sent text: {user_input}")
            if not self.messages or self.messages[-1] != self._format_message(user_input, align='right'):
                self.add_user_message(user_input)
            self.input_field.clear()
            self.sendMessage.emit(user_input)
        self.input_field.setFocus()
        self._is_sending = False

    def attach_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Attach Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            logging.info(f"User attached image: {file_path}")
            self.add_user_image_message(file_path)
            self.sendImage.emit(file_path)

    def import_file(self):
        # Import file content and show as a bot message
        try:
            file_content = anyFileRead.anyReader()
            if file_content:
                self.add_system_message("Imported File Content:")
                self.add_bot_message(str(file_content))
            else:
                self.add_system_message("No content imported.")
        except Exception as e:
            self.add_system_message(f"Error importing file: {e}")

    def clear_conversation(self):
        self.messages.clear()
        self.chat_display.clear()
        logging.info("Conversation cleared.")
        self.display_welcome()
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

    @pyqtSlot(str)
    def display_error(self, error_message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", error_message)

    @pyqtSlot()
    def on_worker_finished(self):
        logging.info("Worker task finished.")

    def show_context_menu(self, pos):
        # Allow copying message text from bubbles
        cursor = self.chat_display.cursorForPosition(pos)
        cursor.select(cursor.SelectionType.LineUnderCursor)
        selected_text = cursor.selectedText()
        menu = QMenu(self)
        copy_action = menu.addAction("Copy Message")
        action = menu.exec(self.chat_display.mapToGlobal(pos))
        if action == copy_action and selected_text:
            QApplication.clipboard().setText(selected_text)

    def closeEvent(self, event):
        self.thread.quit()
        self.thread.wait()
        event.accept()

    def display_welcome(self):
        self.add_system_message("Welcome to Hygieia! Type your message or use the buttons below.\n\nShortcuts: Enter=Send, Ctrl+L=Clear, Ctrl+Up/Down=History, Drag-and-drop files/images.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI()
    window.show()
    sys.exit(app.exec())