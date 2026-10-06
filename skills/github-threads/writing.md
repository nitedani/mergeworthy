# Writing to people

Read this before drafting any comment, reply or message. A comment is a conversation with a colleague, not a document: write it the way you'd say it across the desk. (PR bodies, reports and specs are documents; they may use structure.)

## Draft by talking

1. Before writing, say to yourself what you'd tell this person if they were sitting next to you: what you found, what you think, what you need from them. Write that down.
2. Read the draft out loud. Anything you wouldn't say to a colleague goes, and gets replaced with what you would say.
3. If a passage can't be fixed sentence by sentence, explain it out loud to an imagined friend and replace the passage with what you said.

## How a good colleague writes

- **Start from their words.** Say back what they asked or proposed, and what you agree with, before your view. "You're right that X. Where I'd go further is Y, because Z."
- **Your view, with its reason.** "I'd do X because Y." Take a position; a reply that only reports findings leaves the thinking to them.
- **The best comment has done the work:** "X breaks because Y, so I did Z. What do you think?"
- **Ask only what needs their decision,** once, at the end, in plain words: "Should vike(app) also catch X?", never a heading over a list of options.
- **Courtesy that's real:** thank them for a real catch, say sorry when you got something wrong ("I was wrong about X: Y"), never "obviously" or "clearly".
- **Concrete over abstract.** Name the file, the call, the number, the framework. Show a design choice as the code the user writes under each option.

## What reads as machine-written, and the fix

| Pattern | Instead |
|---|---|
| A label line or heading in a comment ("Two decisions:", "The question.", "**Fundamental:** the wrong word.") | A sentence: "Two things need your decision." / "I agree, it's the wrong word." |
| Em dashes for asides | A comma, parentheses, or two sentences |
| Groups of three ("fast, simple and robust") | The one or two that matter |
| "Not X, but Y" / "It's not X. It's Y." | Say what is: "The context changed." |
| A question you answer yourself ("What does this mean? It means…") | The answer |
| Dramatic setups ("Here's the thing:", "The result?") | Start with the substance |
| Inflated importance ("crucial", "pivotal", "significant impact") | The fact that shows it: "it returned a 500 on every POST" |
| Blanket hedging ("may potentially", "it seems") | Say what happens, and hedge only what you didn't check, with why |
| Stiff transitions ("Furthermore", "Moreover", "That being said") | "And", "but", "so", or none |
| Every paragraph the same shape and length, each ending on a neat summary | Let length follow the content; stop when the point is made |
| Bold on concepts, inline headers, bullet points for reasoning | Plain prose for reasoning; bullets only for parallel items |
| Fancy verbs ("leverage", "utilize", "facilitate", "delve") | use, help, look at |

## Before posting

Read it as the person you're writing to: would they feel spoken to by a colleague who did the work and thought about it, or handed a report? Would a newcomer who finds the thread later follow it? Rewrite until both answers are yes.
