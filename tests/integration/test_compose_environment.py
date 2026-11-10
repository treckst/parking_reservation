"""Compose configuration must retain credentials supplied through service env_file."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("working_directory", [".", "docker"])
def test_graph_retains_env_file_key_without_interpolation_environment(tmp_path, working_directory):
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker Compose CLI is required for configuration validation")
    root = Path(__file__).resolve().parents[2]
    (tmp_path / "docker").mkdir()
    shutil.copyfile(root / "docker/compose.yaml", tmp_path / "docker/compose.yaml")
    # Synthetic credentials only. No daemon, real .env, or provider is accessed.
    (tmp_path / ".env").write_text("LANGSMITH_API_KEY=test-runtime-env-file-key\n"
        "LANGSMITH_PROJECT=parking\nLANGCHAIN_PROJECT=legacy\n"
        "LANGSMITH_SESSION=old\nLANGCHAIN_SESSION=older\nHOSTED_LANGSERVE_PROJECT_NAME=hosted\n", encoding="utf-8")
    interpolation = tmp_path / "empty.env"
    interpolation.write_text("", encoding="utf-8")
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("LANGSMITH_", "COMPOSE_"))}
    process = subprocess.run(
        [docker, "compose", "--env-file", str(interpolation), "-f", str(tmp_path / "docker/compose.yaml"),
         "config", "--format", "json"],
        cwd=tmp_path / working_directory, env=environment,
        capture_output=True, text=True, check=True, timeout=30,
    )
    graph = json.loads(process.stdout)["services"]["graph"]
    assert graph["environment"]["LANGSMITH_API_KEY"] == "test-runtime-env-file-key"
    # Use the real SDK resolver with the Agent Server destination, not a
    # string-only assertion about YAML. Never access real credentials.
    script = """
import json, os, sys
from langsmith.address import resolve_destination
from langsmith.utils import get_env_var
for key in list(os.environ):
    if key.startswith(('LANGSMITH_', 'LANGCHAIN_')) or key == 'HOSTED_LANGSERVE_PROJECT_NAME':
        del os.environ[key]
os.environ.update(json.loads(sys.argv[1]))
os.environ.update(LANGSMITH_AGENT_ID='parking', LANGSMITH_AGENT_ENVIRONMENT='LOCAL')
get_env_var.cache_clear()
project, address = resolve_destination()
assert project is None and address['id'] == 'parking', (project, address)
"""
    import sys
    subprocess.run([sys.executable, "-c", script, json.dumps(graph["environment"])],
                   check=True, capture_output=True, text=True, timeout=20)
