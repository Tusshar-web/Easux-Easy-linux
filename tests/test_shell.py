"""
Tests for shell hooks, scripts, and installer.
"""

from ai_terminal.shell.installer import (
    get_init_script,
    install_hook,
    uninstall_hook,
    inspect_status,
    SHELL_MARKER_START,
)


def test_get_init_scripts():
    bash_script = get_init_script("bash")
    assert "_ai_bash_completion" in bash_script
    assert "complete -F" in bash_script

    zsh_script = get_init_script("zsh")
    assert "_ai_zsh_completion" in zsh_script
    assert "compdef" in zsh_script


def test_install_and_uninstall_lifecycle(temp_dir):
    rc_file = temp_dir / ".bashrc"
    rc_file.write_text("# Existing user bashrc\nexport FOO=bar\n")

    # 1. Inspect initial status
    st0 = inspect_status("bash", custom_rc=rc_file)
    assert st0["installed"] is False

    # 2. Install
    ok, msg = install_hook("bash", custom_rc=rc_file)
    assert ok is True
    content = rc_file.read_text()
    assert SHELL_MARKER_START in content
    assert "export FOO=bar" in content  # Preserved unrelated content!

    st1 = inspect_status("bash", custom_rc=rc_file)
    assert st1["installed"] is True

    # 3. Idempotent install
    ok_idem, _ = install_hook("bash", custom_rc=rc_file)
    assert ok_idem is True

    # 4. Uninstall
    ok_un, msg_un = uninstall_hook("bash", custom_rc=rc_file)
    assert ok_un is True
    content_un = rc_file.read_text()
    assert SHELL_MARKER_START not in content_un
    assert "export FOO=bar" in content_un  # Still preserved!

    st2 = inspect_status("bash", custom_rc=rc_file)
    assert st2["installed"] is False
