Build initial prompt text that species the first scenario
Calculate location information
Update scenario and location variables for all prompts, next location and all
Calculate character list for location

PROCESS

Reroll Lost Characters by their percentage odds that were left behind, x location lost multiplier
    Apply change of states due to being lost

LOC_CALC: If at a given location, are they still at the same given location or has it changed? (Inference)
    YES:
        is it to one of the recognized locations?... (Inference) Is it close or far away?...
            YES:
                Calculate location information, location is x
                Update scenario and location variables for all prompts, next location and all
                Calculate character list for location
                Calculate lost charater members if any
                If a character is lost from the original source location, with a random roll encounter, they may be there at this unknown provided they got lost at source
                Recalculate present party if characters have reunited
            NO, Close
                Calculate for unknown, location is somewhere near x
                If a character is lost from the original source location, with a random roll encounter, they may be there at this unknown provided they got lost at source
            NO, Far away
                Calculate for unknown, location is somewhere far from x
                If a character is lost from the original source location, with a random roll encounter, they may be there at this unknown provided they got lost at source
    NO:
        Do nothing, we continue

CHAR_CALC: Collect characters at the given location, if it had changed from
Find if user/character last message is forcing a character to spawn where not present. (Inference)
    YES, user/character spawned them:
        Add them to the character at a given location

Per character list
Did user interact with any of the characters in the current character available list?... (Inference)
    YES, PER Character:
        Save in interacted with.

Are there characters non-interacted?...
    YES, PER Character.
        Does Character have a friendship/stranger bond with player?...
            Roll initiative x 2
            Add to list if pass
        No:
            Roll initiative / 2
            Add to list if pass

Is the list still empty?
    Roll initative for everyone, with the x2 and /2 modifiers, pick the highest.

Loop per interacted character
    Calculate character state (Inference)
    Calculate dead ends (Inference)
    Run prompt with rolling emotion (Inference Heavy)
    Go to LOC_CALC
    Go to CHAR_CALC

Loop per interacted character
    Calculate bond progression (Inference)