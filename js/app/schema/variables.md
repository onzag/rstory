# Variables (General)

{{user}}                                                Connor          yes
{{char}}                                                Sasha           no
{{user_pronoun}}                                        he              yes
{{user_possesive}}                                      his             yes
{{user_object_pronoun}}                                 his             yes
{{user_3rd_person_pronoun}}                             him             yes
{{user_conjugation_verb}}                               is              yes
{{user_female_pres}}                                    false           yes
{{user_male_pres}}                                      true            yes
{{user_amb_pres}}                                       false           yes
{{user_male}}                                           true            yes
{{user_female}}                                         false           yes
{{user_intersex}}                                       false           yes
{{char_pronoun}}                                        she             no
{{char_possesive}}                                      her             no
{{char_object_pronoun}}                                 hers            no
{{char_3rd_person_pronoun}}                             her             no
{{char_conjugation_verb}}                               is              no
{{char_female_pres}}                                    true            no
{{char_male_pres}}                                      false           no
{{char_amb_pres}}                                       false           no
{{char_male}}                                           false           no
{{char_female}}                                         true            no
{{char_intersex}}                                       false           no

# Party
{{party_present_members}}                               ["connor", "sasha", "joe"]
yes

party_left_behind_members                               ["fred"]
no

{{party_left_behind_members_info}}                      [{member: "fred", "location": "krakov downtown", "known_to_be_lost": false, known_by_char: true}]
no

{{party_all_members}}                                   connor, sasha, joe, fred
no

{{party_gone_members}}
no

{{party_known_lost_members}}
no

{{non_party}}                                           vue, cat
yes

# Location (NO)
{{in_journey_setting}}                                  true
{{in_domestic_setting}}                                 false
{{all_loc}}                                             inside car, inside camper, krakov downtown, warsaw, kaunas
{{all_journey_loc}}                                     krakov downtown, warsaw, kaunas
{{all_unvisited_journey_loc}}                           warsaw, kaunas
{{current_loc}}                                         krakov downtown
{{initial_journey_loc}}                                 krakov downtown
{{final_journey_loc}}                                   kaunas
{{next_journey_loc}}                                    warsaw
{{next_loc}}                                            inside the car
{{next_loc_ready}}                                      true            # there may not be a chosen next location yet
{{next_loc_is_journey_loc}}                             false           # the next location may be a journey location

# Special modifiers

is_0                bool        list
is_1                bool        list
is_2                bool        list
is_3                bool        list
is_4                bool        list
is_5                bool        list
is_0_or_more        bool        list
is_1_or_more        bool        list
is_2_or_more        bool        list
is_3_or_more        bool        list
is_4_or_more        bool        list
is_5_or_more        bool        list
pronoun             str         list
possesive           str         list
object_pronoun      str         list
object_possesive    str         list
and                 str         list
or                  str         list
not                 bool        bool
union               list        list,list
intersection        list        list,list
difference          list        list,list