# ai-terminal Zsh integration
# Safe, fail-open shell hooks for Zsh

if ! command -v ai >/dev/null 2>&1; then
    return 0 2>/dev/null || exit 0
fi

# 1. Native Zsh completion
_ai_zsh_completion() {
    local -a candidates
    local output
    output=$(ai complete --shell zsh --buffer "$BUFFER" --cursor "$CURSOR" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$output" ]; then
        local -a desc_list
        while IFS= read -r line; do
            [ -n "$line" ] && desc_list+=("$line")
        done <<< "$output"
        _describe 'commands' desc_list
    fi
}
compdef _ai_zsh_completion ai 2>/dev/null || true

# 2. ZLE Widget for Smart Suggestions (Ctrl-G)
_ai_zsh_suggest_widget() {
    local selected
    selected=$(ai suggest --shell-insert 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$selected" ]; then
        BUFFER="$selected"
        CURSOR=${#BUFFER}
    fi
    zle reset-prompt 2>/dev/null || true
}
zle -N _ai_zsh_suggest_widget 2>/dev/null || true
bindkey '^G' _ai_zsh_suggest_widget 2>/dev/null || true

# 3. Zsh preexec and precmd hooks for error/history logging
_ai_zsh_last_cmd=""

_ai_zsh_preexec() {
    _ai_zsh_last_cmd="$1"
}

_ai_zsh_precmd() {
    local exit_code=$?
    if [ -z "$_ai_zsh_last_cmd" ] || [[ "$_ai_zsh_last_cmd" == ai* ]]; then
        return 0
    fi

    (ai record --command "$_ai_zsh_last_cmd" --exit "$exit_code" >/dev/null 2>&1 &)
    _ai_zsh_last_cmd=""
}

autoload -Uz add-zsh-hook 2>/dev/null || true
if typeset -f add-zsh-hook >/dev/null; then
    add-zsh-hook preexec _ai_zsh_preexec 2>/dev/null || true
    add-zsh-hook precmd _ai_zsh_precmd 2>/dev/null || true
fi
