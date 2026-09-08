# FoundRy Starter Walkthrough

This guide is for someone who has found the public FoundRy page and wants a
clear path from the website explanation to the public source and the local
working setup.

It is a visitor guide, not a hosted-builder manual. The public site explains the
idea; the local repository holds the source; the working data lives in a private
loopback workspace; and exports are the handoff artifacts you choose to keep.

## What FoundRy is

FoundRy is the Glee-fully workbench for shaping useful GPTs, Agent Skills,
workflows, and web tools.

The public page describes it as a place to:

- give an idea a purpose
- keep the relevant details together
- record honest checks
- leave behind a portable package

The page is intentionally modest about scope. It points to a locally run
workbench with public source. It does not claim to be a hosted builder or a
cloud app.

## Where to start on the public site

Start at the FoundRy page:

- [FoundRy](https://glee-fully.tools/foundry/)

From there, the page itself points visitors toward four starting points:

- Custom GPT
- Agent Skill
- Workflow
- Web tool

The page also walks through a small working rhythm:

1. Choose the kind of thing you want to make.
2. Describe the audience, purpose, inputs, outputs, and constraints.
3. Connect the relevant pieces and references.
4. Try it and record what happened.
5. Review what still needs another pass.
6. Package the result for handoff.

That sequence is the public guidepost. It is meant to help you think clearly
before you build anything.

## What the public source says about setup

The application README documents a local loopback server:

- run it from the repository root with `python3 -m app.server`
- it opens on `http://127.0.0.1:8765`
- you can change the local port with `--port`
- there is no install step, build step, paid model, or external service required
- the service binds only to loopback and is not meant to be reverse-proxied or
  served as a public deployment target

The current-state assessment and maturation roadmap is the source for what is
already implemented and what still remains in draft form. The application README
is the best place to confirm the supported local workflow before you start.

So the safe reading is:

- you can inspect the public page and the repo source
- you can launch the local app on loopback
- you should not assume any hosted service, signup flow, network exposure, or
  extra runtime beyond the local Python entry point

## How to inspect it locally

The application is in the separate
[Glee-fullyTools-FoundRy repository](https://github.com/OKHP3/Glee-fullyTools-FoundRy),
not this public-site repository. Its local setup is:

1. Clone it: `git clone https://github.com/OKHP3/Glee-fullyTools-FoundRy.git`
2. Enter it: `cd Glee-fullyTools-FoundRy`
3. Read its [application README](https://github.com/OKHP3/Glee-fullyTools-FoundRy/blob/main/docs/application/README.md).
4. Run `python3 -m app.server` from that repository root.
5. Open `http://127.0.0.1:8765` in a browser.

Nothing in the current public docs says you need a special account, paid plan,
or separate hosted builder to use the local app.

## What belongs to private working data

The public site explains the idea and the repository contains the public source.
Anything outside that boundary stays private unless the owner has explicitly
published it.

That means private working data can include:

- in-progress notes
- draft exports
- owner-side evidence
- `.foundry-data/`, which stores the private SQLite working data
- temporary packages that are not meant for public browsing

Do not assume those materials are exposed through the public site just because
FoundRy mentions packaging or evidence.

## What counts as a useful export

The public page uses the language of portable packages. In practice, that means
the result should be something another person can read, inspect, or continue.

Depending on the task, that may be:

- Markdown notes
- JSON
- a ZIP package
- a checked-in page or document in the repo

The important part is not the file type. It is whether the artifact preserves
the brief, the evidence, and the intended next step.

## Good mental model

Use this order of trust:

1. The current repository docs.
2. The public FoundRy page.
3. The local preview of the site.
4. Any private working exports that the owner has chosen to keep.

That keeps the walkthrough grounded in what is actually published and avoids
turning a public explanation into a promise the site does not make.

## Quick summary

- FoundRy is the public explanation of the Glee-fully workbench.
- The public page points to a locally run, source-backed workflow.
- The repo uses a static site and a local Python preview server.
- No extra hosted builder or account requirement is stated in the public docs.
- Private working data and exports should stay separate unless explicitly
  published.
