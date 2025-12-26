
export const character = [
    [
        "user",
        "The name of the user",
        "eg. Alex, Vivianna, Connor",
        (user, character) => user.name,
    ],
    [
        "char",
        "The name of the character",
        "eg. Aria, Thalon, Mira",
        (user, character) => character.name,
    ],
    [
        "user_gender",
        "The gender of the user",
        "male, female or ambiguous",
        (user, character) => user.gender.toLowerCase(),
    ],
    [
        "char_gender",
        "The gender of the character",
        "male, female or ambiguous",
        (user, character) => character.gender.toLowerCase(),
    ],
    [
        "user_sex",
        "The sex of the user",
        "male, female or intersex",
        (user, character) => user.sex.toLowerCase(),
    ],
    [
        "char_sex",
        "The sex of the character",
        "male, female or intersex",
        (user, character) => character.sex.toLowerCase(),
    ],
    [
        "user_pronoun",
        "The 3rd person pronoun of the user",
        "he, she or they",
        (user, character) => user.sex.toLowerCase() === "male" ? "he" : user.sex.toLowerCase() === "female" ? "she" : "they",
    ],
    [
        "char_pronoun",
        "The 3rd person pronoun of the character",
        "he, she or they",
        (user, character) => character.sex.toLowerCase() === "male" ? "he" : character.sex.toLowerCase() === "female" ? "she" : "they",
    ],
    [
        "user_possessive",
        "The possessive pronoun of the user",
        "his, her or their",
        (user, character) => user.gender.toLowerCase() === "male" ? "his" : user.gender.toLowerCase() === "female" ? "her" : "their",
    ],
    [
        "char_possessive",
        "The possessive pronoun of the character",
        "his, her or their",
        (user, character) => character.gender.toLowerCase() === "male" ? "his" : character.gender.toLowerCase() === "female" ? "her" : "their",
    ],
    [
        "user_object_pronoun",
        "The object pronoun of the user",
        "him, her or them",
        (user, character) => user.gender.toLowerCase() === "male" ? "him" : user.gender.toLowerCase() === "female" ? "her" : "them",
    ],
    [
        "char_object_pronoun",
        "The object pronoun of the character",
        "him, her or them",
        (user, character) => character.gender.toLowerCase() === "male" ? "him" : character.gender.toLowerCase() === "female" ? "her" : "them",
    ],
    [
        "user_reflexive_pronoun",
        "The reflexive pronoun of the user",
        "himself, herself or themself",
        (user, character) => user.gender.toLowerCase() === "male" ? "himself" : user.gender.toLowerCase() === "female" ? "herself" : "themself",
    ],
    [
        "char_reflexive_pronoun",
        "The reflexive pronoun of the character",
        "himself, herself or themself",
        (user, character) => character.gender.toLowerCase() === "male" ? "himself" : character.gender.toLowerCase() === "female" ? "herself" : "themself",
    ],
    [
        "user_ownership_pronoun",
        "The ownership pronoun of the user",
        "his, hers or theirs",
        (user, character) => user.gender.toLowerCase() === "male" ? "his" : user.gender.toLowerCase() === "female" ? "hers" : "theirs",
    ],
    [
        "char_ownership_pronoun",
        "The ownership pronoun of the character",
        "his, hers or theirs",
        (user, character) => character.gender.toLowerCase() === "male" ? "his" : character.gender.toLowerCase() === "female" ? "hers" : "theirs",
    ],
    [
        "user_is_male",
        "Boolean indicating if the user is male",
        "true or false",
        (user, character) => user.gender.toLowerCase() === "male",
    ],
    [
        "user_is_female",
        "Boolean indicating if the user is female",
        "true or false",
        (user, character) => user.gender.toLowerCase() === "female",
    ],
    [
        "user_is_ambiguous",
        "Boolean indicating if the user is of ambiguous gender",
        "true or false",
        (user, character) => user.gender.toLowerCase() === "ambiguous",
    ],
    [
        "char_is_male",
        "Boolean indicating if the character is male",
        "true or false",
        (user, character) => character.gender.toLowerCase() === "male",
    ],
    [
        "char_is_female",
        "Boolean indicating if the character is female",
        "true or false",
        (user, character) => character.gender.toLowerCase() === "female",
    ],
    [
        "char_is_ambiguous",
        "Boolean indicating if the character is of ambiguous gender",
        "true or false",
        (user, character) => character.gender.toLowerCase() === "ambiguous",
    ],
    [
        "user_sex_is_male",
        "Boolean indicating if the user sex is male",
        "true or false",
        (user, character) => user.sex.toLowerCase() === "male",
    ],
    [
        "user_sex_is_female",
        "Boolean indicating if the user sex is female",
        "true or false",
        (user, character) => user.sex.toLowerCase() === "female",
    ],
    [
        "user_sex_is_intersex",
        "Boolean indicating if the user sex is intersex",
        "true or false",
        (user, character) => user.sex.toLowerCase() === "intersex",
    ],
    [
        "char_sex_is_male",
        "Boolean indicating if the character sex is male",
        "true or false",
        (user, character) => character.sex.toLowerCase() === "male",
    ],
    [
        "char_sex_is_female",
        "Boolean indicating if the character sex is female",
        "true or false",
        (user, character) => character.sex.toLowerCase() === "female",
    ],
    [
        "char_sex_is_intersex",
        "Boolean indicating if the character sex is intersex",
        "true or false",
        (user, character) => character.sex.toLowerCase() === "intersex",
    ],
];

