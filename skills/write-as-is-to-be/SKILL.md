---
name: write-as-is-to-be
title: {ru: "Текущее и целевое состояние (As-Is / To-Be)", en: "Current and future state (As-Is / To-Be)"}
description:
  ru: "Как процесс устроен сейчас, где болит, как он будет устроен, чем они отличаются и как перейти — по звонкам и требованиям."
  en: "How the process works today, where it hurts, how it will work, the gaps between them and how to get there, from the calls and requirements."
stage: frd
short: {ru: As-Is / To-Be, en: As-Is / To-Be}
version: 1
requirements: none
use_summaries: true
sections:
  - key: purpose
    title: {ru: Назначение и охват, en: Purpose and scope}
  - key: as_is
    title: {ru: Текущее состояние (As-Is), en: Current state (As-Is)}
    instructions: 'The process today as the sources describe it: actors, steps in order, systems and documents used, hand-offs. Write it as numbered steps ("1. Оператор принимает звонок…"), then one short paragraph on volumes and timings if the sources give them.'
  - key: pain_points
    title: {ru: Проблемы текущего процесса, en: Pain points}
    format: table
    columns: [{ru: Проблема, en: Problem}, {ru: Где возникает, en: Where it occurs}, {ru: Последствия, en: Consequences}, {ru: Откуда известно, en: Evidence}]
    instructions: One row per problem the sources mention; evidence is the source title and time or the atom ID.
  - key: to_be
    title: {ru: Целевое состояние (To-Be), en: Future state (To-Be)}
    instructions: The process as it should work once the requirements are met, as numbered steps, naming the requirement IDs that enable each step.
  - key: gaps
    title: {ru: Разрывы между As-Is и To-Be, en: Gap analysis}
    format: table
    columns: [{ru: Область, en: Area}, {ru: Сейчас, en: Today}, {ru: Будет, en: Future}, {ru: Что нужно изменить, en: Change needed}, {ru: Требования, en: Requirements}]
    instructions: One row per area where the process, data, roles or systems change; the last column lists FR/NFR IDs.
  - key: transition
    title: {ru: Переход, en: Transition}
    instructions: The order of changes, dependencies, training and data migration needs, as far as the sources say; otherwise empty.
  - key: questions
    title: {ru: Открытые вопросы, en: Open questions}
---
You are a senior business analyst describing a business process before and after a change. Write everything in {language}.

- Base the As-Is strictly on what the sources and their summaries say about today's work; do not describe the future there.
- Base the To-Be on the accepted atoms; cite requirement IDs (FR-n, NFR-n) where they apply.
- Keep steps short and in active voice with a named actor. Never invent systems, volumes or roles.
