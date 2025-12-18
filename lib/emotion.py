from os import path, listdir

def read_emotion_list(emotion_path: str) -> list[str]:
    """Read the list of emotions from the given file path"""
    with open(emotion_path, "r", encoding="utf-8") as f:
        emotions = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # check that every emotion is unique and lowercase and has no spaces
    seen = set()
    for emotion in emotions:
        if emotion in seen:
            raise ValueError(f"Duplicate emotion found in emotion list: {emotion}")
        if " " in emotion:
            raise ValueError(f"Emotion contains spaces, which is not allowed: {emotion}")
        if emotion != emotion.lower():
            raise ValueError(f"Emotion must be lowercase: {emotion}")
        seen.add(emotion)

    # emotions that are considered common for the character start with !, we remove the ! for usage, and keep a separate list
    common_emotions = [e[1:] for e in emotions if e.startswith("!")]
    emotions = [e for e in emotions if not e.startswith("!")]
    return (emotions, common_emotions)

class EmotionHandler:
    """Class to handle emotions for characters"""

    def __init__(self, general_path: str):
        self.general_path = general_path
        self.emotions, self.common_emotions = read_emotion_list(path.join(general_path, "emotions.txt"))

        print(f"Loaded {len(self.emotions) + len(self.common_emotions)} emotions, {len(self.common_emotions)} common emotions.")

        # find neutral emotion
        self.all_emotions = self.emotions + self.common_emotions
        if "neutral" not in self.all_emotions:
            raise ValueError("Emotion list must contain a 'neutral' emotion")
        
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
        
    def get_system_instructions(self, character_name: str) -> str:
        """Get system instructions regarding emotions for the character"""
        common_emotion_tags = "\n".join(f":{em}:" for em in self.common_emotions)
        remaining_emotion_tags = "\n".join(f":{em}:" for em in self.emotions)
        instructions = f"\nCRITICAL FORMATTING RULE:\n"
        instructions += f"\nYou MUST include emotion tags in the response, e.g., :happy: or :sad: in each paragraph\n"
        instructions += f"\nMost commonly use these tags:\n{common_emotion_tags}\n\nAdditionally consider tags:\n{remaining_emotion_tags}"
        instructions += f"\nYou MUST use at least one emotion tag per paragraph to indicate the character's current emotional state.\n"
        return instructions