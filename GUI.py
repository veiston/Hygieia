import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QFileDialog, QProgressBar, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG, QThread, QObject, pyqtSlot

logging.basicConfig(level=logging.INFO)

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    @pyqtSlot(str)
    def process_text(self, text):
        try:
            # Simulate processing
            logging.info(f"Processing text: {text}")
            # Perform text processing here
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @pyqtSlot(str)
    def process_image(self, image_path):
        try:
            # Simulate processing
            logging.info(f"Processing image: {image_path}")
            # Perform image processing here
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

class ChatbotUI(QMainWindow):
    sendMessage = pyqtSignal(str)  # Signal for sending user text input
    sendImage = pyqtSignal(str)    # Signal for sending image path

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alfie - Medical AI Chatbot")
        self.setGeometry(100, 100, 600, 500)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Maintain a list of conversation messages as HTML strings.
        self.messages = []

        # Main vertical layout
        self.layout = QVBoxLayout(self.central_widget)

        # Chat display area with HTML support.
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setAcceptRichText(True)
        self.layout.addWidget(self.chat_display)

        # Horizontal layout for input field and buttons.
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_text)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_text)
        input_layout.addWidget(self.send_button)

        self.attach_button = QPushButton("Attach Image")
        self.attach_button.clicked.connect(self.attach_image)
        input_layout.addWidget(self.attach_button)

        self.layout.addLayout(input_layout)

        # Clear conversation button.
        self.clear_button = QPushButton("Clear Conversation")
        self.clear_button.clicked.connect(self.clear_conversation)
        self.layout.addWidget(self.clear_button)

        # Progress bar for LLM responses.
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        # Initialize worker and thread
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.start()

        # Connect signals
        self.sendMessage.connect(self.worker.process_text)
        self.sendImage.connect(self.worker.process_image)
        self.worker.error.connect(self.display_error)
        self.worker.finished.connect(self.on_worker_finished)

    def _render_messages(self):
        """Re-render the conversation from the stored messages."""
        conversation_html = "\n".join(self.messages)
        self.chat_display.setHtml(conversation_html)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def _format_message(self, message: str, align: str, bg_color: str) -> str:
        return (
            f"<div align='{align}' style='margin:5px;'>"
            f"<span style='background-color:{bg_color}; padding:8px; border-radius:10px; display:inline-block; color:#000000; font-size: 14px;'>"
            f"{message}"
            f"</span></div>"
        )

    def add_user_message(self, message: str) -> None:
        formatted = self._format_message(message, align='right', bg_color='#DCF8C6')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"User message added: {message}")

    def add_bot_message(self, message: str) -> None:
        formatted = self._format_message(message, align='left', bg_color='#F0F0F0')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"Bot message added: {message}")

    def update_last_bot_message(self, message: str) -> None:
        if self.messages:
            self.messages[-1] = self._format_message(message, align='left', bg_color='#F0F0F0')
            self._render_messages()
            logging.info(f"Bot message updated: {message}")

    def send_text(self):
        user_input = self.input_field.text().strip()
        if user_input:
            logging.info(f"User sent text: {user_input}")
            self.add_user_message(user_input)
            self.input_field.clear()
            self.sendMessage.emit(user_input)

    def attach_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Attach Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            logging.info(f"User attached image: {file_path}")
            self.sendImage.emit(file_path)

    def clear_conversation(self):
        self.messages.clear()
        self.chat_display.clear()
        logging.info("Conversation cleared.")

    def set_input_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)

    @pyqtSlot(str)
    def display_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    @pyqtSlot()
    def on_worker_finished(self):
        logging.info("Worker task finished.")

    def closeEvent(self, event):
        self.thread.quit()
        self.thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI()
    window.show()
    sys.exit(app.exec())
