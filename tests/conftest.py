import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "benchmark" / "projects" / "shopcalc" / "project"
GIT = ["git", "-c", "user.email=t@qualitylens", "-c", "user.name=t"]


@pytest.fixture
def sample_root(tmp_path) -> Path:
    dest = tmp_path / "proj"
    shutil.copytree(SAMPLE, dest)
    return dest


@pytest.fixture
def make_change(tmp_path):
    """Create a git repo from the sample project with one commit applying `edits` [(file, old, new)]."""
    def _make(edits):
        repo = tmp_path / "repo"
        shutil.copytree(SAMPLE, repo)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True)
        subprocess.run(GIT + ["commit", "-qm", "base"], cwd=repo, check=True)
        for rel, old, new in edits:
            p = repo / rel
            p.write_text(p.read_text().replace(old, new, 1))
        subprocess.run(GIT + ["commit", "-qam", "change"], cwd=repo, check=True)
        return repo
    return _make
