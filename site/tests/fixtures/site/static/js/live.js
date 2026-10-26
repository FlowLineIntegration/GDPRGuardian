// Jeu d'essai du démon : mêmes règles que site/src/format.rs (Intl fr-FR / en-GB, tailles en base 1024).
// Daemon fixture: the same rules as site/src/format.rs (Intl fr-FR / en-GB, sizes in base 1024).
'use strict';
(() => {
  const fr = document.documentElement.lang === 'fr';
  const locale = fr ? 'fr-FR' : 'en-GB';
  const int = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format;
  const oneDecimal = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format;
  const UNITS = fr ? ['o', 'Ko', 'Mo', 'Go', 'To'] : ['B', 'KB', 'MB', 'GB', 'TB'];
  const bytes = (value) => {
    let scaled = value;
    let unit = 0;
    while (unit < UNITS.length - 1 && Math.round(scaled * 10) / 10 >= 1024) { scaled /= 1024; unit += 1; }
    return (unit ? oneDecimal(scaled) : int(scaled)) + ' ' + UNITS[unit];
  };
  const percent = (part, total) => (total > 0 ? (part / total) * 100 : 0);

  const FORMAT = {
    uses_hour: (s) => int(s.uses_hour),
    uses_hour_protocol: (s) => int(s.uses_hour_protocol),
    docs_protocol: (s) => int(s.docs_protocol),
    bytes_hour: (s) => bytes(s.bytes_hour),
    docs_total: (s) => int(s.docs_total),
    bytes_total: (s) => bytes(s.bytes_total),
    visitors_total: (s) => int(s.visitors_total),
    visitors_today: (s) => int(s.visitors_today),
    cpu_percent: (s) => oneDecimal(s.cpu_percent),
    ram_used: (s) => bytes(s.ram_used_bytes),
    ram_total: (s) => bytes(s.ram_total_bytes),
    ram_percent: (s) => oneDecimal(percent(s.ram_used_bytes, s.ram_total_bytes)),
  };

  const apply = (stats) => {
    for (const element of document.querySelectorAll('[data-live]')) {
      const format = FORMAT[element.dataset.live];
      if (!format) continue;
      const text = format(stats);
      if (element.textContent !== text) element.textContent = text;
    }
  };

  if (!('EventSource' in window)) return;
  const source = new EventSource('/api/live');
  source.addEventListener('stats', (event) => {
    try { apply(JSON.parse(event.data)); } catch (_) { /* événement illisible ignoré / unreadable event ignored */ }
  });
})();
