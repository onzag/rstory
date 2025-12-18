from os import path
import random

def read_states_list(states_path: str) -> list[str]:
    """Read the list of states from the given file path"""
    with open(states_path, "r", encoding="utf-8") as f:
        states = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # check that every emotion is unique and lowercase and has no spaces
    seen = set()
    for state in states:
        if state in seen:
            raise ValueError(f"Duplicate state found in state list: {state}")
        if " " in state:
            raise ValueError(f"State contains spaces, which is not allowed: {state}")
        if state != state.upper():
            raise ValueError(f"State must be uppercase: {state}")
        seen.add(state)

    # states that are considered common for the character start with !, we remove the ! for usage, and keep a separate list
    common_states = [e[1:] for e in states if e.startswith("!")]
    states = [e for e in states if not e.startswith("!")]
    
    # states however have a random spawn rate, indicated by them having a = and a floating point number after them
    state_rates_common = {}
    state_rates = {}

    for state in states + common_states:
        if "=" in state:
            parts = state.split("=")
            state_name = parts[0]
            try:
                rate = float(parts[1])
            except ValueError:
                raise ValueError(f"Invalid spawn rate for state '{state_name}': {parts[1]}")
            # check that rate is between 0 and 1
            if rate < 0.0 or rate > 1.0:
                raise ValueError(f"Spawn rate for state '{state_name}' must be between 0.0 and 1.0")
            if state in states:
                state_rates[parts[0]] = rate
            else:
                state_rates_common[parts[0]] = rate
        else:
            if state in states:
                state_rates[state] = 0.0  # default rate
            else:
                state_rates_common[state] = 0.0  # default rate

    return (state_rates, state_rates_common)

def read_end_states_list(end_states_path: str) -> list[(str, str)]:
    """Read the list of end states from the given file path"""
    with open(end_states_path, "r", encoding="utf-8") as f:
        end_states = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # this file contains a STATE:DESCRIPTION format
    for i in range(len(end_states)):
        parts = end_states[i].split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid end state format: {end_states[i]}. Must be STATE: DESCRIPTION")
        end_states[i] = (parts[0].strip(), parts[1].strip())

    # check that every end state is unique and uppercase and has no spaces
    seen = set()
    for state, description in end_states:
        if state in seen:
            raise ValueError(f"Duplicate end state found in end state list: {state}")
        if " " in state:
            raise ValueError(f"End state contains spaces, which is not allowed: {state}")
        if state != state.upper():
            raise ValueError(f"End state must be uppercase: {state}")
        seen.add(state)

    return end_states


class StatesHandler:
    def __init__(self, general_path: str):
        self.general_path = general_path
        # load states from the states.txt file
        self.states, self.common_states = read_states_list(path.join(general_path, "states.txt"))
        self.end_states = read_end_states_list(path.join(general_path, "end_states.txt"))

        print(f"Loaded {len(self.states) + len(self.common_states)} states, {len(self.common_states)} common states.")

    def get_all_states(self) -> list[str]:
        """Get a list of all states (including common states)"""
        return list(self.states.keys()) + list(self.common_states.keys())
    
    def get_random_applied_states(self) -> list[str]:
        """Get a list of randomly applied states based on their spawn rates"""

        applied_states = []
        for state, rate in self.states.items():
            if random.random() < rate:
                applied_states.append(state)
        for state, rate in self.common_states.items():
            if random.random() < rate:
                applied_states.append(state)
        return applied_states
    
    def apply_names(self, character_name: str, username: str):
        # we apply the character name and username to the end_states descriptions
        applied_end_states = []
        for state, description in self.end_states:
            description = description.replace("{{char}}", character_name)
            description = description.replace("{{user}}", username)
            applied_end_states.append((state, description))
        self.end_states = applied_end_states
    
    def get_next_applying_states(self, current_applying_states: list[list[str, int]], llm_given_states_add: list[str], llm_given_states_reduce: list[str]) -> list[list[str, int]]:
        """Get a list of states that are currently applying based on their durations"""
        random_states = self.get_random_applied_states()
        new_applying_states = []
        for state_info in current_applying_states:
            state = state_info[0]
            intensity = state_info[1]
            if state in llm_given_states_add or state in random_states:
                intensity += 1  # increase intensity if state is given again
                if intensity > 4:
                    intensity = 4  # cap intensity at 4
            if state in llm_given_states_reduce:
                intensity -= 1  # decrease intensity if state is reduced
                if intensity < 0:
                    intensity = 0  # cap intensity at 0
            if intensity > 0:
                new_applying_states.append([state, intensity])
        # now let's add possibly new states from llm_given_states_add and random_states
        for state in llm_given_states_add + random_states:
            if state not in [s[0] for s in new_applying_states]:
                new_applying_states.append([state, 1])  # add new state with intensity 1
        return new_applying_states
    
    def get_system_instructions(self, character_name):
        common_states = list(self.common_states.keys())
        common_states_increase_tags = "\n".join([f"[[{state}_INCREASE]]" for state in common_states])
        common_states_decrease_tags = "\n".join([f"[[{state}_DECREASE]]" for state in common_states])
        normal_states = list(self.states.keys())
        normal_states_increase_tags = "\n".join([f"[[{state}_INCREASE]]" for state in normal_states])
        normal_states_decrease_tags = "\n".join([f"[[{state}_DECREASE]]" for state in normal_states])
        basic_prompt = f"While providing responses, add state tags to help indicate the character's current emotional and mental states; {character_name}" + \
               " very commonly falls into certain states, described by the tags:\n" + common_states_increase_tags + "\nwhich can be decreased by specifying:\n" + common_states_decrease_tags + \
                "\n\nAdditionally, consider other states that may apply, described by the tags:\n" + normal_states_increase_tags + "\nand decrease by specifying:\n" + normal_states_decrease_tags + \
                "\nUse these tags to reflect changes in the character's emotional and mental states throughout the conversation."
        end_prompt = f"If something catastrophic happens in the story, an end tag may be required to indicate a significant effect, the following end tags may be used when appropriate:\n" + \
            "\n".join([f"[[{state}]]: {description}" for state, description in self.end_states]) + \
            "\nUse these tags only when the story context justifies their application."
        return basic_prompt + "\n\n" + end_prompt
    
    def get_next_applying_states_from_llm_response(self, current_applying_states: list[list[str, int]], llm_response: str) -> list[list[str, int]]:
        """Get the next applying states based on the LLM response"""
        llm_given_states_add = []
        llm_given_states_reduce = []
        for state in self.get_all_states():
            if f"[[{state}_INCREASE]]" in llm_response:
                llm_given_states_add.append(state)
            if f"[[{state}_DECREASE]]" in llm_response:
                llm_given_states_reduce.append(state)
        return self.get_next_applying_states(current_applying_states, llm_given_states_add, llm_given_states_reduce)
    
    def llm_response_has_end_state(self, llm_response: str) -> tuple[bool, str]:
        """Check if the LLM response contains an end state tag, and return the state if found"""
        for state, description in self.end_states:
            if f"[[{state}]]" in llm_response:
                return (True, state, description)
        return (False, "", "")