export const party = [
    [
        "party",
        "The list of party members",
        "eg. [Arya, Thalon, Mira]",
        (user, character, party) => party.members.map(member => member.name),
    ],
    [
        "party_present_members",
        "The list of present party members",
        "eg. [Arya, Thalon]",
        (user, character, party) => party.members.filter(member => member.isPresent).map(member => member.name),
    ],
    [
        "party_leftbehind_members",
        "The list of left behind party members",
        "eg. [Mira]",
        (user, character, party) => party.members.filter(member => !member.isPresent).map(member => member.name),
    ],
    [
        "party_currentlylost_members",
        "The list of members that got lost after being left behind (known to this member)",
        "eg. [Mira]",
        (user, character, party) => party.members.filter(member => !member.isPresent && member.isLost && member.isKnownToBeLostBy.includes(character)).map(member => member.name),
    ],
    [
        "party_ex_members",
        "The list of ex-party members",
        "eg. [Dorian]",
        (user, character, party) => party.exMembers.map(member => member.name),
    ],
    [
        "non_party_members_at_location",
        "The list of non-party members available in the current location of the world",
        "eg. [Luna, Kiro]",
        (user, character, party) => party.nonMembersAtLocation.map(member => member.name),
    ],
    [
        "non_party_members_at_world",
        "The list of all characters available in the world, including the party itself",
        "eg. [Arya, Thalon, Mira, Dorian, Luna, Kiro]",
        (user, character, party) => party.worldMembers.map(member => member.name),
    ]
];

export const world = [
    [
        "current_location",
        "The name of the current location",
        "eg. Eldoria, Shadowfen",
        (user, character, party, world) => world.currentLocation.name,
    ],
    [
        "in_journey_world",
        "Boolean indicating if the party is currently in a journey",
        "true or false",
        (user, character, party, world) => world.inJourney,
    ],
    [
        "journey_destination",
        "The name of the journey destination",
        "eg. Eldoria, Shadowfen",
        (user, character, party, world) => world.inJourney ? world.journey.destination : "",
    ],
    [
        "journey_origin",
        "The name of the journey origin",
        "eg. Eldoria, Shadowfen",
        (user, character, party, world) => world.inJourney ? world.journey.origin : "",
    ],
    [
        "journey_completed",
        "Boolean indicating if the journey has been completed",
        "true or false",
        (user, character, party, world) => world.inJourney ? world.journey.isCompleted : false,
    ],
    [
        "current_in_vehicle",
        "Boolean indicating if the party is currently in a vehicle",
        "true or false",
        (user, character, party, world) => world.currentLocation.isVehicle,
    ],
    [
        "current_in_vehicle_long_distance",
        "Boolean indicating if the party is currently in a long-distance capable vehicle",
        "true or false",
        (user, character, party, world) => world.currentLocation.isVehicle && world.currentLocation.isLongDistance,
    ],
    [
        "current_is_safe_location",
        "Boolean indicating if the current location is a safe location",
        "true or false",
        (user, character, party, world) => world.currentLocation.isSafe,
    ]
];

