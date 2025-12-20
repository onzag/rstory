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
    plus_states = []
    
    for state in states + common_states:
        if "=" in state:
            parts = state.split("=")
            state_name = parts[0]
            plus_state = False
            if state_name[-1] == "+":
                state_name = state_name[:-1]
                plus_state = True
            try:
                rate = float(parts[1])
            except ValueError:
                raise ValueError(f"Invalid spawn rate for state '{state_name}': {parts[1]}")
            # check that rate is between 0 and 1
            if rate < 0.0 or rate > 1.0:
                raise ValueError(f"Spawn rate for state '{state_name}' must be between 0.0 and 1.0")
            if state_name in states:
                state_rates[state_name] = rate
            else:
                state_rates_common[state_name] = rate

            if plus_state:
                plus_states.append(state_name)
        else:
            plus_state = False
            if state[-1] == "+":
                state = state[:-1]
                plus_state = True
            if state in states:
                state_rates[state] = 0.0  # default rate
            else:
                state_rates_common[state] = 0.0  # default rate

            if plus_state:
                plus_states.append(state)

    return (state_rates, state_rates_common, plus_states)

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
        self.states, self.common_states, self.plus_states = read_states_list(path.join(general_path, "states.txt"))
        self.end_states = read_end_states_list(path.join(general_path, "end_states.txt"))

        self.llm_previously_applied_state_with_random_odd = {}

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
    
    def get_states_with_random_odds(self) -> list[str]:
        """Get a list of states that have random spawn odds"""
        applied_states = []
        for state, rate in self.states.items():
            if rate > 0.0:
                applied_states.append(state)
        return applied_states
    
    def reroll_llm_previously_applied_state_with_random_odd(self):
        """Reroll the states that were previously applied by the LLM with random odds
        removes them based on their spawn rates"""
        for state in list(self.llm_previously_applied_state_with_random_odd.keys()):
            rate = self.states.get(state, 0.0)
            # double the likelihood of it being removed
            # so the LLM can trigger it again more easily
            if (random.random() * 2) >= rate:
                if state in self.llm_previously_applied_state_with_random_odd:
                    print("Freed LLM previously applied state with random odd: ", state)
                    del self.llm_previously_applied_state_with_random_odd[state]
    
    def apply_names(self, character_name: str, username: str):
        self.character_name = character_name
        self.username = username
        # we apply the character name and username to the end_states descriptions
        applied_end_states = []
        for state, description in self.end_states:
            description = description.replace("{{char}}", character_name)
            description = description.replace("{{user}}", username)
            applied_end_states.append((state, description))
        self.end_states = applied_end_states

    def format_state_human_readable(self, state: str) -> str:
        """Format a state to be more human readable by replacing underscores with spaces and capitalizing words"""
        return state.replace("_", " ").title()
    
    def format_state_human_readable_list(self, states: list[str]) -> str:
        """Format a list of states to be more human readable"""
        return ", ".join([self.format_state_human_readable(state) for state in states])
    
    def get_next_applying_states(
            self,
            current_applying_states: list[list[str, int, int]],
            llm_given_states_add: list[str],
            llm_given_states_reduce: list[str],
            llm_given_states_remove: list[str],
            states_to_add_if_not_present: list[str],
            states_to_reduce_if_present: list[str],
        ) -> list[list[str, int, int]]:
        """Get a list of states that are currently applying based on their durations"""
        random_states = self.get_random_applied_states()

        states_with_random_odds = self.get_states_with_random_odds()
        self.reroll_llm_previously_applied_state_with_random_odd()
        for state in states_with_random_odds:
            if state in llm_given_states_add:
                # we want to be very careful when the LLM wants to add a state that has random odds
                if state in self.llm_previously_applied_state_with_random_odd:
                    # we deny it
                    print(f"Denied LLM request to add state with random odds again: {state}")
                    llm_given_states_add.remove(state)
                else:
                    # we allow it and mark it as previously applied
                    self.llm_previously_applied_state_with_random_odd[state] = True

        new_applying_states = []
        for state_info in current_applying_states:
            state = state_info[0]
            intensity = state_info[1]
            decay_rate = state_info[2]
            new_decay_rate = decay_rate - 1
            if new_decay_rate == 0:
                if intensity == 4:
                    intensity -= 2  # decrease intensity faster if at max
                else:
                    intensity -= 1  # decrease intensity if duration is over
                new_decay_rate = 3  # reset decay rate

            if state in llm_given_states_add or state in random_states:
                intensity += 1  # increase intensity if state is given again
                if intensity > 4:
                    intensity = 4  # cap intensity at 4
            if state in llm_given_states_reduce or state in states_to_reduce_if_present:
                # we will remove altogether because the AI seems to struggle with reducing intensity properly
                intensity = 0
            if state in llm_given_states_remove:
                intensity = 0  # remove state if state is removed
            if intensity > 0:
                new_applying_states.append([state, intensity, new_decay_rate])
        # now let's add possibly new states from llm_given_states_add and random_states
        for state in llm_given_states_add + random_states:
            if state not in [s[0] for s in new_applying_states]:
                new_applying_states.append([state, 1, 3])  # add new state with intensity 1
        for state_to_add_if_not_present in states_to_add_if_not_present:
            if state_to_add_if_not_present not in [s[0] for s in new_applying_states] and state_to_add_if_not_present not in llm_given_states_reduce:
                new_applying_states.append([state_to_add_if_not_present, 1, 3])  # add new state with intensity 1
        return new_applying_states
    
    def get_system_instructions(self):
        return ""
        
        # will disable and make it a post inference task instead, because this confuses the LLM too much
        #common_states = list(self.common_states.keys())
        #common_states_increase_tags = "\n".join([f"{state}_INCREASE" for state in common_states])
        #common_states_decrease_tags = "\n".join([f"{state}_DECREASE" for state in common_states])
        #normal_states = list(self.states.keys())
        #normal_states_increase_tags = "\n".join([f"{state}_INCREASE" for state in normal_states])
        #normal_states_decrease_tags = "\n".join([f"{state}_DECREASE" for state in normal_states])
        #basic_prompt = f"\nYou MUST include one of these phrases or tags at the end of every response" + \
        #       "\n\nThe tags to use are:\n" + common_states_increase_tags  + common_states_decrease_tags + normal_states_increase_tags + normal_states_decrease_tags + \
        #        "\n\nYou MUST use at most 3 of these tags to reflect changes in the character's emotional and mental state by the end of the conversation."
        #end_prompt = f"You MUST use one of these phrases or tags only if something catastrophic happens:\n" + \
        #    "\n".join([f"{state}: {description}" for state, description in self.end_states]) + \
        #    "\nYou MUST use these tags only when the story context justifies their application."
        #return basic_prompt + "\n\n" + end_prompt

    def get_post_inference_system_instructions(self) -> str:
        """Return the post inference step instructions"""
        return f"You are an assistant that analyses conversations between {self.character_name} and {self.username}. Your task is to determine which emotional and mental states should be applied to {self.character_name} based on the conversation. " + \
               f"You will output a list of states to increase and decrease in the following format:\n\n" + \
               f"Increase: state1, state2, ...\n" + \
               f"Decrease: state3, state4, ...\n" + \
               f"Add: state5, state6, ...\n\n" + \
               f"Remove: state5, state6, ...\n\n" + \
               f"You MUST separate the states with commas and the lists must be on separate lines. " + \
               f"Only include states that are relevant to the conversation. " + \
               f"\n\n{self.character_name} commonly experiences the following states:\n" + \
               f"{self.format_state_human_readable_list(self.states.keys())}\n\n" + \
               f"\n\nA list of all possible states:\n" + \
               f"{self.format_state_human_readable_list(self.get_all_states())}\n\n"
    
    def get_post_inference_confirmation_prompt(self) -> str:
        """Return the post inference confirmation prompt"""
        return "Your analysis MUST be (output ONLY in the exact format):\n\nIncrease: state1, state2, ...\nDecrease: state3, state4, ...\nAdd: state5, state6, ...\n\nRemove: state5, state6, ..."
    
    def analyze_response_for_states(self, llm_response: str) -> tuple[list[str], list[str], list[str]]:
        """Analyze the LLM response to determine which states to increase and decrease"""
        llm_response = llm_response.lower()
        increase_states = []
        decrease_states = []
        remove_states = []

        all_states = self.get_all_states()
        all_states_lower = [s.lower() for s in all_states]
        all_states_human_readable_lower = [self.format_state_human_readable(s).lower() for s in all_states]

        # parse the response for the Increase and Decrease lists
        lines = llm_response.splitlines()
        previous_line_was_increase = False
        previous_line_was_decrease = False
        previous_line_was_add = False
        previous_line_was_remove = False

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # check for invalid lines that seem to be roleplay or narrative
            invalid_indicators = ["i feel", "i am", "my", "me", "he", "she", "it", "you", "asks", "says"]
            spaced_line = " " + line + " "
            if any(" " + indicator + " " in spaced_line for indicator in invalid_indicators):
                print("Warning: Skipping potential invalid line in state analysis:", line)
                continue  # skip this line

            should_increase = "increase" in line and not "decrease" in line and not "add" in line and not "remove" in line
            should_decrease = ("decrease" in line or "reduce" in line) and not "increase" in line and not "add" in line and not "remove" in line
            should_add = "add" in line and not "increase" in line and not "decrease" in line and not "remove" in line
            should_remove = ("remove" in line or "discard" in line) and not "increase" in line and not "decrease" in line and not "add" in line

            if not should_increase and not should_decrease and not should_add and not should_remove:
                # use the previous line context if available
                should_increase = previous_line_was_increase
                should_decrease = previous_line_was_decrease
                should_add = previous_line_was_add
                should_remove = previous_line_was_remove

            for index, state in enumerate(all_states_lower):
                if state in line:
                    if (should_increase or should_add) and all_states[index] not in increase_states:
                        increase_states.append(all_states[index])
                    elif should_decrease and all_states[index] not in decrease_states:
                        decrease_states.append(all_states[index])
                    elif should_remove and all_states[index] not in remove_states:
                        remove_states.append(all_states[index])
            for index, state in enumerate(all_states_human_readable_lower):
                if state in line:
                    if (should_increase or should_add) and all_states[index] not in increase_states:
                        increase_states.append(all_states[index])
                    elif should_decrease and all_states[index] not in decrease_states:
                        decrease_states.append(all_states[index])
                    elif should_remove and all_states[index] not in remove_states:
                        remove_states.append(all_states[index])

            if not should_increase and not should_decrease and not should_add and not should_remove:
                print("Warning: Could not determine if line is for increase, decrease, add, or remove:", line)

            previous_line_was_decrease = should_decrease
            previous_line_was_increase = should_increase
            previous_line_was_add = should_add
            previous_line_was_remove = should_remove

        return increase_states, decrease_states, remove_states
    
    def get_mini_bonuses(self, applied_states: list[list[str, int, int]]) -> int:
        """Get the number of mini bond bonuses from the applied states"""
        mini_bonuses = 0
        for state_info in applied_states:
            state = state_info[0]
            if state in self.plus_states:
                mini_bonuses += state_info[1]  # add intensity as mini bonuses
        return mini_bonuses