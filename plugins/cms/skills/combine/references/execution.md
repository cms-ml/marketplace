# Running Combine

Read this reference before running Combine from the `/cvmfs` container or
through `combine-run-remote`, when interpreting the server's JSON result, or
when working through a failing command.

## Contents

1. [When to run and when to explain](#when-to-run-and-when-to-explain)
2. [Choosing how to execute](#choosing-how-to-execute)
3. [Running in the shell](#running-in-the-shell)
4. [Running in the /cvmfs container](#running-in-the-cvmfs-container)
5. [Running through combine-run-remote](#running-through-combine-run-remote)
6. [Interpreting the result](#interpreting-the-result)
7. [Worked example](#worked-example)

## When to run and when to explain

**Diagnose from the command first.** For a reported failing command, check
whether the cause is visible in the command itself: an option set outside its
allowed range, inconsistent options, a typo, a wrong file or mode. If it is,
explain the cause and the fix directly, cross-checking the exact rule in the
`combine` sources. Running is then optional confirmation.

**Run** when:

- The user reports a command that errors or gives an unexpected result, the
  cause is **not** visible from the command, and you can reproduce it.
- The user asks you to run, try or check something.
- You proposed a fix and want to confirm it works.

**Don't run, explain from the corpus instead,** when:

- The failure is explainable from the command and its options alone.
- No execution is available: Combine isn't on `PATH` and the
  `combine-run-remote` server isn't connected. Never fabricate execution
  results. Say that execution isn't available, then reason about the command
  from the sources (what the option does, what the error usually means).
- The task is batch submission (e.g. `combineTool.py --job-mode condor`).
  Don't submit jobs on the user's behalf.
- The inputs are large and only the size-capped `combine-run-remote` server is
  available.

## Choosing how to execute

**Do this check first, before every execution.** Run `command -v combine` with
the Bash tool. Its result decides everything else:

- **`combine` is on `PATH`** → run in the **shell**. Don't call `run_combine`,
  even though it is in your tool list. The user has Combine installed and their
  files on disk, and the shell uses those files in place, by path. `run_combine`
  works in an isolated workspace that can't see the user's files, so it fails
  to find them.
- **`combine` is not on `PATH`, but the site has `/cvmfs/unpacked.cern.ch` and
  `apptainer`** (check with `test -d /cvmfs/unpacked.cern.ch` and
  `command -v apptainer`; both are there on lxplus and cmslpc; `test -d`
  avoids the permission prompt Claude Code gives for listing a directory
  outside the working directory) → run Combine in
  the official container, in the user's directory. See
  [Running in the /cvmfs container](#running-in-the-cvmfs-container).
- **Neither** → use the `combine-run-remote` server.

The mere presence of the `run_combine` tool is not a reason to use it: it is a
fallback for users with neither a local Combine nor the container. Once a
local or container Combine is available, treat `run_combine` as unavailable
for the session.

> **The mistake to avoid.** The user says: "run
> `combine -M AsymptoticLimits -d data/tutorials/counting/realistic-counting-experiment.txt`".
>
> **Wrong:** `command -v combine` prints a path inside the user's Combine
> installation, yet the model calls
> `run_combine(command="combine -M AsymptoticLimits -d data/tutorials/…")`. It
> fails: the remote workspace is empty, so the relative path isn't there.
>
> **Right:** `command -v combine` prints a path, so run the command with the
> Bash tool in the user's working directory, where the relative path resolves:
> `combine -M AsymptoticLimits -d data/tutorials/counting/realistic-counting-experiment.txt`.
> Read the expected limit from stdout. No `run_combine` call.

The ways of running Combine are different tools. The shell and the container
run the real executable in the user's directory against their files.
`run_combine` copies the files you pass into a throwaway sandbox on a remote
server.

| Path                 | When                                       | Inputs                                     | Limits                                                      |
| -------------------- | ------------------------------------------ | ------------------------------------------ | ----------------------------------------------------------- |
| Shell                | `combine` is on `PATH`                     | The user's files, by path                  | None; outputs persist                                       |
| `/cvmfs` container   | No `combine`, but `/cvmfs` and `apptainer` | The user's files, in the bound directories | Outputs persist; ~15 s start-up per command                 |
| `combine-run-remote` | Neither, and the CERN network is reachable | Only the files you pass, flat by base name | Size-capped inputs, shorter timeouts; inputs leave the site |
| None                 | No Combine, no container, no server        | —                                          | Don't run; explain from the `combine` sources               |

In every case run **one** Combine-family command at a time (`combine`,
`text2workspace.py`, `combineCards.py`, `combineTool.py`): no pipes, redirects
or chained commands.

## Running in the shell

- Run one command, e.g. `combine -M AsymptoticLimits -d datacard.txt -m 125`.
  It runs in the user's current working directory, so the datacard and the
  shape files it references must already be there. Don't invent file contents.
- Read the exit code, stdout and stderr directly. A non-zero exit is the
  debugging case: cross-check `stderr` against the `combine` sources.
- Output files (e.g. `higgsCombine*.root`) land in the working directory.

## Running in the /cvmfs container

When Combine isn't installed, run it from the official Combine container,
which CVMFS serves unpacked: there is no image to pull, and the user's files
stay on their site:

```bash
IMG=/cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/combine-container:CMSSW_16_0_0-combine_v11.1.0-harvester_v4.0.0
apptainer exec --cleanenv -B /cvmfs -B "$PWD" "$IMG" bash -c \
  'source /cvmfs/cms.cern.ch/cmsset_default.sh; cd /home/cmsusr/CMSSW_16_0_0/src; eval $(scramv1 runtime -sh); cd '"$PWD"'; combine -M AsymptoticLimits -d datacard.txt -m 125'
```

- Replace only the last part (`combine …`) with the command to run. Keep one
  Combine command per call.
- **`-B` must cover every directory the command reads or writes**: the working
  directory (`-B "$PWD"`) and wherever the datacards and shape files live,
  e.g. `-B /uscms_data` on cmslpc or `-B /eos` on lxplus. A path outside the
  bound directories looks missing inside the container.
- `/home/cmsusr/CMSSW_<version>` is the CMSSW area inside the image; its
  version matches the image tag.
- Tested with the tag above (Combine v11.1.0) on cmslpc (EL9, no CERN
  network): about 14 s per command, printing `<<< v11.1.0 >>>`. The same image
  runs combine-assistant's CI. Other tags are listed by
  `ls -d /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-analysis/general/combine-container:*`
  (not tested here). Pick the version the user's analysis needs, and say
  which one you used.

## Running through combine-run-remote

`run_combine` takes:

| Argument    | Content                                                                                                                |
| ----------- | ---------------------------------------------------------------------------------------------------------------------- |
| `command`   | The full command line, e.g. `"combine -M AsymptoticLimits -d datacard.txt -m 125"`. One command, no pipes or redirects |
| `files`     | Text inputs as `{filename: content}`: the datacard and any text configs                                                |
| `files_b64` | Binary inputs as `{filename: base64}`: the ROOT shape files a datacard references                                      |
| `timeout_s` | Optional; the server clamps it to its ceiling                                                                          |

The command runs in an isolated, throwaway workspace on a remote machine.
**Only the files you pass exist there**, so a path to a file you didn't pass
fails with "file not found".

When the user gives a path to a datacard, read it yourself; don't ask them to
paste it:

1. Read the datacard at the given path.
2. Find its `shapes` lines: each names a ROOT file the datacard uses. Read
   those too, as base64.
3. Call `run_combine` with the datacard in `files` and every referenced ROOT
   file in `files_b64`, and refer to them in `command` by **base name**
   (`-d datacard.txt`, not the original absolute path): the workspace is flat.

Ask the user for a file only if you can't read it. Pass every file the command
needs: a shape datacard that references `shapes.root` doesn't run unless
`shapes.root` is in `files_b64`.

## Interpreting the result

The server returns JSON with three possible outcomes:

- **`error` is set** (and `returncode` is null): a setup failure, such as a
  disallowed executable, an oversized input, an unsafe filename, or Combine not
  found on the server. Not a physics result. If it says "not found on PATH",
  tell the user the server has no Combine environment; don't guess numbers.
- **`returncode` is non-zero**: Combine ran and failed. Read `stderr` and
  cross-check it against the sources (`combine-forum` for the message,
  `combine-code` for what the code checks).
- **`returncode` is 0**: success. Report the results from `stdout` and note the
  `artifacts` produced (e.g. `higgsCombine*.root`).

Also watch `timed_out` (raise `timeout_s`, or note that the job needs a local
Combine) and the `*_truncated` flags (the output was cut to its tail).

## Worked example

> _User:_ "This errors: `combine -M FitDiagnostics -d card.txt --robustHesse 1`,
> and here's my datacard."

1. Run `combine -M FitDiagnostics -d card.txt --robustHesse 1`: in the shell if
   Combine is on `PATH` (the card is on disk), otherwise
   `run_combine(command=..., files={"card.txt": <their card>})`.
2. Inspect the result. If Combine wasn't found, execution isn't available: say
   so and don't guess numbers. If it exited non-zero, read `stderr`.
3. Take the key `stderr` line and
   `search_docs(query="<that error text>", source="combine-forum")`; if needed,
   check `combine-code` for what the failing step requires.
4. Propose the fix (cite the forum thread or docs), then re-run the corrected
   command to confirm.
5. Report what failed, why (with citations), and the confirmed working command.
