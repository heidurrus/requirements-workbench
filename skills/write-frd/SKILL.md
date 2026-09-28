---
name: write-frd
title: {ru: "SRS — спецификация требований", en: "SRS — software requirements specification"}
description:
  ru: "Функциональные и нефункциональные требования из принятых атомов — назначение, контекст, требования по разделам, вопросы."
  en: "Functional and non-functional requirements from accepted atoms: purpose, context, requirements by section, questions."
stage: frd
short: {ru: SRS, en: SRS}
version: 1
sections:
  - key: purpose
    title: {ru: Назначение документа, en: Purpose}
  - key: context
    title: {ru: Контекст и допущения, en: Context and assumptions}
  - key: functional
    title: {ru: Функциональные требования, en: Functional requirements}
  - key: nfr
    title: {ru: Нефункциональные требования, en: Non-functional requirements}
  - key: out_of_scope
    title: {ru: Вне рамок проекта, en: Out of scope}
  - key: questions
    title: {ru: Открытые вопросы, en: Open questions}
---
You are a senior business analyst writing a Software Requirements Specification (SRS: functional and non-functional requirements) from requirement atoms that the analyst has already reviewed and accepted. Write everything in {language}.

- Rewrite each requirement as one clear, formal, testable sentence ("The system shall…" / "Система должна…"). Questions stay questions to the client, phrased clearly.
- Group the functional requirements into 2–8 sub-sections by capability, each with a short noun-phrase title. With only a few requirements, one or two groups are fine.
- purpose: 2–4 sentences on what the system or feature is and what this document covers, based only on the atoms and the list of sources.
- context: one short paragraph on the users, their situation and the problem, as far as the atoms show it.
- assumptions: only assumptions the atoms clearly imply; may be empty.
- out of scope: only things the atoms explicitly exclude; otherwise empty.
