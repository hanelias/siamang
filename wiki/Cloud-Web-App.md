# Using the Web App

The siamang Cloud web app is where you do everything: create projects, edit your
survey, deploy it, watch responses, run analysis, and manage your team. This page
is a tour of the interface, screen by screen, with the common actions on each.

## Finding your way around

After you sign in, the **top bar** shows your current organization (click it to
switch organizations and projects), a light/dark **theme** toggle, a **settings**
button, and your **account** menu.

The **left sidebar** changes with context. At the **organization** level it lists
**Projects**, **Team**, and **Settings**. Inside a **project** it lists
**Dashboard · Repository · Database · Deployments · Analysis · Connectors · Files
· Settings**, with a status dot by the project name showing its latest validation
state.

---

## Organization screens

### Organizations

Your workspace overview. It shows the organization, its **type** (personal or
cooperative), your **role**, and the current **plan**. From here an owner can
give a personal workspace a team name and turn it into a **cooperative** so you
can invite people. The subscription always stays with the owner.

### Projects

The list of projects in your organization, and where you create new ones. Click
**New project** to start; you can begin from the ready-made **example study** or
an empty project, and a repository and database are created for you. Each row
shows the project's status and response count. If you have reached your plan's
project limit, the button is disabled with a prompt to upgrade.

### Team

A read-only **roster** of everyone in the organization, with their email, role,
and join date. Inviting people, changing roles, and removing members happens in
**Settings → Members** (the **Manage members** button takes you there), so those
actions stay in one owner/admin-gated place.

---

## Project screens

### Dashboard

The project's home. A row of stats (status, branch, responses, commits,
deployments) sits above **Data insights** — live charts over all collected
responses: response/respondent counts, partial rate, last-response time, a
responses-per-day chart, a **frequency** chart for any variable, and a two-way
**crosstab**. Below that are the README, recent commits, a language breakdown,
and the latest deployment. See [[Analysis & Reports|Cloud-Analysis-and-Reporting]].

### Repository

Your survey as code. The file tree is on the left; click a file to open it in the
in-browser **code editor**, with syntax highlighting for Python, YAML, and
Markdown. Common actions:

- **Edit and commit** — make changes, then **Save & commit** (or Ctrl/Cmd+S),
  write a message, and commit. The platform never saves without a commit, so your
  history stays clean.
- **See validation** — each code file shows a **valid** badge or an error/warning
  count; click the badge to see the details. Validation runs on every commit.
- **Browse history** — the **Commits** list shows the branch's history; click a
  commit to see its diff.
- **Branches and pull requests** — switch branches, create a new branch, and
  open or merge **pull requests** from the toolbar.
