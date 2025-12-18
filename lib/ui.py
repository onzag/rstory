# we will now use pyside for the UI
from PySide6 import QtWidgets, QtCore, QtGui
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
    character_finished_typing = Signal(str)
    
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
    
class ChatMessage:
    def __init__(
            self,
            parent,
            role,
            content,
            uninitialized=False,
            scroll_to_bottom=True,
        ):
        self.parent = parent
        self.label = QLabel()
        if role == "user":
            self.label.setStyleSheet("background-color: #D1E7DD; padding: 5px; border-radius: 5px;")
        elif role == "assistant":
            if uninitialized:
                self.label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px; border: 2px dashed #6c757d;")
            else:
                self.label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")
        else:
            self.label.setStyleSheet("background-color: #E2E3E5; padding: 5px; border-radius: 5px;")

        if role == "user" or role == "assistant":
            self.label.setTextFormat(QtCore.Qt.RichText)
            self.label.setText(format_content(content))
        else:
            self.label.setTextFormat(QtCore.Qt.PlainText)
            self.label.setText(content)

        if not uninitialized:
            self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        # change the cursor to one for selecting text
        self.label.setCursor(QtCore.Qt.IBeamCursor)

        # add metadata to the label for role
        self.role = role
        self.editing = False
        self.index = len(parent.messages)
        self.plain_text = content
        self.uninitialized = uninitialized

        # add a context menu to copy text
        self.label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        if not uninitialized:
            self.label.customContextMenuRequested.connect(self._show_context_menu)
        
        self.label.setWordWrap(True)

        # add the label to the chat history layout before the stretch
        layout = parent.chat_history_container.widget().layout()
        layout.insertWidget(layout.count() - 1, self.label)
        
        # scroll to bottom
        if scroll_to_bottom:
            QtCore.QTimer.singleShot(100, self.parent._scroll_to_bottom)

        parent.messages.append(self)

    def reinsert_into_layout(self, layout):
        layout.insertWidget(layout.count() - 1, self.label)

    def unmark_uninitialized(self):
        if self.uninitialized:
            self.uninitialized = False

            self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self.label.customContextMenuRequested.connect(self._show_context_menu)

            # remove the dashed border
            if self.role == "assistant":
                self.label.setStyleSheet("background-color: #F8D7DA; padding: 5px; border-radius: 5px;")

    def is_uninitialized(self):
        return self.uninitialized
    
    def setText(self, text):
        self.plain_text = text
        self.label.setText(format_content(text))

    def reIndex(self, new_index):
        self.index = new_index

    def start_edit_mode(self):
        """Switch the message to edit mode"""
        if not self.editing:
            self.editing = True

            # replace the label with a QTextEdit
            self.text_edit = QtWidgets.QTextEdit()
            self.text_edit.setPlainText(self.plain_text)
            self.text_edit.setStyleSheet("background-color: #fff3cd; padding: 5px; border-radius: 5px;")
            
            # Make it grow with content - no scrollbars
            self.text_edit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.text_edit.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.text_edit.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            
            # Calculate height based on document
            doc_height = self.text_edit.document().size().height()
            self.text_edit.setMinimumHeight(int(doc_height) + 20)
            
            # Update height when content changes
            self.text_edit.textChanged.connect(self._update_text_edit_height)

            # trigger _update_text_edit_height to set initial height after some time because it is not doing so
            # add scroll to bottom after layout is updated
            QtCore.QTimer.singleShot(100, lambda: self._update_text_edit_height(scroll_to_bottom=True))

            # set the custom context menu
            self.text_edit.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.text_edit.customContextMenuRequested.connect(self._show_context_menu)
            
            layout = self.parent.chat_history_container.widget().layout()
            layout.replaceWidget(self.label, self.text_edit)
            self.label.hide()
            self.text_edit.show()

            # focus the text edit
            self.text_edit.setFocus()
    
    def _update_text_edit_height(self, scroll_to_bottom=False):
        """Update text edit height based on content"""
        if hasattr(self, 'text_edit') and self.text_edit:
            doc_height = self.text_edit.document().size().height()
            self.text_edit.setMinimumHeight(int(doc_height) + 20)

            if scroll_to_bottom:
                # Move cursor to end and keep focus
                cursor = self.text_edit.textCursor()
                cursor.movePosition(QtGui.QTextCursor.End)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.setFocus()
                
                # Scroll to show the entire text edit, focusing on the bottom
                # Use negative yMargin to ensure bottom is visible
                QtCore.QTimer.singleShot(50, lambda: self.parent.chat_history_container.ensureWidgetVisible(
                    self.text_edit, 0, 100
                ))

    def cancel_edit_mode(self):
        """Cancel edit mode and revert to original text"""
        if self.editing:
            self.editing = False

            # replace the QTextEdit with the label
            layout = self.parent.chat_history_container.widget().layout()
            layout.replaceWidget(self.text_edit, self.label)
            self.text_edit.hide()
            self.label.show()

            # delete the text edit
            self.text_edit.deleteLater()
            self.text_edit = None

    def finish_edit_mode(self):
        """Finish edit mode and save changes"""
        if self.editing:
            new_text = self.text_edit.toPlainText()
            self.setText(format_content(new_text))

            self.editing = False

            # replace the QTextEdit with the label
            layout = self.parent.chat_history_container.widget().layout()
            layout.replaceWidget(self.text_edit, self.label)
            self.text_edit.hide()
            self.label.show()

            # delete the text edit
            self.text_edit.deleteLater()
            self.text_edit = None
                        
            self.parent.on_message_edited(self.index, new_text)

    def _show_context_menu(self, position):
        """Show context menu for copying text"""
        widget = self.label if not self.editing else self.text_edit
        
        menu = QtWidgets.QMenu()
        copy_action = menu.addAction("Copy")

        edit_action = None
        save_action = None
        delete_action = None
        cancel_action = None
        
        if self.role in ["user", "assistant"]:
            if not self.editing:
                edit_action = menu.addAction("Edit")
                delete_action = menu.addAction("Delete")
            else:
                save_action = menu.addAction("Save")
                cancel_action = menu.addAction("Cancel")
        
        # Show menu at the widget's position
        action = menu.exec(widget.mapToGlobal(position))
        
        if action == copy_action:
            clipboard = QtWidgets.QApplication.clipboard()
            # copy the selected text if any, else copy all text
            if self.editing:
                # in edit mode it is already plain text
                if self.text_edit.textCursor().hasSelection():
                    clipboard.setText(self.text_edit.textCursor().selectedText())
                else:
                    clipboard.setText(self.text_edit.toPlainText())
            else:
                if self.label.hasSelectedText():
                    clipboard.setText(reformat_content(self.label.selectedText()))
                else:
                    clipboard.setText(self.plain_text)
        elif action == edit_action and edit_action is not None:
            # get the message object for that index
            message_obj = self
            # change the message to edit mode
            # call the method on the main thread somehow
            message_obj.start_edit_mode()
        elif action == save_action and save_action is not None:
            # get the message object for that index
            message_obj = self.parent.messages[self.index]
            message_obj.finish_edit_mode()
        elif action == cancel_action and cancel_action is not None:
            # get the message object for that index
            self.cancel_edit_mode()
        elif action == delete_action and delete_action is not None:
            self.parent.on_message_deleted(self.index)
            self.label.deleteLater()

