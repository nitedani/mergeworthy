# The model, sourced by serve.sh, claude-local and the sandbox. Sizes and speeds were measured on one 16 GB GPU with the
# desktop using ~1.2 GB, leaving 1 GB of VRAM free at peak (prompt processing included); re-measure for yours.
_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LLM_PROFILE=gsq  # the name serve.sh uses to notice a changed setup
# Qwen3.8-27B, GSQ-RCO IQ3_XXS (ISTA-DASLab) with its MTP head, 4-bit KV (160K peaked at 15.05 GB; 128K needs less).
# K and V must have the same type: mixed types lose the fast kernels (68 tok/s decode, ~40 tok/s prompt).
LLM_MODEL="Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf"
LLM_ARGS=(-ctk q4_0 -ctv q4_0 --spec-type draft-mtp --mmproj "$_dir/weights/mmproj-gsq-Qwen3.8-27B-BF16.gguf")
# Thinking cap: past LLM_THINK_BUDGET tokens the server ends the thinking with the message below and the model answers.
# Uncapped, it spiralled (7.3K thinking tokens, 98 s, for a 4-sentence code review); at 1024 the same review took 12 s with
# the same finding. -1 turns the cap off.
LLM_ARGS+=(--reasoning-budget "${LLM_THINK_BUDGET:-1024}" --reasoning-budget-message "Thinking budget reached. Stop thinking and act now with what you have.")
# Vision (screenshots the agent takes and reads): the projector runs on the CPU, so it costs no VRAM.
LLM_ARGS+=(--no-mmproj-offload)
LLM_CTX="${LLM_CTX:-131072}"  # 128K; claude-local compacts at this same size, so the server never holds unused context
