from os import path
import random

def read_scenery_file(file_path: str) -> str:
    content = None
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    static_locations = []
    journey_locations = []
    variables = []

    for line in content.splitlines():
        if line.startswith("#"):
            continue
        elif not line.strip():
            continue
        elif line.startswith("?"):
            variables.append(line[1:].strip()) 
        elif line.startswith("!"):
            static_locations.append(line[1:].strip())
        else:
            journey_locations.append(line.strip())

    return (static_locations, journey_locations, variables)

def read_variable_as_float(variables: list[str], variable_name: str) -> float:
    for var in variables:
        if var.startswith(f"{variable_name}="):
            return float(var.split("=")[1].strip())
    raise ValueError(f"Variable '{variable_name}' not found in variables.")

def read_variable_as_string(variables: list[str], variable_name: str) -> str:
    for var in variables:
        if var.startswith(f"{variable_name}="):
            return var.split("=")[1].strip()
    raise ValueError(f"Variable '{variable_name}' not found in variables.")

def process_location(location: str, available_statuses: list[str] = None) -> str:
    # split by : to get the location name and description
    parts = location.split(":")
    if len(parts) < 2:
        raise ValueError(f"Location '{location}' is not in the correct format. Expected 'Location Name: Description'.")
    location_name = parts[0].strip()
    location_description_raw = parts[1].strip().split(";")
    location_description = location_description_raw[0].strip()
    
    special_config = location_description_raw[1].strip() if len(location_description_raw) > 1 else ""
    special_config_splitted = special_config.split(" ")
    
    when = []
    not_when = []

    is_when = False
    is_not_when = False
    for config in special_config_splitted:
        if config == "when":
            is_when = True
            is_not_when = False
            continue
        elif config == "not":
            is_not_when = True
            is_when = False
            continue
        else:
            if available_statuses is not None and config not in available_statuses:
                raise ValueError(f"Location '{location}' has unknown special configuration '{config}'. Available statuses: {available_statuses}")
            elif is_when:
                when.append(config)
            elif is_not_when:
                not_when.append(config)
            else:
                raise ValueError(f"Location '{location}' has invalid special configuration '{special_config}'.")
    
    return (location_name, location_description, when, not_when)
    

