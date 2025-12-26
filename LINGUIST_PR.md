Title: Add Ailang language to GitHub Linguist

Description:
This repository contains sample files and a suggested languages.yml entry to add Ailang (.ailang) to GitHub Linguist.

Suggested languages.yml entry to add to github/linguist/config/languages.yml:

Ailang:
  type: programming
  color: "#00AABB"
  extensions:
    - ".ailang"
  tm_scope: "source.ailang"

What I added in this branch:
- linguist/Ailang.languages.yml (language metadata snippet)
- samples/ailang/Library.Regex_Thompson.ailang (real sample exercising core features)
- LINGUIST_PR.md (this file) with PR text and instructions

How to open the PR to github/linguist:
1. Fork https://github.com/github/linguist
2. In your fork, create a branch (e.g. add-ailang).
3. Copy the languages.yml snippet into _config/languages.yml in the appropriate place (alphabetical).
4. Add the sample file under samples/ailang/ (or add to test fixtures as required by linguist contributing guide).
5. Run the linguist tests locally (see CONTRIBUTING.md in github/linguist) and ensure the sample fixtures detect as Ailang.
6. Open a PR against github/linguist with the description from this file. Reference this repository and the sample.

Notes:
- If you would like, I can open the PR text for you to paste into the upstream PR body. Copy the block below as the PR description.

PR description (copy/paste):
"""
Add support for the Ailang programming language (.ailang)

This PR adds a languages.yml entry for Ailang and provides a sample file (Library.Regex_Thompson.ailang) demonstrating language features.

- language: Ailang
- extensions: .ailang
- sample: AiLang-Author/Ailang-Self-Hosting-/samples/ailang/Library.Regex_Thompson.ailang

Please let me know if you want changes to the tm_scope or color.
"""
