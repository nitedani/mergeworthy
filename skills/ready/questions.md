# The questions

Each brief gives the reader: the base and head SHAs to read at, the area it covers, the decisions already made (not to reopen), one question below, and its evidence rule. A reader that finds nothing says what it searched. A reader that confirms nearly every suspicion it started with was building a case, not reading.

## bug

Through documented use, does the head behave wrongly where a user can see it?
Evidence: a script or test that fails on the head and passes on the base, traced to documented use on both ends. List every candidate you dropped, with why.

## shape

If this area were designed today from a map of all of it, what shape would it have, and which behavior-preserving moves toward that shape are worth their diff?
Evidence: a map of every file and function in the area (what it decides, its inputs, outputs and state). A claim that a layer is missing a check holds only after searching every layer for an owner of that behavior. A change in behavior or public surface goes to the owner as a decision.

## earn

What in this diff doesn't earn its place: a mechanism with no named user scenario, dead or speculative surface, duplicated intent, redundant tests, comments that narrate or justify?
Evidence: each finding with its location and its price in lines. A removal comes with a probe that could fail, run through real use.

## read

Reading the diff top to bottom as a person would, where do they stumble: a name that doesn't match its behavior, a function at the wrong level or on the wrong side of a boundary, needless indirection, logic written twice?
Evidence: every file and function rated 0 to 10 with a reason, then a separate list confirming each was rated. Mostly 10s means the reading was shallow.

## preserved

Does the head still behave like the tree before the structural commits?
Evidence: the old tests run on the new code, adapting only renames, and the same scenarios run on both trees with their outputs compared.

## review

Does the final head do what the issue asks, safely, within the repo's standards?
Evidence: revert the fix and confirm the failure returns; quote every asked-for behavior that is missing or only partly there. Tag each claim observed (file and line, or command and output), inferred, or unknown; only observed closes anything.

## claims

Is every sentence in the PR body and its notes true of the final head?
Evidence: each claim matched to the head SHA, the gate or CI run it cites, or the screenshot that shows it.
