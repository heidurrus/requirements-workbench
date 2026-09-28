---
name: quality-check
title: Проверка качества
description: Правила проверки требований — измеримость, размытые слова, двусмысленность, несколько требований в одном, проверяемость.
stage: quality
version: 1
vague_words:
  ru: [быстр, удобн, интуитивн, современн, надёжн, надежн, дружелюбн, оптимальн, эффективн, гибк, масштабируем, по возможности, при необходимости, как правило, максимально]
  en: [fast, quick, user-friendly, intuitive, easy, modern, reliable, efficient, flexible, scalable, as appropriate, if possible, robust, seamless, as soon as possible]
rules: []
---
Check each functional and non-functional requirement and report only real problems, with a one-sentence message:
- not_measurable: a quality requirement (speed, load, availability, capacity…) without a number or threshold.
- vague: subjective words such as "fast" or "convenient" that nobody can test.
- ambiguous: can be read in more than one way.
- compound: several requirements in one sentence.
- untestable: no way to check it was met.
