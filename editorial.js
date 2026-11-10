/* Lexi2 editorial layer placeholder.
 *
 * The Dicionário Aberto corpus is presented as source text with explicit
 * flags. Reviewed editorial wording is a future layer; this file intentionally
 * does not add or alter any definition.
 */
'use strict';
var LexiEditorial = {
 get: function () { return null; },
 sourceSenses: function (row) {
  return (row && row[2]) ? row[2] : [];
 }
};
