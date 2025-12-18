from llama_cpp import Llama
from sys import argv
from os import path
import os
import json
from lib.bonds import BondsHandler
from lib.emotion import EmotionHandler, read_emotion_list
from lib.states import StatesHandler
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
        f.write('{"history": [], "username": null, "bond": 0.0, "applied_states": [], "stranger": true}')

conversation_log_path = path.join(character_folder, "logs", conversation_log_value)
# read the conversation log from json
chat_history_all = json.load(open(conversation_log_path, "r", encoding="utf-8"))
chat_history = chat_history_all["history"]
current_bond_weight = chat_history_all["bond"]
current_applied_states = chat_history_all["applied_states"]
current_stranger = chat_history_all["stranger"]
current_ended = chat_history_all.get("ended", None)
username = chat_history_all["username"]

def save_conversation_log():
    """Save the current chat history to the conversation log file"""
    with open(conversation_log_path, "w", encoding="utf-8") as f:
        json.dump(chat_history_all, f, ensure_ascii=False, indent=4)

def update_username(new_username):
    """Update the username in the chat history and save the log"""
    username = new_username
    chat_history_all["username"] = new_username
    save_conversation_log()

def update_bond(new_bond: float, save=True):
    """Update the bond weight in the chat history and save the log"""
    chat_history_all["bond"] = new_bond
    if save:
        save_conversation_log()

def update_applied_states(new_states, save=True):
    """Update the applied states in the chat history and save the log"""
    chat_history_all["applied_states"] = new_states
    if save:
        save_conversation_log()

def update_stranger(is_stranger, save=True):
    """Update the stranger status in the chat history and save the log"""
    chat_history_all["stranger"] = is_stranger
    if save:
        save_conversation_log()