class ChatWindow(QMainWindow):
    def __init__(self, character_name, initial_chat_history, username):
        super().__init__()
        self.character_name = character_name
        self.setWindowTitle("Chat with " + character_name)
        self.setGeometry(100, 100, 1200, 600)

        # add a central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.messages = []
        self.username = username

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
        for msg in initial_chat_history:
            content = msg["content"]
            self._add_message_label(msg["role"], content)
        
        # Scroll to bottom after UI is fully rendered (use longer delay to ensure layout is complete)
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)
        
        # make a copy to avoid potential mutation issues
        self.initial_chat_history = initial_chat_history.copy()
        self.has_initialized_first = False

    def _add_message_label(
            self,
            role,
            content,
            scroll_to_bottom=False,
            uninitialized=False,
        ):
        message = ChatMessage(
            parent=self,
            role=role,
            content=content,
            uninitialized=uninitialized,
            scroll_to_bottom=scroll_to_bottom,
        )

        return message

    def _on_user_input_enter(self):
        """Handle Enter key press in user input box"""
        user_text = self.user_input.toPlainText().strip()
        if user_text:
            self._add_message_label("user", user_text, scroll_to_bottom=True)
            # clear the user input box
            self.user_input.clear()

            # run inference with the user input
            self.run_inference(user_text, False)
    
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

        # delete from messages list
        del self.messages[index]
        # re-index remaining messages
        for i in range(index, len(self.messages)):
            self.messages[i].reIndex(i)

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
        if self.ended:
            return  # do not run inference if chat has ended
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
        self._add_message_label("assistant", "<i>" + self.character_name + " is answering...</i>", scroll_to_bottom=True, uninitialized=True)
    
    @Slot(str)
    def _add_character_text(self, text):
        """Slot called from worker thread - safe for UI updates"""
        # find the last label which should be from assistant
        last_message = self.messages[-1]
        if last_message.role == "assistant":
            # if it is uninitialized, replace the text whole
            if last_message.is_uninitialized():
                last_message.setText(text)
                last_message.unmark_uninitialized()
            else:
                # append text
                current_text = last_message.plain_text
                new_text = current_text + text
                last_message.setText(new_text)

        # scroll to bottom
        QtCore.QTimer.singleShot(100, self._scroll_to_bottom)
    
    @Slot(str)
    def _character_finished_typing(self, ended=None):
        """Slot called from worker thread - safe for UI updates"""
        # find the last assistant label and enable selection and editing
        last_message = self.messages[-1]
        if last_message.role == "assistant":
            last_message.unmark_uninitialized()

        if ended is not None:
            self.ended = ended
            self.update_status("Chat has ended: " + ended)
            self.block_chat()

    @Slot()
    def _on_inference_finished(self):
        """Called when inference is finished"""
        if not self.ended:
            self.unblock_chat()
            # focus the user input box
            self.user_input.setFocus()

    @Slot(str)
    def _on_inference_error(self, error_msg):
        """Called if inference fails"""
        self.update_status(error_msg, "Error")
        # block chat for now
        self.block_chat()

    def run(self, ended, prepare_function, run_inference_function, edit_message_function, delete_message_function, update_username_function):
        """Run chat function in a background thread while UI runs on main thread"""
        # Prepare LLM in another thread
        self.prepare_function = prepare_function
        self.run_inference_function = run_inference_function
        self.delete_message_function = delete_message_function
        self.edit_message_function = edit_message_function
        self.update_username_function = update_username_function
        self.ended = ended

        # first ask the user for their username if not set
        while not self.username:
            # Create input dialog with icon
            dialog = QtWidgets.QInputDialog(self)
            dialog.setWindowTitle("Enter Username")
            dialog.setLabelText("Please enter your username, make sure this will be how you call yourself in the chat:")
            dialog.setTextValue(self.username if self.username else "")
            dialog.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxQuestion))
            
            ok = dialog.exec()
            if ok:
                self.username = dialog.textValue().strip()
                if self.username:
                    self.update_username_function(self.username)

        if not ended:
            self.prepare_llm()
        else:
            self.update_status("Chat has ended: " + ended)
            self.block_chat()

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

    def character_finished_typing(self, ended=None):
        # trigger the event from the thread, this is called from the inference thread
        self.inference_thread.character_finished_typing.emit(ended)

    def block_chat(self):
        # block the user input box
        self.user_input.setDisabled(True)

    def unblock_chat(self):
        # unblock the user input box
        self.user_input.setDisabled(False)