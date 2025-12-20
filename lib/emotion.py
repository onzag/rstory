from os import path, listdir

from lib.nlp import SubjectDetector

def read_emotion_list(emotion_path: str, all_states: list[str]):
    """Read the list of emotions from the given file path"""
    with open(emotion_path, "r", encoding="utf-8") as f:
        emotions_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # check that every emotion is unique and lowercase and has no spaces
    common_emotions = {}
    emotions = {}

    seen = set()
    for emotion in emotions_list:
        splitted = emotion.split(":")
        emotion_value = splitted[0].strip()
        is_common = emotion_value.startswith("!")
        if is_common:
            emotion_value = emotion_value[1:]

        emotion_states_parsed = []
        emotion_states = splitted[1].strip().split(",") if len(splitted) > 1 else []
        for state in emotion_states:
            state = state.strip()
            sign = state[0]
            if sign in ["+", "-"]:
                state = state[1:].strip()
            else:
                sign = "+"  # default to +

            if state not in all_states:
                raise ValueError(f"Emotion '{emotion_value}' references unknown state '{state}'")
            
            emotion_states_parsed.append((sign, state))
            
        if emotion_value in seen:
            raise ValueError(f"Duplicate emotion found in emotion list: {emotion}")
        if " " in emotion_value:
            raise ValueError(f"Emotion contains spaces, which is not allowed: {emotion}")
        if emotion_value != emotion_value.lower():
            raise ValueError(f"Emotion must be lowercase: {emotion}")
        seen.add(emotion_value)

        if is_common:
            common_emotions[emotion_value] = emotion_states_parsed
        else:
            emotions[emotion_value] = emotion_states_parsed

    # emotions that are considered common for the character start with !, we remove the ! for usage, and keep a separate list
    return (emotions, common_emotions)

def read_phrase_list(phrase_path: str, all_emotions: list[str]) -> list[str]:
    """Read the list of phrases from the given file path"""
    with open(phrase_path, "r", encoding="utf-8") as f:
        phrases = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    general_context_phrases = {}
    subject_context_phrases = {}

    for phrase in phrases:
        splitted = phrase.split(":", 1)
        if len(splitted) != 2:
            raise ValueError(f"Phrase line is not correctly formatted (missing ':'): {phrase}")
        emotion = splitted[1].strip()
        phrase_text = splitted[0].strip()
        if emotion not in all_emotions:
            raise ValueError(f"Phrase references unknown emotion '{phrase_text}': {emotion}")
        
        is_general = False
        if phrase_text.startswith("!"):
            phrase_text = phrase_text[1:]
            is_general = True

        if is_general:
            general_context_phrases[phrase_text] = emotion
        else:
            subject_context_phrases[phrase_text] = emotion

    return (general_context_phrases, subject_context_phrases)

