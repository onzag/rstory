from os import path, listdir
import json
from typing_extensions import Literal

class BondsHandler:
    def __init__(self, character_folder):
        self.character_folder = character_folder
        self.bonds_folder = path.join(character_folder, "bonds")

        self.bonds_config_path = path.join(self.bonds_folder, "config.json")
        # check the following attributes exist in config.json
        # bond_climb_rate, positive float
        # bond_stranger_breakaway, positive int
        # bond_stranger_breakaway_reset_multiplier, positive float
        # bond_stranger_breakaway_reset_negative_multiplier, positive float
        # bond_stranger_messages_breakaway, positive int
        # bond_stranger_messages_breakaway_multiplier, positive float
        # bond_stranger_messages_breakaway_negative_multiplier, positive float
        # bond_stranger_negative_bias_multiplier, positive float
        # bond_negative_bias_multiplier, positive float
        if not path.exists(self.bonds_config_path):
            raise ValueError("Missing bonds config.json file in bonds folder")
        with open(self.bonds_config_path, "r", encoding="utf-8") as f:
            self.bonds_config = json.load(f)

        required_attributes = {
            "bond_climb_rate": "pos_float",
            "bond_stranger_breakaway": "pos_int",
            "bond_stranger_breakaway_reset_multiplier": "pos_float",
            "bond_stranger_breakaway_reset_negative_multiplier": "pos_float",
            "bond_stranger_messages_breakaway": "pos_int",
            "bond_stranger_messages_breakaway_multiplier": "pos_float",
            "bond_stranger_messages_breakaway_negative_multiplier": "pos_float",
            "bond_stranger_negative_bias_multiplier": "pos_float",
            "bond_negative_bias_multiplier": "pos_float",
        }
        for attr in required_attributes:
            if attr not in self.bonds_config:
                raise ValueError(f"Missing required attribute '{attr}' in bonds config.json")
            value = self.bonds_config[attr]
            if required_attributes[attr] == "pos_int":
                if not isinstance(value, int) or value <= 0:
                    raise ValueError(f"Attribute '{attr}' must be a positive integer in bonds config.json")
            elif required_attributes[attr] == "float_0_1":
                if not isinstance(value, (float, int)) or value < 0 or value > 1:
                    raise ValueError(f"Attribute '{attr}' must be a float between 0 and 1 in bonds config.json")
            elif required_attributes[attr] == "pos_float":
                if not isinstance(value, (float, int)) or value <= 0:
                    raise ValueError(f"Attribute '{attr}' must be a positive float in bonds config.json")
                
        self.bond_climb_rate = self.bonds_config["bond_climb_rate"]
        self.bond_stranger_breakaway = self.bonds_config["bond_stranger_breakaway"]
        self.bond_stranger_breakaway_reset_multiplier = self.bonds_config["bond_stranger_breakaway_reset_multiplier"]
        self.bond_stranger_breakaway_reset_negative_multiplier = self.bonds_config["bond_stranger_breakaway_reset_negative_multiplier"]
        self.bond_stranger_messages_breakaway = self.bonds_config["bond_stranger_messages_breakaway"]
        self.bond_stranger_messages_breakaway_multiplier = self.bonds_config["bond_stranger_messages_breakaway_multiplier"]
        self.bond_stranger_messages_breakaway_negative_multiplier = self.bonds_config["bond_stranger_messages_breakaway_negative_multiplier"]
        self.bond_stranger_negative_bias_multiplier = self.bonds_config["bond_stranger_negative_bias_multiplier"]
        self.bond_negative_bias_multiplier = self.bonds_config["bond_negative_bias_multiplier"]

        # list all the files in bonds_folder
        self.bond_files = [f for f in listdir(self.bonds_folder) if f.endswith(".txt")]
        # now we need to see if the bond files have a valid filename, it should be a number between -100 and 100 then a _ and another number between -100 and 100 indicating the bond range
        self.bond_ranges = []
        self.stranger_bond = None
        self.stranger_bad_bond = None
        for bond_file in self.bond_files:
            # skip stranger.txt file
            if bond_file == "stranger.txt" or bond_file == "stranger_bad.txt":
                continue

            parts = bond_file[:-4].split("_")
            if len(parts) != 2:
                raise ValueError(f"Invalid bond file name '{bond_file}', should be in format '<min>_<max>.txt'")
            try:
                min_bond = int(parts[0])
                max_bond = int(parts[1])
                if min_bond < -100 or min_bond > 100 or max_bond < -100 or max_bond > 100 or min_bond >= max_bond:
                    raise ValueError(f"Invalid bond range in file name '{bond_file}', values should be between -100 and 100 and min < max")
                self.bond_ranges.append([min_bond, max_bond, bond_file])
            except ValueError:
                raise ValueError(f"Invalid bond file name '{bond_file}', should contain integers")
        # now we must ensure that these bond ranges do not overlap, however the max_value is exclusive
        self.bond_ranges.sort(key=lambda x: x[0])
        for i in range(len(self.bond_ranges) - 1):
            if self.bond_ranges[i][1] > self.bond_ranges[i + 1][0]:
                raise ValueError(f"Bond ranges overlap between files '{self.bond_ranges[i][2]}' and '{self.bond_ranges[i + 1][2]}'")
            
        # now we want to ensure that there are no gaps in the bond ranges from -100 to 100
        current_min = -100
        for min_bond, max_bond, bond_file in self.bond_ranges:
            if min_bond != current_min:
                raise ValueError(f"Bond ranges have a gap before file '{bond_file}', expected min bond {current_min} but got {min_bond}")
            current_min = max_bond
            
        # now read the bond texts
        self.bond_texts = {}
        for min_bond, max_bond, bond_file in self.bond_ranges:
            with open(path.join(self.bonds_folder, bond_file), "r", encoding="utf-8") as f:
                self.bond_texts[(min_bond, max_bond)] = f.read().strip()

        # check stranger.txt exists
        if not path.exists(path.join(self.bonds_folder, "stranger.txt")):
            raise ValueError("Missing 'stranger.txt' file in bonds folder")
        
        if not path.exists(path.join(self.bonds_folder, "stranger_bad.txt")):
            raise ValueError("Missing 'stranger_bad.txt' file in bonds folder")

        with open(path.join(self.bonds_folder, "stranger.txt"), "r", encoding="utf-8") as f:
            self.stranger_bond = f.read().strip()

        with open(path.join(self.bonds_folder, "stranger_bad.txt"), "r", encoding="utf-8") as f:
            self.stranger_bad_bond = f.read().strip()
        
    def check_against_status(self, states: list[str]) -> bool:
        # this is for checking, we need to check that every status is indicated in each bond file as a line stating <status>: value
        # add "*" to states to indicate general instructions
        states.append("*")
        for min_bond, max_bond in self.bond_texts:
            bond_text = self.bond_texts[(min_bond, max_bond)]
            bond_text_line_splits = bond_text.splitlines()
            for state in states:
                if not any(line.startswith(f"{state}:") for line in bond_text_line_splits):
                    raise ValueError(f"State '{state}' not found in bond range {min_bond} to {max_bond}")
                
        # also check stranger bond
        bond_text = self.stranger_bond
        bond_text_line_splits = bond_text.splitlines()
        for state in states:
            if not any(line.startswith(f"{state}:") for line in bond_text_line_splits):
                raise ValueError(f"State '{state}' not found in stranger bond")
            
        # also check stranger bad bond
        bond_text = self.stranger_bad_bond
        bond_text_line_splits = bond_text.splitlines()
        for state in states:
            if not any(line.startswith(f"{state}:") for line in bond_text_line_splits):
                raise ValueError(f"State '{state}' not found in stranger bad bond")

    def apply_names(self, character_name: str, username: str):
        self.character_name = character_name
        self.username = username

        """Apply the character name and username to the bond texts"""
        for key in self.bond_texts:
            text = self.bond_texts[key]
            text = text.replace("{{char}}", character_name)
            text = text.replace("{{user}}", username)
            self.bond_texts[key] = text

        for key in self.stranger_bond:
            text = self.stranger_bond
            text = text.replace("{{char}}", character_name)
            text = text.replace("{{user}}", username)
            self.stranger_bond = text

        for key in self.stranger_bad_bond:
            text = self.stranger_bad_bond
            text = text.replace("{{char}}", character_name)
            text = text.replace("{{user}}", username)
            self.stranger_bad_bond = text

        # now we can process the bonrds further, each bondfile has text separated by lines
        self.processed_bonds = {}
        for min_bond, max_bond in self.bond_texts:
            bond_text = self.bond_texts[(min_bond, max_bond)]
            bond_lines = bond_text.splitlines()
            bond_dict = {}
            for line in bond_lines:
                if ":" in line:
                    state, value = line.split(":", 1)
                    bond_dict[state.strip()] = value.strip()
            self.processed_bonds[(min_bond, max_bond)] = bond_dict

        self.processed_stranger_bond = {}
        stranger_lines = self.stranger_bond.splitlines()
        for line in stranger_lines:
            if ":" in line:
                state, value = line.split(":", 1)
                self.processed_stranger_bond[state.strip()] = value.strip()

        self.processed_stranger_bad_bond = {}
        stranger_bad_lines = self.stranger_bad_bond.splitlines()
        for line in stranger_bad_lines:
            if ":" in line:
                state, value = line.split(":", 1)
                self.processed_stranger_bad_bond[state.strip()] = value.strip()

    def get_instructions_for_bond(self, bond_value: int, applying_states: list[list[str, int]], stranger_bond: bool) -> dict[str, str]:
        """Get the bond instructions for the given bond value"""
        processed_bond = None
        if stranger_bond:
            if bond_value < 0:
                processed_bond = self.processed_stranger_bad_bond
            else:
                processed_bond = self.processed_stranger_bond
        else:
            for min_bond, max_bond in self.processed_bonds:
                if bond_value >= min_bond and bond_value < max_bond:
                    processed_bond = self.processed_bonds[(min_bond, max_bond)]
                    break

        if bond_value >= 100:
            for min_bond, max_bond in self.processed_bonds:
                if max_bond == 100:
                    processed_bond = self.processed_bonds[(min_bond, max_bond)]
                    break

        if processed_bond is None:
            print(f"Warning: No bond instructions found for bond value {bond_value}")
            return ""
        
        # now we want to get the instructions for the applying states
        intensity_labels = [
            (0, ""),
            (1, ""),
            (2, "Very "),
            (3, "Extremely "),
            (4, "Extremely and Overwhelmingly "),
        ]
        all_instructions = processed_bond.get("*", "")

        for state, intensity in applying_states:
            if state in processed_bond:
                intensity_label = ""
                for level, label in intensity_labels:
                    if intensity >= level:
                        intensity_label = label
                state_wordified = state.replace("_", " ").lower()
                # capitalize first letter
                state_wordified = state_wordified[0].upper() + state_wordified[1:]

                is_added = " is "
                first_word = state_wordified.split(" ")[0].lower()
                # check if is is required, check if it ends in s
                if first_word[-1] == "s":
                    is_added = " "
                all_instructions += "\n" + self.character_name + is_added + "currently " + intensity_label + state_wordified + ", " + processed_bond[state] + ", to remove this state add the tag " + state.upper() + "_DECREASE at the end of the message."

        return all_instructions + f"\nkeep the answer at most two paragraphs long and do not predict {self.username} nor his reactions, roleplay as {self.character_name} only."
        
    def calculate_bond_change(self, current_bond: float, current_stranger: bool, total_messages_exchanged: int, change: Literal["pos", "neg", "neutral"]) -> float:
        next_bond_amount = current_bond
        if change == "pos":
            next_bond_amount += self.bond_climb_rate
            if next_bond_amount > 100:
                next_bond_amount = 100
        elif change == "neg":
            next_bond_amount -= self.bond_climb_rate*(self.bond_stranger_negative_bias_multiplier if current_stranger else self.bond_negative_bias_multiplier)
            if next_bond_amount < -100:
                next_bond_amount = -100
        else:
            pass  # neutral, no change

        next_stranger = current_stranger
        if current_stranger:
            if abs(next_bond_amount) >= self.bond_stranger_breakaway:
                next_bond_amount = next_bond_amount * (self.bond_stranger_breakaway_reset_negative_multiplier if next_bond_amount < 0 else self.bond_stranger_breakaway_reset_multiplier)
                next_stranger = False
            elif total_messages_exchanged >= self.bond_stranger_messages_breakaway:
                next_bond_amount = next_bond_amount * (self.bond_stranger_messages_breakaway_negative_multiplier if next_bond_amount < 0 else self.bond_stranger_messages_breakaway_multiplier)
                next_stranger = False

        return next_bond_amount, next_stranger
    
    def get_system_instructions(self) -> str:
        return f"You MUST include one of these at the end of the reply:\nINTERACTION_POSITIVE\nINTERACTION_NEGATIVE\nINTERACTION_NEUTRAL\n\nThis specifies whether the interaction was positive, negative or neutral and grows or shrinks the bond accordingly"
    
    def calculate_bond_change_from_message(self, current_bond: float, current_stranger: bool, total_messages_exchanged: int, message: str) -> tuple[float, bool]:
        """Find the INTERACTION_POSITIVE, INTERACTION_NEGATIVE, or INTERACTION_NEUTRAL tag in the message and calculate the bond change accordingly"""
        change = "neutral"
        # just grab the text because of issues with the LLM sometimes not following instructions properly
        if "INTERACTION_POSITIVE" in message:
            change = "pos"
        elif "INTERACTION_NEGATIVE" in message:
            change = "neg"

        return self.calculate_bond_change(current_bond, current_stranger, total_messages_exchanged, change)