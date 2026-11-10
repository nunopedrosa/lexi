'use strict';

var t = LexiI18n.t;
var listNode = document.getElementById('list');
var countNode = document.getElementById('count');
var statusNode = document.getElementById('status');
var moreButton = document.getElementById('more');
var searchInput = document.getElementById('search');
var prioritySelect = document.getElementById('priority');
var posSelect = document.getElementById('pos');
var sourceSelect = document.getElementById('source');
var languageSelect = document.getElementById('language');

var allRows = [];
var shown = 0;
var PAGE = 100;
var currentLanguage = 'pt-PT';

function norm(value) {
 return (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function readLanguage() {
 try {
  var raw = localStorage.getItem('lexi2.prefs');
  if (raw) {
   var prefs = JSON.parse(raw);
   var saved = LexiI18n.normalise(prefs && prefs.language);
   if (saved) return saved;
  }
  var legacy = LexiI18n.normalise(localStorage.getItem('lexi2.lang'));
  if (legacy) return legacy;
 } catch (error) {}
 var list = (navigator.languages && navigator.languages.length)
  ? navigator.languages
  : [navigator.language || ''];
 for (var i = 0; i < list.length; i++) {
  var next = LexiI18n.normalise(list[i]);
  if (next) return next;
 }
 return 'en';
}

function persistLanguage(value) {
 try {
  var prefs = { priberam: false, language: value };
  var raw = localStorage.getItem('lexi2.prefs');
  if (raw) {
   var existing = JSON.parse(raw);
   if (existing && typeof existing === 'object') prefs = existing;
  }
  prefs.language = value;
  prefs.priberam = !!prefs.priberam;
  localStorage.setItem('lexi2.prefs', JSON.stringify(prefs));
 } catch (error) {}
}

function setText(id, key) {
 var node = document.getElementById(id);
 if (node) node.textContent = t(key);
}

function setOptionText(select, value, text) {
 for (var i = 0; i < select.options.length; i++) {
  if (select.options[i].value === value) {
   select.options[i].textContent = text;
   return;
  }
 }
}

function languageAria() {
 var name = currentLanguage === 'en' ? t('language.nameEn') : t('language.namePt');
 return t('language.aria', { language: name });
}

function applyLanguage() {
 document.documentElement.lang = currentLanguage;
 document.title = t('missingPage.title') + ' — Lexi';
 setText('missing-subtitle', 'missingPage.subtitle');
 setText('page-title', 'missingPage.title');
 setText('page-intro', 'missingPage.intro');
 setText('search-label', 'missingPage.search');
 setText('priority-label', 'missingPage.priority');
 setText('pos-label', 'missingPage.pos');
 setText('source-label', 'missingPage.source');
 setText('back-link', 'missingPage.back');
 setText('csv-link', 'missingPage.downloadCsv');
 setText('json-link', 'missingPage.downloadJson');
 setText('more', 'missingPage.more');
 searchInput.placeholder = t('missingPage.searchPlaceholder');
 setOptionText(prioritySelect, '', t('missingPage.all'));
 setOptionText(sourceSelect, '', t('missingPage.all'));
 setOptionText(sourceSelect, 'hunspell', t('missingPage.sourceHunspell'));
 setOptionText(sourceSelect, 'curated', t('missingPage.sourceCurated'));
 if (posSelect.options.length) posSelect.options[0].textContent = t('missingPage.all');
 languageSelect.value = currentLanguage;
 languageSelect.setAttribute('aria-label', languageAria());
 renderCount();
}

function priorityLabel(value) {
 var key = 'missingPage.priority' + (value || 3);
 return t(key);
}

function sourceLabels(source) {
 var parts = String(source || '').split('+');
 var labels = [];
 for (var i = 0; i < parts.length; i++) {
  if (parts[i] === 'curated') labels.push(t('missingPage.sourceCurated'));
  else if (parts[i] === 'hunspell') labels.push(t('missingPage.sourceHunspell'));
  else if (parts[i]) labels.push(parts[i]);
 }
 return labels.join(' + ');
}

function noteLabels(notes) {
 var parts = String(notes || '').split(';');
 var labels = [];
 var map = {
  curated_supplement: 'missingPage.noteCurated',
  not_in_words_pt: 'missingPage.noteNotWords',
  near_da_candidate: 'missingPage.noteNear',
  preao90_not_in_natura_list: 'missingPage.notePreao',
  wikt_bridge: 'missingPage.noteWikt'
 };
 for (var i = 0; i < parts.length; i++) {
  var code = parts[i].trim();
  if (!code || code === 'no_da_entry') continue;
  var key = map[code];
  var text = key ? t(key) : code;
  if (labels.indexOf(text) < 0) labels.push(text);
 }
 return labels;
}

function detail(parent, text) {
 if (!text) return;
 var span = document.createElement('span');
 span.textContent = text;
 parent.appendChild(span);
}

function item(row) {
 var node = document.createElement('div');
 node.className = 'missing-item';

 var head = document.createElement('div');
 head.className = 'missing-head';
 var lemma = document.createElement('strong');
 lemma.className = 'missing-lemma';
 lemma.textContent = row[0];
 head.appendChild(lemma);

 var priority = document.createElement('span');
 priority.className = 'missing-tag';
 priority.textContent = priorityLabel(row[6]);
 head.appendChild(priority);

 var source = document.createElement('span');
 source.className = 'missing-tag';
 source.textContent = sourceLabels(row[7]);
 head.appendChild(source);
 node.appendChild(head);

 var details = document.createElement('div');
 details.className = 'missing-detail';
 var pos = (row[1] && row[1].length) ? row[1].join(' · ') : t('missingPage.posUnknown');
 detail(details, pos);
 if (row[2]) detail(details, t('missingPage.preao') + ': ' + row[2]);
 if (row[3]) detail(details, t('missingPage.near') + ': ' + row[3]);
 if (row[8]) detail(details, t('missingPage.note') + ': ' + row[8]);
 if (row[9]) detail(details, t('missingPage.wiktHeadword') + ': ' + row[9]);
 var notes = noteLabels(row[5]);
 for (var i = 0; i < notes.length; i++) detail(details, notes[i]);
 node.appendChild(details);
 return node;
}

function rowMatches(row) {
 var query = norm(searchInput.value.trim());
 if (query && norm(row[0]).indexOf(query) < 0) return false;
 if (prioritySelect.value && String(row[6] || 3) !== prioritySelect.value) return false;
 if (posSelect.value && (row[1] || []).indexOf(posSelect.value) < 0) return false;
 if (sourceSelect.value && String(row[7] || '').split('+').indexOf(sourceSelect.value) < 0) return false;
 return true;
}

function filteredRows() {
 return allRows.filter(rowMatches);
}

function renderCount() {
 if (!allRows.length) {
  countNode.textContent = '';
  return;
 }
 var total = filteredRows().length;
 if (!total) {
  countNode.textContent = t('missingPage.none');
 } else {
  countNode.textContent = t('missingPage.count', {
   shown: Math.min(shown || PAGE, total),
   total: total
  });
 }
}

function render(reset) {
 var rows = filteredRows();
 if (reset) shown = Math.min(PAGE, rows.length);
 else shown = Math.min(shown + PAGE, rows.length);

 while (listNode.firstChild) listNode.removeChild(listNode.firstChild);
 var fragment = document.createDocumentFragment();
 for (var i = 0; i < shown; i++) fragment.appendChild(item(rows[i]));
 listNode.appendChild(fragment);

 if (!rows.length) {
  countNode.textContent = t('missingPage.none');
 } else {
  countNode.textContent = t('missingPage.count', {
   shown: shown,
   total: rows.length
  });
 }
 moreButton.hidden = shown >= rows.length;
}

function buildPosFilter() {
 var seen = {};
 var values = [];
 for (var i = 0; i < allRows.length; i++) {
  var pos = allRows[i][1] || [];
  for (var j = 0; j < pos.length; j++) {
   if (!seen[pos[j]]) {
    seen[pos[j]] = true;
    values.push(pos[j]);
   }
  }
 }
 values.sort();
 while (posSelect.options.length > 1) posSelect.remove(1);
 for (var k = 0; k < values.length; k++) {
  var option = document.createElement('option');
  option.value = values[k];
  option.textContent = values[k];
  posSelect.appendChild(option);
 }
 posSelect.options[0].textContent = t('missingPage.all');
}

function load() {
 statusNode.textContent = t('missingPage.loading');
 fetch('data/missing-meta.json').then(function (response) {
  if (!response.ok) throw Error('missing-meta');
  return response.json();
 }).then(function (meta) {
  var shards = meta.shards || meta.keys || [];
  return Promise.all(shards.map(function (key) {
   return fetch('data/missing/' + key + '.json').then(function (response) {
    if (!response.ok) throw Error(key);
    return response.json();
   });
  })).then(function (parts) {
   return parts.reduce(function (accumulator, part) {
    return accumulator.concat(part);
   }, []);
  });
 }).then(function (rows) {
  allRows = rows;
  allRows.sort(function (a, b) {
   return norm(a[0]).localeCompare(norm(b[0]), 'pt');
  });
  buildPosFilter();
  statusNode.textContent = '';
  render(true);
 }).catch(function () {
  statusNode.textContent = t('missingPage.loadFailed');
 });
}

function changeLanguage(value) {
 currentLanguage = LexiI18n.setLanguage(value);
 persistLanguage(currentLanguage);
 applyLanguage();
 render(true);
}

searchInput.addEventListener('input', function () { render(true); });
prioritySelect.addEventListener('change', function () { render(true); });
posSelect.addEventListener('change', function () { render(true); });
sourceSelect.addEventListener('change', function () { render(true); });
moreButton.addEventListener('click', function () { render(false); });
languageSelect.addEventListener('change', function () {
 changeLanguage(languageSelect.value);
});

currentLanguage = readLanguage();
LexiI18n.setLanguage(currentLanguage);
applyLanguage();
load();
