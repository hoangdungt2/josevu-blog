"""Git operations: add/commit/push and rm/commit/push."""
import subprocess

from .config import settings


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=settings.repo_root,
        capture_output=True,
        text=True,
    )


def commit_and_push(paths: list[str], message: str) -> tuple[bool, str]:
    add = _run(["git", "add", "--", *paths])
    if add.returncode != 0:
        return False, add.stderr or add.stdout
    commit = _run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        # Could be "nothing to commit" — surface so the UI can decide.
        return False, commit.stderr or commit.stdout
    push = _run(["git", "push"])
    if push.returncode != 0:
        return False, push.stderr or push.stdout
    return True, ""


def rm_and_push(path: str, message: str) -> tuple[bool, str]:
    rm = _run(["git", "rm", "--", path])
    if rm.returncode != 0:
        return False, rm.stderr or rm.stdout
    commit = _run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        return False, commit.stderr or commit.stdout
    push = _run(["git", "push"])
    if push.returncode != 0:
        return False, push.stderr or push.stdout
    return True, ""
