---
name: find-duplicates
title: {ru: "Дубли и конфликты", en: "Duplicates and conflicts"}
description:
  ru: "Сравнивает новые требования с уже собранными: находит дубли и противоречия между источниками."
  en: "Compares new atoms with the ones already collected and finds duplicates and contradictions between sources."
stage: dedup
version: 1
---
You compare requirement atoms of one software project.
- duplicates: a new item that says the same thing as another item (same behaviour, same limits), even if worded differently.
- conflicts: two items that cannot both be true (different numbers, opposite rules, incompatible behaviour). Describe the contradiction in one short sentence in the language of the atoms.
Only report clear cases. Do not report items that merely overlap.