ALT_CACHE = {}
def get_emotion_alternatives(emotion: str, all_emotions_expanded: set[str]) -> set[str]:
    """Get alternative names for the given emotion, only if such alternatives are not in all_emotions"""

    if emotion in ALT_CACHE:
        return ALT_CACHE[emotion]
    
    emotion_expanded = expand_emotion(emotion)

    synonymlist = [
        ["happy", "joyful", "cheerful", "content"],
        ["sad", "unhappy", "sorrowful", "downcast"],
        ["angry", "mad", "furious", "irate"],
        ["surprised", "astonished", "amazed", "startled"],
        ["fearful", "afraid", "scared", "anxious"],
        ["disgusted", "revolted", "nauseated", "sickened"],
        ["neutral", "calm", "composed", "unemotional"],
        ["excited", "enthusiastic", "eager", "thrilled"],
        ["bored", "uninterested", "weary", "apathetic"],
        ["confused", "perplexed", "baffled", "puzzled"],
        ["loving", "affectionate", "fond", "adoring"],
        ["hating", "detest", "loathe", "despise"],
        ["proud", "pleased", "satisfied", "accomplished"],
        ["ashamed", "guilty", "embarrassed", "regretful"],
        ["relaxed", "calm", "peaceful", "serene"],
        ["nervous", "anxious", "tense", "uneasy"],
        ["curious", "inquisitive", "interested", "inquiring"],
        ["confident", "self-assured", "bold", "assertive"],
        ["jealous", "envious", "resentful", "covetous"],
        ["grateful", "thankful", "appreciative", "obliged"],
        ["lonely", "isolated", "solitary", "forlorn"],
        ["hopeful", "optimistic", "expectant", "positive"],
        ["frustrated", "irritated", "annoyed", "exasperated"],
        ["determined", "resolute", "steadfast", "persistent"],
        ["sympathetic", "compassionate", "understanding", "caring"],
        ["guilty", "remorseful", "regretful", "contrite"],
        ["relieved", "comforted", "reassured", "soothed"],
        ["embarrassed", "ashamed", "self-conscious", "flustered"],
        ["optimistic", "hopeful", "positive", "upbeat"],
        ["pessimistic", "negative", "cynical", "doubtful"],
        ["determined", "resolute", "persistent", "tenacious"],
        ["anxious", "nervous", "uneasy", "worried"],
        ["enthusiastic", "excited", "eager", "zealous"],
        ["apathetic", "indifferent", "uninterested", "detached"],
        ["affectionate", "loving", "fond", "caring"],
        ["desperate", "hopeless", "frantic", "despairing", "distressed"],
    ]
    alternatives = set([])
    for synset in synonymlist:
        for emotion in emotion_expanded:
            if emotion in synset:
                for alt in synset:
                    if alt != emotion and alt not in all_emotions_expanded:
                        alternatives |= expand_emotion(alt)
    alternatives |= emotion_expanded  # always include the expanded forms of the original emotion
    ALT_CACHE[emotion] = alternatives
    return alternatives

EXPAND_CACHE = {}
def expand_emotion(emotion: str) -> set[str]:
    """Expand the emotion into possible variations"""
    if emotion in EXPAND_CACHE:
        return EXPAND_CACHE[emotion]
    
    variations = set([emotion])
    base_form = emotion
    if emotion.endswith("ed"):
        base_form = emotion[:-2]
        variations.add(emotion[:-2])  # remove ed
    if emotion.endswith("ing"):
        base_form = emotion[:-3]
        variations.add(emotion[:-3])  # remove ing
    if emotion.endswith("y"):
        base_form = emotion[:-1]
        variations.add(emotion[:-1] + "iness")  # change y to iness
    if emotion.endswith("ness"):
        base_form = emotion[:-4]
        variations.add(emotion[:-4])  # remove ness
    if emotion.endswith("ful"):
        base_form = emotion[:-3]
        variations.add(emotion[:-3])  # remove ful
    if emotion.endswith("less"):
        base_form = emotion[:-4]
        variations.add(emotion[:-4])  # remove less
    if emotion.endswith("ly"):
        base_form = emotion[:-2]
        variations.add(emotion[:-2])  # remove ly
    if emotion.endswith("s"):
        base_form = emotion[:-1]
        variations.add(emotion[:-1])  # remove s
    if emotion.endswith("es"):
        base_form = emotion[:-2]
        variations.add(emotion[:-2])  # remove es
    if emotion.endswith("ier"):
        base_form = emotion[:-3]
        variations.add(emotion[:-3])  # remove ier
    if emotion.endswith("iest"):
        base_form = emotion[:-4]
        variations.add(emotion[:-4])  # remove iest
    if emotion.endswith("er"):
        base_form = emotion[:-2]
        variations.add(emotion[:-2])  # remove er
    if emotion.endswith("est"):
        base_form = emotion[:-3]
        variations.add(emotion[:-3])  # remove est
    # now make assumptions and add variations based on the base form
    # made, please, doe
    if base_form != "mad" and base_form != "pleas" and base_form != "do":
        if not base_form.endswith("e"):
            variations.add(base_form + "e")  # add e
        else:
            variations.add(base_form[:-1])  # remove e

    expanded_endings = ["ed", "ing", "y", "ness", "ly", "s", "es", "ier", "iest", "er", "est", "edly", "ingly", "ily", "fulness", "lessness", "iness", "ers", "est", "ies"]
    # prevent contradictions
    if not emotion.endswith("ful"):
        expanded_endings.append("ful")
    if not emotion.endswith("less"):
        expanded_endings.append("less")

    for ending in expanded_endings:
        new_form = base_form + ending
        if new_form != "made" and new_form != "done" and new_form != "please" and new_form != "doe" and not base_form.endswith(ending) and not new_form in variations:  # exceptions
            variations.add(new_form)  # add endings

    EXPAND_CACHE[emotion] = variations

    return variations

