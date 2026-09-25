# ai-terminal Bash integration
# Safe, fail-open shell hooks for Bash

# Check if ai command exists
if ! command -v ai >/dev/null 2>&1; then
    return 0 2>/dev/null || exit 0
fi

# 1. Native Tab Completion function for 'ai' command
_ai_bash_completion() {
    local cur prev words cword
    _init_completion -n : 2>/dev/null || {
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
    }

    local candidates
    candidates=$(ai complete --shell bash --buffer "$COMP_LINE" --cursor "$COMP_POINT" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$candidates" ]; then
        COMPREPLY=( $(compgen -W "$candidates" -- "$cur") )
    fi
}
complete -F _ai_bash_completion ai 2>/dev/null || true

# 2. Smart Suggestion Keybinding (Ctrl-G)
_ai_bash_suggest_widget() {
    local selected
    selected=$(ai suggest --shell-insert 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$selected" ]; then
        READLINE_LINE="$selected"
        READLINE_POINT=${#READLINE_LINE}
    fi
}
# Bind Ctrl-G in bash readline if supported
if [[ $- == *i* ]]; then
    bind -x '"\C-g": _ai_bash_suggest_widget' 2>/dev/null || true
fi

# 3. Post-command hook to track command events and errors
_ai_last_command=""
_ai_bash_preexec() {
    _ai_last_command="$BASH_COMMAND"
}

_ai_bash_postcommand() {
    local exit_code=$?
    # Ignore empty or assistant commands
    if [ -z "$_ai_last_command" ] || [[ "$_ai_last_command" == ai* ]] || [[ "$_ai_last_command" == _ai* ]]; then
        return 0
    fi

    # Record event in background without blocking shell
    (ai record --command "$_ai_last_command" --exit "$exit_code" >/dev/null 2>&1 &)
    _ai_last_command=""
}

# Attach to DEBUG trap and PROMPT_COMMAND safely
if [[ $- == *i* ]]; then
    trap '_ai_bash_preexec' DEBUG 2>/dev/null || true
    if [[ ! "$PROMPT_COMMAND" =~ _ai_bash_postcommand ]]; then
        PROMPT_COMMAND="_ai_bash_postcommand${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
    fi
fi
