from llama_cpp import Llama
from sys import argv
from os import path
import os
import json
from lib.ui import ChatWindow
from PySide6.QtWidgets import QApplication

# Path to your GGUF file (adjust to your fast SSD)
# must be Llama 3.3 compatible model for these settings to work properly
model_path = argv[1]

character_folder = argv[2]
character_system_description_path = path.join(character_folder, "system.txt")
character_name_path = path.join(character_folder, "name.txt")
# read character name from name.txt
with open(character_name_path, "r", encoding="utf-8") as f:
    character_name_value = f.read().strip()

# check that character_folder/logs exists and if not create it
logs_folder = path.join(character_folder, "logs")
if not path.exists(logs_folder):
    os.makedirs(logs_folder)

conversation_log_value = argv[3] if len(argv) > 3 else "last.json"
if conversation_log_value == "new":
    # we must copy last.json if it exists as an archived conversation
    # check if last.json exists
    last_log_path = path.join(character_folder, "logs", "last.json")
    if path.exists(last_log_path):
        # find a new name for the archived log
        i = 1
        while True:
            archived_log_path = path.join(character_folder, "logs", f"archived_{i}.json")
            if not path.exists(archived_log_path):
                break
            i += 1
        # copy last.json to archived_{i}.json
        os.rename(last_log_path, archived_log_path)
    conversation_log_value = "last.json"
# check that last.json exists, if not create an empty one
last_log_path = path.join(character_folder, "logs", "last.json")
if not path.exists(last_log_path):
    with open(last_log_path, "w", encoding="utf-8") as f:
        f.write("[]")

conversation_log_path = path.join(character_folder, "logs", conversation_log_value)
# read the conversation log from json
chat_history = json.load(open(conversation_log_path, "r", encoding="utf-8"))

def save_conversation_log():
    """Save the current chat history to the conversation log file"""
    with open(conversation_log_path, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=4)

# System prompt read from bio.txt
with open(character_system_description_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

def count_tokens(text, llm_instance):
    """Estimate token count for a given text"""
    return len(llm_instance.tokenize(text.encode('utf-8')))

def format_prompt(history, user_message, llm_instance=None, max_context=6000):
    """Format the conversation history with proper role tags for Llama 3.3
    Uses sliding window to keep only recent messages that fit in context.
    Reserves space for system prompt, new message, and response generation.
    """
    # Start with system prompt
    system_part = f"<|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|>"
    
    # Format the new user message
    user_part = ""
    if user_message is not None:
        user_part = f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    # Count tokens for system and user parts (reserve space)
    if llm_instance:
        system_tokens = count_tokens(system_part, llm_instance)
        user_tokens = count_tokens(user_part, llm_instance)
        available_tokens = max_context - system_tokens - user_tokens
        
        # Build history from most recent messages backwards
        history_parts = []
        token_count = 0
        
        # Iterate through history in reverse to keep most recent messages
        for msg in reversed(history):
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                msg_text = f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                msg_text = f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
            else:
                #internal role, skip
                continue
            
            msg_tokens = count_tokens(msg_text, llm_instance)
            
            # Check if adding this message would exceed available tokens
            if token_count + msg_tokens > available_tokens:
                break
            
            history_parts.insert(0, msg_text)  # Insert at beginning to maintain order
            token_count += msg_tokens
        
        # Combine all parts
        prompt = system_part + "".join(history_parts) + user_part
        
        # Log token usage
        #total_tokens = system_tokens + token_count + user_tokens
        #print(f"[Token usage: {total_tokens}/{max_context}, kept {len(history_parts)} history messages]", flush=True)
    else:
        # Fallback without token counting (shouldn't happen in practice)
        prompt = system_part
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        prompt += user_part
    
    return prompt

# Create QApplication instance before any widgets
app = QApplication([])
chat_window = ChatWindow(character_name_value, chat_history)

# display the window
chat_window.show()

print("Using model:", model_path)
print("Character system loaded from:", character_system_description_path)
print("Conversation log path:", conversation_log_path)
print("Starting chat with character:", character_name_value)

print("Loading Llama model...")

def prepare_llm():
    chat_window.update_status("Loading model...")

    # Create a simple Llama instance
    llm = Llama(
        model_path=model_path,
        n_ctx=1024*8,
        n_gpu_layers=40,     # only a few layers on GPU, safe for 24GB VRAM
        n_threads=16,        # CPU threads
        verbose=False,
        temperature=0.9,
    )

    chat_window.update_status("Model loaded. Ready to chat!")

    return llm

def run_inference(llm: Llama, user_input, dangling_user_message):
    if not user_input:
        return  # skip empty input

    # check if last message is from user
    if dangling_user_message:
        chat_window.update_status("Continuing previous conversation...")
    else:
        chat_window.update_status("Running inference...")

    # Update chat history if last message is not from user
    if not dangling_user_message:
        chat_history.append({"role": "user", "content": user_input})
        save_conversation_log()
        
    # Format the prompt with history
    prompt = format_prompt(chat_history, None if dangling_user_message else user_input, llm_instance=llm, max_context=8192 - 512)
        
    # Generate response
    chat_window.character_is_typing()
    response = ""
    for token in llm(
        prompt, 
        max_tokens=8192, 
        stream=True, 
        stop=["<|eot_id|>", "<|start_header_id|>"],
        repeat_penalty=1.1,           # Penalize repetitions (1.0 = no penalty, higher = more penalty)
        frequency_penalty=0.5,        # Reduce likelihood of frequently used tokens
        presence_penalty=0.5,          # Encourage new topics/ideas
        temperature=1,              # Creativity of responses
        top_p=0.9,                   # Nucleus sampling
    ):
        text = token["choices"][0]["text"]
        chat_window.add_character_text(text)
        response += text
        
    chat_history.append({"role": "assistant", "content": response.strip()})
    save_conversation_log()

    chat_window.update_status("Ready for next message.")
    chat_window.character_finished_typing()

def edit_message(index, new_content):
    """Edit a message in the chat history and save the log"""
    if 0 <= index < len(chat_history):
        chat_history[index]["content"] = new_content
        save_conversation_log()

def delete_message(index):
    """Delete a message from the chat history and save the log"""
    if 0 <= index < len(chat_history):
        del chat_history[index]
        save_conversation_log()

# Start the chat
chat_window.run(prepare_llm, run_inference, edit_message, delete_message)
app.exec()