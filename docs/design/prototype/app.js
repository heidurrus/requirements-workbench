/* Requirements Workbench — redesign prototype. Static, no build step. Sample content is invented. */
(() => {
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const I = (n, c = "") => `<svg class="i ${c}"><use href="#i-${n}"/></svg>`;
const K = (k) => `<span class="kbd">${k}</span>`;

/* ---------------- Sample data ---------------- */
const TYPES = { br: ["BR", "Бизнес-требование"], fr: ["FR", "Функциональное"], nfr: ["NFR", "Нефункциональное"], rsk: ["RSK", "Риск"], as: ["AS", "Как сейчас"], q: ["Q", "Вопрос"] };
const ST = { pending: ["На ревью", "accent", "clock"], accepted: ["Принято", "ok", "check"], rejected: ["Отклонено", "", "x"] };

const sources = [
  { id: "s6", kind: "wave", title: "Уточнение по отчётам и скорости", date: "24 сент.", len: "27 мин", who: "Ирина Власова, Олег Шубин", state: "new", a: 0, p: 7, r: 0 },
  { id: "s5", kind: "wave", title: "Демо текущей системы", date: "22 сент.", len: "61 мин", who: "3 участника", state: "work", a: 0, p: 0, r: 0 },
  { id: "s4", kind: "doc", title: "Регламент обработки заказов.docx", date: "19 сент.", len: "14 стр.", who: "Документ заказчика", state: "ready", a: 9, p: 0, r: 3 },
  { id: "s3", kind: "mail", title: "Письмо: требования информационной безопасности", date: "18 сент.", len: "2 стр.", who: "От: Павел Дронов", state: "ready", a: 6, p: 0, r: 0 },
  { id: "s2", kind: "wave", title: "Созвон по складу и остаткам", date: "17 сент.", len: "38 мин", who: "Ирина Власова, Олег Шубин", state: "ready", a: 11, p: 2, r: 1 },
  { id: "s1", kind: "wave", title: "Интервью с руководителем продаж", date: "14 сент.", len: "52 мин", who: "Ирина Власова, Олег Шубин", state: "ready", a: 14, p: 1, r: 2 },
];
const srcById = Object.fromEntries(sources.map(s => [s.id, s]));

const atoms = [
  { id: 1, code: "NFR-3", t: "nfr", st: "pending", pr: "Must", src: "s1", at: "21:03", who: "Олег Шубин", conflict: 2,
    text: "Страница каталога открывается не дольше 2 секунд при 500 одновременных пользователях",
    quote: "Две секунды на открытие каталога — это нормально, даже если в системе одновременно пятьсот человек." },
  { id: 2, code: "NFR-7", t: "nfr", st: "pending", pr: "—", src: "s6", at: "04:02", who: "Ирина Власова", conflict: 1,
    text: "Страница каталога открывается не дольше 1 секунды",
    quote: "Каталог должен открываться за секунду. Две секунды нас не устраивают, дилеры уйдут к конкурентам." },
  { id: 3, code: "FR-12", t: "fr", st: "pending", pr: "Should", src: "s6", at: "09:40", who: "Ирина Власова",
    text: "Руководитель продаж выгружает отчёт по заказам дилера в Excel за выбранный период",
    quote: "Мне нужен отчёт по каждому дилеру за любой период, и чтобы его можно было открыть в Excel." },
  { id: 4, code: "RSK-2", t: "rsk", st: "pending", pr: "—", src: "s2", at: "19:48", who: "Олег Шубин",
    text: "Выгрузка остатков из 1С может не выдержать обмен чаще одного раза в час",
    quote: "Честно говоря, я не уверен, что наша 1С потянет обмен каждые пятнадцать минут. Сейчас он идёт раз в сутки." },
  { id: 5, code: "Q-4", t: "q", st: "pending", pr: "—", src: "s1", at: "33:20", who: "Ирина Власова",
    text: "Кто согласует кредитный лимит дилера: финансовая служба или руководитель продаж?",
    quote: "Лимит… это хороший вопрос. Раньше его ставили финансисты, но последний год решаю я. Надо уточнить." },
  { id: 6, code: "AS-3", t: "as", st: "pending", pr: "—", src: "s6", at: "12:15", who: "Олег Шубин",
    text: "Остатки сейчас рассылаются дилерам один раз в день файлом Excel",
    quote: "Сейчас мы каждое утро рассылаем дилерам эксельку с остатками. К обеду она уже неактуальна." },
  { id: 17, code: "FR-13", t: "fr", st: "pending", pr: "Should", src: "s6", at: "15:32", who: "Ирина Власова",
    text: "Руководитель продаж видит, какие дилеры не делали заказов больше 30 дней",
    quote: "Хочу видеть, кто из дилеров замолчал. Если месяц нет заказов — это сигнал, надо звонить." },
  { id: 18, code: "BR-3", t: "br", st: "pending", pr: "—", src: "s6", at: "18:05", who: "Ирина Власова",
    text: "Отчёты по продажам готовятся без участия ИТ-отдела",
    quote: "Сейчас каждый отчёт — это заявка в ИТ и три дня ожидания. Так быть не должно." },
  { id: 19, code: "NFR-8", t: "nfr", st: "pending", pr: "—", src: "s6", at: "21:47", who: "Олег Шубин",
    text: "Отчёт за год по одному дилеру формируется не дольше 10 секунд",
    quote: "Годовой отчёт по дилеру должен строиться секунд за десять, не больше, иначе им не будут пользоваться." },
  { id: 20, code: "Q-5", t: "q", st: "pending", pr: "—", src: "s6", at: "24:30", who: "Олег Шубин",
    text: "Должен ли дилер видеть отчёты по своим заказам или только руководитель продаж?",
    quote: "А дилеру самому эти отчёты нужны? Мы это не обсуждали, я бы спросил у коммерческого директора." },
  { id: 7, code: "FR-1", t: "fr", st: "accepted", pr: "Must", src: "s2", at: "12:41", who: "Ирина Власова",
    text: "Дилер видит остатки по каждому складу с задержкой не более 15 минут",
    quote: "Остатки нужны почти в реальном времени. Пятнадцать минут — это потолок, дальше дилер уже звонит менеджеру." },
  { id: 8, code: "FR-2", t: "fr", st: "accepted", pr: "Must", src: "s1", at: "08:15", who: "Ирина Власова",
    text: "Дилер оформляет заказ из корзины без участия менеджера, если сумма не превышает кредитный лимит",
    quote: "Если дилер в пределах своего лимита, зачем ему менеджер? Пусть оформляет сам." },
  { id: 9, code: "BR-1", t: "br", st: "accepted", pr: "Must", src: "s1", at: "03:30", who: "Ирина Власова",
    text: "Сократить долю заказов, оформленных по телефону и почте, с 70% до 20% за первый год",
    quote: "Сейчас семьдесят процентов заказов идут через телефон и почту. Через год хочу видеть двадцать." },
  { id: 10, code: "AS-1", t: "as", st: "accepted", pr: "—", src: "s1", at: "05:12", who: "Ирина Власова",
    text: "Менеджер вручную переносит заказ из письма в 1С; на один заказ уходит до 25 минут",
    quote: "Менеджер получает письмо, открывает 1С и вбивает всё руками. Минут двадцать пять на заказ." },
  { id: 11, code: "FR-5", t: "fr", st: "accepted", pr: "Should", src: "s1", at: "27:45", who: "Ирина Власова",
    text: "Дилер получает уведомление на почту при каждой смене статуса заказа",
    quote: "Дилер должен узнавать о смене статуса сразу, письмом. Не надо заставлять его заходить и проверять." },
  { id: 12, code: "NFR-1", t: "nfr", st: "accepted", pr: "Must", src: "s3", at: "стр. 1", who: "Павел Дронов",
    text: "Вход в кабинет дилера защищён двухфакторной аутентификацией",
    quote: "Доступ внешних пользователей допускается только при наличии второго фактора (СМС или приложение)." },
  { id: 13, code: "BR-2", t: "br", st: "accepted", pr: "Should", src: "s2", at: "02:10", who: "Ирина Власова",
    text: "Дилер самостоятельно отслеживает отгрузку, не обращаясь к менеджеру",
    quote: "Половина звонков менеджерам — это «где моя машина с товаром». Это дилер должен видеть сам." },
  { id: 14, code: "RSK-1", t: "rsk", st: "accepted", pr: "—", src: "s2", at: "31:05", who: "Олег Шубин",
    text: "Команда интеграции 1С занята другим проектом до конца ноября",
    quote: "Ребята из 1С до конца ноября на проекте маркировки, раньше они к нам не подключатся." },
  { id: 15, code: "Q-2", t: "q", st: "accepted", pr: "—", src: "s1", at: "41:50", who: "Олег Шубин",
    text: "Нужна ли английская версия кабинета на первом этапе?",
    quote: "У нас есть дилеры в Казахстане и Армении. Нужен ли им английский — я не знаю." },
  { id: 16, code: "FR-9", t: "fr", st: "rejected", pr: "—", src: "s4", at: "стр. 6", who: "Регламент", reason: "Вне рамок проекта",
    text: "Дилер может изменить цену позиции в заказе",
    quote: "Цена позиции может быть скорректирована по согласованию с менеджером." },
];

const transcript = [
  [1, "02:48", "Анна Серова", "Давайте начнём с цели. Что должно измениться через год после запуска кабинета?"],
  [2, "03:30", "Ирина Власова", "Сейчас семьдесят процентов заказов идут через телефон и почту. Через год хочу видеть двадцать.", [9]],
  [2, "05:12", "Ирина Власова", "Менеджер получает письмо, открывает 1С и вбивает всё руками. Минут двадцать пять на заказ. Если в заказе ошибка, всё по новой.", [10]],
  [3, "06:40", "Олег Шубин", "И ещё менеджеры параллельно отвечают на звонки про остатки, поэтому заказы копятся до вечера."],
  [1, "07:55", "Анна Серова", "Может ли дилер оформить заказ сам, без менеджера?"],
  [2, "08:15", "Ирина Власова", "Если дилер в пределах своего лимита, зачем ему менеджер? Пусть оформляет сам. Выше лимита — только через согласование.", [8]],
  [3, "21:03", "Олег Шубин", "Две секунды на открытие каталога — это нормально, даже если в системе одновременно пятьсот человек.", [1]],
  [2, "27:45", "Ирина Власова", "Дилер должен узнавать о смене статуса сразу, письмом. Не надо заставлять его заходить и проверять.", [11]],
  [1, "33:02", "Анна Серова", "Кто сегодня устанавливает кредитный лимит дилера?"],
  [2, "33:20", "Ирина Власова", "Лимит… это хороший вопрос. Раньше его ставили финансисты, но последний год решаю я. Надо уточнить.", [5]],
  [3, "41:50", "Олег Шубин", "У нас есть дилеры в Казахстане и Армении. Нужен ли им английский — я не знаю.", [15]],
  [2, "44:10", "Ирина Власова", "И последнее: историю заказов нужно хранить минимум два года, у нас сезонность."],
];

const backlog = [
  { lvl: "epic", title: "Самостоятельное оформление заказа", goal: "Снять с менеджеров ручной ввод заказов", key: "DLR-101", on: true, open: true },
  { lvl: "story", id: "st1", title: "Оформление заказа в пределах кредитного лимита", ac: 4, invest: "ok", ref: "FR-2", pr: "Must", key: "DLR-102", on: true, open: true },
  { lvl: "sub", title: "API: проверка кредитного лимита", on: true, key: "DLR-103" },
  { lvl: "sub", title: "Экран корзины и подтверждения", on: true, key: "DLR-104" },
  { lvl: "sub", title: "Согласование заказа сверх лимита", on: false },
  { lvl: "story", id: "st2", title: "Уведомления о смене статуса заказа", ac: 3, invest: "ok", ref: "FR-5", pr: "Should", key: "DLR-105", on: true },
  { lvl: "story", id: "st3", title: "История заказов дилера за 24 месяца", ac: 2, invest: "warn", ref: "FR-7", pr: "Should", on: true },
  { lvl: "epic", title: "Остатки и отгрузки", goal: "Убрать звонки «где мой товар»", on: true, open: true },
  { lvl: "story", id: "st4", title: "Остатки по складам с задержкой до 15 минут", ac: 3, invest: "ok", ref: "FR-1", pr: "Must", key: "DLR-106", on: true, stale: true },
  { lvl: "story", id: "st5", title: "Отслеживание отгрузки по заказу", ac: 3, invest: "ok", ref: "FR-4", pr: "Should", on: true },
  { lvl: "story", id: "st6", title: "Отчёт по заказам дилера в Excel", ac: 2, invest: "warn", ref: "FR-12", pr: "Could", on: false },
  { lvl: "epic", title: "Безопасность и доступ", goal: "Выполнить требования службы ИБ", on: true, open: true },
  { lvl: "story", id: "st7", title: "Вход с двухфакторной аутентификацией", ac: 4, invest: "ok", ref: "NFR-1", pr: "Must", on: true },
  { lvl: "story", id: "st8", title: "Журнал действий дилера для службы ИБ", ac: 2, invest: "ok", ref: "NFR-2", pr: "Should", on: true },
  { lvl: "story", id: "st9", title: "Роли и права: дилер, менеджер, руководитель продаж", ac: 5, invest: "ok", ref: "NFR-4", pr: "Must", on: true },
  { lvl: "epic", title: "Отчёты для руководителя продаж", goal: "Отчёты без заявок в ИТ", on: true, open: true },
  { lvl: "story", id: "st10", title: "Дилеры без заказов больше 30 дней", ac: 3, invest: "ok", ref: "FR-13", pr: "Should", on: true },
  { lvl: "story", id: "st11", title: "Годовой отчёт по дилеру не дольше 10 секунд", ac: 2, invest: "ok", ref: "NFR-8", pr: "Could", on: true },
  { lvl: "sub", title: "Витрина данных по заказам", on: true },
  { lvl: "sub", title: "Экран отчёта и выгрузка в Excel", on: true },
];

const skills = [
  ["Общее", [["house-rules", "Общие инструкции", "Термины и стиль для всех шагов", "own"]]],
  ["Источники", [["summarize-source", "Сводка источника", "Встроенный", ""], ["extract-requirements", "Извлечение требований", "Своя копия · изменён 22 сент.", "own", true], ["find-duplicates", "Дубли и конфликты", "Встроенный", ""]]],
  ["Документы", [["write-frd", "SRS — спецификация требований", "Встроенный", ""], ["write-brd", "BRD — бизнес-требования", "Встроенный", ""], ["write-vision-scope", "Vision & Scope", "Встроенный", ""], ["write-risk-register", "Реестр рисков", "Встроенный", ""], ["write-as-is-to-be", "As-Is / To-Be", "Встроенный", ""], ["quality-check", "Проверка качества", "Встроенный", ""], ["fix-requirement", "Исправление требования", "Встроенный", ""]]],
  ["Бэклог", [["split-into-stories", "Декомпозиция на истории", "Встроенный", ""], ["invest-check", "Проверка INVEST", "Встроенный", ""]]],
  ["Шаблоны Word", [["export-standard", "Word — обычный", "Используется в проекте", ""], ["export-gost", "Word — ГОСТ", "Не используется", "off"]]],
];

/* ---------------- State ---------------- */
const S = { screen: "overview", atom: 1, checked: new Set(), filter: "pending", source: "s1", story: "st1", finding: 0, compare: false, inspector: true };

/* ---------------- Sidebar ---------------- */
function nav() {
  const cur = S.screen === "source" ? "sources" : S.screen;
  const row = (go, icon, label, extra = "", attrs = "") => `<button class="nav-row" data-go="${go}" ${cur === go ? 'aria-current="page"' : ""} title="${label}" ${attrs}>${icon}<span class="lbl grow trunc">${label}</span>${extra}</button>`;
  const pending = atoms.filter(a => a.st === "pending").length;
  $("#nav").innerHTML = `
    ${row("overview", I("home"), "Обзор")}
    <div class="nav-label lbl">Конвейер</div>
    ${row("sources", `<span class="ring done"></span>`, "Источники", `<span class="count lbl num">6</span>`)}
    ${sources.slice(0, 3).map(s => `<button class="nav-row child" data-go="source" data-src="${s.id}" ${S.screen === "source" && S.source === s.id ? 'aria-current="page"' : ""}><span class="trunc grow">${s.title}</span>${s.state === "work" ? '<span class="spinner"></span>' : s.state === "new" ? '<span class="dot accent"></span>' : ""}</button>`).join("")}
    ${row("atoms", `<span class="ring active" style="--p:${Math.round(100 * (atoms.length - pending) / atoms.length)}"></span>`, "Требования", `<span class="count todo lbl num">${pending} на ревью</span>`)}
    ${row("document", `<span class="ring stale" style="--p:100"></span>`, "Документы", `<span class="count warn lbl">устарел</span>`)}
    <button class="nav-row child" data-go="document" ${S.screen === "document" ? 'aria-current="page"' : ""}><span class="trunc grow">SRS · v2</span><span class="dot warn"></span></button>
    <button class="nav-row child" data-go="document"><span class="trunc grow">BRD · v1</span></button>
    <button class="nav-row child" data-go="document"><span class="trunc grow">Реестр рисков · v1</span></button>
    ${row("backlog", `<span class="ring active" style="--p:60"></span>`, "Бэклог", `<span class="count lbl num">11 историй</span>`)}
    ${row("export", `<span class="ring" style="--p:0"></span>`, "Выгрузка", `<span class="count lbl num">5 из 14</span>`)}
  `;
  $$(".side-foot .nav-row").forEach(b => b.toggleAttribute("aria-current", false));
  const f = $(`.side-foot .nav-row[data-go="${S.screen}"]`); if (f) f.setAttribute("aria-current", "page");
}

/* ---------------- Toolbars ---------------- */
const TB = {
  overview: () => [`Обзор`, `Портал дилера · обновлено сегодня в 10:42`, `
    <button class="btn" data-act="import">${I("import")}Импортировать…</button>
    <button class="btn rec" data-act="record"><i></i>Записать звонок</button>
    <button class="btn primary" data-go="atoms">Разобрать 10 требований${I("arrow-r")}</button>`],
  sources: () => [`Источники`, `6 источников · 1 распознаётся · 10 требований ждут ревью`, `
    <label class="search tb-opt" style="width:240px">${I("search", "s14")}<input placeholder="Поиск по источникам"><span class="kbd">/</span></label>
    <button class="btn" data-act="import">${I("import")}Импортировать…</button>
    <button class="btn rec" data-act="record"><i></i>Записать звонок</button>
    <button class="btn primary" data-go="atoms">К требованиям${I("arrow-r")}</button>`],
  source: () => { const s = srcById[S.source]; return [`<span class="tb-crumb">Источники  ›  </span>${s.title}`, `${s.date} · ${s.len} · ${s.who} · распознано локально`, `
    <button class="btn ghost tb-opt" data-toast="Транскрипт скопирован">Скопировать текст</button>
    <button class="btn tb-opt2" data-toast="Сводка обновлена">${I("spark")}<span class="lbl-b">Обновить сводку</span></button>
    <button class="btn" data-toast="Требования извлекаются заново">${I("refresh")}Извлечь заново…</button>
    <button class="btn primary" data-go="atoms">Требования из источника · ${s.a + s.p + s.r}${I("arrow-r")}</button>`]; },
  atoms: () => { const p = atoms.filter(a => a.st === "pending").length, acc = atoms.filter(a => a.st === "accepted").length;
    return [`Требования`, `${p} на ревью · принято ${acc} из ${atoms.length} · 1 конфликт`, `
    <div class="seg" role="tablist"><button aria-selected="true">Требования <span class="n">${atoms.length}</span></button><button data-toast="Вкладка «Для заказчика»: вопросы, поручения и письмо">Для заказчика <span class="n">3</span></button></div>
    <button class="btn" data-toast="Новое требование">${I("plus")}Добавить</button>
    <button class="btn primary" data-go="document">Обновить документ${I("arrow-r")}</button>`]; },
  document: () => [`SRS — Портал дилера`, `Версия 2 · черновик · 24 требования · собрана 23 сент. в 18:20`, `
    <button class="popbtn tb-opt" data-toast="Статус версии"><span class="lab">Статус</span>Черновик${I("updown", "s12")}</button>
    <button class="btn ${S.compare ? "" : ""}" data-act="compare" aria-pressed="${S.compare}">${I("compare")}${S.compare ? "Скрыть сравнение" : "Сравнить с v1"}</button>
    <button class="btn" data-toast="Экспорт в Word — шаблон «Обычный»">${I("word")}Экспорт в Word${I("chev-d", "s12")}</button>
    <button class="btn primary" data-toast="Обновлено 2 раздела · версия 3">${I("refresh")}Обновить изменённое · 2</button>`],
  backlog: () => [`Бэклог`, `4 эпика · 11 историй · к выгрузке отмечено 10 · собран из SRS v2`, `
    <button class="btn ghost tb-opt" data-toast="Уточнение для ИИ">Уточнить…</button>
    <button class="btn" data-toast="Проверка INVEST: 2 замечания">${I("check")}Проверить по INVEST</button>
    <button class="btn" data-toast="Новая история">${I("plus")}История</button>
    <button class="btn primary" data-go="export">К выгрузке в Jira · 10${I("arrow-r")}</button>`],
  export: () => [`Выгрузка`, `Jira подключена · проект DLR · последняя выгрузка 23 сент.`, `
    <button class="btn" data-toast="Предпросмотр обновлён">${I("refresh")}Обновить предпросмотр</button>
    <button class="btn primary" data-act="push">Выгрузить 12 задач в DLR ${K("⌘↵")}</button>`],
  skills: () => [`Скиллы`, `Инструкции для каждого шага ИИ · 2 изменены в этом проекте`, `
    <button class="btn tb-opt" data-toast="Импорт скилла из .zip">${I("import")}Импортировать…</button>
    <button class="btn" data-toast="Скилл выгружен в .zip">${I("export")}Экспорт в .zip</button>
    <button class="btn primary" data-toast="Сохранено (версия 4)">Сохранить ${K("⌘S")}</button>`],
  settings: () => [`Настройки`, `Ключи и токены хранятся только на этом компьютере`, ``],
};

function toolbar() {
  const [title, sub, actions] = TB[S.screen]();
  const insp = ["sources", "source", "atoms", "document", "backlog", "skills"].includes(S.screen);
  $("#toolbar").innerHTML = `
    <button class="btn ghost icon" data-act="sidebar" title="Скрыть или показать боковую панель · ⌘\\" aria-label="Боковая панель">${I("sidebar")}</button>
    ${S.screen === "source" ? `<button class="btn ghost icon" data-go="sources" title="Назад к источникам · ⌘[" aria-label="Назад">${I("arrow-l")}</button>` : ""}
    <div class="tb-title grow"><h1 class="trunc">${title}</h1><p class="trunc num">${sub}</p></div>
    <div class="tb-actions">${actions}
      <span class="tb-sep"></span>
      <button class="btn ghost icon" data-act="theme" title="Светлая или тёмная тема · ⇧⌘L" aria-label="Тема">${I(isDark() ? "sun" : "moon")}</button>
      ${insp ? `<button class="btn ghost icon" data-act="inspector" aria-pressed="${S.inspector}" title="Скрыть или показать инспектор · ⌥⌘I" aria-label="Инспектор">${I("inspector")}</button>` : ""}
    </div>`;
}

/* ---------------- Screens ---------------- */
const typeTag = (t) => `<span class="type ${t}" title="${TYPES[t][1]}">${TYPES[t][0]}</span>`;
const statusTag = (st) => `<span class="status ${ST[st][1]}">${I(ST[st][2], "s12")}${ST[st][0]}</span>`;
const stageRow = (ring, name, text, btn) => `<div class="stage">${ring}<h4>${name}</h4>${btn}<p>${text}</p></div>`;

const screens = {
  overview: () => `<div class="scroll" style="height:100%"><div class="ov">
    <div class="ov-head"><h2>Портал дилера</h2><p>ООО «Северный путь» · 6 источников, 20 требований, 3 документа</p></div>
    <div class="next">
      <div class="grow"><div class="cap">Следующий шаг</div><h3>Разобрать 10 новых требований</h3><p>Из созвона «Уточнение по отчётам и скорости». Среди них конфликт: каталог за 1 или за 2 секунды.</p></div>
      <button class="btn primary lg" data-go="atoms">Начать ревью${I("arrow-r")}</button>
    </div>
    <div class="ov-grid">
      <section><div class="sec-title"><h3>Конвейер</h3><span class="t3">от записи до задач в Jira</span></div>
        ${stageRow('<span class="ring done"></span>', "Источники", "6 источников. «Демо текущей системы» распознаётся, осталось около 6 минут.", `<button class="btn sm" data-go="sources">Открыть</button>`)}
        ${stageRow('<span class="ring active" style="--p:62"></span>', "Требования", "10 на ревью, 9 принято, 1 отклонено. Один конфликт ждёт решения.", `<button class="btn sm primary" data-go="atoms">Разобрать · 10</button>`)}
        ${stageRow('<span class="ring stale" style="--p:100"></span>', "Документы", "SRS v2 устарел: после сборки изменилось 2 требования. BRD и реестр рисков актуальны.", `<button class="btn sm" data-go="document">Обновить SRS</button>`)}
        ${stageRow('<span class="ring active" style="--p:60"></span>', "Бэклог", "4 эпика, 11 историй. 2 замечания INVEST. Одна история собрана по устаревшему требованию.", `<button class="btn sm" data-go="backlog">Открыть</button>`)}
        ${stageRow('<span class="ring" style="--p:0"></span>', "Выгрузка", "В Jira 5 задач из 14. Ждут выгрузки: 7 новых и 2 изменённые.", `<button class="btn sm" data-go="export">Открыть</button>`)}
      </section>
      <section><div class="sec-title"><h3>Для заказчика</h3><span class="t3 num">3 вопроса · 2 поручения</span><button class="btn sm" data-toast="Письмо заказчику готово">${I("mail", "s14")}Составить письмо</button></div>
        ${[["q", "Кто согласует кредитный лимит дилера: финансовая служба или руководитель продаж?", "Интервью с руководителем продаж · 33:20 · открыт"],
           ["q", "Каталог должен открываться за 1 или за 2 секунды?", "Конфликт NFR-3 и NFR-7 · отправлен 24 сент."],
           ["q", "Нужна ли английская версия кабинета на первом этапе?", "Интервью с руководителем продаж · 41:50 · открыт"]]
          .map(([t, h, m]) => `<div class="simple-row">${typeTag(t)}<h4>${h}</h4><span></span><p>${m}</p></div>`).join("")}
        ${[["Прислать выгрузку заказов за 2025 год", "Олег Шубин · до 30 сент."], ["Согласовать перечень ролей с ИБ", "Анна Серова · до 2 окт."]]
          .map(([h, m]) => `<div class="simple-row"><input type="checkbox" class="cb" aria-label="Выполнено"><h4>${h}</h4><span></span><p>${m}</p></div>`).join("")}
      </section>
      <section><div class="sec-title"><h3>С прошлого раза</h3><span class="t3">вчера, 18:30</span></div>
        ${[["Импортирован «Уточнение по отчётам и скорости»", "5 требований извлечено автоматически", "10:42"], ["Найден конфликт между NFR-3 и NFR-7", "Разные требования к скорости каталога", "10:42"],
           ["Запись «Демо текущей системы» поставлена на распознавание", "61 минута · локально, GigaAM", "10:15"], ["SRS v1 отправлен на согласование", "Статус изменён: «На согласовании»", "вчера"], ["В Jira выгружено 5 задач", "DLR-101 … DLR-106", "23 сент."]]
          .map(([h, m, t]) => `<div class="simple-row"><span class="dot" style="margin-top:6px;color:var(--c-line-control)"></span><h4>${h}</h4><time>${t}</time><p>${m}</p></div>`).join("")}
      </section>
      <section><div class="sec-title"><h3>Документы</h3><span class="t3">3 документа</span><button class="btn sm" data-go="document">Открыть</button></div>
        ${[["SRS — спецификация требований", "Версия 2 · 24 требования · 3 замечания качества", "warn", "Устарел"], ["BRD — бизнес-требования", "Версия 1 · 6 требований", "accent", "На согласовании"], ["Реестр рисков", "Версия 1 · 4 риска", "ok", "Согласован"]]
          .map(([h, m, k, st]) => `<div class="simple-row"><span class="kind" style="width:24px;height:24px">${I("doc", "s14")}</span><h4>${h}</h4><span class="status ${k}">${st}</span><p>${m}</p></div>`).join("")}
      </section>
      <section><div class="sec-title"><h3>Требования по типам</h3><span class="t3 num">20 всего</span></div>
        ${Object.keys(TYPES).map(k => { const l = atoms.filter(a => a.t === k), n = l.length || 1, a = l.filter(x => x.st === "accepted").length, p = l.filter(x => x.st === "pending").length; return `<div class="typebar">${typeTag(k)}<span class="mini"><i class="a" style="width:${100 * a / n}%"></i><i class="p" style="width:${100 * p / n}%"></i><i class="r" style="width:${100 * (n - a - p) / n}%"></i></span><span class="t3 num">${TYPES[k][1]} · ${a} принято, ${p} на ревью</span></div>`; }).join("")}
      </section>
      <section><div class="sec-title"><h3>Недавние источники</h3><span class="t3">6 всего</span><button class="btn sm" data-go="sources">Все источники</button></div>
        ${sources.slice(0, 4).map(s => `<div class="simple-row"><span class="kind" style="width:24px;height:24px">${I(s.kind, "s14")}</span><h4>${s.title}</h4><time>${s.date}</time><p>${s.len} · ${s.state === "work" ? "распознаётся, 42%" : s.p ? s.p + " требований ждут ревью" : "разобран"}</p></div>`).join("")}
      </section>
    </div></div></div>`,

  sources: () => `<div class="panes has-inspector has-context ${S.inspector ? "" : "no-insp"}">
    <section class="pane"><div class="pane-body scroll">
      <table class="table"><thead><tr><th>Источник</th><th class="c-wide">Участники</th><th>Дата</th><th class="c-wide">Объём</th><th>Требования</th><th class="c-xwide">Разбор</th><th>Состояние</th></tr></thead><tbody>
      ${sources.map(s => { const n = s.a + s.p + s.r; return `<tr data-src="${s.id}" ${S.source === s.id ? 'aria-selected="true"' : ""}>
        <td><div class="name"><span class="kind">${I(s.kind)}</span><div><b>${s.title}</b><span>${s.kind === "wave" ? "Запись звонка" : s.kind === "mail" ? "Письмо" : "Документ"}</span></div></div></td>
        <td class="c-wide t2">${s.who}</td><td class="t2 num" style="white-space:nowrap">${s.date}</td><td class="c-wide t2 num">${s.len}</td>
        <td class="num" style="white-space:nowrap">${n ? `${n}${s.p ? ` <span class="status accent">· ${s.p} на ревью</span>` : ""}` : '<span class="t3">—</span>'}</td>
        <td class="c-xwide">${n ? `<span class="mini" title="принято ${s.a}, на ревью ${s.p}, отклонено ${s.r}"><i class="a" style="width:${100 * s.a / n}%"></i><i class="p" style="width:${100 * s.p / n}%"></i><i class="r" style="width:${100 * s.r / n}%"></i></span>` : ""}</td>
        <td>${s.state === "work" ? `<span class="status accent"><span class="spinner"></span>Распознаётся · 42%</span>` : s.state === "new" ? `<span class="status accent">${I("clock", "s12")}Ждёт ревью</span>` : `<span class="status ok">${I("check", "s12")}Разобран</span>`}</td></tr>`; }).join("")}
      </tbody></table>
      <div class="drop">${I("import", "s20")}<div><b>Перетащите файлы сюда</b>, чтобы добавить источники. Аудио и видео, транскрипты Teams и Zoom, документы Word и PDF, письма. Можно несколько сразу.</div></div>
    </div></section>
    ${sourcePreview()}
    ${sourceAtoms()}
  </div>`,

  source: () => `<div class="panes has-inspector has-context ${S.inspector ? "" : "no-insp"}">
    <section class="pane">
      <div class="scope"><div class="seg"><button aria-pressed="true">Все реплики</button><button>Только с требованиями <span class="n">9</span></button></div>
        <span class="grow"></span><label class="search opt" style="width:220px">${I("search", "s14")}<input placeholder="Поиск по тексту"></label>
        <button class="btn ghost sm" data-toast="Режим правки транскрипта">${I("pencil", "s14")}Исправить текст</button></div>
      <div class="pane-body scroll"><div class="transcript">${transcript.map(([s, t, who, text, at], i) => `
        <div class="seg-line ${i === 5 ? "playing" : ""}" tabindex="0"><time class="mono">${t}</time><span class="spk s${s}"><span class="trunc">${who}</span></span>
          <div><p class="seg-text">${at ? hl(text) : text}</p>
          ${at ? `<div class="seg-atoms">${at.map(id => { const a = atoms.find(x => x.id === id); return `<button class="seg-atom" data-atom="${a.id}">${typeTag(a.t).replace(TYPES[a.t][0], a.code)}<span class="trunc">${a.text}</span></button>`; }).join("")}</div>` : ""}</div></div>`).join("")}</div></div>
      <div class="player"><button class="play" aria-label="Воспроизвести" title="Воспроизвести · пробел">${I("play", "s14")}</button><span class="mono t2">08:15</span><div class="wave-wrap"><div class="wave"></div></div><span class="mono t3">52:04</span>
        <button class="popbtn" title="Скорость воспроизведения">1,25×${I("updown", "s12")}</button></div>
    </section>
    <aside class="pane secondary inspector">
      <div class="pane-head"><div class="seg"><button aria-pressed="true">Сводка</button><button>Участники <span class="n">3</span></button></div><span class="grow"></span><button class="btn ghost sm" data-toast="Сводка скопирована как письмо">Скопировать как письмо</button></div>
      <div class="pane-body scroll"><div class="insp-body"><div class="prose">
        <p>Руководитель продаж хочет перевести дилеров на самостоятельное оформление заказов, чтобы разгрузить менеджеров и сократить ошибки ручного ввода.</p>
        <h3>Главное</h3><ul><li><b>Цель:</b> доля заказов по телефону и почте с 70% до 20% за год.</li><li><b>Сейчас:</b> менеджер переносит заказ в 1С вручную, до 25 минут на заказ.</li><li><b>Заказ без менеджера</b> возможен в пределах кредитного лимита.</li><li><b>Скорость:</b> каталог не дольше 2 секунд при 500 пользователях.</li></ul>
        <h3>Открытые вопросы</h3><ul><li>Кто согласует кредитный лимит дилера?</li><li>Нужна ли английская версия на первом этапе?</li></ul>
        <h3>Поручения</h3><ul><li><b>Олег Шубин:</b> прислать выгрузку заказов за 2025 год до 30 сентября.</li></ul></div></div></div>
    </aside>
    ${sourceAtoms()}
  </div>`,

  atoms: () => `<div class="panes has-inspector has-context ${S.inspector ? "" : "no-insp"}">
    <section class="pane">
      <div class="scope">
        <div class="seg" id="atom-filter">${[["pending", "На ревью"], ["accepted", "Принятые"], ["rejected", "Отклонённые"], ["conflict", "Конфликты"], ["all", "Все"]].map(([k, l]) => `<button data-filter="${k}" class="${k === "rejected" ? "opt-seg" : ""}" aria-pressed="${S.filter === k}">${l} <span class="n ${k === "conflict" ? "danger" : ""}">${countFilter(k)}</span></button>`).join("")}</div>
        <button class="popbtn opt"><span class="lab">Тип</span>Все${I("updown", "s12")}</button>
        <button class="popbtn opt"><span class="lab">Источник</span>Все${I("updown", "s12")}</button>
        <span class="grow"></span>
        <label class="search" style="width:clamp(160px,20cqw,320px)">${I("search", "s14")}<input placeholder="Поиск по требованиям и цитатам"><span class="kbd">/</span></label>
      </div>
      <div class="pane-body scroll list" id="atom-list"></div>
      <div class="bulk" id="bulk"></div>
    </section>
    <aside class="pane secondary inspector" id="atom-insp"></aside>
    <aside class="pane secondary context" id="atom-ctx"></aside>
  </div>`,

  document: () => `<div style="display:flex;flex-direction:column;height:100%">
    <div class="tabs doc-tabs" role="tablist"><button role="tab" aria-selected="true">SRS <span class="n">v2</span><span class="dot warn" title="Устарел"></span></button><button role="tab" aria-selected="false">BRD <span class="n">v1</span></button><button role="tab" aria-selected="false">Реестр рисков <span class="n">v1</span></button><button role="tab" aria-selected="false" class="t3">${I("plus", "s14")}Новый документ</button></div>
    <div class="panes has-outline has-inspector has-context grow ${S.inspector ? "" : "no-insp"} ${S.compare ? "comparing" : ""}" style="min-height:0">
    <aside class="pane secondary outline"><div class="pane-body scroll"><div class="outline-body">
      <div class="cap" style="padding:var(--s-4) var(--s-4) var(--s-3)">Содержание</div>
      ${[["1", "Назначение документа"], ["2", "Контекст и допущения"], ["3", "Функциональные требования", "", "warn"], ["3.1", "Заказы", "l2 cur"], ["3.2", "Остатки и отгрузки", "l2", "warn"], ["3.3", "Отчёты", "l2"], ["4", "Нефункциональные требования", "", "danger"], ["5", "Вне рамок проекта"], ["6", "Открытые вопросы"]]
        .map(([n, t, c = "", d]) => `<button class="ol-row ${c}" ${c.includes("cur") ? 'aria-current="true"' : ""}><span class="n">${n}</span><span class="grow">${t}</span>${d ? `<span class="dot ${d}"></span>` : ""}</button>`).join("")}
      <div class="cap" style="padding:var(--s-7) var(--s-4) var(--s-3)">Версии</div>
      <button class="ver" aria-current="true"><b>Версия 2</b><span class="status warn">Черновик</span><span>23 сент., 18:20 · 24 требования</span></button>
      <button class="ver"><b>Версия 1</b><span class="status accent">На согласовании</span><span>19 сент., 12:05 · отправлена заказчику</span></button>
    </div></div></aside>
    <section class="pane deskpane"><div class="pane-body scroll"><div class="desk">${S.compare ? `<div class="paper-col old"><div class="paper-label">Версия 1<span class="status accent">На согласовании</span></div>${paper(true)}</div><div class="paper-col"><div class="paper-label">Версия 2<span class="status warn">Черновик</span><span class="grow"></span><span class="t3" style="font-weight:400">изменено 2 · добавлено 3</span></div>${paper()}</div>` : paper()}</div></div></section>
    <aside class="pane secondary inspector">
      <div class="pane-head"><div class="seg"><button aria-pressed="true">Качество <span class="n">3</span></button><button>Изменения <span class="n">2</span></button><button>Сведения</button></div></div>
      <div class="pane-body scroll"><div class="findings" id="findings"></div></div>
      <div class="insp-foot"><button class="btn primary" data-toast="Исправления применены · документ обновлён">Применить все и обновить</button><span class="grow"></span><span class="t3" style="align-self:center">${K("[")} ${K("]")} между замечаниями</span></div>
    </aside>
    <aside class="pane secondary context">
      <div class="pane-head"><h2>Откуда требование FR-1</h2><span class="grow"></span><button class="btn ghost sm" data-go="source">Открыть источник</button></div>
      <div class="pane-body scroll">${contextTranscript(7)}</div>
    </aside>
  </div></div>`,

  backlog: () => `<div class="panes has-inspector has-context ${S.inspector ? "" : "no-insp"}">
    <section class="pane">
      <div class="scope"><div class="seg"><button aria-pressed="true">Все <span class="n">11</span></button><button>К выгрузке <span class="n">10</span></button><button>С замечаниями <span class="n">2</span></button></div>
        <span class="banner warn opt" style="min-height:28px;padding-block:0">${I("warn", "s14")}<span><b>1 история</b> собрана по устаревшему требованию</span></span>
        <span class="grow"></span><button class="btn ghost sm" data-toast="Все узлы свёрнуты">Свернуть всё</button></div>
      <div class="pane-body scroll tree" role="tree" id="tree"></div>
    </section>
    <aside class="pane secondary inspector" id="story-insp"></aside>
    <aside class="pane secondary context">
      <div class="pane-head"><h2>Требование FR-2 в документе</h2><span class="grow"></span><button class="btn ghost sm" data-go="document">Открыть SRS</button></div>
      <div class="pane-body scroll"><div class="insp-body">
        <div class="insp-sec"><span class="cap">SRS v2 · раздел 3.1 «Заказы»</span><p class="story-text">Система должна позволять дилеру оформить заказ из корзины без участия менеджера, если сумма заказа вместе с неоплаченными заказами не превышает кредитный лимит дилера.</p></div>
        <div class="insp-sec"><span class="cap">Свидетельство</span>${evidence(atoms[7])}</div>
        <div class="insp-sec"><span class="cap">Связанные требования</span>${[atoms[8], atoms[4]].map(a => `<div class="simple-row" style="padding:var(--s-4) 0">${typeTag(a.t).replace(TYPES[a.t][0], a.code)}<h4 style="font-weight:400">${a.text}</h4></div>`).join("")}</div>
      </div></div>
    </aside>
  </div>`,

  export: () => `<div class="panes has-outline wide-outline">
    <aside class="pane secondary outline"><div class="pane-body scroll"><div class="skills-list">
      <div class="cap" style="padding:var(--s-4) var(--s-4) var(--s-3)">Куда выгружать</div>
      <button class="dest" aria-current="true"><span class="kind">${I("jira")}</span><b>Задачи в Jira</b><span class="status accent">10 к выгрузке</span><span class="sub">Проект DLR, подключено</span></button>
      <button class="dest"><span class="kind">${I("word")}</span><b>Документы в Word</b><span class="status">3 документа</span><span class="sub">Шаблон «Обычный»</span></button>
      <button class="dest"><span class="kind">${I("table")}</span><b>Матрица трассировки</b><span class="status">xlsx</span><span class="sub">От цитаты до задачи Jira</span></button>
      <button class="dest"><span class="kind">${I("mail")}</span><b>Письмо заказчику</b><span class="status">3 вопроса</span><span class="sub">Вопросы и поручения</span></button>
    </div></div></aside>
    <section class="pane"><div class="pane-body scroll">
      <div style="padding:var(--s-8) var(--gutter) var(--s-6);display:grid;gap:var(--s-7)">
        <div class="counts"><div><b>10</b><span>создать</span></div><div><b>2</b><span>обновить</span></div><div><b>5</b><span>без изменений</span></div><div><b>6</b><span>пропустить</span></div><div><b style="color:var(--c-warn)">1</b><span>есть в Jira, нет в бэклоге</span></div></div>
        <div class="banner info">${I("info")}<span><b style="color:inherit">Предпросмотр ничего не меняет в Jira.</b> Задачи появятся только после кнопки «Выгрузить». Цитаты заказчика в описания не попадут: проект помечен как NDA.</span></div>
      </div>
      <table class="table"><thead><tr><th style="width:36px"><input type="checkbox" class="cb" checked aria-label="Выбрать все"></th><th>Задача</th><th>Тип</th><th class="c-wide">Требование</th><th class="c-wide">Приоритет</th><th>Ключ</th><th>Действие</th></tr></thead><tbody>
      ${backlog.filter(b => b.lvl !== "sub").map(b => `<tr><td><input type="checkbox" class="cb" ${b.on ? "checked" : ""} aria-label="Выгружать"></td>
        <td><div class="name" style="padding-left:${b.lvl === "story" ? 20 : 0}px"><span class="glyph ${b.lvl === "epic" ? "e" : "s"}">${b.lvl === "epic" ? "E" : "S"}</span><span style="font-weight:${b.lvl === "epic" ? 600 : 400}">${b.title}</span></div></td>
        <td class="t2">${b.lvl === "epic" ? "Эпик" : "История"}</td><td class="c-wide mono t2">${b.ref || ""}</td><td class="c-wide t2">${b.pr || ""}</td>
        <td class="mono">${b.key ? `<a href="#">${b.key}</a>` : '<span class="t3">—</span>'}</td>
        <td>${!b.on ? '<span class="status">Пропустить</span>' : b.stale ? `<span class="status warn">${I("refresh", "s12")}Обновить</span>` : b.key ? `<span class="status">Без изменений</span>` : `<span class="status ok">${I("plus", "s12")}Создать</span>`}</td></tr>`).join("")}
      </tbody></table></div></section>
  </div>`,

  skills: () => `<div class="panes has-outline wide-outline has-inspector ${S.inspector ? "" : "no-insp"}">
    <aside class="pane secondary outline"><div class="pane-body scroll"><div class="skills-list">
      ${skills.map(([g, items]) => `<div class="cap" style="padding:var(--s-5) var(--s-4) var(--s-3)">${g}</div>` + items.map(([id, name, sub, tag, cur]) => `<button class="sk-row" ${cur ? 'aria-current="true"' : ""}>${I(g === "Шаблоны Word" ? "word" : "spark", "s14")}<b class="trunc">${name}</b>${tag === "own" ? '<span class="badge accent">Свой</span>' : tag === "off" ? "" : ""}<span class="sub trunc">${sub}</span></button>`).join("")).join("")}
    </div></div></aside>
    <section class="pane">
      <div class="editor-head"><div style="display:flex;gap:var(--s-4);align-items:center"><h2>Извлечение требований</h2><span class="badge accent">Свой</span><span class="badge">версия 3</span></div>
        <p>Находит в источнике требования шести типов и цитату-свидетельство для каждого. Работает на шаге «Источники → Требования».</p></div>
      <div class="tabs" role="tablist">${[["Инструкции", 1], ["Правила", 0, 4], ["Попробовать", 0], ["Контракт", 0], ["История", 0, 3]].map(([t, on, n]) => `<button role="tab" aria-selected="${!!on}">${t}${n ? ` <span class="n">${n}</span>` : ""}</button>`).join("")}</div>
      <div class="pane-body scroll"><div class="editor-body split">
        <div style="display:grid;gap:var(--s-4);align-content:start"><div style="display:flex;align-items:center;gap:var(--s-4)"><span class="cap">Инструкции для ИИ</span><span class="grow"></span><span class="status warn">${I("pencil", "s12")}Есть несохранённые изменения</span></div>
<div class="code" contenteditable="true" spellcheck="false"><span class="hd"># Роль</span>
Ты старший бизнес-аналитик. Ты читаешь один источник проекта (транскрипт звонка, письмо или документ) и выделяешь из него атомы требований: короткие, самостоятельные, проверяемые утверждения.

<span class="hd"># Типы</span>
- business: чего хочет добиться бизнес и зачем. Цель, результат, правило, метрика.
- functional: поведение системы. «Дилер видит остатки по каждому складу».
- nfr: качество или ограничение. С числом, если оно прозвучало.
- risk: неопределённое событие, которое может навредить проекту.
- current: факт о том, как работа устроена сейчас.
- question: то, что осталось открытым или противоречит сказанному раньше.

<span class="hd"># Правила</span>
- Одно утверждение — один атом. Не объединяй «поиск по номеру и по имени».
- Формулируй от роли: «Дилер оформляет…», а не «Система должна позволять…».
- Цитата дословная, на языке источника: <span class="var">{language}</span>.
<span class="cm">- Поручения людям («пришлю до пятницы») не являются требованиями.</span>

<span class="hd"># Словарь проекта</span>
<span class="var">{glossary}</span></div></div>
        <div style="display:grid;gap:var(--s-4);align-content:start"><div style="display:flex;align-items:center;gap:var(--s-4)"><span class="cap">Проверка на источнике</span><span class="grow"></span><button class="popbtn">Созвон по складу и остаткам${I("updown", "s12")}</button><button class="btn sm" data-toast="Пробный запуск: 14 требований">${I("play", "s12")}Запустить</button></div>
          <div class="banner">${I("info")}<span>Пробный запуск ничего не сохраняет. Ниже — чем результат отличается от текущих требований.</span></div>
          <div>${[["ins", "fr", "Дилер видит дату следующей поставки для позиции, которой нет на складе"], ["ins", "as", "Остатки рассылаются дилерам раз в день файлом Excel"], ["del", "fr", "Олег пришлёт выгрузку заказов за 2025 год"], ["", "fr", "Дилер видит остатки по каждому складу с задержкой не более 15 минут"], ["", "rsk", "Выгрузка остатков из 1С может не выдержать обмен чаще раза в час"]]
            .map(([d, t, text]) => `<div class="simple-row">${typeTag(t)}<h4 style="font-weight:400">${d === "ins" ? `<ins>${text}</ins>` : d === "del" ? `<del>${text}</del>` : text}</h4><span class="status ${d === "ins" ? "ok" : d === "del" ? "danger" : ""}">${d === "ins" ? "Появится" : d === "del" ? "Исчезнет" : "Без изменений"}</span></div>`).join("")}</div>
        </div>
      </div></div>
    </section>
    <aside class="pane secondary inspector">
      <div class="pane-head"><h2>Сведения</h2></div>
      <div class="pane-body scroll"><div class="insp-body">
        <div class="insp-sec"><span class="cap">Где используется</span>
          <div class="form-card"><div class="form-row"><div class="lab">Портал дилера</div><div class="ctl"><input type="checkbox" class="switch" checked aria-label="Использовать в проекте «Портал дилера»"></div><p>Этот проект. Применяется при каждом извлечении.</p></div>
          <div class="form-row"><div class="lab">Остальные и новые проекты</div><div class="ctl"><input type="checkbox" class="switch" aria-label="Использовать по умолчанию"></div><p>Сейчас там работает встроенный скилл.</p></div></div></div>
        <div class="insp-sec"><span class="cap">О скилле</span><dl class="kv"><dt>Имя</dt><dd class="mono">extract-requirements-dealer</dd><dt>Основан на</dt><dd>Извлечение требований (встроенный, v3)</dd><dt>Шаг</dt><dd>Источники → Требования</dd><dt>Изменён</dt><dd>22 сент., 16:40</dd></dl></div>
        <div class="insp-sec"><span class="cap">История</span><ul class="timeline"><li><time>22 сент., 16:40</time><span>Версия 3 · добавлен словарь проекта</span></li><li><time>20 сент., 11:12</time><span>Версия 2 · формулировка от роли</span></li><li><time>19 сент., 09:30</time><span>Версия 1 · копия встроенного</span></li></ul></div>
        <div class="insp-sec"><button class="btn danger" data-act="confirm-delete" style="justify-self:start">${I("trash")}Удалить скилл…</button></div>
      </div></div>
    </aside>
  </div>`,

  settings: () => `<div class="panes has-outline has-context no-inspector">
    <aside class="pane secondary outline"><div class="pane-body scroll"><div class="outline-body">
      ${[["doc", "Проект", 1], ["spark", "Модель ИИ"], ["mic", "Запись и распознавание"], ["jira", "Jira"], ["sun", "Вид и язык"], ["info", "О программе"]].map(([i, t, c]) => `<button class="ol-row" ${c ? 'aria-current="true"' : ""}>${I(i)}<span class="grow">${t}</span></button>`).join("")}
    </div></div></aside>
    <section class="pane"><div class="pane-body scroll"><div class="form">
      <div class="form-group"><h3>Проект</h3><div class="form-card">
        <div class="form-row"><label for="pn">Название</label><div class="ctl"><input id="pn" class="field" value="Портал дилера" style="width:280px"></div><p>Попадает на титульный лист документов и в описания задач Jira.</p></div>
        <div class="form-row"><div class="lab">Только локально</div><div class="ctl"><input type="checkbox" class="switch" aria-label="Только локально"></div><p>ИИ работает на этом компьютере, текст источников не уходит в облако.</p></div>
        <div class="form-row"><div class="lab">Язык результатов</div><div class="ctl"><div class="seg"><button aria-pressed="true">Как в источниках</button><button>Русский</button><button>English</button></div></div><p>На этом языке ИИ пишет сводки, требования, документы и истории.</p></div>
        <div class="form-row"><div class="lab">Извлекать требования сразу</div><div class="ctl"><input type="checkbox" class="switch" checked aria-label="Извлекать требования сразу"></div><p>После распознавания записи требования появятся без вашего участия.</p></div>
        <div class="form-row"><div class="lab">Что попадает в Jira</div><div class="ctl"><div class="seg"><button>Цитаты</button><button aria-pressed="true">Только ссылки</button><button>Ничего</button></div></div><p>Дословные цитаты заказчика видит вся команда разработки.</p></div>
      </div></div>
      <div class="form-group"><h3>Модель ИИ</h3><div class="form-card">
        <div class="form-row"><div class="lab">Где работает ИИ</div><div class="ctl"><div class="seg"><button aria-pressed="true">Claude · облако</button><button>Встроенная</button><button>Ollama</button></div></div><p>Лучшее качество. В Anthropic уходит только текст, аудио остаётся на компьютере.</p></div>
        <div class="form-row"><label for="key">Ключ Anthropic API</label><div class="ctl"><input id="key" class="field mono" value="sk-ant-••••••••••••4f2a" style="width:220px"><button class="btn" data-toast="Ключ работает">Проверить</button></div><p><span class="status ok">${I("check", "s12")}Ключ проверен сегодня в 09:58</span></p></div>
        <div class="form-row"><div class="lab">Модель</div><div class="ctl"><button class="popbtn">Claude Opus · лучшее качество${I("updown", "s12")}</button></div><p>Быстрая модель дешевле, но чаще пропускает нефункциональные требования.</p></div>
      </div></div>
      <div class="form-group"><h3>Файл проекта</h3><div class="form-card">
        <div class="form-row"><div class="lab">Сохранить проект в файл</div><div class="ctl"><button class="btn">${I("export")}Сохранить проект…</button></div><p>Источники, требования, версии документов, бэклог и история в одном файле.</p></div>
        <div class="form-row"><div class="lab">Отправить в архив</div><div class="ctl"><button class="btn danger" data-act="confirm-delete">Отправить в архив…</button></div><p>Проект исчезнет из списка. Его можно вернуть в любой момент.</p></div>
      </div></div>
    </div></div></section>
    <aside class="pane secondary context"><div class="pane-head"><h2>Состояние системы</h2></div><div class="pane-body scroll"><div class="insp-body">
      <div class="insp-sec"><span class="cap">Этот компьютер</span><dl class="kv"><dt>Процессор</dt><dd>Apple M3 Pro · 18 ГБ</dd><dt>Ускорение</dt><dd><span class="status ok">${I("check", "s12")}Metal</span></dd><dt>Свободно</dt><dd class="num">308 ГБ</dd></dl></div>
      <div class="insp-sec"><span class="cap">Распознавание речи</span><dl class="kv"><dt>Модель</dt><dd>GigaAM v3 · локально</dd><dt>Спикеры</dt><dd><span class="status ok">${I("check", "s12")}Разделение включено</span></dd><dt>ffmpeg</dt><dd><span class="status ok">${I("check", "s12")}Найден</span></dd></dl></div>
      <div class="insp-sec"><span class="cap">Данные</span><dl class="kv"><dt>Папка</dt><dd class="trunc">~/Library/…/RequirementsWorkbench</dd><dt>Проектов</dt><dd class="num">4</dd><dt>Версия</dt><dd class="num">4.0.0</dd></dl></div>
    </div></div></aside>
  </div>`,
};

/* ---------------- Pieces ---------------- */
function hl(text) { const m = text.match(/^(.*?[.?!…])\s+(.*)$/); return m ? `<mark>${m[1]}</mark> ${m[2]}` : `<mark>${text}</mark>`; }
function countFilter(k) { return k === "all" ? atoms.length : k === "conflict" ? atoms.filter(a => a.conflict).length : atoms.filter(a => a.st === k).length; }
function visibleAtoms() { return atoms.filter(a => S.filter === "all" || (S.filter === "conflict" ? a.conflict : a.st === S.filter)); }

function sourceAtoms() {
  const s = srcById[S.source], l = atoms.filter(a => a.src === S.source);
  return `<aside class="pane secondary context">
      <div class="pane-head"><h2>Требования из источника</h2><span class="t3 num">${s.a + s.p + s.r}</span><span class="grow"></span><span class="status ok">${s.a} принято</span></div>
      <div class="pane-body scroll">${l.map(a => `<button class="row" data-go="atoms" data-atom="${a.id}" style="grid-template-columns:52px minmax(0,1fr);padding-inline:var(--s-6)">${typeTag(a.t)}<div><div class="row-title" style="font-size:var(--t-body);line-height:var(--lh-body)">${a.text}</div><div class="row-meta"><span class="mono">${a.at}</span><span class="sep"></span>${statusTag(a.st)}</div></div></button>`).join("")}</div>
    </aside>`;
}
function sourcePreview() {
  const s = srcById[S.source], n = s.a + s.p + s.r;
  return `<aside class="pane secondary inspector"><div class="pane-body scroll"><div class="insp-body">
    <div class="insp-sec"><span class="cap">${s.kind === "wave" ? "Запись звонка" : s.kind === "mail" ? "Письмо" : "Документ"} · ${s.date}</span><h2 class="insp-statement">${s.title}</h2></div>
    <div style="display:flex;gap:var(--s-4);flex-wrap:wrap"><button class="btn primary" data-go="source">Открыть транскрипт ${K("↵")}</button><button class="btn" data-go="atoms">Требования · ${n}</button></div>
    <div class="insp-sec"><span class="cap">Сводка</span><div class="prose"><p>Руководитель продаж хочет перевести дилеров на самостоятельное оформление заказов, чтобы разгрузить менеджеров и сократить ошибки ручного ввода.</p><ul><li><b>Цель:</b> доля заказов по телефону с 70% до 20% за год.</li><li><b>Сейчас:</b> до 25 минут ручного ввода на заказ.</li><li><b>Открыто:</b> кто согласует кредитный лимит.</li></ul></div></div>
    <div class="insp-sec"><span class="cap">Сведения</span><dl class="kv"><dt>Участники</dt><dd>${s.who}</dd><dt>Объём</dt><dd class="num">${s.len}</dd><dt>Требования</dt><dd class="num">${s.a} принято · ${s.p} на ревью · ${s.r} отклонено</dd><dt>Распознано</dt><dd>Локально, GigaAM v3</dd><dt>Файл</dt><dd class="trunc">interview-sales-14-09.m4a</dd></dl></div>
    <div class="insp-sec"><button class="btn danger" style="justify-self:start" data-toast="Источник удалён">${I("trash")}Удалить источник…</button></div>
  </div></div></aside>`;
}

function evidence(a) {
  const s = srcById[a.src];
  return `<div class="evidence"><div class="evidence-head">${I(s.kind, "s14")}<b class="trunc">${s.title}</b><span class="grow"></span><span class="mono">${a.at}</span></div>
    <div class="ev-line"><span class="mono">…</span><span><span class="who">Анна Серова.</span> А какая задержка для вас допустима?</span></div>
    <div class="ev-line hit"><span class="mono">${a.at}</span><span><span class="who">${a.who}.</span> <mark>${a.quote}</mark></span></div>
    <div class="ev-line"><span class="mono">…</span><span><span class="who">Олег Шубин.</span> Это надо проверить на нашей стороне, я уточню.</span></div></div>`;
}

function contextTranscript(atomId) {
  const a = atoms.find(x => x.id === atomId) || atoms[0];
  const lines = [[1, "…", "Анна Серова", "Давайте про остатки. Как дилер узнаёт о них сегодня?"], [3, "11:58", "Олег Шубин", "Каждое утро рассылаем файл. К обеду он уже неактуален, и дилеры начинают звонить."],
    [1, "12:30", "Анна Серова", "А какая задержка для вас допустима?"], [2, a.at, a.who, a.quote, true], [3, "13:20", "Олег Шубин", "Это надо проверить на нашей стороне, я уточню у команды 1С."], [1, "13:45", "Анна Серова", "Хорошо, запишу как риск. Двигаемся к отгрузкам?"], [2, "14:02", "Ирина Власова", "Да. Половина звонков менеджерам — это «где моя машина с товаром»."]];
  return `<div class="transcript">${lines.map(([s, t, who, text, hit]) => `<div class="seg-line ${hit ? "playing" : ""}"><time class="mono">${t}</time><span class="spk s${hit ? 2 : s}"><span class="trunc">${who}</span></span><p class="seg-text">${hit ? `<mark>${text}</mark>` : text}</p></div>`).join("")}</div>`;
}

function paper(old) {
  const req = (id, t, html, foot = "", cls = "") => `<div class="req ${cls}" data-req="${id}"><span class="req-id type ${t} plain">${id}</span><p>${html}</p><div class="req-foot">${foot}</div></div>`;
  const chip = (s, at) => `<button class="chip" data-go="source">${I("wave", "s12")}<span class="trunc">${s}</span><span class="mono t3">${at}</span></button>`;
  const d = S.compare && !old;
  return `<article class="paper" ${old ? 'style="opacity:.92"' : ""}>
    <div class="paper-kicker num">SRS · версия ${old ? "1 · на согласовании · 19 сент." : "2 · черновик · 24 требования · 23 сент., 18:20"}</div>
    <h1>Портал дилера. Спецификация требований</h1>
    <h2 style="margin-top:0">1. Назначение документа</h2>
    <p>Документ описывает требования к порталу, через который дилеры ООО «Северный путь» самостоятельно оформляют заказы, видят остатки и отслеживают отгрузки. Он служит основой для оценки, разработки и приёмки первой очереди.</p>
    <h2>2. Контекст и допущения</h2>
    <p>Сегодня 70% заказов приходят по телефону и почте. Менеджер переносит каждый заказ в 1С вручную и тратит на это до 25 минут. Остатки рассылаются дилерам раз в день файлом Excel.</p>
    <div class="req" style="box-shadow:inset 2px 0 0 var(--c-line-control);border-radius:0 var(--r-md) var(--r-md) 0;background:var(--c-fill-1);margin-top:var(--s-5)"><span class="cap">Свой текст · закреплён, пересборка его не изменит</span><p>Согласовано с заказчиком 12 сентября: первая очередь охватывает только дилеров из России.</p></div>
    <h2>3. Функциональные требования</h2>
    <h3>3.1 Заказы</h3>
    ${req("FR-2", "fr", old ? "Дилер оформляет заказ из корзины без участия менеджера." : `Дилер оформляет заказ из корзины без участия менеджера${d ? "<ins>, если сумма заказа не превышает кредитный лимит</ins>" : ", если сумма заказа не превышает кредитный лимит"}.`, chip("Интервью с руководителем продаж", "08:15") + (old ? "" : `<span class="chip mono">DLR-102</span>`))}
    ${req("FR-5", "fr", "Дилер получает уведомление на почту при каждой смене статуса заказа.", chip("Интервью с руководителем продаж", "27:45") + (old ? "" : `<span class="chip mono">DLR-105</span>`))}
    ${req("FR-7", "fr", `Менеджер видит историю заказов дилера ${old ? "за 12 месяцев" : d ? "за <del>12</del> <ins>24</ins> месяца" : "за 24 месяца"}.`, chip("Интервью с руководителем продаж", "44:10"))}
    <h3>3.2 Остатки и отгрузки</h3>
    ${req("FR-1", "fr", "Дилер видит остатки по каждому складу с задержкой не более 15 минут.", chip("Созвон по складу и остаткам", "12:41") + (old ? "" : `<span class="badge warn">Требование изменилось после сборки</span>`), old ? "" : "stale sel")}
    ${req("FR-4", "fr", "Дилер быстро находит статус отгрузки по номеру заказа.", chip("Созвон по складу и остаткам", "02:10") + (old ? "" : `<span class="badge warn">Размыто: «быстро»</span>`))}
    ${old ? "" : `<h2>4. Нефункциональные требования</h2>
    ${req("NFR-1", "nfr", "Вход в кабинет дилера защищён двухфакторной аутентификацией.", `<button class="chip" data-go="source">${I("mail", "s12")}<span class="trunc">Письмо: требования ИБ</span><span class="mono t3">стр. 1</span></button>`)}
    ${req("NFR-3", "nfr", "Страница каталога открывается не дольше 2 секунд при 500 одновременных пользователях.", chip("Интервью с руководителем продаж", "21:03") + `<span class="badge danger">Конфликт с NFR-7</span>`)}`}
  </article>`;
}

function renderFindings() {
  const f = [["warn", "FR-4", "Размытая формулировка", "«Быстро» нельзя проверить. Укажите время или число действий.", "Дилер находит статус отгрузки по номеру заказа не более чем за 2 действия."],
             ["danger", "NFR-3", "Конфликт требований", "NFR-3 и NFR-7 задают разное время открытия каталога: 2 и 1 секунда.", ""],
             ["warn", "FR-7", "Нет роли", "Не указано, видит ли историю сам дилер или только менеджер.", "Менеджер и дилер видят историю заказов дилера за 24 месяца."]];
  $("#findings").innerHTML = `<div class="banner warn">${I("warn")}<span><b>2 раздела устарели.</b> После сборки изменились FR-1 и FR-7.</span></div>` + f.map(([k, id, h, p, fix], i) => `
    <div class="finding" role="button" tabindex="0" data-finding="${i}" ${S.finding === i ? 'aria-selected="true"' : ""}>
      <div class="finding-head"><span class="status ${k}">${I("warn", "s12")}${h}</span><span class="grow"></span><span class="mono t3">${id}</span></div>
      <p>${p}</p>${fix ? `<div class="fix"><span class="cap" style="display:block;margin-bottom:2px">Предложение ИИ</span>${fix}</div>` : ""}
      <div class="finding-actions">${fix ? `<button class="btn sm primary" data-toast="Требование ${id} исправлено · блок обновлён">Принять исправление</button><button class="btn sm">Изменить…</button>` : `<button class="btn sm primary" data-go="atoms">Разобрать конфликт</button>`}<button class="btn sm ghost" data-toast="Замечание скрыто">Скрыть</button></div>
    </div>`).join("");
}

function renderAtoms() {
  const list = visibleAtoms();
  if (!list.find(a => a.id === S.atom) && list[0]) S.atom = list[0].id;
  const el = $("#atom-list"); if (!el) return;
  el.classList.toggle("selecting", S.checked.size > 0);
  el.innerHTML = list.length ? `<div class="list-head"><input type="checkbox" class="cb" id="check-all" aria-label="Выбрать все показанные" ${S.checked.size && S.checked.size === list.length ? "checked" : ""}><span class="cap">Тип</span><span class="cap">Требование</span><span class="cap col-x">Источник</span><span class="cap col-x">Спикер</span><span class="cap col-x">Приоритет</span><span class="cap" style="justify-self:end">Статус</span></div>` +
    list.map(a => `<div class="row ${a.st} ${a.id === S.atom ? "focus" : ""}" role="option" tabindex="${a.id === S.atom ? 0 : -1}" data-atom="${a.id}" aria-selected="${S.checked.has(a.id) || a.id === S.atom}">
      <input type="checkbox" class="cb" data-check="${a.id}" ${S.checked.has(a.id) ? "checked" : ""} aria-label="Выбрать">
      ${typeTag(a.t).replace(TYPES[a.t][0], a.code)}
      <div><div class="row-title">${a.text}</div><div class="row-quote">«${a.quote}»</div>
        <div class="row-meta"><span class="m-src">${srcById[a.src].title}</span><span class="sep m-src"></span><span class="mono">${a.at}</span>${a.conflict ? `<span class="sep"></span><span class="conf">${I("warn", "s12")}Конфликт с ${atoms.find(x => x.id === a.conflict).code}</span>` : ""}${a.reason ? `<span class="sep"></span><span>${a.reason}</span>` : ""}</div></div>
      <span class="col-x trunc">${srcById[a.src].title}</span><span class="col-x trunc">${a.who}</span><span class="col-x">${a.pr}</span>
      <span class="col-status">${statusTag(a.st)}</span>
    </div>`).join("")
    : `<div class="empty"><div class="empty-glyph">${I("check", "s20")}</div><h3>Здесь пусто</h3><p>В этом фильтре нет требований. Все новые требования разобраны.</p><button class="btn primary lg" data-go="document">Обновить документ${I("arrow-r")}</button></div>`;
  renderInspector(); renderBulk();
}

function renderInspector() {
  const a = atoms.find(x => x.id === S.atom); const el = $("#atom-insp"); if (!el || !a) return;
  const other = a.conflict && atoms.find(x => x.id === a.conflict);
  el.innerHTML = `<div class="pane-head">${typeTag(a.t).replace(TYPES[a.t][0], a.code)}<span class="t3">${TYPES[a.t][1]}</span><span class="grow"></span>${statusTag(a.st)}</div>
    <div class="pane-body scroll"><div class="insp-body">
      <h2 class="insp-statement">${a.text}</h2>
      ${other ? `<div class="conflict"><h4>${I("warn", "s14")}Противоречит другому требованию</h4>
        <div class="conflict-sides"><div class="conflict-side"><b>A</b><span>${a.text} <span class="t3">· ${a.who}, ${srcById[a.src].date}</span></span></div><div class="conflict-side"><b>B</b><span>${other.text} <span class="t3">· ${other.who}, ${srcById[other.src].date}</span></span></div></div>
        <div class="conflict-actions"><button class="btn sm" data-toast="Оставлено A · B отклонено">Оставить A</button><button class="btn sm" data-toast="Оставлено B · A отклонено">Оставить B</button><button class="btn sm">Объединить…</button><button class="btn sm" data-toast="Вопрос добавлен во вкладку «Для заказчика»">Спросить заказчика</button></div></div>` : ""}
      <div class="insp-sec"><span class="cap">Свидетельство</span>${evidence(a)}</div>
      <div class="insp-sec"><span class="cap">Свойства</span><dl class="kv"><dt>Тип</dt><dd><button class="popbtn" style="height:24px">${TYPES[a.t][1]}${I("updown", "s12")}</button></dd><dt>Приоритет</dt><dd><button class="popbtn" style="height:24px">${a.pr === "—" ? "Не задан" : a.pr}${I("updown", "s12")}</button></dd><dt>Спикер</dt><dd>${a.who}</dd><dt>В документах</dt><dd>${a.st === "accepted" ? `<a href="#/document">SRS v2 · раздел 3.2</a>` : '<span class="t3">Пока нет: требование не принято</span>'}</dd><dt>Модель</dt><dd class="t2">Claude Opus</dd></dl></div>
      <div class="insp-sec"><span class="cap">История</span><ul class="timeline"><li><time>24 сент., 10:42</time><span>Извлечено из источника</span></li>${a.st !== "pending" ? `<li><time>24 сент., 11:05</time><span>${ST[a.st][0]} · Анна Серова</span></li>` : ""}</ul></div>
    </div></div>
    <div class="insp-foot"><button class="btn primary" data-decide="accepted">${I("check")}Принять ${K("A")}</button><button class="btn" data-decide="rejected">${I("x")}Отклонить ${K("X")}</button><button class="btn" data-toast="Правка формулировки">${I("pencil")}Править ${K("E")}</button></div>`;
  const ctx = $("#atom-ctx");
  if (ctx) ctx.innerHTML = `<div class="pane-head"><h2 class="trunc">${srcById[a.src].title}</h2><span class="grow"></span><button class="btn ghost sm" data-go="source">Открыть источник ${K("↵")}</button></div><div class="pane-body scroll">${contextTranscript(a.id)}</div>
    <div class="player"><button class="play" aria-label="Слушать цитату" title="Слушать цитату · пробел">${I("play", "s14")}</button><span class="mono t2">${a.at}</span><div class="wave-wrap"><div class="wave"></div></div></div>`;
}

function renderBulk() {
  const el = $("#bulk"); if (!el) return; const n = S.checked.size;
  const conf = [...S.checked].filter(id => atoms.find(a => a.id === id).conflict).length;
  el.classList.toggle("on", n > 0);
  el.innerHTML = `<b class="num">Выбрано: ${n}</b>${conf ? `<span class="t-conf num">в конфликтах: ${conf}</span>` : ""}<span class="sep"></span>
    <button class="btn primary" data-bulk="accepted">Принять ${n - conf} ${K("A")}</button><button class="btn" data-bulk="rejected">Отклонить ${K("X")}</button><button class="btn opt">Тип…</button><button class="btn opt">Приоритет…</button>
    <span class="sep"></span><button class="btn ghost" data-bulk="clear">Снять выбор ${K("esc")}</button>`;
}

function renderTree() {
  const el = $("#tree"); if (!el) return; let hide = false, hideSub = false;
  el.innerHTML = `<div class="tree-head"><input type="checkbox" class="cb" checked aria-label="Все к выгрузке"><span class="cap">Задача</span><span class="cap col-x">Критерии</span><span class="cap col-x">INVEST</span><span class="cap col-x">Требование</span><span class="cap col-x">Приоритет</span><span class="cap">Jira</span></div>` +
    backlog.map((b, i) => {
      if (b.lvl === "epic") { hide = !b.open; hideSub = false; } else if (hide) return ""; if (b.lvl === "story") hideSub = !b.open; else if (b.lvl === "sub" && hideSub) return "";
      const tw = b.lvl === "sub" ? "" : `<span class="twist ${b.open ? "open" : ""}" data-twist="${i}">${I("chev-r", "s12")}</span>`;
      const g = b.lvl === "epic" ? "e" : b.lvl === "story" ? "s" : "t";
      return `<div class="node ${b.lvl} ${b.on ? "" : "off"}" role="treeitem" tabindex="-1" ${b.id ? `data-story="${b.id}"` : ""} aria-selected="${b.id === S.story}">
        <input type="checkbox" class="cb inc" ${b.on ? "checked" : ""} aria-label="Выгружать в Jira">
        <div class="node-title">${tw}<span class="glyph ${g}">${g.toUpperCase()}</span><span class="trunc">${b.title}</span>${b.stale ? `<span class="badge warn">Устарела</span>` : ""}${b.goal ? `<span class="t3 trunc opt" style="font-weight:400;font-size:var(--t-body)">${b.goal}</span>` : ""}</div>
        <span class="col-x num">${b.ac ? b.ac + " критерия" : ""}</span>
        <span class="col-x">${b.invest === "ok" ? `<span class="status ok">${I("check", "s12")}Годится</span>` : b.invest === "warn" ? `<span class="status warn">${I("warn", "s12")}Замечание</span>` : ""}</span>
        <span class="col-x mono">${b.ref || ""}</span><span class="col-x">${b.pr || ""}</span>
        <span class="mono">${b.key ? `<a href="#">${b.key}</a>` : `<span class="t3">${b.on ? "новая" : "—"}</span>`}</span></div>`; }).join("");
  const s = backlog.find(b => b.id === S.story) || backlog[1];
  $("#story-insp").innerHTML = `<div class="pane-head"><span class="glyph s">S</span><span class="t3">История</span><span class="grow"></span>${s.key ? `<a class="mono" href="#">${s.key}</a>` : '<span class="status accent">Новая</span>'}</div>
    <div class="pane-body scroll"><div class="insp-body">
      <h2 class="insp-statement">${s.title}</h2>
      <p class="story-text"><b>Как</b> дилер, <b>я хочу</b> оформить заказ из корзины сам, <b>чтобы</b> не ждать, пока менеджер перенесёт его в 1С.</p>
      ${s.invest === "warn" ? `<div class="banner warn" style="align-items:flex-start">${I("warn")}<span><b>INVEST · S.</b> История слишком большая для одного спринта. Разделите на просмотр и на поиск.</span><button class="btn sm">Разделить</button></div>` : ""}
      <div class="insp-sec"><span class="cap">Критерии приёмки · ${s.ac}</span><div class="ac">${[["заказ на 180 000 ₽, свободный лимит 250 000 ₽", "дилер нажимает «Оформить»", "заказ создан со статусом «Принят», менеджер не участвует"], ["заказ на 300 000 ₽, свободный лимит 250 000 ₽", "дилер нажимает «Оформить»", "заказ уходит на согласование, дилер видит причину"], ["в корзине есть позиция без остатка", "дилер открывает корзину", "позиция помечена, оформление недоступно"]]
        .map(([g, w, t]) => `<div class="ac-item"><div class="ac-row"><b>Дано</b><span>${g}</span></div><div class="ac-row"><b>Когда</b><span>${w}</span></div><div class="ac-row"><b>Тогда</b><span>${t}</span></div></div>`).join("")}</div>
        <button class="btn sm ghost" style="justify-self:start">${I("plus", "s14")}Добавить критерий</button></div>
      <div class="insp-sec"><span class="cap">Свойства</span><dl class="kv"><dt>Эпик</dt><dd>Самостоятельное оформление заказа</dd><dt>Требование</dt><dd><a href="#/document" class="mono">${s.ref}</a> · SRS v2, раздел 3.1</dd><dt>Приоритет</dt><dd><button class="popbtn" style="height:24px">${s.pr}${I("updown", "s12")}</button></dd><dt>Выгружать</dt><dd><input type="checkbox" class="switch" checked aria-label="Выгружать в Jira"></dd><dt>Правки</dt><dd class="t2">Закреплены: пересборка их сохранит</dd></dl></div>
    </div></div>
    <div class="insp-foot"><button class="btn" data-toast="Правка истории">${I("pencil")}Править ${K("E")}</button><button class="btn" data-toast="Подзадача добавлена">${I("plus")}Подзадача</button><button class="btn danger" data-act="confirm-delete">Удалить…</button></div>`;
}

/* ---------------- Render + routing ---------------- */
function render() {
  nav(); toolbar();
  $("#workspace").innerHTML = `<div class="screen on">${screens[S.screen]()}</div>`;
  if (S.screen === "atoms") renderAtoms();
  if (S.screen === "document") { renderFindings(); const r = $(".req.sel"); if (r) r.setAttribute("aria-selected", "true"); }
  if (S.screen === "backlog") renderTree();
  document.title = `${TB[S.screen]()[0].replace(/<[^>]+>/g, "")} — Requirements Workbench`;
}
function go(screen) { if (!screens[screen]) return; S.screen = screen; if (location.hash !== "#/" + screen) history.replaceState(null, "", "#/" + screen); render(); }

function toast(text, undo) {
  const t = document.createElement("div"); t.className = "toast"; t.innerHTML = `<span>${text}</span>${undo ? `<button>Отменить ${K("⌘Z")}</button>` : ""}`;
  if (undo) t.querySelector("button").onclick = () => { undo(); t.remove(); };
  const box = $("#toasts"); box.style.bottom = $("#bulk.on") ? "96px" : ""; box.append(t); while (box.children.length > 2) box.firstChild.remove();
  setTimeout(() => t.remove(), 10000);
}
function decide(ids, st) {
  const prev = ids.map(id => [id, atoms.find(a => a.id === id).st]);
  ids.forEach(id => atoms.find(a => a.id === id).st = st);
  const cur = visibleAtoms(); S.checked.clear();
  const next = cur.find(a => a.st === "pending"); if (next) S.atom = next.id;
  nav(); toolbar(); $("#atom-filter") && $$("#atom-filter button").forEach(b => b.querySelector(".n").textContent = countFilter(b.dataset.filter));
  renderAtoms();
  toast(`${ids.length === 1 ? "Требование" : ids.length + " требования"}: ${ST[st][0].toLowerCase()}`, () => { prev.forEach(([id, s]) => atoms.find(a => a.id === id).st = s); S.atom = prev[0][0]; render(); });
}

const isDark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
function setTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem("rw-proto-theme", t); } catch {} toolbar(); }
function setRail() { const app = $("#app"); const pref = app.dataset.rail; app.classList.toggle("rail", pref ? pref === "1" : innerWidth < 1180); }

