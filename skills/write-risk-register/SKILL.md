---
name: write-risk-register
title: {ru: "Реестр и матрица рисков", en: "Risk register and matrix"}
description:
  ru: "Риски проекта из звонков и требований: причина, вероятность, влияние, уровень, меры и владелец — и матрица вероятность × влияние."
  en: "Project risks from the calls and requirements: cause, probability, impact, level, response and owner, plus a probability × impact matrix."
stage: frd
short: {ru: Риски, en: Risks}
version: 1
requirements: none
use_summaries: true
sections:
  - key: purpose
    title: {ru: Назначение, en: Purpose}
  - key: risks
    title: {ru: Реестр рисков, en: Risk register}
    format: table
    id_prefix: R
    columns: [{ru: ID, en: ID}, {ru: Риск, en: Risk}, {ru: Причина и признаки, en: Cause and triggers}, {ru: Вероятность, en: Probability}, {ru: Влияние, en: Impact}, {ru: Меры реагирования, en: Response}, {ru: Владелец, en: Owner}, {ru: Связанные требования, en: Related requirements}]
    heatmap: {probability: 3, impact: 4}
    instructions: 'Every risk the sources and atoms reveal: unclear or conflicting requirements, dependencies on other teams or systems, deadlines, data quality, integrations, compliance, adoption. Probability and impact are exactly one of "низкая/средняя/высокая" or "low/medium/high" (impact: "низкое/среднее/высокое"). Response: avoid, reduce, transfer or accept, with a concrete action. Owner: a role or name from the sources, else "[уточнить]"/"[to confirm]". Related requirements: the FR/NFR/Q IDs involved, comma-separated.'
  - key: questions
    title: {ru: Вопросы, снижающие неопределённость, en: Questions that reduce uncertainty}
---
You are a senior business analyst and project risk manager building a risk register from elicitation material. Write everything in {language}.

- A risk is an uncertain future event that would affect the project's goals; do not list plain requirements or tasks as risks.
- Open conflicts between atoms and open questions are risks of rework: include the significant ones and cite their IDs.
- purpose: 1–2 sentences on the scope of this register and when it was built.
- Be concrete and sober: no generic risks that the sources do not support.
