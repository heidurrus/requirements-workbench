---
name: write-vision-scope
title: {ru: "Vision & Scope — видение и границы", en: "Vision & Scope"}
description:
  ru: "Видение и границы (по Вигерсу): предпосылки, бизнес-возможность, видение решения, цели, основные возможности, рамки релизов, ограничения."
  en: "Vision and scope (Wiegers style): background, business opportunity, solution vision, objectives, major features, release scope, constraints."
stage: frd
short: {ru: Vision & Scope, en: Vision & Scope}
version: 1
use_summaries: true
sections:
  - key: background
    title: {ru: Предпосылки и бизнес-возможность, en: Background and business opportunity}
    instructions: Why this initiative exists - the situation, the need or opportunity, and what happens if nothing is done.
  - key: vision
    title: {ru: Видение решения, en: Solution vision}
    instructions: 'A concise vision statement in the form "Для <кого>, кому <нужно…>, <продукт> — это <что>, который <ключевая ценность>. В отличие от <альтернатива>, наш продукт <отличие>." / "For <target>, who <need>, the <product> is a <category> that <key benefit>. Unlike <alternative>, our product <differentiator>." Then 2–4 sentences expanding it. Leave parts as [уточнить]/[to confirm] if the sources are silent.'
  - key: objectives
    title: {ru: Бизнес-цели и критерии успеха, en: Business objectives and success criteria}
    instructions: Objectives with measurable success criteria where the sources give them.
  - key: stakeholders
    title: {ru: Заинтересованные стороны, en: Stakeholders}
    format: table
    columns: [{ru: Сторона, en: Stakeholder}, {ru: Главная ценность, en: Major value}, {ru: Ожидания и ограничения, en: Expectations and constraints}]
    instructions: One row per stakeholder the sources name or clearly imply.
  - key: functional
    title: {ru: Основные возможности, en: Major features}
  - key: releases
    title: {ru: Рамки релизов, en: Scope of releases}
    format: table
    columns: [{ru: Возможность, en: Feature}, {ru: Первый релиз, en: First release}, {ru: Следующие релизы, en: Later releases}]
    instructions: One row per major feature group; say what goes into the first release and what later, only as far as the sources say; otherwise "[уточнить]" / "[to confirm]".
  - key: nfr
    title: {ru: Ключевые требования к качеству, en: Key quality attributes}
  - key: out_of_scope
    title: {ru: Вне рамок, en: Limitations and exclusions}
  - key: context
    title: {ru: Допущения, зависимости и риски, en: Assumptions, dependencies and risks}
  - key: questions
    title: {ru: Открытые вопросы, en: Open questions}
---
You are a senior business analyst writing a Vision and Scope document. Write everything in {language}.

- Keep it short and strategic: this document aligns stakeholders on why and what, not on details.
- Group the functional atoms into 3–7 major features (sub-sections), each with a short noun-phrase title; word each item as a capability ("Поиск клиента по номеру телефона" / "Customer search by phone number").
- context (assumptions, dependencies and risks): one short paragraph plus assumptions the atoms imply.
- Use the source summaries for the background, vision and objectives; never invent facts, numbers or dates.
