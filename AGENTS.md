# AGENTS.md

This repo's contributor rules for AI assistants live in [CLAUDE.md](CLAUDE.md). They are tool-agnostic:
read that file and follow it, whatever assistant you are.

Short version: a Bespok3d plugin declares WHAT the printer should end up with, never a script that runs
on the printer. A u1-base plugin additionally may only ADD a hook door: never change or remove one, and
never change stock behaviour when nothing is registered against it (ADR-0043). Before you propose a
change, run `cd plugins/u1-base && ./scripts/check.sh` (nothing to set up: it reads the Snapmaker source
vendored in this repo) and
make it green (fix a real failure, never mute it), and keep every identifier meaningful, nesting
shallow, and em-dashes out.
