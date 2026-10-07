# Writing to people

Read this before drafting anything posted to GitHub (comments, replies, PR and issue bodies) or sent to the user. Write it the way you'd say it to a colleague across the desk. A PR or issue body may use structure, and where `pull-request` or `open-issue` sets its form, that wins.

## Draft by talking

1. Before writing, say to yourself what you'd tell this person if they were sitting next to you: what you found, what you think, what you need from them. Write that down.
2. Read the draft out loud, as the person you're writing to. Anything you wouldn't say to a colleague goes, and gets replaced with what you would say; a newcomer who finds it later must still follow it.
3. If a passage can't be fixed sentence by sentence, explain it out loud to an imagined friend and replace the passage with what you said.

## How a good colleague writes

Every post brings the reader something they didn't have: a finding, a measurement, a better option, a risk, or a decision with its reason. If it wouldn't, think more first.

- **Start from their words.** Quote each point you answer (`> their words`), in their order; say what you agree with before your view.
- **Verdict first, then your view with its reason,** in the order the reader would think it: "I'd do X because Y." Take a position; a reply that only reports findings leaves the thinking to them.
- **The best comment has done the work:** "X breaks because Y, so I did Z. What do you think?"
- **Ask only what needs their decision,** once, at the end, as a plain question a yes or no answers.
- **Full sentences joined by bridges** ("because", "so", "but"), never a label and a fragment; prose for reasoning, lists only for parallel items.
- **Write for a newcomer who finds the thread later:** name each thing plainly where it first appears; no internal labels, no "it" with two meanings.
- **Concrete over abstract:** the file, the call, the number, the framework; show a design choice as the code the user writes under each option.
- **Courtesy that's real:** thank them for a real catch; when you change your mind, say so in one line ("I was wrong about X: Y"); never "obviously".
- **As short as a newcomer can still follow:** clarity comes from one example and the word that links two points, not from more words.

## A reply that carries the load

A maintainer asked whether a design has holes; the user picked this answer:

> It's built! I kept poking at `vike(app)` as the single injection point while implementing it, and it held up. #3557 is the Vike side, ready for your review, and vikejs/vike-server-adapters#10 is the adapter side.
>
> The only real catch I hit: Universal Middleware's router checks a `+middleware`'s `path` against the raw URL, but Vike routes on the decoded one. So an auth `+middleware` with `path: '/dash'` never runs for `/%64ash`. I'd rather fix that at the root than work around it in Vike, so magne4000/universal-middleware#385 decodes the path.

A person talking, verdict first, the one finding with what you do about it, nothing they don't act on.

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
| A telegraphic verdict ("No holes, and it's built.") | A person talking, as in the reply above |
| A word that means something else in the reader's project ("guard" to a Vike maintainer, who has a `+guard` hook) | The exact thing: "a `+middleware` with `path: '/dash'`" |
