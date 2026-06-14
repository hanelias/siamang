# Repository & Editing

Your survey lives as **code in a Git repository**. The **Repository** screen is
where you read and change that code — in the browser or from your own machine —
with **validation on every commit** so a broken survey never goes live by accident.

## The editor

The file tree is on the left. Click a file to open it in the **in-browser code
editor**, with syntax highlighting for Python, YAML, and Markdown. The editor
shows line numbers and marks a file as **modified** until you commit it.

## Edit and commit

The platform never saves without a commit, so your history stays clean and every
change is reviewable.

**What you'll need:** the **member** role or higher.

**Steps**
1. Open **Repository** and click a file (e.g. `survey/questionnaire.py`).
2. Make your changes in the editor.
3. Click **Save & commit** (or press **Ctrl/Cmd+S**).
4. Write a short **commit message** and confirm.

**Result:** your change is committed and **validation runs automatically**. A valid
file shows a green **valid** badge; a problem shows an error or warning count —
click the badge for details. A commit that fails validation tells you exactly what
to fix. See [[Validation and Linting|Validation-and-Linting]].

## Browse history

The **Commits** list shows the branch's history. Click any commit to see its
**diff** and its validation status, so you can trace when something changed.

## Branches and pull requests

Work on a branch and merge it when it is ready.

**Steps**
1. In the Repository toolbar, **create a branch** (or switch to one).
2. Commit your changes there.
3. Open a **pull request**, review the diff, and **merge** it into `main`.

> An owner or admin can **protect** the `main` branch (**Settings → Git**) so
> changes must pass validation before they land.

## Add, move, or delete files

Use **New file** in the toolbar to add a file (for example a new analysis script
under `scripts/`). You can rename, move, and delete files too; each action is a
commit like any other.

## Project secrets

Connectors, Git mirrors, and analysis scripts sometimes need a credential — an API
token, a service-account key. Store these as **project secrets**, never in your
code.

**What you'll need:** the **member** role or higher.

**Steps**
1. Open **Settings → Secrets**.
2. Click **New secret**, enter a **name** and a **value**, and save.
3. Reference it **by name** from `siamang.yaml` or a script.

**Result:** the value is encrypted and **write-only** — afterward only the name is
visible, never the value.

## Connect locally (clone and push)

Prefer your own editor? Clone the repo and push changes back.

**What you'll need:** for **SSH**, add a public key first under
[[Account & Security|Cloud-Account-and-Security]] → **SSH keys**.

**Steps**
1. Open **Repository** and click **Connect locally**.
2. Copy the **HTTPS** or **SSH** clone command shown.
3. Clone, edit on your machine, then `git push`.

**Result:** your pushed commits appear in the Repository and are validated like
browser commits.

## Read reports

Markdown (`.md`) files — including generated reports — open with a rendered
**Preview** and an **Edit** view, plus **MD** and **HTML** download buttons.

## See also

[[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Deploying a Survey|Cloud-Deploying-a-Survey]] · [[Account & Security|Cloud-Account-and-Security]] · [[Analysis & Reports|Cloud-Analysis-and-Reporting]]
