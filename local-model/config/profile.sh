# The model, sourced by serve.sh, claude-local and the sandbox. Sizes and speeds were measured on one 16 GB GPU with the
# desktop using ~1.2 GB, leaving 1 GB of VRAM free at peak (prompt processing included); re-measure for yours.
_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LLM_PROFILE=gsq  # the name serve.sh uses to notice a changed setup
# Qwen3.8-27B, GSQ-RCO IQ3_XXS (ISTA-DASLab) with its MTP head, 4-bit KV (128K loads at 14.8 GB).
# K and V must have the same type: mixed types lose the fast kernels (68 tok/s decode, ~40 tok/s prompt).
LLM_MODEL="Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf"
LLM_ARGS=(-ctk q4_0 -ctv q4_0 --spec-type draft-mtp --mmproj "$_dir/weights/mmproj-gsq-Qwen3.8-27B-BF16.gguf")
# Thinking cap: past LLM_THINK_BUDGET tokens the server ends the thinking with the message below and the model answers.
# Uncapped, it spiralled (7.3K thinking tokens, 98 s, for a 4-sentence code review); at 1024 the same review took 12 s with
# the same finding. -1 turns the cap off.
LLM_ARGS+=(--reasoning-budget "${LLM_THINK_BUDGET:-1024}" --reasoning-budget-message "Thinking budget reached. Stop thinking and act now with what you have.")
# Vision (screenshots the agent takes and reads): the projector runs on the CPU, so it costs no VRAM.
LLM_ARGS+=(--no-mmproj-offload)
# Server context window. claude-local compacts at LLM_COMPACT, below it: the compaction request itself (the whole
# conversation plus the summarizer's prompt and summary) must fit in the window, so the trigger can't sit at its
# edge — at the edge it overflows and the session dies with "Prompt is too long · automatic compaction failed".
LLM_CTX="${LLM_CTX:-131072}"  # user decision 2026-10-03: 128K, so the GPU holds only what sessions use
LLM_COMPACT=$(( LLM_CTX * 3 / 4 ))  # 96K: the compaction request (~96K in + prompt + summary) must fit in the window
