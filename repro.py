#!/usr/bin/env python3
"""Compare host writes in host-created and guest-created workspace directories."""

import pathlib
import subprocess
import tempfile
import time
import uuid


def sbx(*args):
    return subprocess.run(["sbx", *args], check=True, text=True, stdout=subprocess.PIPE).stdout


def main():
    name = "virtiofs-repro-" + uuid.uuid4().hex[:12]
    print(sbx("version").strip(), flush=True)
    # A fresh workspace prevents old mounts or repository settings affecting the test.
    with tempfile.TemporaryDirectory(prefix="sbx-virtiofs-repro-") as directory:
        workspace = pathlib.Path(directory).resolve()

        def guest(command, path):
            return sbx("exec", name, "sh", "-c", command, "repro", str(path))

        try:
            print(f"Creating {name}, workspace={workspace}", flush=True)
            print(sbx("create", "--name", name, "--skills", "off", "shell", str(workspace)), flush=True)
            results = {}
            for origin in ("host", "guest"):
                path = workspace / origin / "probe.txt"
                if origin == "host":
                    path.parent.mkdir()
                    path.write_text("AAAA\n")
                else:
                    guest('mkdir -p "$(dirname "$1")"; printf "AAAA\\n" > "$1"', path)

                # Prime the guest cache, then modify the SAME inode on the host.
                assert guest('cat "$1"', path) == "AAAA\n", "Initial read failed"
                path.write_text("BBBB\n")
                time.sleep(3)
                actual = guest('cat "$1"', path)
                results[origin] = actual
                print(f"{origin}-created directory: host={path.read_text()!r}, guest={actual!r}", flush=True)

            if results == {"host": "BBBB\n", "guest": "AAAA\n"}:
                print("REPRODUCED: only the guest-created directory returned stale data.")
                return 1
            if all(value == "BBBB\n" for value in results.values()):
                print("NOT REPRODUCED: both guest reads saw the host update.")
                return 0
            print("UNEXPECTED: results differ from both the expected behavior and the target bug.")
            return 2
        finally:
            # Remove only this run's sandbox, including after a partially failed create.
            print(f"Removing {name}", flush=True)
            sbx("rm", "--force", name)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, AssertionError) as error:
        print(f"ERROR: {error}", flush=True)
        raise SystemExit(2)
