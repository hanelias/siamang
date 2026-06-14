# Viewing & Exporting Data

Every response your survey collects lands in the project's **database**, where you
can browse it, check its structure, delete individual records, and **export** it in
the format your analysis tools expect. This page covers the **Database** and
**Files** screens.

## Browse your responses

**Steps**
1. Open **Database**.
2. Pick a table on the left — start with **`responses`**. (Analysis scripts can
   write more tables; they appear here too.)
3. On the **Data** tab, page through the rows; **sort** by a column and use the
   row **filter** to find what you need.

**Result:** you see the collected responses as a table, updated as new ones arrive.

## Inspect the structure

The **Schema** tab lists the table's **columns**, their **types**, and whether each
is nullable. Check it before analysis so you know what the data looks like.

## Export your data

**What you'll need:** a table selected in the Database.

**Steps**
1. With a table open, click **Export**.
2. Choose a format: **CSV**, **Excel (.xlsx)**, **SPSS (.sav)**, **Parquet**, or
   **SQLite**.

**Result:** the file downloads. **SPSS** carries variable and value labels;
**CSV**/**Excel** carry the data, with labels available via the survey's dictionary;
**SQLite** is a single-file snapshot of the whole table. For how labels and missing
values travel between formats, see [[Data Import and Export|Data-Import-and-Export]].

## Delete a response (GDPR)

Need to honor an erasure request? You can remove a single record permanently.

**Steps**
1. Open **Database** and select the **`responses`** table.
2. Find the response and click **Delete**.
3. Confirm.

**Result:** the response is permanently removed. The action is recorded in the
organization's **Activity** log.

## Files: outputs and assets

The **Files** screen holds everything generated or uploaded for the project, in two
groups:

- **Repository outputs** — reports and generated tables tracked in your repo.
- **Assets** — files you **Upload**, plus exports.

You can **Upload**, **Download**, or **Delete** anything here. Uploads are capped at
**50 MB per file**.

## Sending data to other systems

**Connectors** — pushing tables to object storage, data warehouses, Google Sheets,
or your own database — are listed under **Connectors** but are marked **Coming
soon** and do not move data yet. Until they ship, get your data out with
**Database → Export** above. See [[Connectors|Cloud-Connectors]] (a Pro / Corporate
feature).

## See also

[[Deploying a Survey|Cloud-Deploying-a-Survey]] · [[Analysis & Reports|Cloud-Analysis-and-Reporting]] · [[Data Import and Export|Data-Import-and-Export]] · [[Connectors|Cloud-Connectors]]
