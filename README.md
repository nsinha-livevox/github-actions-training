# GitHub Actions training

A small repository you can **run, read and break** to learn the basics of GitHub Actions.

Open [`.github/workflows/ci.yml`](.github/workflows/ci.yml) next to this page. The workflow is
about 145 lines, and every part of it is explained below. Parts of it come from a second
repository, [`github-actions-workflows`](https://github.com/nsinha-livevox/github-actions-workflows),
to show how to **reuse** pipelines instead of copying them.

> Line numbers below match the file as delivered. If you edit `ci.yml` they will shift, but the
> numbered markers `(1)` to `(9)` inside the file stay where they are, so use those to find your way.

## 1. What is in this repository

| Path | What it is |
|---|---|
| `.github/workflows/ci.yml` | The workflow this guide explains |
| `app/greeter.py` | A tiny Python app: `greet("Alice")` returns `Hello, Alice!` |
| `tests/test_greeter.py` | Three unit tests for the app |
| `requirements.txt` | The app's dependency (`pytest`), so there is something to install and cache |

You do not need to know Python. The app only gives the workflow something real to build and test.

## 2. The workflow at a glance

```
                 push to main / pull request / "Run workflow" button
                                      |
        +-----------------------------+-----------------------------+
        |                             |                             |
     [hello]                       [build]                        [test]   <- reusable workflow
  variables, secrets,           version, package,              runs pytest on Python 3.11
  conditional step,             upload artifact                and on Python 3.12 (a matrix)
  composite action                    |                             |
                                      +--------------+--------------+
                                                     |
                                                 [publish]         <- only on a push to main
                                      downloads the artifact, reads build's output
```

`hello`, `build` and `test` have no `needs:`, so they start **at the same time on separate
machines**. `publish` has `needs: [build, test]`, so it waits for both and is **skipped** if either
fails.

## 3. Walkthrough of `ci.yml`

### (1) Name: line 7
`name: CI` is the label shown in the **Actions** tab. A repository can have many workflow files
in `.github/workflows/` (no sub-folders), each running on its own.

### (2) Triggers: lines 10 to 18
`on:` says **when** the workflow starts.

| Lines | Trigger | When |
|---|---|---|
| 11 to 12 | `push` with `branches: [main]` | Someone pushes to `main` |
| 13 | `pull_request` | A pull request is opened or updated |
| 14 to 18 | `workflow_dispatch` | You press **Run workflow** in the Actions tab. `inputs:` adds a form field (`who`) |

Other triggers exist: `schedule` (cron), `release`, `issues`, `repository_dispatch` (an outside
system calls the GitHub API) and `workflow_call` (another workflow calls this one, see section 4).

### (3) Permissions: lines 21 to 22
Every run gets a temporary token, `GITHUB_TOKEN`. `contents: read` limits it to reading the
repository. Give a workflow the least it needs.

### (4) Concurrency: lines 25 to 27
Runs with the same `group` are not allowed to overlap. With `cancel-in-progress: true`, pushing
again to the same branch **cancels the older run**. `github.ref` is the branch, so a different
branch has its own group and is not affected.

### (5) Variables, workflow level: lines 30 to 31
`env:` at the top defines `GREETING` for **every job and every step**. The same keyword appears at
three levels, and **the lower level wins**:

| Level | Where in this file | Who can read it |
|---|---|---|
| Workflow | line 31 (`GREETING`) | All jobs, all steps |
| Job | line 38 (`JOB_LEVEL`) | Only steps of the `hello` job |
| Step | line 48 (`STEP_LEVEL`) | Only that one step |

You read a variable in a shell as `$GREETING`, and in YAML expressions as `${{ env.GREETING }}`.

### (6) Job `hello`: lines 35 to 78
**Jobs, runner, steps.** A workflow contains jobs. A job gets its **own fresh machine**
(`runs-on: ubuntu-latest`, line 36) and runs its **steps top to bottom**. If a step fails, the
job stops and the remaining steps are skipped.

| Lines | Step | What it shows |
|---|---|---|
| 40 to 41 | `Say hello` | A **`run`** step is a shell command. `${{ github.actor }}` and `${{ github.ref_name }}` are values from the **`github` context** (also: `env`, `vars`, `secrets`, `needs`, `inputs`, `matrix`) |
| 43 to 44 | `Get the code` | A **`uses`** step runs a ready-made **action**. `actions/checkout@v4` downloads your repository onto the machine. Without it the machine is empty. `@v4` pins the version |
| 46 to 53 | `Three levels of variables` | The step-level variable, plus the other two levels |
| 55 to 66 | `Secrets are masked in the log` | A **secret** can only be read with `${{ secrets.NAME }}`. If you add `DEMO_SECRET` under *Settings > Secrets and variables > Actions*, the log prints `***`, never the value |
| 68 to 71 | `Only on a manual run` | **`if:`** decides whether a step runs. There is no `else`: write a second step with the opposite condition. This one is skipped on pushes and pull requests |
| 73 to 78 | `Write a summary (composite action)` | A **composite action** from the other repository (section 4) |

### (7) Job `build`: lines 81 to 113 (passing data around)
Steps in one job share a machine, but **different jobs run on different machines**, so they need
explicit ways to pass things:

| Need | How | Where |
|---|---|---|
| Value from one step to a later step | Write `name=value` to the file `$GITHUB_OUTPUT`, read it as `${{ steps.<id>.outputs.<name> }}` | Lines 95 to 97 write it (the step has `id: version`), line 102 reads it |
| Value from one job to another job | Map it under the job's `outputs:`, read it as `${{ needs.<job>.outputs.<name> }}` | Line 84 publishes it, line 136 (in `publish`) reads it |
| A file, from one job to another | **Artifacts**: `actions/upload-artifact` and `actions/download-artifact` | Lines 109 to 113 upload, lines 128 to 132 download |

Other things in this job:
* Lines 89 to 93: another **composite action** (Python and the pip **cache**, see below).
* Line 101: `inputs.who || 'world'`. The `inputs` context only has a value on a manual run, so
  `||` supplies a default. Values from `${{ }}` are put into `env:` first, and the script uses the
  shell variable. That is safer than pasting `${{ }}` straight into a script.

### (8) Job `test`: lines 117 to 120 (a reusable workflow)
This job has **no `runs-on` and no `steps`**. `uses:` points to a complete workflow in the other
repository (line 118), and `with:` passes its inputs (line 120). That workflow:
* runs on its own machines,
* creates a **matrix**, one job per Python version in the list. In the run you will see
  `test / pytest on Python 3.11` and `... 3.12` running **in parallel**,
* uploads a test report artifact for each version, even if a test failed.

Try adding `"3.13"` to the list (exercise 3).

### (9) Job `publish`: lines 123 to 145 (dependencies and conditions)
* Line 124, **`needs: [build, test]`**: runs after both succeed. If one of them fails, `publish`
  is skipped.
* Line 125, **job-level `if`**: only for a **push** to **`main`**. On a pull request the whole job
  is skipped. Job-level conditions save a machine.
* Lines 128 to 132 download the artifact that `build` uploaded. Lines 134 to 139 use the version
  `build` published.

## 4. The reusable pieces (repository `github-actions-workflows`)

Two kinds of reuse are used here. Both are called with `uses:` and a **version** after the `@`.

| | **Composite action** | **Reusable workflow** |
|---|---|---|
| What it shares | A group of **steps** | A whole **job (or several)** |
| Used in | A step: `- uses: owner/repo/.github/actions/name@v1` | A job: `uses: owner/repo/.github/workflows/file.yml@v1` |
| Used at (here) | Lines 75, 91 and 142 | Line 118 |
| File | Must be named `action.yml`, with `using: composite` | Any name in `.github/workflows/`, with `on: workflow_call` |
| Runner | None. Runs on the caller's machine | Must define its own `runs-on` |
| In the run page | One collapsed step | Its own expandable job(s) |
| Inputs and outputs | `inputs:` and `outputs:` | `inputs:` and `outputs:` (under `workflow_call`) |

The files in the other repository:
* `.github/actions/write-summary/action.yml`: writes a Markdown block to the run's **Summary**
  page (lines 75 and 142).
* `.github/actions/setup-python-env/action.yml`: installs Python with the pip cache and the
  requirements (line 91).
* `.github/workflows/reusable-python-test.yml`: the matrix test job (line 118).

**Why `@v1`?** A tag pins the exact version you call, so a change in the shared repository cannot
break your pipeline overnight. You move to a new version on purpose (`@v2`).

## 5. Where to look in the GitHub UI

1. **Actions** tab, then pick the run. The **graph** shows the jobs and their `needs` arrows.
2. Click a job to see its steps. Click a step to see its log. Red means failed, grey with a dash
   means skipped.
3. **Summary** page of the run: the blocks written by the `write-summary` action, and the
   **Artifacts** list at the bottom (`package` and one `test-report-python-...` per version).
4. A re-run (top right) uses the same commit. A new push makes a new run.

## 6. Exercises

1. **Change a variable.** Edit `GREETING: Hello` (line 31) to `Hi`, commit to `main`, and read the
   `Say hello` log.
2. **Run it by hand.** Actions tab, **CI**, **Run workflow**, set `who` to your name. Open the
   `package` artifact: `greeting.txt` has your name. Notice that `Only on a manual run` ran.
3. **Grow the matrix.** Add `"3.13"` to the list on line 120. A third test job appears.
4. **Break a test.** In `tests/test_greeter.py`, change an expected string. The matching `test`
   jobs go red, `publish` is **skipped**, and the test report artifact is still there.
5. **Add a secret.** Create `DEMO_SECRET` with a made-up value (never a real one: this
   repository is public), re-run, and look for `***`.
6. **Open a pull request.** Everything runs except `publish` (line 125). Then merge it and watch
   `publish` run on `main`.
7. **Push twice quickly** to a branch. The first run shows as **cancelled** (concurrency, lines
   25 to 27).
8. **Call a pipeline from your own repository.** Copy lines 117 to 120 into a new repository that
   has a `tests/` folder and a `requirements.txt`.

## 7. Concepts this workflow only hints at

* **Cache.** The composite action turns on `cache: pip`. The first run downloads packages, later
  runs restore them. Look for "Cache restored" in the log. A repository gets about 10 GB of cache.
  The generic version is `actions/cache` with a key built from a file hash.
* **Authenticating to a cloud without stored passwords (OIDC).** Instead of saving access keys as
  secrets, a job asks GitHub for a short-lived token and the cloud exchanges it for temporary
  credentials. In AWS it looks like this:
  ```yaml
  permissions:
    id-token: write            # allow the job to request the token
    contents: read
  steps:
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::<account-id>:role/<role-name>
        aws-region: us-west-2
  ```
* **Runners.** `ubuntu-latest` is a GitHub-hosted runner, a fresh machine for every job (and free
  for public repositories like this one). A company can also run its own **self-hosted runners**;
  the job then says `runs-on: [self-hosted, <label>]`. Treat what runs on them with extra care, and
  **never use a self-hosted runner for a public repository**: anyone can open a pull request that
  runs code on it.
* **Marketplace.** There are thousands of ready-made actions (`actions/checkout`,
  `actions/setup-python`, cloud actions). Pin a version, prefer actions from GitHub or the cloud
  vendors, and allow only the ones you trust.
* **Secrets vs variables.** Secrets are encrypted and masked. Non-sensitive settings go in
  **variables** (`${{ vars.NAME }}`). Both can be set per organization, repository or environment.
* **Secrets and `if`.** The `secrets` context is not available in a step's `if:`. Pass the secret
  through `env:` and test it in the script, as lines 58 to 66 do.

## 8. This repository is public: what that means

Public repositories get unlimited minutes on GitHub-hosted runners, which is why this training lives
in one. The flip side is that everyone can read it and open pull requests:

* **Nothing internal goes in here:** no company names, hosts, account numbers or real secrets.
* **Pull requests from forks** run with a **read-only token and without your secrets**, and a
  first-time contributor's run waits for a maintainer to approve it. The workflow file used is the
  one from the pull request, which is another reason never to expose real credentials or a
  self-hosted runner.
* Recommended settings (*Settings > Actions > General*): require approval for fork pull requests
  from outside collaborators, and keep the default workflow permissions on **read**.

## 9. Naming conventions

* Workflow files in a repository: describe the job, for example `ci.yml`, `deploy-staging.yml`,
  `nightly-cron.yml`.
* Composite actions: a folder with a file named exactly `action.yml`.
* Reusable workflows: any name, but a `reusable-` prefix (`reusable-python-test.yml`) makes the
  purpose obvious in a list.

## 10. Cheat sheet

| Keyword | Meaning |
|---|---|
| `on` | The triggers |
| `jobs.<id>` | One job, which runs on its own machine |
| `runs-on` | The machine type |
| `steps` | The commands and actions of a job, run in order |
| `run` / `uses` | A shell command / a packaged action or workflow |
| `needs` | Wait for other jobs, and read their outputs |
| `if` | Run only when the condition is true |
| `env` / `${{ env.X }}` | Variables / reading them in expressions |
| `with` | Inputs to an action or reusable workflow |
| `outputs` | Values a step or job hands on |
| `strategy.matrix` | One job per combination of values |
| `concurrency` | Limit or cancel overlapping runs |
| `permissions` | What the `GITHUB_TOKEN` may do |
| `${{ secrets.X }}`, `${{ vars.X }}` | Secrets and variables |
