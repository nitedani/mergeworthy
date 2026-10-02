# Model profiles, sourced by serve.sh, claude-local and the sandbox. Pick one with LLM_PROFILE=<name>, or write the name
# into ~/local-llm/profile (one word) to change the default. Sizes and speeds were measured on one 16 GB GPU with the
# desktop using ~1.2 GB, leaving 1 GB of VRAM free at peak (prompt processing included); re-measure for yours.
_dir="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LLM_PROFILE="${LLM_PROFILE:-$(cat "$_dir/profile" 2>/dev/null || echo gsq)}"
case "$LLM_PROFILE" in
  gsq)
    # Qwen3.8-27B, GSQ-RCO IQ3_XXS (ISTA-DASLab) with its MTP head: 160K at 4-bit KV peaks at 15.05 GB, 132 tok/s.
    # K and V must have the same type: mixed types lose the fast kernels (68 tok/s decode, ~40 tok/s prompt).
    LLM_MODEL="Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf"; LLM_CTX_DEFAULT=163840
    LLM_ARGS=(-ctk q4_0 -ctv q4_0 --spec-type draft-mtp --mmproj "$_dir/weights/mmproj-gsq-Qwen3.8-27B-BF16.gguf") ;;
  bonsai)
    # PrismML Ternary-Bonsai-2-27B PQ2_0: 192K at 8-bit KV peaks at ~15.0 GB, 89 tok/s.
    LLM_MODEL="Ternary-Bonsai-2-27B-PQ2_0.gguf"; LLM_CTX_DEFAULT=196608
    LLM_ARGS=(-ctk q8_0 -ctv q8_0 --mmproj "$_dir/weights/mmproj-bonsai-Q8_0.gguf") ;;
  *) echo "unknown LLM_PROFILE '$LLM_PROFILE' (gsq, bonsai)" >&2; return 1 2>/dev/null || exit 1 ;;
esac
# Vision (screenshots the agent takes and reads): the projector runs on the CPU, so it costs no VRAM.
LLM_ARGS+=(--no-mmproj-offload)
LLM_CTX="${LLM_CTX:-$LLM_CTX_DEFAULT}"
