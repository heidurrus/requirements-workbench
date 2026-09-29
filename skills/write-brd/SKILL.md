---
name: write-brd
title: {ru: "BRD — бизнес-требования", en: "BRD — business requirements"}
description:
  ru: "Документ бизнес-требований: бизнес-контекст, цели и метрики, заинтересованные стороны, границы, бизнес-требования, ограничения, вопросы."
  en: "Business requirements document: business context, goals and metrics, stakeholders, scope, business requirements, constraints, questions."
stage: frd
atom_types: [business, nfr, question]
context_types: [functional, risk]
decompose: false
short: {ru: BRD, en: BRD}
version: 1
use_summaries: true
sections:
  - key: purpose
    title: {ru: Назначение документа, en: Purpose of this document}
  - key: business_context
    title: {ru: Бизнес-контекст и проблема, en: Business context and problem}
    instructions: The business situation today, the problem or opportunity, who suffers from it and why it matters now. Plain business language, no system design.
  - key: objectives
    title: {ru: Бизнес-цели и показатели успеха, en: Business objectives and success metrics}
    instructions: A short list of business objectives, each with a measurable success metric when the sources give a number; otherwise mark the metric as "[уточнить]" / "[to confirm]".
  - key: stakeholders
    title: {ru: Заинтересованные стороны, en: Stakeholders}
    format: table
    columns: [{ru: Сторона, en: Stakeholder}, {ru: Роль в проекте, en: Role}, {ru: Интересы и ожидания, en: Interests and expectations}]
    instructions: Everyone the sources name or clearly imply (roles, departments, the client, end users), one row each.
  - key: scope
    title: {ru: Границы проекта, en: Project scope}
    instructions: What the project covers, as a few sentences or bullet-like lines, based on the atoms. Exclusions go to "out of scope".
  - key: business
    title: {ru: Бизнес-требования, en: Business requirements}
  - key: nfr
    title: {ru: Ограничения и требования к качеству, en: Constraints and quality requirements}
  - key: context
    title: {ru: Допущения и зависимости, en: Assumptions and dependencies}
  - key: out_of_scope
    title: {ru: Вне рамок проекта, en: Out of scope}
  - key: questions
    title: {ru: Открытые вопросы, en: Open questions}
---
You are a senior business analyst writing a Business Requirements Document (BRD) for the client and business stakeholders. Write everything in {language}.

- A BRD states what the business needs and why, not how a system does it. Word each requirement from the business point of view: "Бизнесу необходимо…", "Оператор должен иметь возможность…" / "The business needs to…", "Operators must be able to…". Avoid technical design and UI details.
- Each business requirement (BR-n) is one item: what the business needs and why, measurable where the atoms allow.
- purpose: 2–3 sentences on the goal of the initiative and who this document is for.
- context (shown as "assumptions and dependencies"): one short paragraph on dependencies and constraints from other teams, systems or contracts that the atoms mention; assumptions only if clearly implied.
- Use the source summaries for the business context, objectives and stakeholders; never invent numbers, names or dates.
