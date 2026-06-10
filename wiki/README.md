# Wiki source

This folder is the **source of truth** for the project's GitHub Wiki. The wiki
itself lives in a separate git repository (`https://github.com/hanelias/siamang.wiki.git`);
these files are authored here (so they are reviewable in pull requests) and then
**published** to that wiki repository.

The wiki covers **two products** in one place:

- **Library** — the `siamang` Python package (pages without a prefix).
- **Cloud Platform** — the `siamang_cloud` platform (pages prefixed `Cloud-`).

## Conventions

- One Markdown file per page. The filename becomes the page title with dashes
  rendered as spaces (`Question-Types.md` → "Question Types").
- `Home.md` is the landing page; `_Sidebar.md` is the navigation; `_Footer.md`
  is the footer shown on every page.
- Link between pages with wiki links: `[[Display text|Target-Page]]`
  (e.g. `[[Question Types|Question-Types]]`). All links are internal — the
  Library and Cloud sections live in the **same** wiki.
- Cloud pages use the `Cloud-` filename prefix to avoid name clashes with
  Library pages (both have a "Configuration" and a "Deployment" page).

## Publishing

```bash
bash wiki/sync.sh
```

The script clones the wiki repository, copies every `*.md` page from this folder
(excluding this `README.md` and `sync.sh`), commits, and pushes.

**Prerequisite:** the wiki must be enabled and initialized. If `git clone` of the
`.wiki.git` fails with "not found", open the repository's **Settings → Features →
Wikis**, ensure Wikis are enabled, then create the first page (Home) once via the
GitHub UI. After that the wiki git repo exists and `sync.sh` can push to it.

To target a different wiki remote, set `WIKI_REMOTE`:

```bash
WIKI_REMOTE=https://github.com/<owner>/<repo>.wiki.git bash wiki/sync.sh
```
