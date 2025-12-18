# we will now use pyside for the UI
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QThread, Signal, Slot
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

def reformat_content(content):
    """Reformat content from QLabel back to plain text (removes HTML tags)"""
    # replace <br> with newlines
    content = content.replace("<br>", "\n")
    # remove <b> and </b> tags and replace with asterisks
    content = content.replace("<b>", "*").replace("</b>", "*")
    return content

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
    # Signals for UI updates from worker thread
    character_is_typing = Signal()
    add_character_text = Signal(str)
    character_finished_typing = Signal()
    
    def __init__(self, run_inference_function, llm, user_input, dangling_user_message, chat_window):
        super().__init__()
        self.run_inference_function = run_inference_function
        self.llm = llm
        self.user_input = user_input
        self.dangling_user_message = dangling_user_message
        self.chat_window = chat_window
    
    def run(self):
        try:
            self.run_inference_function(self.llm, self.user_input, self.dangling_user_message)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class UserInputEventFilter(QtCore.QObject):
    """Event filter to capture Enter key presses in QTextEdit"""
    enter_pressed = Signal()
    
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and not (event.modifiers() & QtCore.Qt.ShiftModifier):
                self.enter_pressed.emit()
                return True  # Event handled
        return super().eventFilter(obj, event)

class ChatWindow(QMainWindow):
    def __init__(self, character_name, initial_chat_history):
        super().__init__()
        self.character_name = character_name
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

        # add a text entry at the bottom for user input, the input should grow in a multiline fashion and not overflow
        # horizontally but vertically instead
        self.user_input = QtWidgets.QTextEdit()
        self.user_input.setFixedHeight(50)
        # set the placeholder text
        self.user_input.setPlaceholderText("Interact with " + character_name + "...")
        # make it a box with rounded corners
        # different styles when enabled and disabled
        self.user_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ccc;
                border-radius: 10px;
                padding: 5px;
                font-size: 14px;
            }
            QTextEdit:disabled {
                border: 2px solid #eee;
                background-color: #f9f9f9;
                color: #aaa;
            }
        """)
        # make it disabled by default
        self.user_input.setDisabled(True)
        layout.addWidget(self.user_input)

        # make the user_input respond to Enter key to send message
        self.user_input_event_filter = UserInputEventFilter()
        self.user_input.installEventFilter(self.user_input_event_filter)
        self.user_input_event_filter.enter_pressed.connect(self._on_user_input_enter)

        # Create a widget and layout for the scroll area content
        chat_content_widget = QWidget()
        chat_content_layout = QVBoxLayout()
        chat_content_widget.setLayout(chat_content_layout)
        self.chat_history_container.setWidget(chat_content_widget)

        # Add stretch to push content to top
        chat_content_layout.addStretch()

        # Add initial chat history to the layout
        for i, msg in enumerate(initial_chat_history):
            content = msg["content"]
            self._add_message_label(msg["role"], content, i)
        
        # Scroll to bottom after UI is fully rendered (use longer delay to ensure layout is complete)
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)
        
        # make a copy to avoid potential mutation issues
        self.initial_chat_history = initial_chat_history.copy()
        self.has_initialized_first = False

    def _add_message_label(
            self,
            role,
            content,
            index,
            scroll_to_bottom=False,
            no_edit=False,
            no_select=False
        ):
        """Helper method to add a message label to chat history"""
        label = QLabel()
        if role == "user":
            label.setStyleSheet("background-color: #D1E7DD; padding: 5px; border-radius: 5px;")
        elif role == "assistant":
            label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")
        else:
            label.setStyleSheet("background-color: #E2E3E5; padding: 5px; border-radius: 5px;")

        if role == "user" or role == "assistant":
            label.setTextFormat(QtCore.Qt.RichText)
            label.setText(format_content(content))
        else:
            label.setTextFormat(QtCore.Qt.PlainText)
            label.setText(content)

        if not no_select:
            label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        # change the cursor to one for selecting text
        label.setCursor(QtCore.Qt.IBeamCursor)

        # add metadata to the label for role
        label.setProperty("role", role)
        label.setProperty("editing", False)
        label.setProperty("index", index)

        # add a context menu to copy text
        label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        if not no_edit:
            label.customContextMenuRequested.connect(self._show_context_menu)
        
        label.setWordWrap(True)

        # add the label to the chat history layout before the stretch
        layout = self.chat_history_container.widget().layout()
        layout.insertWidget(layout.count() - 1, label)

        # scroll to bottom
        if scroll_to_bottom:
            QtCore.QTimer.singleShot(100, self._scroll_to_bottom)

        return label

    def _on_user_input_enter(self):
        """Handle Enter key press in user input box"""
        user_text = self.user_input.toPlainText().strip()
        if user_text:
            last_label = self.chat_history_container.widget().layout().itemAt(self.chat_history_container.widget().layout().count() - 2).widget()
            new_index = last_label.property("index") + 1 if last_label else 0
            self._add_message_label("user", user_text, new_index, scroll_to_bottom=True)
            # clear the user input box
            self.user_input.clear()

            # run inference with the user input
            self.run_inference(user_text, False)

    def _show_context_menu(self, position):
        """Show context menu for copying text"""
        sender = self.sender()
        menu = QtWidgets.QMenu()
        copy_action = menu.addAction("Copy")

        edit_action = None
        save_action = None
        delete_action = None
        if sender.property("role") in ["user", "assistant"]:
            if sender.property("editing") == False:
                edit_action = menu.addAction("Edit")
                delete_action = menu.addAction("Delete")
            else:
                save_action = menu.addAction("Save")
        action = menu.exec_(sender.mapToGlobal(position))
        if action == copy_action:
            clipboard = QtWidgets.QApplication.clipboard()
            # copy the selected text if any, else copy all text
            # we need to check if our sender is currently in edit mode
            if sender.property("editing") == True:
                # in edit mode it is already plain text
                if sender.hasSelectedText():
                    clipboard.setText(sender.selectedText())
                else:
                    clipboard.setText(sender.text())
            else:
                if sender.hasSelectedText():
                    clipboard.setText(reformat_content(sender.selectedText()))
                else:
                    clipboard.setText(reformat_content(sender.text()))
        elif action == edit_action and edit_action is not None:
            # allow editing the label text
            sender.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextEditorInteraction)
            sender.setFocus()
            # change the text to the reformatted content as plain text
            sender.setText(reformat_content(sender.text()))
            # make the sender color light yellow to indicate edit mode
            sender.setStyleSheet("background-color: #FFF3CD; padding: 5px; border-radius: 5px;")
            sender.setProperty("editing", True)
        elif action == save_action and save_action is not None:
            # disable editing the label text
            sender.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            sender.setProperty("editing", False)
            # change the text back to formatted content
            plain_text = sender.text()
            sender.setText(format_content(plain_text))
            # restore the original color based on role
            if sender.property("role") == "user":
                sender.setStyleSheet("background-color: #D1E7DD; padding: 5px; border-radius: 5px;")
            elif sender.property("role") == "assistant":
                sender.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")
            self.on_message_edited(sender.property("index"), plain_text)
        elif action == delete_action and delete_action is not None:
            self.on_message_deleted(sender.property("index"))
            sender.deleteLater()

    def on_message_edited(self, index, new_content):
        self.edit_message_function(index, new_content)

        # also update the initial chat history to reflect the change if has_initialized_first is still false
        if not self.has_initialized_first:
            if 0 <= index < len(self.initial_chat_history):
                self.initial_chat_history[index]["content"] = new_content

    def on_message_deleted(self, index):
        self.delete_message_function(index)

        # also update the initial chat history to reflect the change if has_initialized_first is still false
        if not self.has_initialized_first:
            if 0 <= index < len(self.initial_chat_history):
                del self.initial_chat_history[index]

        # refresh indices of remaining messages
        for i in range(index, len(self.initial_chat_history)):
            label = self.chat_history_container.widget().layout().itemAt(i).widget()
            label.setProperty("index", i)

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
        self.inference_thread = RunInferenceThread(self.run_inference_function, self.llm, user_input, dangling_user_message, self)
        
        # Connect thread signals to main thread slots
        self.inference_thread.character_is_typing.connect(self._character_is_typing)
        self.inference_thread.add_character_text.connect(self._add_character_text)
        self.inference_thread.character_finished_typing.connect(self._character_finished_typing)
        self.inference_thread.finished.connect(self._on_inference_finished)
        self.inference_thread.error.connect(self._on_inference_error)
        
        self.inference_thread.start()

    @Slot()
    def _character_is_typing(self):
        """Slot called from worker thread - safe for UI updates"""
        # this basically means to add a new entry with empty text for the assistant
        last_label = self.chat_history_container.widget().layout().itemAt(self.chat_history_container.widget().layout().count() - 2).widget()
        new_index = last_label.property("index") + 1 if last_label else 0
        new_label = self._add_message_label("assistant", "<i>" + self.character_name + " is answering...</i>", new_index, scroll_to_bottom=True, no_select=True, no_edit=True)
        new_label.setProperty("uninitialized", True)
        # add special border to indicate typing
        new_label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px; border: 2px dashed #6c757d;")
    
    @Slot(str)
    def _add_character_text(self, text):
        """Slot called from worker thread - safe for UI updates"""
        # find the last label which should be from assistant
        layout = self.chat_history_container.widget().layout()
        last_label = layout.itemAt(layout.count() - 2).widget()
        if last_label.property("role") == "assistant":
            # if it is uninitialized, replace the text whole
            if last_label.property("uninitialized") == True:
                last_label.setText(format_content(text))
                last_label.setProperty("plain_text", text)
                last_label.setProperty("uninitialized", False)
            else:
                # append text
                current_text = last_label.property("plain_text")
                new_text = current_text + text
                last_label.setProperty("plain_text", new_text)
                last_label.setText(format_content(new_text))

        # scroll to bottom
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)
    
    @Slot()
    def _character_finished_typing(self):
        """Slot called from worker thread - safe for UI updates"""
        # find the last assistant label and enable selection and editing
        layout = self.chat_history_container.widget().layout()
        last_label = layout.itemAt(layout.count() - 2).widget()
        if last_label.property("role") == "assistant":
            last_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            last_label.customContextMenuRequested.connect(self._show_context_menu)

        # remove the dashed border
        last_label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")

    @Slot()
    def _on_inference_finished(self):
        """Called when inference is finished"""
        self.unblock_chat()

    @Slot(str)
    def _on_inference_error(self, error_msg):
        """Called if inference fails"""
        self.update_status(error_msg, "Error")
        # block chat for now
        self.block_chat()

    def run(self, prepare_function, run_inference_function, edit_message_function, delete_message_function):
        """Run chat function in a background thread while UI runs on main thread"""
        # Prepare LLM in another thread
        self.prepare_function = prepare_function
        self.run_inference_function = run_inference_function
        self.delete_message_function = delete_message_function
        self.edit_message_function = edit_message_function

        self.prepare_llm()

    def _on_window_close(self):
        """Called when window is closed - terminate application"""
        # Force terminate the entire process (kills all threads)
        os.kill(os.getpid(), signal.SIGTERM)

    def character_is_typing(self):
        # trigger the event from the thread, this is called from the inference thread
        self.inference_thread.character_is_typing.emit()

    def add_character_text(self, text):
        # trigger the event from the thread, this is called from the inference thread
        self.inference_thread.add_character_text.emit(text)

    def character_finished_typing(self):
        # trigger the event from the thread, this is called from the inference thread
        self.inference_thread.character_finished_typing.emit()

    def block_chat(self):
        # block the user input box
        self.user_input.setDisabled(True)

    def unblock_chat(self):
        # unblock the user input box
        self.user_input.setDisabled(False)