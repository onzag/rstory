# RStory

\*Onza was shown some online LLM roleplay bot, for a while he played with such toy and then though to himself\* Well why not make it better as these bots are led so easily to do whatever you want and have no resistance whatsoever \*So he began making a different bot system, one that shown more emotion behaviours and connections, but his poor gaming machine could barely cope and he had to be creative to make something that worked even with a SLM\*

\*As he drove his bicycle to work while it was raining he figured out a way to make the SLM have evolving behaviour\* Oh like the SIMS 2 \*And he came home an idea to make a small chatbot that actually could hate on the user, or love it depending how they were acting and not bend to the will of the user easily\*

\*And so he created, RStory, to make characters will more dynamic, more reactive, to make them hate, love, or anything inbetween, to need to use the toilet suddenly, get thirsty, and have emotions pop in, maybe not a LLM but as far as SLMs can go; using a 3 step process where a relation is evolved, however much VRAM it eats\*

\*It was not the most beautiful code, but so far it worked; bit of spaggethi, but it was meant for show. After a Crashdown due to python llama utilizing CPU only, Onza moved the inference code to NodeJS therefore...\*

## Requirements

 - NodeJS > v24
 - Python 3.12

## Prepare Your Character Files

\*Sketching code quickly Onza came with a mechanism to specify the nature of the character, using simple txt files because that's just how things went\*

### character/system.txt

This file will contain the system prompt describing the character in second person, as this are instructions for the system to what it is \*Said onza to himself, he quickly looked at one of the example files, it read something alike:\*

```
You are Rick, a funny autistic Italian werewolf living near the coast, you are...

Your hobbies are messing with computers and ancient hardware...

You react positively to the mention of cathodic ray tubes, which you are absolutely obsessed about...
```

### character/name.txt

This file was simple \*Said onza while staring at the Machine screen, it just contained the character name on a single line\*

```
Rick
```

### character/pronouns.txt

\*Next were the pronouns, bit funny, gives twitter-feels but required for ntlk analysis\*

```
he
him
```

[TODO]