const commands = [["home", "Обзор", "overview", "⌘0"], ["wave", "Источники", "sources", "⌘1"], ["atoms", "Требования", "atoms", "⌘2"], ["doc", "Документы", "document", "⌘3"], ["tree", "Бэклог", "backlog", "⌘4"], ["export", "Выгрузка", "export", "⌘5"], ["skills", "Скиллы", "skills", "⌘6"], ["gear", "Настройки", "settings", "⌘,"]];
function palette(open) {
  $("#scrim").classList.toggle("on", open); $("#palette").classList.toggle("on", open);
  if (!open) return; const q = $("#palette-q"); q.value = ""; fillPalette(""); q.focus();
}
function fillPalette(q) {
  const m = (s) => s.toLowerCase().includes(q.toLowerCase());
  const acts = [["mic", "Записать звонок", "", "⌘R"], ["import", "Импортировать файлы…", "", "⌘O"], ["refresh", "Обновить изменённое в SRS", "", ""], ["word", "Экспортировать SRS в Word", "", "⌘E"], ["mail", "Составить письмо заказчику", "", ""]].filter(c => m(c[1]));
  const nav = commands.filter(c => m(c[1])); const at = q ? atoms.filter(a => m(a.text) || m(a.code)).slice(0, 5) : [];
  const src = sources.filter(s => q && m(s.title)).slice(0, 4);
  let first = true; const on = () => { const r = first ? " on" : ""; first = false; return r; };
  $("#palette-list").innerHTML =
    (acts.length ? `<div class="cap">Действия</div>` + acts.map(c => `<button class="pl${on()}" data-toast="${c[1]}">${I(c[0])}<span>${c[1]}</span><span class="keys">${c[3] ? K(c[3]) : ""}</span></button>`).join("") : "") +
    (nav.length ? `<div class="cap">Перейти</div>` + nav.map(c => `<button class="pl${on()}" data-go="${c[2]}">${I(c[0])}<span>${c[1]}</span><span class="keys">${K(c[3])}</span></button>`).join("") : "") +
    (at.length ? `<div class="cap">Требования</div>` + at.map(a => `<button class="pl${on()}" data-go="atoms" data-atom="${a.id}">${I("atoms")}<span class="mono">${a.code}</span><span class="trunc">${a.text}</span></button>`).join("") : "") +
    (src.length ? `<div class="cap">Источники</div>` + src.map(s => `<button class="pl${on()}" data-go="source" data-src="${s.id}">${I(s.kind)}<span class="trunc">${s.title}</span><span class="keys t3">${s.date}</span></button>`).join("") : "") || `<div class="empty" style="padding:var(--s-9)"><p>Ничего не найдено по запросу «${q}»</p></div>`;
}
function sheet(kind) {
  const el = $("#sheet"); if (!kind) { el.classList.remove("on"); $("#scrim").classList.remove("on"); return; }
  el.innerHTML = kind === "push" ? `<h2 id="sheet-t">Выгрузить 12 задач в проект DLR?</h2><p class="t2">В Jira появятся новые задачи, две существующие будут обновлены. Отменить выгрузку из приложения нельзя.</p>
      <dl class="kv"><dt>Сайт</dt><dd>northway.atlassian.net</dd><dt>Проект</dt><dd>DLR · Dealer Portal</dd><dt>Создать</dt><dd class="num">10 задач</dd><dt>Обновить</dt><dd class="num">2 задачи: описание и критерии</dd><dt>Цитаты</dt><dd>Не выгружаются, только ссылки</dd></dl>
      <div class="sheet-actions"><button class="btn lg" data-act="sheet-close">Отмена</button><button class="btn lg primary" data-act="sheet-close" data-toast="Готово: 10 задач создано, 2 обновлено">Да, выгрузить в DLR ${K("⌘↵")}</button></div>`
    : `<h2 id="sheet-t">Удалить безвозвратно?</h2><p class="t2">Это действие затронет только выбранный объект. В течение 10 секунд его можно отменить.</p>
      <div class="sheet-actions"><button class="btn lg" data-act="sheet-close">Отмена</button><button class="btn lg" style="background:var(--c-danger-fill);color:#fff" data-act="sheet-close" data-toast="Удалено">Удалить</button></div>`;
  el.classList.add("on"); $("#scrim").classList.add("on"); el.querySelector("button").focus();
}

