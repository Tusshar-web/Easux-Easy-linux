"""
Tests for context detection and manifest parsers.
"""

from ai_terminal.context.manifests import (
    parse_package_json,
    parse_makefile,
    parse_python_project,
    parse_docker_project,
)
from ai_terminal.context.detector import ProjectDetector


def test_parse_package_json(temp_dir):
    pkg_file = temp_dir / "package.json"
    pkg_file.write_text('{"name": "my-app", "scripts": {"dev": "vite", "test": "jest"}}')

    info = parse_package_json(pkg_file)
    assert info is not None
    assert info["name"] == "my-app"
    assert "dev" in info["scripts"]
    assert "test" in info["scripts"]


def test_parse_makefile(temp_dir):
    mf = temp_dir / "Makefile"
    mf.write_text("all:\n\tgcc main.c\n\nclean:\n\trm -f a.out\n")

    targets = parse_makefile(mf)
    assert targets == ["all", "clean"]


def test_parse_python_project(temp_dir):
    pyproject = temp_dir / "pyproject.toml"
    pyproject.write_text('[tool.pytest.ini_options]\naddopts = "-q"\n')

    info = parse_python_project(temp_dir)
    assert info is not None
    assert "pytest" in info["tools"]


def test_detector_integration(temp_repo, temp_dir):
    (temp_dir / "package.json").write_text('{"scripts": {"dev": "vite"}}')
    (temp_dir / "Makefile").write_text("test:\n\techo test\n")

    detector = ProjectDetector(temp_repo)
    ctx = detector.detect(temp_dir)

    assert "node" in ctx.kinds
    assert "make" in ctx.kinds
    assert "dev" in ctx.npm_scripts
    assert "test" in ctx.make_targets
