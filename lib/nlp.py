import nltk

nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('punkt_tab', quiet=True)

class SubjectDetector:
    def __init__(self, known_subject: str, subject_pronouns: list[str]):
        self.known_subject_original = known_subject
        self.known_subject = known_subject.lower()
        self.pronouns = subject_pronouns
    
    def analyze_sentence(self, text: str, own: bool = False) -> list[str]:
        tokens = nltk.word_tokenize(text)
        pos_tags = nltk.pos_tag(tokens)
        
        results = []
        current_subject = None
        
        for i, (word, tag) in enumerate(pos_tags):
            # Detect subjects: proper nouns, pronouns, or "the [noun]"
            next_subject = None
            next_subject_simple = None

            if tag in ('NNP', 'PRP'):  # Proper noun or pronoun
                next_subject = word.lower()
                next_subject_simple = next_subject

                if own and word.lower() in ["i", "me"]:
                    next_subject = self.known_subject
                    next_subject_simple = self.known_subject
            elif word.lower() in ["someone", "somebody", "anyone", "anybody"]:
                next_subject = word.lower()
                next_subject_simple = word.lower()
            elif (word.lower() == 'the' or word.lower() == "a" or word.lower() == "an") and i + 1 < len(pos_tags):
                # "the man" -> subject is "the man"
                next_word, next_tag = pos_tags[i + 1]
                next_next_word, next_next_tag = pos_tags[i + 2] if i + 2 < len(pos_tags) else (None, None)
                if next_tag.startswith('NN'):
                    next_subject = f"{word} {next_word}"
                    next_subject_simple = next_word.lower()
                if next_next_tag is not None and next_next_tag.startswith('NN') and next_tag in ('JJ', 'DT'):
                    next_subject = f"{word} {next_word} {next_next_word}"
                    next_subject_simple = next_next_word.lower()

            if next_subject is None:
                continue

            # detect if the next_subject is actually the current known subject
            if current_subject is not None and current_subject == self.known_subject and next_subject_simple in self.pronouns:
                next_subject = self.known_subject
            else:
                next_subject = next_subject.lower()

            if next_subject.lower() == self.known_subject:
                current_subject = self.known_subject
                results.append(self.known_subject_original)
            else:
                current_subject = next_subject
                results.append(next_subject)
        
        return results