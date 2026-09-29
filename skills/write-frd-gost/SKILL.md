---
name: write-frd-gost
title: {ru: "ТЗ по мотивам ГОСТ 34", en: "Technical specification (GOST 34 style)"}
description:
  ru: "Структура и стиль в духе ГОСТ 34.602 — «Общие сведения», «Назначение и цели», «Требования к системе» — официально-деловой стиль."
  en: "Structure and style after GOST 34.602: general information, purpose and goals, system requirements; formal style."
stage: frd
atom_types: [functional, nfr, question]
decompose: true
short: {ru: ТЗ ГОСТ 34, en: GOST 34 spec}
version: 1
sections:
  - key: purpose
    title: {ru: Общие сведения, en: General information}
  - key: context
    title: {ru: Характеристика объекта автоматизации, en: Description of the automated process}
  - key: functional
    title: {ru: Требования к функциям, en: Functional requirements}
  - key: nfr
    title: {ru: Требования к системе в целом, en: System-wide requirements}
  - key: out_of_scope
    title: {ru: Ограничения, en: Limitations}
  - key: questions
    title: {ru: Вопросы, требующие согласования, en: Items to be agreed}
---
Ты ведущий бизнес-аналитик и пишешь техническое задание в официально-деловом стиле, принятом в документах по ГОСТ 34.602. Пиши на языке: {language}.

- Каждое требование — одно предложение в форме «Система должна …» / «В системе должна быть обеспечена …», без разговорных оборотов, местоимений «мы», «вы» и оценочных слов.
- Функциональные требования сгруппируй в подразделы по функциям системы (2–8 подразделов), заголовок — отглагольное существительное («Регистрация обращений», «Отображение истории»).
- purpose (Общие сведения): наименование системы или функции, её назначение и область применения — 2–4 предложения.
- context (Характеристика объекта автоматизации): кто пользователи, в каком процессе участвуют и какая проблема решается.
- assumptions: только допущения, которые прямо следуют из атомов.
- out of scope (Ограничения): только то, что в атомах явно исключено.