# System prompt read from bio.txt
with open(character_system_description_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()
SYSTEM_PROMPT_EMOTIONS = None
SYSTEM_PROMPT_STATES = None
SYSTEM_PROMPT_BONDS = None

CACHE_TOKENS = {}
def count_tokens(text, llm_instance):
    """Estimate token count for a given text"""
    global CACHE_TOKENS
    if text in CACHE_TOKENS:
        CACHE_TOKENS[text]["used_in_last_count"] = True
        return CACHE_TOKENS[text]["value"]
    
    if llm_instance is None:
        # rough estimate: 1 token per 4 characters, used for debugging without LLM
        return len(text) // 4
    token_count = len(llm_instance.tokenize(text.encode('utf-8')))
    CACHE_TOKENS[text] = {"value": token_count, "used_in_last_count": True}
    return token_count

def clean_token_cache():
    # Remove entries not used in the last count
    global CACHE_TOKENS
    keys_to_remove = [key for key, value in CACHE_TOKENS.items() if not value["used_in_last_count"]]
    for key in keys_to_remove:
        del CACHE_TOKENS[key]

def prepare_token_cache():
    # Mark all entries as not used
    global CACHE_TOKENS
    for key in CACHE_TOKENS:
        CACHE_TOKENS[key]["used_in_last_count"] = False

def format_prompt(history, llm_instance=None, max_context=6000, special_instructions=""):
    """Format the conversation history with proper role tags for Llama 3.3
    Uses sliding window to keep only recent messages that fit in context.
    Reserves space for system prompt, new message, and response generation.
    """
    prepare_token_cache()

    # Start with system prompt
    combined_system_prompt = SYSTEM_PROMPT + "\n" + SYSTEM_PROMPT_EMOTIONS + "\n" + SYSTEM_PROMPT_STATES + "\n" + SYSTEM_PROMPT_BONDS
    system_part = f"<|start_header_id|>system<|end_header_id|>\n\n{combined_system_prompt}<|eot_id|>"

    end_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
    
    # Format the new user message
    if special_instructions:
        special_instructions = f"<|start_header_id|>user<|end_header_id|>\n\n*{special_instructions}*<|eot_id|>"

    # TODO delete repetitive states, or delete them altogether from history?
    # TODO figure why emotions are still not working well with Llama 3.3
    
    # Count tokens for system and user parts (reserve space)
    system_tokens = count_tokens(system_part, llm_instance)
    special_instructions_tokens = 0
    if special_instructions:
        special_instructions_tokens = count_tokens(special_instructions, llm_instance)
    end_prompt_tokens = count_tokens(end_prompt, llm_instance)
    available_tokens = max_context - system_tokens - special_instructions_tokens - end_prompt_tokens
        
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

    # wedge special instructions one before history
    if special_instructions:
        history_parts.insert(len(history_parts) - 1, special_instructions)
        token_count += special_instructions_tokens

    token_count += system_tokens

    # Combine all parts
    prompt = system_part + "".join(history_parts) + end_prompt

    print(prompt)
        
    # Log token usage
    #total_tokens = system_tokens + token_count + user_tokens
    print(f"[Token usage: {token_count}/{max_context}, kept {len(history_parts)} history messages]", flush=True)

    clean_token_cache()
    
    return prompt

# Create QApplication instance before any widgets
app = QApplication([])
chat_window = ChatWindow(character_name_value, chat_history, username)

# display the window
chat_window.show()

print("Using model:", model_path)
print("Character system loaded from:", character_system_description_path)
print("Conversation log path:", conversation_log_path)
print("Starting chat with character:", character_name_value)

emotion_handler = EmotionHandler(character_folder)
states_handler = StatesHandler(character_folder)
bonds_handler = BondsHandler(character_folder)
bonds_handler.check_against_status(states_handler.get_all_states())

print("Loading Llama model...")

def prepare_llm():
    # during this call we got the username from the chat window already so we will use that
    bonds_handler.apply_names(character_name_value, chat_window.username)
    states_handler.apply_names(character_name_value, chat_window.username)

    global SYSTEM_PROMPT_EMOTIONS
    global SYSTEM_PROMPT_STATES
    global SYSTEM_PROMPT_BONDS
    SYSTEM_PROMPT_EMOTIONS = emotion_handler.get_system_instructions(character_name_value)
    SYSTEM_PROMPT_STATES = states_handler.get_system_instructions(character_name_value)
    SYSTEM_PROMPT_BONDS = bonds_handler.get_system_instructions()

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

    global bonds_handler
    global current_bond_weight
    global current_applied_states
    global current_stranger
    global current_ended
    system_prompt_for_end = bonds_handler.get_instructions_for_bond(
        current_bond_weight,
        current_applied_states,
        current_stranger,
    )
        
    # Format the prompt with history
    prompt = format_prompt(
        chat_history,
        llm_instance=llm,
        max_context=8192 - 512,
        special_instructions=system_prompt_for_end
    )
        
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

    # calculate bond and states changes
    new_bond, new_stranger = bonds_handler.calculate_bond_change_from_message(
        current_bond_weight,
        current_stranger,
        len([msg for msg in chat_history if msg["role"] == "user" or msg["role"] == "assistant"]),
        response,
    )
    new_applied_states = states_handler.get_next_applying_states_from_llm_response(
        current_applied_states,
        response,
    )

    print(f"Updated bond: {current_bond_weight} -> {new_bond}, stranger: {current_stranger} -> {new_stranger}, applied states: {current_applied_states} -> {new_applied_states}")

    update_bond(new_bond, save=False)
    update_stranger(new_stranger, save=False)
    update_applied_states(new_applied_states, save=False)
    current_bond_weight = new_bond
    current_stranger = new_stranger
    current_applied_states = new_applied_states
    chat_history.append({"role": "assistant", "content": response.strip()})
    save_conversation_log()

    chat_window.update_status("Ready for next message.")

    end_tag_found = states_handler.llm_response_has_end_state(response)
    if end_tag_found[0]:
        chat_window.character_finished_typing(end_tag_found[2])
        chat_history_all["ended"] = end_tag_found[2]
        current_ended = end_tag_found[2]
        save_conversation_log()
    else:
        chat_window.character_finished_typing(None)

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
chat_window.run(
    current_ended,
    prepare_llm,
    run_inference,
    edit_message,
    delete_message,
    update_username,
)
app.exec()