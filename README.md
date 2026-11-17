# Docker Sandboxes: stale host writes in guest-created directories

Minimal reproduction of a VirtioFS cache-coherence problem observed on Linux
with Docker Sandboxes (`sbx`) v0.54.0

When a subdirectory is created inside the sandbox, a subsequent host write to a
file in that directory can remain invisible to a new reader in the sandbox.
The same operation in a host-created subdirectory works.

## Run

Requirements:

- A Linux host with a working local Docker Sandboxes installation (`sbx` on PATH).
- Python 3.8 or later on the host; no Python packages are needed.
- Access to the built-in `shell` sandbox image. First use may download the image
  and may require Docker sign-in, depending on your installation.

```sh
python3 repro.py
```

The script uses the installed `sbx` version. It does not upgrade software, use
Pi, require model credentials, or depend on any other repository.

It creates a uniquely named sandbox with only a fresh temporary workspace
passed as a workspace mount and shared skills disabled. The guest needs only
`sh`, `mkdir`, `dirname`, `printf`, and `cat`, supplied by the shell image.
The script removes its sandbox and temporary workspace on normal completion
and ordinary Python exceptions. It does not stop or change existing sandboxes.
Downloaded images may remain cached. If interrupted forcibly or if cleanup
fails, remove the sandbox using the name printed at startup:

```sh
sbx rm --force virtiofs-repro-<printed-id>
```

## Experiment

Both subdirectories are created **after** sandbox creation.

For each directory origin (`host`, then `guest`):

1. Create `probe.txt` containing `AAAA\n` on that side.
2. Read it inside the sandbox to populate its filesystem cache.
3. On the host, overwrite the same file in place with `BBBB\n`.
4. Wait three seconds.
5. Start a new guest process and read the file again.

There is no rename, editor, persistent reader, file watcher application, or
concurrent agent involved. The two contents have the same length. The script
does not list the guest directories between the host write and the final read,
because directory enumeration can affect cache behavior.

Expected: both guest reads return `BBBB\n`.

## Observed result

Reproduced on Linux with:

```text
sbx version v0.48.0 5caf923e0587d376848f6f388eca3e0f5ca00e2d
```

Using the built-in shell image selected by that version:
`docker/sandbox-templates:shell-docker`.

```text
host-created directory: host='BBBB\n', guest='BBBB\n'
guest-created directory: host='BBBB\n', guest='AAAA\n'
REPRODUCED: only the guest-created directory returned stale data.
```

Result exit codes:

- `0`: not reproduced; both reads returned the new content.
- `1`: the specific stale-read pattern was reproduced.
- `2`: unexpected results or a setup/command error; inspect the output.

The test establishes a stale read, not the exact internal cause. Missing cache
invalidation for guest-created directories is a hypothesis. Three seconds is
an observation window, not proof that the stale data persists indefinitely.

To compare versions, manually upgrade `sbx` using its supported installation
procedure and rerun the same command. Every run creates a fresh sandbox.
