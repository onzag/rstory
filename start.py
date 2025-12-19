#from llama_cpp import Llama
from sys import argv
from os import path
import os
import json
from lib.bonds import BondsHandler
from lib.emotion import EmotionHandler
from lib.states import StatesHandler
from lib.ui import ChatWindow
from PySide6.QtWidgets import QApplication
import websocket

CONTEXT_WINDOW_SIZE = 8192
REPEAT_PENALTY = 1.1
FREQUENCY_PENALTY = 0.5
PRESENCE_PENALTY = 0.5
TEMPERATURE = 1.0
TOP_P = 0.9

# Path to your GGUF file (adjust to your fast SSD)
# must be Llama 3.3 compatible model for these settings to work properly
model_path = argv[1]

character_folder = argv[2]
character_system_description_path = path.join(character_folder, "system.txt")
character_name_path = path.join(character_folder, "name.txt")
character_pronouns_path = path.join(character_folder, "pronouns.txt")

# wait until the server is ready
import time
time.sleep(1)  # wait a bit for the server to start, cheap, trash code but whatever

if not path.exists(character_folder):
    print("Character folder does not exist:", character_folder)
    exit(1)

def save_settings():
    """Save current settings to settings.json"""
    global CONTEXT_WINDOW_SIZE
    global REPEAT_PENALTY
    global FREQUENCY_PENALTY
    global PRESENCE_PENALTY
    global TEMPERATURE
    global TOP_P
    global character_folder
    settings = {
        "context_window_size": CONTEXT_WINDOW_SIZE,
        "repeat_penalty": REPEAT_PENALTY,
        "frequency_penalty": FREQUENCY_PENALTY,
        "presence_penalty": PRESENCE_PENALTY,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }
    with open(path.join(character_folder, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def load_settings():
    """Load settings from settings.json if it exists"""
    global CONTEXT_WINDOW_SIZE
    global REPEAT_PENALTY
    global FREQUENCY_PENALTY
    global PRESENCE_PENALTY
    global TEMPERATURE
    global TOP_P
    global character_folder
    settings_path = path.join(character_folder, "settings.json")
    if path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            CONTEXT_WINDOW_SIZE = settings.get("context_window_size", CONTEXT_WINDOW_SIZE)
            REPEAT_PENALTY = settings.get("repeat_penalty", REPEAT_PENALTY)
            FREQUENCY_PENALTY = settings.get("frequency_penalty", FREQUENCY_PENALTY)
            PRESENCE_PENALTY = settings.get("presence_penalty", PRESENCE_PENALTY)
            TEMPERATURE = settings.get("temperature", TEMPERATURE)
            TOP_P = settings.get("top_p", TOP_P)

load_settings()
save_settings()

# read character name from name.txt
with open(character_name_path, "r", encoding="utf-8") as f:
    character_name_value = f.read().strip()

with open(character_pronouns_path, "r", encoding="utf-8") as f:
    character_pronouns_value = [pronoun.strip().lower() for pronoun in f.read().strip().split("\n") if pronoun.strip()]

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
def count_tokens(text):
    """Estimate token count for a given text"""
    global CACHE_TOKENS
    if text in CACHE_TOKENS:
        CACHE_TOKENS[text]["used_in_last_count"] = True
        return CACHE_TOKENS[text]["value"]
    
    # call to webserver to get token count
    ws = websocket.create_connection("ws://localhost:8000")
    ws.send(json.dumps({"action": "count_tokens", "text": text}))
    response = json.loads(ws.recv())
    ws.close()

    if response["type"] == "error":
        raise Exception("Failed to count tokens:", response["message"])

    token_count = response["n_tokens"]
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

def format_prompt(history, max_context=6000, special_instructions=""):
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
    
    # Count tokens for system and user parts (reserve space)
    system_tokens = count_tokens(system_part)
    special_instructions_tokens = 0
    if special_instructions:
        special_instructions_tokens = count_tokens(special_instructions)
    end_prompt_tokens = count_tokens(end_prompt)
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
            
        msg_tokens = count_tokens(msg_text)
            
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

states_handler = StatesHandler(character_folder)
emotion_handler = EmotionHandler(character_folder, states_handler.get_all_states())
bonds_handler = BondsHandler(character_folder)
bonds_handler.check_against_status(states_handler.get_all_states())

print("Loading Llama model...")

def prepare_llm():
    # during this call we got the username from the chat window already so we will use that
    bonds_handler.apply_names(character_name_value, chat_window.username)
    states_handler.apply_names(character_name_value, chat_window.username)
    emotion_handler.apply_names(character_name_value, chat_window.username, character_pronouns=character_pronouns_value)

    global SYSTEM_PROMPT_EMOTIONS
    global SYSTEM_PROMPT_STATES
    global SYSTEM_PROMPT_BONDS
    SYSTEM_PROMPT_EMOTIONS = emotion_handler.get_system_instructions()
    SYSTEM_PROMPT_STATES = states_handler.get_system_instructions()
    SYSTEM_PROMPT_BONDS = bonds_handler.get_system_instructions()

    chat_window.update_status("Loading model...")

    # start with neutral emotion
    # check last assistant for emotion if it exist
    last_message = None
    for msg in reversed(chat_history):
        if msg["role"] == "assistant":
            last_message = msg
            break
    if last_message is not None:
        emotion_handler.restart_rolling_emotions()
        # split the message into words to simuate rolling tokens
        last_emotion = None
        for word in last_message["content"].split():
            last_emotion_given, _ = emotion_handler.process_rolling_token(word + " ")
            if last_emotion_given is not None:
                last_emotion = last_emotion_given
        if last_emotion is None:
            last_emotion = "neutral"
            print("No emotion detected in previous assistant message, starting with neutral emotion.")
        else:
            print(f"Previous assistant message found, starting with emotion: {last_emotion}")
        chat_window.showcase_emotion_from_prepare(last_emotion)
    else:
        chat_window.showcase_emotion_from_prepare("neutral")
        print("No previous assistant message found, starting with neutral emotion.")

    # call a http request to the node server to indicate we are ready
    model_path_absolute = path.abspath(model_path)
    
    # call to webserver to get token count
    ws = websocket.create_connection("ws://localhost:8000")
    ws.send(json.dumps({"action": "load_model", "model_path": model_path_absolute}))
    response = json.loads(ws.recv())
    ws.close()

    if response["type"] == "error":
        chat_window.update_status("Failed to load model.")
        raise Exception("Failed to load model:", response["message"])

    chat_window.update_status("Model loaded. Ready to chat!")

def run_inference(user_input, dangling_user_message):
    if not user_input:
        return  # skip empty input
    
    if user_input.startswith("/"):
        global CONTEXT_WINDOW_SIZE
        global TEMPERATURE
        global TOP_P
        global REPEAT_PENALTY
        global FREQUENCY_PENALTY
        global PRESENCE_PENALTY
        global current_bond_weight

        command_parts = user_input.split(" ", 1)
        command = command_parts[0]
        argument = command_parts[1] if len(command_parts) > 1 else ""
        if command == "/help":
            help_text = "Available commands:\n"
            help_text += "/context_window [number] - Set the context window size (default 8192)\n"
            help_text += "/temperature [number] - Set the temperature for response generation (default 1.0)\n"
            help_text += "/top_p [number] - Set the top_p for nucleus sampling (default 0.9)\n"
            help_text += "/repeat_penalty [number] - Set the repeat penalty (default 1.1)\n"
            help_text += "/frequency_penalty [number] - Set the frequency penalty (default 0.5)\n"
            help_text += "/presence_penalty [number] - Set the presence penalty (default 0.5)\n"
            help_text += "/bond - Show the current bond level with the character\n"
            chat_window.add_system_text(help_text)
        elif command == "/context_window":
            if not argument:
                chat_window.add_system_text(f"Current context window size: {CONTEXT_WINDOW_SIZE}")
                return
            try:
                new_value = int(argument)
                CONTEXT_WINDOW_SIZE = new_value
                chat_window.add_system_text(f"Context window size set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for context window size.")
        elif command == "/temperature":
            if not argument:
                chat_window.add_system_text(f"Current temperature: {TEMPERATURE}")
                return
            try:
                new_value = float(argument)
                TEMPERATURE = new_value
                chat_window.add_system_text(f"Temperature set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for temperature.")
        elif command == "/top_p":
            if not argument:
                chat_window.add_system_text(f"Current top_p: {TOP_P}")
                return
            try:
                new_value = float(argument)
                TOP_P = new_value
                chat_window.add_system_text(f"top_p set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for top_p.")
        elif command == "/repeat_penalty":
            if not argument:
                chat_window.add_system_text(f"Current repeat penalty: {REPEAT_PENALTY}")
                return
            try:
                new_value = float(argument)
                REPEAT_PENALTY = new_value
                chat_window.add_system_text(f"Repeat penalty set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for repeat penalty.")
        elif command == "/frequency_penalty":
            if not argument:
                chat_window.add_system_text(f"Current frequency penalty: {FREQUENCY_PENALTY}")
                return
            try:
                new_value = float(argument)
                FREQUENCY_PENALTY = new_value
                chat_window.add_system_text(f"Frequency penalty set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for frequency penalty.")
        elif command == "/presence_penalty":
            if not argument:
                chat_window.add_system_text(f"Current presence penalty: {PRESENCE_PENALTY}")
                return
            try:
                new_value = float(argument)
                PRESENCE_PENALTY = new_value
                chat_window.add_system_text(f"Presence penalty set to {new_value}.")
                save_settings()
            except ValueError:
                chat_window.add_system_text("Invalid value for presence penalty.")
        elif command == "/bond":
            chat_window.add_system_text(f"Current bond level: {current_bond_weight:.2f}")
        else:
            chat_window.add_system_text(f"Unknown command: {command}. Type /help for a list of commands.")
        return

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
        max_context=CONTEXT_WINDOW_SIZE - 512,
        special_instructions=system_prompt_for_end
    )

    # Generate response
    chat_window.character_is_typing()
    response = ""
    emotion_handler.restart_rolling_emotions()
    emotions_triggered = set([])
    states_triggered_add = set([])
    states_triggered_discard = set([])

    # we will start a streaming request to the server
    prompt_url = "http://localhost:8000/generate"
    action = {
        "action": "generate",
        "prompt": prompt,
        "max_tokens": 8192,
        "stream": True,
        "stop": ["<|eot_id|>", "<|start_header_id|>"],
        "repeat_penalty": REPEAT_PENALTY,           # Penalize repetitions (1.0 = no penalty, higher = more penalty)
        "frequency_penalty": FREQUENCY_PENALTY,        # Reduce likelihood of frequently used tokens
        "presence_penalty": PRESENCE_PENALTY,          # Encourage new topics/ideas
        "temperature": TEMPERATURE,              # Creativity of responses
        "top_p": TOP_P,                   # Nucleus sampling
    }
    ws = websocket.create_connection("ws://localhost:8000")
    ws.send(json.dumps(action))

    next_message = json.loads(ws.recv())
    while next_message["type"] != "done" and next_message["type"] != "error":
        if next_message["type"] == "token":
            text = next_message["text"]
            chat_window.add_character_text(text)
            emotion_triggered, state_triggered = emotion_handler.process_rolling_token(text)
            if emotion_triggered is not None:
                chat_window.showcase_emotion(emotion_triggered)
                emotions_triggered.add(emotion_triggered)
            for state in state_triggered:
                sign = state[0]
                state_name = state[1]
                if sign == "+":
                    states_triggered_add.add(state_name)
                    if state_name in states_triggered_discard:
                        states_triggered_discard.remove(state_name)
                elif sign == "-":
                    states_triggered_discard.add(state_name)
                    if state_name in states_triggered_add:
                        states_triggered_add.remove(state_name)
            response += text
        next_message = json.loads(ws.recv())

    ws.close()

    if next_message["type"] == "error":
        chat_window.add_system_text(f"Error during generation: {next_message['message']}")

    # check if no INTERACTION_POSITIVE, INTERACTION_NEGATIVE or INTERACTION_NEUTRAL was added, if not add NEUTRAL by default
    interaction_states = ["INTERACTION_POSITIVE", "INTERACTION_NEGATIVE", "INTERACTION_NEUTRAL"]
    if not any(interaction_state in response for interaction_state in interaction_states):
        to_add = "INTERACTION_NEUTRAL"
        if response.endswith("\n"):
            to_add = "\nINTERACTION_NEUTRAL"
        else:
            to_add = "\n\nINTERACTION_NEUTRAL"
        response += to_add
        print("Missing interaction state detected, adding INTERACTION_NEUTRAL by default.")
        chat_window.add_character_text(to_add)

    # calculate bond and states changes
    new_applied_states = states_handler.get_next_applying_states_from_llm_response(
        current_applied_states,
        response,
        states_triggered_add,
        states_triggered_discard,
    )
    mini_bonuses = states_handler.get_mini_bonuses(new_applied_states)
    new_bond, new_stranger = bonds_handler.calculate_bond_change_from_message(
        current_bond_weight,
        current_stranger,
        len([msg for msg in chat_history if msg["role"] == "user" or msg["role"] == "assistant"]),
        response,
        mini_bonuses,
    )

    print(f"Updated bond: {current_bond_weight} -> {new_bond}, stranger: {current_stranger} -> {new_stranger}, applied states: {current_applied_states} -> {new_applied_states}, bond mini bonuses: {mini_bonuses}")

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