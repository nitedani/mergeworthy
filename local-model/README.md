# Local model tooling

Run Claude Code on a local model, and let Claude sessions hand it bounded tasks. Claude keeps every decision; the local model does steps whose result Claude can check cheaply. How and when: [DELEGATION.md](DELEGATION.md).

| Folder | What's in it |
| --- | --- |
| `bin/` | `serve.sh` (start, stop and watch the llama.cpp server), `claude-local` (Claude Code on the local model), `local-agent` (hand it a ticket), `claude-usage` (subscription usage and the delegation level) |
| `config/` | `profile.sh` (the model, context size, KV cache), `delegation.conf` (when to delegate more), `chat-template.jinja` (the model's template, changed to accept the system message Claude Code sends mid-conversation) |
| `prompts/` | `claude-local-overrides.md` and `claude-local-prompt.md` (what a `claude-local` session gets on top of the methodology), `ticket-agent.md` (a ticket agent's whole instructions) |
| `skills/` | One file per `local-agent` mode: what it's for, the agent's instructions, the ticket sections it needs |
| `sandbox/` | The sandbox every ticket runs in: network for reading docs and source, no credentials, a fake `gh` |
| `eval/bin/` | Replay a real task in the sandbox to compare models or methodology versions (`new-run <task> [arm]`, `queue`, `show-run`); the tasks are your own |

The model: Qwen3.8-27B GSQ-RCO IQ3_XXS with its MTP head, 160K context at 4-bit KV (Claude Code compacts at about 113K), on one 16 GB NVIDIA GPU.

Setup:
1. Build [PrismML-Eng/llama.cpp](https://github.com/PrismML-Eng/llama.cpp) (branch `prism`) with CUDA into `~/local-llm/build`, so `build/bin/llama-server` exists. Upstream llama.cpp supports the same flags, but on this setup its prebuilt Linux binary needs glibc 2.38 and its Docker image ran 25× slower (1.9 vs 49.6 tok/s, the VRAM didn't fit through Docker Desktop).
2. Put the model and its `mmproj` file that `config/profile.sh` names into `~/local-llm/weights/`.
3. Run `install.sh`: it copies `bin/`, `config/` and `prompts/` flat into `~/local-llm`, `skills/` and `sandbox/` as folders, `eval/` into `~/local-llm-eval`, and links `claude-local`, `local-agent` and `claude-usage` into `~/.local/bin`.

The server never loads while another program (a game) is using the GPU, unloads when one starts, and `touch ~/local-llm/.disabled` keeps it off.