export const utils = [
    [
        "is_male character",
        "Boolean indicating if the character is male",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.gender.toLowerCase() === "male";
                }
            }
            return false;
        }
    ],
    [
        "is_female character",
        "Boolean indicating if the character is female",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.gender.toLowerCase() === "female";
                }
            }
            return false;
        }
    ],
    [
        "is_ambiguous character",
        "Boolean indicating if the character is of ambiguous gender",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.gender.toLowerCase() === "ambiguous";
                }
            }
            return false;
        }
    ],
    [
        "is_sex_male character",
        "Boolean indicating if the character sex is male",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.sex.toLowerCase() === "male";
                }
            }
            return false;
        }
    ],
    [
        "is_sex_female character",
        "Boolean indicating if the character sex is female",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.sex.toLowerCase() === "female";
                }
            }
            return false;
        }
    ],
    [
        "is_sex_intersex character",
        "Boolean indicating if the character sex is intersex",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyone) {
                if (member.name == characterQuestioned) {
                    return member.reference.sex.toLowerCase() === "intersex";
                }
            }
            return false;
        }
    ],
    [
        "is_member character",
        "Boolean indicating if the character is a member of the party",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.members) {
                if (member.name == characterQuestioned) {
                    return true;
                }
            }
            return false;
        }
    ],
    [
        "is_present_member character",
        "Boolean indicating if the character is a present member of the party",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.members) {
                if (member.name == characterQuestioned) {
                    return member.isPresent;
                }
            }
            return false;
        }
    ],
    [
        "is_leftbehind_member character",
        "Boolean indicating if the character is a left behind member of the party",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.members) {
                if (member.name == characterQuestioned) {
                    return !member.isPresent;
                }
            }
            return false;
        }
    ],
    [
        "is_currentlylost_member character",
        "Boolean indicating if the character is a member that got lost after being left behind (known to this member)",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.members) {
                if (member.name == characterQuestioned) {
                    return !member.isPresent && member.isLost && member.isKnownToBeLostBy.includes(character);
                }
            }
            return false;
        }
    ],
    [
        "is_non_member character",
        "Boolean indicating if the character is a non-member available in the current location of the world",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.nonMembers) {
                if (member.name == characterQuestioned) {
                    return true;
                }
            }
            return false;
        }
    ],
    [
        "is_ex_member character",
        "Boolean indicating if the character is an ex-member of the party",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.exMembers) {
                if (member.name == characterQuestioned) {
                    return true;
                }
            }
            return false;
        }
    ],
    [
        "is_at_location character",
        "Boolean indicating if the character is at the current location of the world",
        "true or false",
        (user, character, party, world, characterQuestioned) => {
            if (!characterQuestioned) return false;
            for (const member of party.everyoneAtLocation) {
                if (member.name == characterQuestioned) {
                    return true;
                }
            }
            return false;
        }
    ],
    [
        "size list",
        "The size of the list",
        "eg. 3",
        (user, character, party, world, list) => {
            if (!list || !Array.isArray(list)) return 0;
            return list.length;
        }
    ],
    [
        "intersect list1 list2",
        "intersects two lists",
        "eg. [Arya, Thalon]",
        (user, character, party, world, list1, list2) => {
            if (!list1 || !Array.isArray(list1)) return [];
            if (!list2 || !Array.isArray(list2)) return [];
            return list1.filter(value => list2.includes(value));
        }
    ],
    [
        "union list1 list2",
        "unites two lists",
        "eg. [Arya, Thalon, Mira]",
        (user, character, party, world, list1, list2) => {
            if (!list1 || !Array.isArray(list1)) return [];
            if (!list2 || !Array.isArray(list2)) return [];
            return Array.from(new Set([...list1, ...list2]));
        }
    ],
    [
        "difference list1 list2",
        "difference between two lists",
        "eg. [Arya]",
        (user, character, party, world, list1, list2) => {
            if (!list1 || !Array.isArray(list1)) return [];
            if (!list2 || !Array.isArray(list2)) return [];
            return list1.filter(value => !list2.includes(value));
        }
    ],
    [
        "format_and list",
        "formats a list with commas and 'and'",
        "eg. Arya, Thalon, and Mira",
        (user, character, party, world, list) => {
            if (!list || !Array.isArray(list)) return "";
            if (list.length === 0) return "";
            if (list.length === 1) return list[0];
            if (list.length === 2) return `${list[0]} and ${list[1]}`;
            return `${list.slice(0, -1).join(', ')}, and ${list[list.length - 1]}`;
        }
    ],
    [
        "fomat_or list",
        "formats a list with commas and 'or'",
        "eg. Arya, Thalon, or Mira",
        (user, character, party, world, list) => {
            if (!list || !Array.isArray(list)) return "";
            if (list.length === 0) return "";
            if (list.length === 1) return list[0];
            if (list.length === 2) return `${list[0]} or ${list[1]}`;
            return `${list.slice(0, -1).join(', ')}, or ${list[list.length - 1]}`;
        }
    ]
];