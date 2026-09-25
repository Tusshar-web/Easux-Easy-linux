"""
Tests for secret, token, and credential redaction.
"""

from ai_terminal.safety.redactor import redact_secrets


def test_redact_private_key():
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1W9Z\n"
        "randomcharactersandkeys\n"
        "-----END RSA PRIVATE KEY-----"
    )
    redacted = redact_secrets(pem)
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "MIIEowIBAAKCAQEA0Y1W9Z" not in redacted


def test_redact_github_token():
    cmd = "curl -H 'Authorization: token ghp_1234567890abcdefghijklmnopqrstuvwxyz' https://api.github.com"
    redacted = redact_secrets(cmd)
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted


def test_redact_aws_key():
    cmd = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
    redacted = redact_secrets(cmd)
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted


def test_redact_bearer_token():
    text = "curl -H 'Authorization: Bearer secret_bearer_token_value_here' https://example.com"
    redacted = redact_secrets(text)
    assert "Bearer [REDACTED_TOKEN]" in redacted
    assert "secret_bearer_token_value_here" not in redacted


def test_redact_password_assignment():
    text = "mysql -u root -ppassword1234 -e 'SHOW DATABASES;'"
    text_env = 'export DB_PASSWORD="super_secret_password_here"'
    redacted = redact_secrets(text_env)
    assert "[REDACTED_SECRET]" in redacted
    assert "super_secret_password_here" not in redacted
