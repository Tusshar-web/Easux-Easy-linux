from setuptools import setup, find_packages

setup(
    name="ai-terminal",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ai=ai_terminal.cli:main",
        ],
    },
)