/* ---------------- Events ---------------- */
document.addEventListener("click", (e) => {
  const t = e.target;
  const check = t.closest("[data-check]"); if (check) { const id = +check.dataset.check; check.checked ? S.checked.add(id) : S.checked.delete(id); renderAtoms(); return; }
  if (t.id === "check-all") { const l = visibleAtoms(); S.checked = new Set(t.checked ? l.map(a => a.id) : []); renderAtoms(); return; }
  if (t.closest("input, .code")) return;
  const tw = t.closest("[data-twist]"); if (tw) { const b = backlog[+tw.dataset.twist]; b.open = !b.open; renderTree(); return; }
  const g = t.closest("[data-go]");
  const toastEl = t.closest("[data-toast]");
  const act = t.closest("[data-act]")?.dataset.act;
  if (act === "sheet-close") sheet(null);
  if (g) { if (g.dataset.src) S.source = g.dataset.src; if (g.dataset.atom) { S.atom = +g.dataset.atom; S.filter = "all"; } palette(false); go(g.dataset.go); if (toastEl) toast(toastEl.dataset.toast); return; }
  if (toastEl) { palette(false); toast(toastEl.dataset.toast); }
  if (act === "theme") setTheme(isDark() ? "light" : "dark");
  if (act === "sidebar") { const app = $("#app"); app.dataset.rail = app.classList.contains("rail") ? "0" : "1"; setRail(); }
  if (act === "inspector") { S.inspector = !S.inspector; const p = $(".panes"); p.classList.toggle("no-insp", !S.inspector); p.classList.toggle("insp-open", S.inspector); toolbar(); }
  if (act === "compare") { S.compare = !S.compare; render(); }
  if (act === "push") sheet("push");
  if (act === "confirm-delete") sheet("delete");
  if (act === "record") toast("Запись началась · системный звук и микрофон");
  if (act === "import") toast("Выберите файлы или перетащите их в окно");
  const f = t.closest("[data-filter]"); if (f) { S.filter = f.dataset.filter; S.checked.clear(); $$("#atom-filter button").forEach(b => b.setAttribute("aria-pressed", b === f)); renderAtoms(); return; }
  const d = t.closest("[data-decide]"); if (d) { decide([S.atom], d.dataset.decide); return; }
  const b = t.closest("[data-bulk]"); if (b) { if (b.dataset.bulk === "clear") { S.checked.clear(); renderAtoms(); } else decide([...S.checked].filter(id => b.dataset.bulk !== "accepted" || !atoms.find(a => a.id === id).conflict), b.dataset.bulk); return; }
  const row = t.closest(".row[data-atom]"); if (row && S.screen === "atoms") { S.atom = +row.dataset.atom; renderAtoms(); return; }
  const sa = t.closest(".seg-atom"); if (sa) { S.atom = +sa.dataset.atom; S.filter = "all"; go("atoms"); return; }
  const sr = t.closest("tr[data-src]"); if (sr) { if (S.source === sr.dataset.src) go("source"); else { S.source = sr.dataset.src; render(); } return; }
  const st = t.closest("[data-story]"); if (st) { S.story = st.dataset.story; renderTree(); return; }
  const fi = t.closest("[data-finding]"); if (fi) { S.finding = +fi.dataset.finding; renderFindings(); return; }
  const seg = t.closest(".seg button, .tabs button"); if (seg && !seg.dataset.filter) { const attr = seg.hasAttribute("aria-selected") ? "aria-selected" : "aria-pressed"; $$("button", seg.parentNode).forEach(x => x.setAttribute(attr, x === seg)); }
  const ol = t.closest(".ol-row, .sk-row, .dest, .ver"); if (ol) { $$("." + ol.classList[0], ol.parentNode).forEach(x => x.toggleAttribute("aria-current", false)); ol.setAttribute("aria-current", "true"); }
  if (t.id === "scrim") { palette(false); sheet(null); }
  if (t.closest("#cmd-open")) palette(true);
  if (t.closest("#proj")) toast("Проекты: Портал дилера, CRM контакт-центра, Склад 2.0");
});
$("#palette-q").addEventListener("input", e => fillPalette(e.target.value));
document.addEventListener("keydown", (e) => {
  const mod = e.metaKey || e.ctrlKey, typing = e.target.closest("input:not([type=checkbox]), textarea, [contenteditable]");
  if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); palette(!$("#palette").classList.contains("on")); return; }
  if (e.key === "Escape") { if ($("#palette.on") || $("#sheet.on")) { palette(false); sheet(null); } else if (S.checked.size) { S.checked.clear(); renderAtoms(); } return; }
  if ($("#palette.on")) { const items = $$("#palette-list .pl"), i = items.findIndex(x => x.classList.contains("on"));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); items[i]?.classList.remove("on"); const n = items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length]; n?.classList.add("on"); n?.scrollIntoView({ block: "nearest" }); }
    if (e.key === "Enter") items[i]?.click(); return; }
  if (mod && /^[0-6]$/.test(e.key)) { e.preventDefault(); go(commands[+e.key][2]); return; }
  if (mod && e.key === ",") { e.preventDefault(); go("settings"); return; }
  if (mod && e.key === "\\") { e.preventDefault(); $('[data-act="sidebar"]').click(); return; }
  if (mod && e.shiftKey && e.key.toLowerCase() === "l") { e.preventDefault(); setTheme(isDark() ? "light" : "dark"); return; }
  if (typing || mod) return;
  if (S.screen === "atoms") { const l = visibleAtoms(), i = l.findIndex(a => a.id === S.atom);
    if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); if (l[i + 1]) { S.atom = l[i + 1].id; renderAtoms(); $(".row.focus")?.scrollIntoView({ block: "nearest" }); } }
    if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); if (l[i - 1]) { S.atom = l[i - 1].id; renderAtoms(); $(".row.focus")?.scrollIntoView({ block: "nearest" }); } }
    if (e.key === "a") decide(S.checked.size ? [...S.checked] : [S.atom], "accepted");
    if (e.key === "x") decide(S.checked.size ? [...S.checked] : [S.atom], "rejected");
    if (e.key === " ") { e.preventDefault(); S.checked.has(S.atom) ? S.checked.delete(S.atom) : S.checked.add(S.atom); renderAtoms(); }
    if (e.key === "Enter") go("source"); }
  if (e.key === "/") { const s = $(".workspace .search input, .toolbar .search input"); if (s) { e.preventDefault(); s.focus(); } }
});
addEventListener("resize", setRail);
addEventListener("hashchange", () => { const s = location.hash.replace("#/", ""); if (screens[s] && s !== S.screen) go(s); });

/* ---------------- Boot ---------------- */
const params = new URLSearchParams(location.search);
try { const t = params.get("theme") || localStorage.getItem("rw-proto-theme"); if (t) document.documentElement.dataset.theme = t; } catch {}
if (params.get("select")) S.checked = new Set([1, 3, 4]);
if (params.get("compare")) S.compare = true;
setRail();
go(location.hash.replace("#/", "") || "overview");
if (params.get("palette")) palette(true);
})();
