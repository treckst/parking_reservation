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
    (tmp_path / ".env").write_text("LANGSMITH_API_KEY=test-runtime-env-file-key\n", encoding="utf-8")
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
