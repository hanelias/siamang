# Organizations & Team

An **organization** is your workspace on siamang Cloud. It owns your **projects**,
your **team**, and your **plan** — everything you create lives inside one. This
page explains organizations, how to invite people, and exactly who can do what.

> The subscription always belongs to the organization **owner**. Billing and plan
> changes are covered in [[Plans & Billing|Cloud-Subscription-Tiers]].

## Personal vs. cooperative

Every organization is one of two types:

- **Personal** — a solo workspace. It has a single member: you, the owner.
- **Cooperative** — a team workspace. You can invite other people and give them
  roles.

You can start personal and turn it into a cooperative later (see below) — your
projects and data stay exactly as they are.

## Switch between organizations and projects

If you belong to more than one organization, click your **organization name** in
the top bar to switch organizations and jump between their projects. Everything on
screen — projects, team, billing — re-scopes to the organization you pick.

## Turn a personal workspace into a team

**What you'll need:** the **owner** role.

**Steps**
1. Open **Organization settings** (the **Settings** button, or **Manage** from the
   **Organizations** screen).
2. On the **General** tab, set the **type** to **cooperative** and give the
   workspace a team name.
3. Save.

**Result:** the organization can now have multiple members — invite them next.

## Invite a teammate

**What you'll need:** a **cooperative** organization; the **owner** or **admin**
role. Your invitee needs their own siamang Cloud account, and your plan must have
room (see member limits in [[Plans & Billing|Cloud-Subscription-Tiers]]).

**Steps**
1. Open **Organization settings → Members**.
2. Click **Invite member**.
3. Enter their **email** and pick a **role** — **admin** or **member**.
4. Send the invite.

**Result:** they join the organization with the role you chose. The **Team** screen
shows the full roster (email, role, join date); invites, role changes, and removals
all live in **Settings → Members**.

## Roles & permissions

Every member has exactly one of three roles. Your **role** decides what *you* can
do; your **plan** decides what the *organization* can do — they are independent.

| Role | Can do |
| :--- | :--- |
| **owner** | Everything, including changing the **plan** and billing, organization settings, and SSO. There is **one** owner. |
| **admin** | Manage the organization profile and **members** (invite, change roles, remove), **create projects**, set branch protection, and manage integrations. |
| **member** | **Contribute to projects**: edit code, run analysis, deploy, and manage project secrets. |

Only the **owner** can buy, change, or cancel the subscription, regardless of plan.

## Change a role or remove a member

**What you'll need:** the **owner** or **admin** role.

**Steps**
1. Open **Organization settings → Members**.
2. Find the person in the list.
3. Change their **role** from the dropdown, or click **Remove** to take them out.

**Result:** access updates immediately. You cannot change or remove the **owner**.

## Activity & audit

**Organization settings → Activity** is an audit feed of what happened across the
organization — deploys, runs, invites, deletions — with a time-range filter. It is
visible to the **owner** and **admins**, and is handy for compliance or for seeing
who changed what.

## See also

[[Plans & Billing|Cloud-Subscription-Tiers]] · [[Your First Project|Cloud-Your-First-Project]] · [[Account & Security|Cloud-Account-and-Security]] · [[Using the Web App|Cloud-Web-App]]
