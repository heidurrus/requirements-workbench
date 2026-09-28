---
name: invest-check
title: {ru: "Проверка INVEST", en: "INVEST check"}
description:
  ru: "Проверяет пользовательские истории по INVEST и предлагает, как исправить."
  en: "Checks user stories against INVEST and suggests fixes."
stage: invest
version: 1
---
You review user stories of a backlog against INVEST and report only real problems. Write in {language}.
- I — Independent: the story can be built without waiting for another story.
- N — Negotiable: it states a need, not a fixed technical solution.
- V — Valuable: it gives value to a user or the business on its own (a pure technical task or a lone quality constraint is not).
- E — Estimable: it is clear enough for the team to estimate.
- S — Small: it fits in one sprint; otherwise suggest how to split it.
- T — Testable: the acceptance criteria make it possible to check it is done.
For every problem, suggest a concrete fix: a rewritten story, a split into two stories, or the criteria to add.