- **New file** — add a file to the repo.
- **Connect locally** — get clone/push instructions (over HTTPS or SSH) so you
  can work from your own machine instead of the browser. (Add an SSH key in your
  [Profile](#profile) first.)
- **Read reports** — Markdown (`.md`) files open with a rendered **Preview** and
  an **Edit** view, and download buttons for **MD** and **HTML**.

### Deployments

Publish your survey and watch fieldwork. Click **New deployment** and pick an
**environment** (for example a small pilot, then the main run) to compile your
latest commit and publish it. Each deployment card shows:

- A **status** (Live / Building / Failed / Stopped) and the **public survey URL**
  — the link you share with respondents.
- A live **monitor** while collecting: responses so far (and against the cap), a
  progress bar, **quota** cells, and the survey's **codebook** of variables.
- **Logs** from the build, and actions to **Stop** a live survey or **Redeploy**
  one that is stopped or failed.

Use **Preview** (top right) to build a staging version you can click through
yourself; a preview does not accept real responses.

### Database

Browse and export your responses. The left lists the project's **tables**
(`responses` plus any tables your analysis writes). For the selected table:

- **Data** tab — paginated, sortable rows with a quick row **filter**.
- **Schema** tab — the columns, their types, and whether they are nullable.
- **Export** — download the table as **CSV**, **Excel (.xlsx)**, **SPSS (.sav)**,
  **Parquet**, or **SQLite**.
- **Delete a response** — remove a single response permanently (useful for GDPR
  erasure requests).

### Analysis

Run analysis over your data. The **Scripts** section lists the analysis steps
declared in your `siamang.yaml`; for each you can **View in Repo** or **Run** it.
**Run all** runs every step in order and combines their reports. Every run lands
in **Run history** and finishes **completed** or **failed**; click a run for its
**Logs** and **Outputs** (report, new database tables, downloadable files). On
Plus and above, a **Schedules** panel lets you run a script or run-all
automatically on a cron schedule. See
[[Analysis & Reports|Cloud-Analysis-and-Reporting]] and
[[Analysis SDK|Cloud-Analysis-SDK]].

### Files

Everything generated or uploaded for the project, in two groups: **Repository
outputs** (reports and generated tables tracked in your repo) and **Assets**
(files you upload, plus exports). You can **Upload** a file and **Download** or
**Delete** anything here.

### Connectors

A preview catalog of places you will be able to send project data — object
storage, data warehouses, Google Sheets, and your own database. Connectors are
marked **Coming soon** and do not move data yet; until they ship, use **Database
→ Export**. A Pro/Corporate feature — see [[Connectors|Cloud-Connectors]].

### Settings (project)

Settings that apply to this project only, in tabs:

- **General** — project name and default branch.
- **Runtime** — the Python version and packages, read from your `siamang.yaml`
  (edit them in the file and commit).
- **Secrets** — encrypted, write-only values your analysis scripts and connectors
  can reference by name.
- **Git** — protect the `main` branch so changes must pass validation before they
  land.
- **Git mirrors** — keep the repo in sync with GitHub or GitLab (a Pro feature).
- **Danger Zone** — permanently delete the project and its data.

---

## Account & organization settings

### Profile

Your personal account, in tabs:

- **Account** — your display name.
- **Security** — change your password.
- **Appearance** — light or dark theme.
- **API keys** — personal access tokens (`sck_…`) for tools and scripts. A token
  is shown **once** when you create it, so copy it then; you can revoke it later.
- **SSH keys** — add a public key so you can clone and push the repo over SSH.

### Organization settings

Settings that apply to the whole organization (open the **Settings** button or
**Manage** from Organizations), in tabs:

- **General** — organization name and type (personal vs cooperative).
- **Members** — invite teammates and set their **role**: **owner** (full control,
  including billing), **admin** (manage members and projects), or **member**
  (contribute: edit code, run analysis, deploy). Owners and admins manage this.
- **Billing** — your plan and upgrades. During the beta, plans switch instantly
  and nothing is charged. See [[Plans & Billing|Cloud-Subscription-Tiers]].
- **Integrations** — outgoing **Webhooks** for events like deploys and runs, with
  a delivery log (a Plus feature); **SSO** configuration is marked Coming soon.
  See [[Schedules & Webhooks|Cloud-Scheduling-and-Webhooks]].
- **Activity** — an audit feed of actions across the organization (deploys, runs,
  invites, deletions) with a time-range filter.

## Step-by-step guides

Task-focused how-tos for the screens above:
[[Account & Security|Cloud-Account-and-Security]] ·
[[Organizations & Team|Cloud-Organizations-and-Team]] ·
[[Your First Project|Cloud-Your-First-Project]] ·
[[Repository & Editing|Cloud-Repository-and-Editing]] ·
[[Deploying a Survey|Cloud-Deploying-a-Survey]] ·
[[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]] ·
[[FAQ & Troubleshooting|Cloud-FAQ-and-Troubleshooting]]

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Analysis & Reports|Cloud-Analysis-and-Reporting]] · [[Plans & Billing|Cloud-Subscription-Tiers]] · [[siamang Cloud — Overview|Cloud-Overview]]