class EmotionHandler:
    """Class to handle emotions for characters"""

    def __init__(self, general_path: str, all_states: list[str]):
        self.general_path = general_path
        self.emotions, self.common_emotions = read_emotion_list(path.join(general_path, "emotions.txt"), all_states)

        print(f"Loaded {len(self.emotions.keys()) + len(self.common_emotions.keys())} emotions, {len(self.common_emotions.keys())} common emotions.")

        # find neutral emotion
        self.all_emotions = list(self.emotions.keys()) + list(self.common_emotions.keys())
        self.all_emotions_expanded = set()
        for emotion in self.all_emotions:
            self.all_emotions_expanded |= expand_emotion(emotion)
        if "neutral" not in self.all_emotions:
            raise ValueError("Emotion list must contain a 'neutral' emotion")
        
        self.all_phrases_general, self.all_phrases_subject = read_phrase_list(path.join(general_path, "phrases.txt"), self.all_emotions)
        
        print(f"Expanded emotions into count: {len(self.all_emotions_expanded)}")
        
        # check that for each emotion there is a corresponding folder in emotions/
        for emotion in self.all_emotions:
            image, loop_files, talking_loops = self.get_emotion_image(emotion)
            if image is None:
                # only give a warning
                print(f"Warning: No base image found for emotion '{emotion}', hence it can't be visualized.")

            if len(loop_files) == 0:
                print(f"Warning: No loop video files found for emotion '{emotion}', the character will have no video actions but a harsh cut.")
            else:
                transition_to_neutral = self.get_emotion_transition(emotion, "neutral")
                if transition_to_neutral is None:
                    print(f"Warning: The emotion '{emotion}' has loops but no transition video to at least 'neutral', which will lead to abrupt cuts.")

            if len(talking_loops) == 0:
                print(f"Warning: No talking loop video files found for emotion '{emotion}', the character will have no talking video actions but use a default loop. (if applicable)")
        
    def get_emotion_image(self, emotion: str) -> str:
        """Get the image file path for the given emotion"""
        if emotion not in self.all_emotions:
            return (None, [], [])
        emotion_folder = path.join(self.general_path, "emotions", emotion)
        image_file = path.join(self.general_path, "emotions", emotion, "base.jpg")
        # check if image file exists
        if not path.exists(image_file):
            return (None, [], [])
        # find video loop files they are named loop_1.mp4, loop_2.mp4, etc. within the emotion folder
        loop_files = []
        for file in listdir(emotion_folder):
            if file.startswith("loop_") and file.endswith(".mp4"):
                loop_files.append(path.join(emotion_folder, file))

        talking_loop_files = []
        for file in listdir(emotion_folder):
            if file.startswith("talking_loop_") and file.endswith(".mp4"):
                talking_loop_files.append(path.join(emotion_folder, file))
        
        return (image_file, loop_files, talking_loop_files)
    
    def get_emotion_transition(self, from_emotion: str, to_emotion: str) -> str:
        """Get the transition video file path from one emotion to another"""
        transition_file = path.join(self.general_path, "emotions", from_emotion, f"transition_to_{to_emotion}.mp4")
        if path.exists(transition_file):
            return transition_file
        else:
            return None
        
    def apply_names(self, character_name: str, username: str, character_pronouns: list[str]):
        self.character_name = character_name
        self.username = username

        self.subject_detector = SubjectDetector(character_name, character_pronouns)
        
    def get_system_instructions(self) -> str:
        """Get system instructions regarding emotions for the character"""
        common_emotion_tags = "\n".join(em for em in self.common_emotions.keys())
        #remaining_emotion_tags = "\n".join(em for em in self.emotions.keys())
        instructions = f"\nYou MUST use emotions in each paragraph to indicate the emotional state of {self.character_name}."
        instructions += f"\n{self.character_name} is very prone to being:\n{common_emotion_tags}"
        instructions += "\n\nYou MUST use asterisks *like this* to indicate and describe actions or descriptions outside of dialogue, always speak about yourself in third person when using asterisks."
        return instructions
    
    def restart_rolling_emotions(self):
        self.in_asterisk_description = False
        self.rolling_text = ""
        print("Restarted rolling emotion detection.")

    def process_rolling_token(self, token: str):
        self.rolling_text += token

        text_to_process = self.rolling_text
        text_to_process_in_asterisk = self.in_asterisk_description
        asterisk_updated_rolling_text = False
        if "*" in token:
            text_to_process = self.rolling_text.rsplit("*", 1)[0]  # get all text before the last asterisk
            asterisk_updated_rolling_text = True

            self.in_asterisk_description = not self.in_asterisk_description
            # restart anything after the asterisk
            self.rolling_text = token.split("*")[-1]

        # asterisk descriptions are in 3rd person
        subject_list = self.subject_detector.analyze_sentence(text_to_process, own=not text_to_process_in_asterisk)
        first_subject = subject_list[0] if len(subject_list) > 0 else None
        last_subject = subject_list[-1] if len(subject_list) > 0 else None

        if not first_subject and not last_subject:
            return (None, [])

        # check if the first subject is the character
        last_emotion_in_sentence = None
        last_states_triggered = []
        last_emotion_in_sentence_index = -1
        if first_subject and first_subject.lower() == self.character_name.lower():
            rolling_text_comparable = f" {text_to_process.lower()} "
            for emotion in self.all_emotions:
                emotion_all_triggers = get_emotion_alternatives(emotion, self.all_emotions_expanded)
                for trigger in emotion_all_triggers:
                    index = rolling_text_comparable.rfind(f" {trigger} ")
                    if index > last_emotion_in_sentence_index:
                        last_emotion_in_sentence_index = index
                        last_emotion_in_sentence = emotion
                        last_states_triggered = self.emotions.get(emotion, []) + self.common_emotions.get(emotion, [])
            for phrase, emotion in list(self.all_phrases_subject.items()) + list(self.all_phrases_general.items()):
                index = rolling_text_comparable.rfind(f" {phrase} ")
                if index > last_emotion_in_sentence_index:
                    last_emotion_in_sentence_index = index
                    last_emotion_in_sentence = emotion
                    last_states_triggered = self.emotions.get(emotion, []) + self.common_emotions.get(emotion, [])
        else:
            for phrase, emotion in self.all_phrases_general.items():
                rolling_text_comparable = f" {text_to_process.lower()} "
                index = rolling_text_comparable.rfind(f" {phrase} ")
                if index > last_emotion_in_sentence_index:
                    last_emotion_in_sentence_index = index
                    last_emotion_in_sentence = emotion
                    last_states_triggered = self.emotions.get(emotion, []) + self.common_emotions.get(emotion, [])

        # the character has changed just now we need to update our rolling text, if it hasn't already
        if last_subject != first_subject and not asterisk_updated_rolling_text:
            # find where the last subject started at which index last_subject appears
            last_subject_index = text_to_process.lower().rfind(last_subject.lower())
            if last_subject_index == -1:
                self.rolling_text = last_subject[0].upper() + last_subject[1:] + " "
            else:
                self.rolling_text = text_to_process[last_subject_index:]

        if last_emotion_in_sentence is not None:
            print(f"Detected rolling emotion: {last_emotion_in_sentence} triggering states {last_states_triggered} from text: {text_to_process}")

        return (last_emotion_in_sentence, last_states_triggered)