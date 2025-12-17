# we will now use pyside for the UI
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QThread, Signal, Slot
import threading
import os
import signal

def format_content(content):
    """Format content for display in QLabel (supports basic HTML)"""
    # we will replace newlines with <br> for HTML display
    content = content.replace("\n", "<br>")
    # we need to also find asterisks for bold which start the bold text and then find where it ends at the next asterisk
    formatted = ""
    bold = False
    i = 0
    while i < len(content):
        if content[i] == "*":
            if bold:
                formatted += "</b>"
                bold = False
            else:
                formatted += "<b>"
                bold = True
            i += 1
        else:
            formatted += content[i]
            i += 1

    # if bold is still True, close the tag
    if bold:
        formatted += "</b>"

    return formatted

class PrepareLLMThread(QThread):
    """Thread for preparing LLM without blocking UI"""
    finished = Signal(object)  # Emits the LLM instance when ready
    error = Signal(str)
    
    def __init__(self, prepare_function):
        super().__init__()
        self.prepare_function = prepare_function
    
    def run(self):
        try:
            llm = self.prepare_function()
            self.finished.emit(llm)
        except Exception as e:
            self.error.emit(str(e))

class RunInferenceThread(QThread):
    """Thread for running inference without blocking UI"""
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, run_inference_function, llm, user_input, dangling_user_message):
        super().__init__()
        self.run_inference_function = run_inference_function
        self.llm = llm
        self.user_input = user_input
        self.dangling_user_message = dangling_user_message
    
    def run(self):
        try:
            self.run_inference_function(self.llm, self.user_input, self.dangling_user_message)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class ChatWindow(QMainWindow):
    def __init__(self, character_name, initial_chat_history):
        super().__init__()
        self.setWindowTitle("Chat with " + character_name)
        self.setGeometry(100, 100, 1200, 600)

        # add a central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # add a status label
        self.status_label = QLabel("Status: Ready", self)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        self.central_widget.setLayout(layout)

        # create a container for the chat history that is scrollable
        self.chat_history_container = QtWidgets.QScrollArea()
        self.chat_history_container.setWidgetResizable(True)
        layout.addWidget(self.chat_history_container)

        # Create a widget and layout for the scroll area content
        chat_content_widget = QWidget()
        chat_content_layout = QVBoxLayout()
        chat_content_widget.setLayout(chat_content_layout)
        self.chat_history_container.setWidget(chat_content_widget)

        # Add initial chat history to the layout
        for msg in initial_chat_history:
            content = msg["content"]
            # the content is html formatted, so use QLabel to render it
            label = QLabel()
            if msg["role"] == "user":
                label.setStyleSheet("background-color: #D1E7DD; padding: 5px; border-radius: 5px;")
            elif msg["role"] == "assistant":
                label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")
            else:
                label.setStyleSheet("background-color: #E2E3E5; padding: 5px; border-radius: 5px;")

            if msg["role"] == "user" or msg["role"] == "assistant":
                label.setTextFormat(QtCore.Qt.RichText)
                label.setText(format_content(content))
            else:
                label.setTextFormat(QtCore.Qt.PlainText)
                label.setText(content)
            
            label.setWordWrap(True)
            chat_content_layout.addWidget(label)

        # Add stretch to push content to top
        chat_content_layout.addStretch()
        
        # Scroll to bottom after UI is fully rendered (use longer delay to ensure layout is complete)
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)
            
        self.initial_chat_history = initial_chat_history
        self.has_initialized_first = False

    def _scroll_to_bottom(self):
        """Helper method to scroll chat history to bottom"""
        scrollbar = self.chat_history_container.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """Override Qt's closeEvent to call cleanup before closing"""
        self._on_window_close()
        event.accept()  # Allow the window to close

    def update_status(self, message, status_type="Status"):
        self.status_label.setText(f"{status_type}: {message}")

    def prepare_llm(self):
        self.block_chat()

        # Create and start the prepare thread
        self.prepare_thread = PrepareLLMThread(self.prepare_function)
        self.prepare_thread.finished.connect(self._on_llm_ready)
        self.prepare_thread.error.connect(self._on_llm_error)
        self.prepare_thread.start()

    @Slot(object)
    def _on_llm_ready(self, llm):
        """Called when LLM is ready"""
        self.llm = llm

        self.update_status("LLM initialized!")

        if not self.has_initialized_first:
            self.has_initialized_first = True
            # find the last user or assistant message in initial chat history
            dangling_message = None
            for msg in reversed(self.initial_chat_history):
                if msg["role"] == "user":
                    dangling_message = msg["content"]
                    break
                elif msg["role"] == "assistant":
                    break
            if dangling_message:
                # run inference on that message as the history was cut off
                self.run_inference(dangling_message, True)
            else:
                self.unblock_chat()
        else:
            self.unblock_chat()

    @Slot(str)
    def _on_llm_error(self, error_msg):
        """Called if LLM preparation fails"""
        self.update_status(error_msg, "Error")

    def run_inference(self, user_input, dangling_user_message):
        # in the same manner as prepare_llm, run inference in another thread
        self.block_chat()
        self.inference_thread = RunInferenceThread(self.run_inference_function, self.llm, user_input, dangling_user_message)
        self.inference_thread.finished.connect(self._on_inference_finished)
        self.inference_thread.error.connect(self._on_inference_error)
        self.inference_thread.start()

    @Slot()
    def _on_inference_finished(self):
        """Called when inference is finished"""
        self.unblock_chat()

    @Slot(str)
    def _on_inference_error(self, error_msg):
        """Called if inference fails"""
        self.update_status(error_msg, "Error")

    def run(self, prepare_function, run_inference_function):
        """Run chat function in a background thread while UI runs on main thread"""
        # Prepare LLM in another thread
        self.prepare_function = prepare_function
        self.run_inference_function = run_inference_function

        self.prepare_llm()

    def _on_window_close(self):
        """Called when window is closed - terminate application"""
        # Force terminate the entire process (kills all threads)
        os.kill(os.getpid(), signal.SIGTERM)

    def character_is_typing(self):
        pass

    def add_character_text(self, text):
        pass

    def block_chat(self):
        pass

    def unblock_chat(self):
        pass