class SceneryHandler:
    def __init__(self, character_path: str, available_statuses: list[str] = []):
        self.static_locations, self.journey_locations, self.variables = read_scenery_file(path.join(character_path, "scenarios.txt"))

        self.journey_fumble_rate = int(read_variable_as_float(self.variables, "FUMBLE_RATE"))
        self.change_rate = read_variable_as_float(self.variables, "PROACTIVITY_RATE")
        self.min_messages_before_change = int(read_variable_as_float(self.variables, "MIN_MESSAGES"))
        self.min_messages_before_change_initial = int(read_variable_as_float(self.variables, "MIN_MESSAGES_BEFORE_INITIAL"))
        self.min_messages_before_reject = int(read_variable_as_float(self.variables, "PROBABILITY_REJECTION_COOLDOWN_MESSAGES"))
        self.when_multiplier = int(read_variable_as_float(self.variables, "WHEN_MULTIPLIER"))
        self.initial_change_rate = read_variable_as_float(self.variables, "INITIAL_PROACTIVITY_RATE")
        self.stubborness_rate = read_variable_as_float(self.variables, "STUBBORNESS_RATE")

        self.initial_locations = [s.strip() for s in read_variable_as_string(self.variables, "INITIAL_LOCATIONS").split(",")]

        # we will do this to throw errors on init just in case
        for loc in self.static_locations:
            process_location(loc, available_statuses)
        for loc in self.journey_locations:
            process_location(loc, available_statuses)


    def apply_names(self, character_name: str, username: str) -> str:
        self.character_name = character_name
        self.username = username

        # replace all instances of {char} and {user} in the scenery strings and journey locations
        self.static_locations = [loc.replace("{{char}}", character_name).replace("{{user}}", username) for loc in self.static_locations]
        self.journey_locations = [loc.replace("{{char}}", character_name).replace("{{user}}", username) for loc in self.journey_locations]

        # now we can process these values as needed
        self.processed_static_locations = []
        self.processed_journey_locations = []
        for loc in self.static_locations:
            processed_location = process_location(loc)
            self.processed_static_locations.append(processed_location)
        for loc in self.journey_locations:
            processed_location = process_location(loc)
            self.processed_journey_locations.append(processed_location)
            
    def get_system_prompt_for_scenery_change_check(self):
        general_instructions = (
            "You are an AI assistant that determines if during the last message from the user, they have accepted a change of scenery or location. "
            "Respond with 'YES' if they have accepted a change of scenery, or 'NO' if they have not. "
            "Only respond with 'YES' or 'NO' and nothing else."
        )

        return general_instructions
    
    def get_system_prompt_confirmation_prompt(self, last_requested_location_change: str) -> str:
        """Return the post inference confirmation prompt"""
        return f"The character has requested to change the location to: {last_requested_location_change.replace('_', ' ').capitalize()}. Did the user accept this change? Answer with a simple 'YES' or 'NO'."
    
    def get_random_scenery_request(
        self,
        all_visited_locations: list[str],
        messages_since_last_location_change: int,
        messages_since_last_rejection: int,
        current_applying_states: list[list[str, int, int]],
    ) -> str:
        change_to_check_with = self.min_messages_before_change_initial if not all_visited_locations and not messages_since_last_rejection else self.min_messages_before_change
        probability_to_check_with = self.initial_change_rate if not all_visited_locations and not messages_since_last_rejection else self.change_rate

        if messages_since_last_location_change < change_to_check_with:
            print("Scenery change not considered due to min messages before change.")
            return None
        
        if messages_since_last_rejection != None and messages_since_last_rejection < self.min_messages_before_reject:
            print("Scenery change not considered due to rejection cooldown.")
            return None
        
        if random.random() > probability_to_check_with:
            print("Scenery change not considered due to probability check.")
            return None
        
        available_journey_locations = [loc for loc in self.processed_journey_locations if loc[0] not in self.already_visited_journey_locations]
        available_static_locations = self.processed_static_locations.copy()
        
        if not available_journey_locations and not available_static_locations:
            print("No available locations for scenery change.")
            return None

        current_applying_states_list = [state[0] for state in current_applying_states] 
        # we will duplicate journey locations based on when conditions
        weighted_journey_locations = []
        for loc in available_journey_locations:
            weight = 1
            for condition in loc[2]:  # when conditions
                if condition in current_applying_states_list:
                    weight *= self.when_multiplier
            for condition in loc[3]:  # not conditions
                if condition in current_applying_states_list:
                    weight = 0  # exclude this location
            if loc[0] not in self.initial_locations and not all_visited_locations:
                weight = 0  # exclude non-initial locations if no locations have been visited yet
            for _ in range(weight):
                weighted_journey_locations.append(loc)

        weighted_static_locations = []
        for loc in available_static_locations:
            weight = 1
            for condition in loc[2]:  # when conditions
                if condition in current_applying_states_list:
                    weight *= self.when_multiplier
            for condition in loc[3]:  # not conditions
                if condition in current_applying_states_list:
                    weight = 0  # exclude this location
            if loc[0] not in self.initial_locations and not all_visited_locations:
                weight = 0  # exclude non-initial locations if no locations have been visited yet
            for _ in range(weight):
                weighted_static_locations.append(loc)

        print("Weighted journey locations:", weighted_journey_locations)
        print("Weighted static locations:", weighted_static_locations)
        
        # choose between journey or static location 50/50
        if weighted_journey_locations and (not weighted_static_locations or random.choice([True, False])):
            available_journey_next_options = []
            for i in range(0, self.journey_fumble_rate):
                if i < len(weighted_journey_locations):
                    available_journey_next_options.append(weighted_journey_locations[i])
            
            print("Choosing between journey locations:", available_journey_next_options)
            chosen_location = random.choice(available_journey_next_options)
            print("Chosen journey location for scenery change options", chosen_location)
        elif weighted_static_locations:
            print("Choosing between static locations:", weighted_static_locations)
            chosen_location = random.choice(weighted_static_locations)
            print("Chosen static location for scenery change", chosen_location)
        else:
            print("No suitable location found for scenery change.")
            return None

        return chosen_location
    
    def get_prompt_for_scenery_change_request(
        self,
        all_visited_locations: list[str],
        messages_since_last_location_change: int,
        messages_since_last_rejection: int,
        current_applying_states: list[list[str, int, int]],
        last_requested_location_change: str,
        last_requested_location_change_was_accepted: bool,
        last_requested_location_change_was_rejected: bool,
    ):
        if last_requested_location_change_was_accepted:
            print(f"Scenery change was accepted")
            return None, f"\n\n{self.username} accepted to go to {last_requested_location_change.replace('_', ' ').lower().capitalize()} ensure to describe the way towards the new location in detail."
        
        if last_requested_location_change_was_rejected:
            print(f"Scenery change was rejected")
            # check against stubborness rate
            if random.random() < self.stubborness_rate:
                print(f"Scenery change will be re-requested due to stubborness.")
                return last_requested_location_change, f"\n\n{self.username} rejected to go to {last_requested_location_change.replace('_', ' ').lower().capitalize()} but you really want to go there, try to convince them again."
            else:
                print(f"Scenery change will not be re-requested due to stubborness.")
                return None, f"\n\n{self.username} rejected to go to {last_requested_location_change.replace('_', ' ').lower().capitalize()}, respect their decision and continue the story in the current location."

        random_location = self.get_random_scenery_request_change(
            all_visited_locations,
            messages_since_last_location_change,
            messages_since_last_rejection,
            current_applying_states
        )
        if random_location is None:
            return None, ""
        else:
            return random_location[0], f"\n\nIMPORTANT: {self.character_name} Should suggest changing the scenery to: {random_location[0].replace("_", " ").lower().capitalize()}. {random_location[1]}"