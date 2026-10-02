# Local model tooling

Run Claude Code on a local model, and let Claude sessions hand bounded tasks to it. Claude keeps every decision; the local model does steps whose result Claude can check cheaply (`methodology-local-delegation.md`).

- `serve.sh`, `profile.sh`, `profile`: start, stop and configure the local llama.cpp server (model, context size, KV cache; idle unload). It won't load while another program (a game) is using the GPU, unloads when one starts, and `touch ~/local-llm/.disabled` keeps it off.
- `claude-local`: Claude Code on the local model, with its own config folder. It builds the methodology without the scripts' source (`build-local-methodology.sh`), adds `local-model-overrides.md` and the built-in prompt `local-model-prompt.md`, and stops the server when no local session is left (`serve.sh reap` covers a killed wrapper).
- `local-agent <mode> <ticket.md>`: a ticket for the local model, run headless in a sandbox (`sandbox/`: network for reading docs and source, no credentials, a fake `gh`). Modes: `facts`, `evidence`, `reproduce`, `run`, `implement`, `cold-read`. Its whole instructions are `delegate-instructions.md`.
- `claude-usage`: usage of every `claude-swap` account; `claude-usage --mode` prints the delegation level (`delegation.conf`).
- `templates/`: the chat template, changed to accept the system message Claude Code sends mid-conversation.
- `eval/bin/`: replay a real task in the sandbox and compare models or methodology versions. `new-run <task> [arm]` copies `~/local-llm-eval/templates/<task>/` (`ws/` a git checkout cut at the task's time, `prompt.md`, optional `gh-snapshot/`) and runs the agent with the installed methodology or `methodology-<arm>.md`; `queue` runs several in turn, `show-run` summarizes one. Tasks and their graders are your own.

Setup: build llama.cpp into `~/local-llm/build`, so `build/bin/llama-server` exists (PrismML-Eng/llama.cpp, branch `prism`, runs both profiles; the bonsai profile's PQ2_0 needs it).
Put the weights `profile.sh` names (the model and its `mmproj` file) into `~/local-llm/weights/`.

`install.sh` copies all of this into `~/local-llm` and `~/local-llm-eval` and links the commands into `~/.local/bin`.
