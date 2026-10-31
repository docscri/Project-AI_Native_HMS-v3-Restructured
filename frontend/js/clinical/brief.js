// Brief: summary (new reports first, then history), past visits as events, and values over time. All cited.
function paneBrief(v) {
  const b = v.brief, tab = S.btab || "summary";
  if (!b?.summary) return `<p class="muted cx-lead">${["waiting", "with_doctor"].includes(v.status) ? "Preparing brief…" : "—"}</p>`;
  if (tab === "events") {
    if (!b.events.length) return `<p class="muted cx-lead">First visit.</p>`;
    const shown = S.allEvents ? b.events : b.events.slice(0, 5);
    return `<div class="timeline">${shown.map(e => `<div class="tl"><div class="tl-head"><b>${longDate(e.date)}</b><span>${esc(e.doctor)}</span></div>
      <div class="items"><button class="btn small" data-a="note-view" data-v="${e.visit_id}">Note & prescription</button>${e.documents.map(d => `<button class="btn small" data-a="open-doc" data-v="${d.id}">📄 ${esc(docTitle(d))}</button>`).join("")}</div>
      <div class="muted" style="font-size:13.5px;margin-top:6px">${esc(e.text)}</div>
      ${(e.addenda || []).map(x => `<div class="add-line"><small>Addendum · ${stampOf(x.signed_at)} · ${esc(x.signed_by_name)}</small><p>${esc(x.text)}</p></div>`).join("")}</div>`).join("")}</div>
      ${b.events.length > 5 ? `<div><button class="btn small" data-a="cs-allev">${S.allEvents ? "Show fewer" : `Show all ${b.events.length}`}</button></div>` : ""}`;
  }
  if (tab === "charts") {   // single readings as compact tiles first, then trends; each group latest first
    if (!b.charts.length) return `<p class="muted cx-lead">No values yet.</p>`;
    const one = c => c.series.every(ser => ser.points.length === 1), tiles = b.charts.filter(one), trends = b.charts.filter(c => !one(c));
    return `${tiles.length ? `<div class="bchart-tiles">${tiles.map(c => chartCard(c)).join("")}</div>` : ""}${trends.length ? `<div class="bchart-grid">${trends.map(c => chartCard(c, b.charts.indexOf(c))).join("")}</div>` : ""}`;
  }
  const paras = b.summary.filter(p => p.sentences.length);
  const nums = briefNums(b), sup = ids => `<sup class="cs">${ids.map(id => `<button data-a="cite" data-v="${id}" title="${esc(citeLabel(id))}">${nums.get(id)}</button>`).join("")}</sup>`;
  return paras.length ? paras.map(p => `<p class="cx-lead">${p.sentences.map(x => flagged(x.text, x.flags) + sup(x.cites)).join(" ")}</p>`).join("") : `<p class="muted cx-lead">First visit.</p>`;
}
const num = x => String(+x);
// Summary citations numbered in reading order; the Sources panel shows the same numbers.
const briefNums = b => { const m = new Map(); (b?.summary || []).forEach(p => p.sentences.forEach(x => x.cites.forEach(id => m.has(id) || m.set(id, m.size + 1)))); return m; };
const shown = p => p.text ?? num(p.value);   // the value as written (1.0 stays 1.0)
const docTitle = d => d.title || d.extracted?.title || d.filename.replace(/\.[^.]+$/, "");
// Values outside the usual range, marked inside the sentence.
const flagged = (text, flags) => (flags || []).reduce((h, f) => h.split(esc(f)).join(`<mark class="abn">${esc(f)}</mark>`), esc(text));
const monYr = d => new Date(d).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
// One test over time. Two lines only for BP (systolic, diastolic): blue and deep coral, validated against the card.
// About four round values between lo and hi (e.g. 90, 100, 110, 120).
function niceTicks(lo, hi) {
  if (hi <= lo) return [lo];
  const raw = (hi - lo) / 3, mag = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(st => st >= raw);
  const out = []; for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(+t.toFixed(6));
  return out;
}
function chartSvg(c, big) {
  const W = big ? 720 : 320, H = big ? 300 : 112, L = big ? 44 : 30, R = big ? 18 : 10, T = big ? 22 : 12, B = big ? 30 : 20, pts = c.series.flatMap(x => x.points);
  const band = c.series.length === 1 ? c.series[0].range : null;
  const ms = d => new Date(d).getTime(), t0 = Math.min(...pts.map(p => ms(p.date))), t1 = Math.max(...pts.map(p => ms(p.date)));
  const edges = (band || []).filter(e => e != null);   // a printed range can be one-sided ("< 200")
  let lo = Math.min(...pts.map(p => p.value), ...edges), hi = Math.max(...pts.map(p => p.value), ...edges);
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.15; lo -= pad; hi += pad;
  const x = d => t1 === t0 ? (L + W - R) / 2 : L + (ms(d) - t0) / (t1 - t0) * (W - L - R);
  const y = val => T + (hi - val) / (hi - lo) * (H - T - B);
  const colors = c.series.length > 1 ? ["#2a78d6", "#D9542F"] : ["var(--ink)"];
  const ticks = big ? niceTicks(lo + pad, hi - pad) : [lo + pad, hi - pad];
  const days = [...new Set(pts.map(p => p.date))].sort();
  let xLabels = [days[0], ...(days.length > 1 ? [days.at(-1)] : [])];
  if (big) { xLabels = []; for (const d of days) if (!xLabels.length || x(d) - x(xLabels.at(-1)) > 80) xLabels.push(d); if (days.length > 1 && x(days.at(-1)) - x(xLabels.at(-1)) > 0) { if (x(days.at(-1)) - x(xLabels.at(-1)) <= 80) xLabels.pop(); xLabels.push(days.at(-1)); } }
  const lines = c.series.map((ser, i) => `${ser.points.length > 1 ? `<path d="${ser.points.map((p, j) => `${j ? "L" : "M"}${x(p.date).toFixed(1)},${y(p.value).toFixed(1)}`).join("")}" fill="none" stroke="${colors[i]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>` : ""}
    ${ser.points.map(p => `<g class="bpt" ${big ? `data-a="cite" data-v="${p.cite}" tabindex="0" role="button"` : ""} aria-label="${esc(ser.name)} ${shown(p)} ${esc(c.unit)}, ${longDate(p.date)}${p.out ? ", outside usual range" : ""}"><circle cx="${x(p.date)}" cy="${y(p.value)}" r="${big ? 14 : 10}" fill="transparent"/><circle cx="${x(p.date)}" cy="${y(p.value)}" r="${big ? 5 : 3.5}" fill="${c.series.length === 1 && p.out ? "#D9542F" : colors[i]}" stroke="${p.out ? (c.series.length === 1 ? "#D9542F" : "var(--ink)") : "var(--surface)"}" stroke-width="2"/>
      <text class="bpt-tip" x="${Math.min(Math.max(x(p.date), L + 28), W - R - 28)}" y="${Math.max(y(p.value) - 12, 12)}" text-anchor="middle">${shown(p)} · ${monYr(p.date)}</text></g>`).join("")}`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(c.test)} over time">
    ${band ? `<rect x="${L}" y="${y(band[1] ?? hi)}" width="${W - L - R}" height="${y(band[0] ?? lo) - y(band[1] ?? hi)}" class="bchart-band" rx="4"><title>${rangeText(band)}</title></rect>` : ""}
    ${big ? ticks.map(t => `<line x1="${L}" y1="${y(t)}" x2="${W - R}" y2="${y(t)}" class="bchart-grid-line"/>`).join("") : ""}
    <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" class="bchart-axis"/>
    ${ticks.map(t => `<text x="${L - 8}" y="${y(t) + 4}" text-anchor="end" class="bchart-tick">${num(+t.toFixed(1))}</text>`).join("")}
    ${xLabels.map((d, i) => `<text x="${x(d)}" y="${H - (big ? 8 : 4)}" text-anchor="${xLabels.length > 1 && i === 0 ? "start" : xLabels.length > 1 && i === xLabels.length - 1 ? "end" : "middle"}" class="bchart-tick">${big ? new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "2-digit" }) : monYr(d)}</text>`).join("")}
    ${lines}</svg>`;
}
function chartCard(c, i) {
  const last = c.series.map(ser => ser.points.at(-1)), out = last.some(p => p.out);
  const head = `<div class="bchart-head"><b>${esc(c.test)}</b><span class="${out ? "abn" : ""}">${last.map(shown).join("/")}${c.unit ? " " + esc(c.unit) : ""}</span></div>`;
  if (c.series.every(ser => ser.points.length === 1))   // one reading isn't a trend: a value tile
    return `<button class="bchart bchart-one" data-a="cite" data-v="${last[0].cite}">${head}<span class="bchart-when">${longDate(last[0].date)}</span></button>`;
  const legend = c.series.length > 1 ? `<div class="bchart-legend">${c.series.map((ser, k) => `<span><i style="background:${["#2a78d6", "#D9542F"][k]}"></i>${esc(ser.name)}</span>`).join("")}</div>` : "";
  return `<button class="bchart" data-a="chart-open" data-v="${i}" aria-label="${esc(c.test)}: open a larger chart">${head}${legend}${chartSvg(c, false)}</button>`;
}
const rangeText = r => r[0] == null ? `below ${num(r[1])}` : r[1] == null ? `above ${num(r[0])}` : `${num(r[0])}–${num(r[1])}`;
// Larger view of one chart, with every reading and its source.
function openChart(c) {
  M = { kind: "chart" };
  // one row per date; BP shows systolic/diastolic together
  const byDay = {};
  c.series.forEach(ser => ser.points.forEach(p => { (byDay[p.date] = byDay[p.date] || []).push(p); }));
  const rows = Object.entries(byDay).sort((a, b) => b[0].localeCompare(a[0])).map(([date, ps]) => ({ date, text: ps.map(shown).join("/"), out: ps.some(p => p.out), cite: ps[0].cite }));
  const ser = c.series.length === 1 && c.series[0], range = ser?.range;
  modal(`<div><h2>${esc(c.test)}</h2><span class="muted">${esc(c.unit || "")}${range ? ` · ${ser.range_from === "report" ? "report range" : "usual"} ${rangeText(range)}` : ""}</span></div>
    ${c.series.length > 1 ? `<div class="bchart-legend">${c.series.map((ser, k) => `<span><i style="background:${["#2a78d6", "#D9542F"][k]}"></i>${esc(ser.name)}</span>`).join("")}</div>` : ""}
    <div class="bchart-big">${chartSvg(c, true)}</div>
    <div class="bchart-rows">${rows.map(p => `<button data-a="cite" data-v="${p.cite}"><span>${longDate(p.date)}</span><b class="${p.out ? "abn" : ""}">${esc(p.text)} ${esc(c.unit || "")}</b><small>${esc(citeLabel(p.cite))}</small></button>`).join("")}</div>`, true);
}
