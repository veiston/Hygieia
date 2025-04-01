import sys
import logging
import markdown
import anyFileRead  # new import
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
        self.setWindowTitle("Hygieia - Medical AI Chatbot")
        self.setGeometry(100, 100, 600, 500)
        
        # Set a global dark style sheet for an elegant, rounded, and beautiful appearance.
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
            }
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
                background-color: #3A8DFF;
                border: none;
                color: white;
                padding: 8px 16px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #2C79D1;
            }
            QProgressBar {
                background-color: #555;
                border: 1px solid #444;
                border-radius: 10px;
                text-align: center;
                color: #EEE;
            }
            QProgressBar::chunk {
                background-color: #3A8DFF;
                border-radius: 10px;
            }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Maintain a list of conversation messages as HTML strings.
        self.messages = []
        
        # Flag to prevent duplicate sends
        self._is_sending = False

        # Main vertical layout
        self.layout = QVBoxLayout(self.central_widget)
        
        # Chat display area with HTML support.
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setAcceptRichText(True)
        
        # Add WhatsApp-style styling
        self.chat_display.document().setDefaultStyleSheet("""
            .message-container {
                margin: 0;
                padding: 0;
            }
            
            .message-bubble {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                color: #333;
            }
            
            .user-message {
                background-color: #92D050;
                border-radius: 20px;
                padding: 10px 15px;
                margin: 5px;
                max-width: 80%;
                word-wrap: break-word;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 20px;
            }
            
            .bot-message {
                background-color: #E8F5E9;
                border-radius: 20px;
                padding: 10px 15px;
                margin: 5px;
                max-width: 80%;
                word-wrap: break-word;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 5px;
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
            }
            
            .user-message:hover,
            .bot-message:hover,
            .system-message:hover {
                filter: brightness(95%);
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        """)
        
        self.layout.addWidget(self.chat_display)
        
        # Horizontal layout for input field and buttons.
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_text) # send on Enter key
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_text)
        input_layout.addWidget(self.send_button)
        
        self.attach_button = QPushButton("Attach Image")
        self.attach_button.clicked.connect(self.attach_image)
        input_layout.addWidget(self.attach_button)
        
        self.import_button = QPushButton("Import File")  # new button
        self.import_button.clicked.connect(self.import_file)
        input_layout.addWidget(self.import_button)
        
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
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _format_message(self, message: str, align: str, bg_color: str = None) -> str:
        """Format a message with WhatsApp-style bubble styling using CSS classes."""
        converted = markdown.markdown(message)
        message_class = {"right": "user-message", "left": "bot-message", "center": "system-message"}.get(align, "user-message")
        return f"""
        <div class="message-container">
            <div class="message-bubble {message_class}">
                {converted}
            </div>
        </div>
        """

    def add_user_message(self, message: str) -> None:
        """Add a user message to the conversation."""
        formatted = self._format_message(message, align='right')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"User message added: {message}")

    def add_bot_message(self, message: str) -> None:
        """Add a bot message to the conversation."""
        formatted = self._format_message(message, align='left')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"Bot message added: {message}")

    def add_system_message(self, message: str) -> None:
        """Add a system message to the conversation."""
        formatted = self._format_message(message, align='center')
        self.messages.append(formatted)
        self._render_messages()
        logging.info(f"System message added: {message}")

    def update_last_bot_message(self, message: str) -> None:
        """Update the last bot message in the conversation."""
        if self.messages:
            self.messages[-1] = self._format_message(message, align='left')
            self._render_messages()

    def send_text(self):
        """Handle sending text messages."""
        if self._is_sending:
            return
        self._is_sending = True
        user_input = self.input_field.text().strip()
        if user_input:
            logging.info(f"User sent text: {user_input}")
            self.add_user_message(user_input)
            self.input_field.clear()
            self.sendMessage.emit(user_input)
        self._is_sending = False

    def attach_image(self):
        """Handle image attachment."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Attach Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            logging.info(f"User attached image: {file_path}")
            self.sendImage.emit(file_path)

    def import_file(self):
        """Use anyFileRead to convert file content to text and display it."""
        file_content = anyFileRead.anyReader()  # call anyReader to get file text
        if file_content:
            self.add_system_message("Imported File Content:")
            self.add_bot_message(str(file_content))
        else:
            self.add_system_message("No content imported.")

    def clear_conversation(self):
        """Clear the conversation history."""
        self.messages.clear()
        self.chat_display.clear()
        logging.info("Conversation cleared.")

    def set_input_enabled(self, enabled: bool):
        """Enable or disable input controls."""
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)

    @pyqtSlot(str)
    def display_error(self, error_message):
        """Display an error message to the user."""
        QMessageBox.critical(self, "Error", error_message)

    @pyqtSlot()
    def on_worker_finished(self):
        """Handle worker thread completion."""
        logging.info("Worker task finished.")

    def closeEvent(self, event):
        """Handle window close event."""
        self.thread.quit()
        self.thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI()
    window.show()
    sys.exit(app.exec())