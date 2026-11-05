import os
import subprocess
from pathlib import Path


def test_install_preserves_other_jobs_and_is_idempotent(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    table = tmp_path / "crontab"
    table.write_text("MAILTO=owner\n5 0 * * * /existing/train-job\n")
    crontab = fake_bin / "crontab"
    crontab.write_text(
        '#!/bin/sh\nif [ "$1" = "-l" ]; then cat "$TEST_CRONTAB"; else cat "$1" > "$TEST_CRONTAB"; fi\n'
    )
    crontab.chmod(0o755)
    root = Path(__file__).resolve().parents[1]
    env = dict(
        os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}", TEST_CRONTAB=str(table)
    )
    for _ in range(2):
        subprocess.run(
            ["bash", str(root / "scripts/install-cron.sh")],
            env=env,
            check=True,
            capture_output=True,
        )
    content = table.read_text()
    assert "MAILTO=owner\n5 0 * * * /existing/train-job\n" in content
    assert content.count("# BEGIN premium-laptop-watch") == 1
    assert content.count("scripts/cron.sh") == 1
    assert "17 */2 * * *" in content


def test_cron_wrapper_prevents_overlapping_sweeps(tmp_path):
    import fcntl

    state = tmp_path / "state"
    state.mkdir()
    lock = (state / "sweep.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    uv = fake_bin / "uv"
    uv.write_text("#!/bin/sh\nexit 99\n")
    uv.chmod(0o755)
    env = dict(
        os.environ, LAPTOP_STATE_DIR=str(state), PATH=f"{fake_bin}:{os.environ['PATH']}"
    )
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["bash", str(root / "scripts/cron.sh")],
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_unreadable_crontab_is_not_replaced(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "installed"
    command = fake_bin / "crontab"
    command.write_text(
        '#!/bin/sh\nif [ "$1" = "-l" ]; then echo "permission denied" >&2; exit 1; fi\ntouch "$TEST_INSTALL_MARKER"\n'
    )
    command.chmod(0o755)
    root = Path(__file__).resolve().parents[1]
    env = dict(
        os.environ,
        PATH=f"{fake_bin}:{os.environ['PATH']}",
        TEST_INSTALL_MARKER=str(marker),
        LAPTOP_STATE_DIR=str(tmp_path / "state"),
    )
    result = subprocess.run(
        ["bash", str(root / "scripts/install-cron.sh")],
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not marker.exists()
