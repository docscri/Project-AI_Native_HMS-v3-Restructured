/* enhancers */
const chevron = '<svg class="dd-chev" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10l5 5 5-5"/></svg>';
const calIcon = '<svg class="dd-chev" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>';
function textOf(el) { return [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim(); }
function enhance(root) {
  root.querySelectorAll("label.field:not(.fl)").forEach(f => {
    const ctl = f.querySelector("input, select, textarea"); if (!ctl) return;
    const text = textOf(f); [...f.childNodes].forEach(n => { if (n.nodeType === 3) n.remove(); });
    if (!text) return;
    f.classList.add("fl");
    if (!ctl.getAttribute("aria-label")) ctl.setAttribute("aria-label", text);
    const span = document.createElement("span"); span.className = "fl-label"; span.textContent = text; f.prepend(span);
  });
  root.querySelectorAll("div.field:not(.fl)").forEach(f => {
    if (f.querySelector("input, select, textarea")) return;
    const text = f.textContent.trim(), next = f.nextElementSibling; f.classList.add("fl");
    if (!next) return;
    if (next.matches("input")) { f.remove(); return; }
    const span = document.createElement("span"); span.className = "grp-label"; span.textContent = text;
    next.prepend(span); next.classList.add("has-grp"); f.remove();
  });
  root.querySelectorAll("select:not([data-dd])").forEach(makeDropdown);
  root.querySelectorAll('input[type="date"]:not([data-dd])').forEach(makeDatePicker);
  root.querySelectorAll('input[type="time"]:not([data-dd])').forEach(makeTimePicker);
  root.querySelectorAll('input[type="number"]:not([data-step])').forEach(makeStepper);
}
function closeMenus(except) { document.querySelectorAll(".dd.open").forEach(d => d !== except && !d.contains(except) && d.classList.remove("open")); }
function makeDropdown(sel) {
  sel.dataset.dd = "1";
  const wrap = document.createElement("div");
  wrap.className = "dd" + (sel.classList.contains("cx-select") ? " dark" : "") + (sel.style.width === "auto" ? " inline" : "");
  const btn = document.createElement("button"); btn.type = "button"; btn.className = "dd-btn"; btn.setAttribute("aria-haspopup", "listbox");
  if (sel.disabled) btn.disabled = true;
  const menu = document.createElement("div"); menu.className = "dd-menu"; menu.setAttribute("role", "listbox");
  const paint = () => {
    const o = sel.options[sel.selectedIndex];
    btn.innerHTML = `<span class="dd-val">${esc(o ? o.text : "")}</span>${chevron}`;
    menu.innerHTML = [...sel.options].map((op, i) => `<button type="button" role="option" class="dd-opt" data-i="${i}" aria-selected="${i === sel.selectedIndex}">${esc(op.text)}</button>`).join("");
  };
  paint();
  sel.parentNode.insertBefore(wrap, sel); wrap.append(btn, menu, sel); sel.classList.add("dd-native"); sel.tabIndex = -1;
  btn.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); closeMenus(wrap); wrap.classList.toggle("open"); menu.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" }); });
  menu.addEventListener("click", e => {
    const o = e.target.closest(".dd-opt"); if (!o) return; e.preventDefault(); e.stopPropagation();
    sel.selectedIndex = Number(o.dataset.i); paint(); wrap.classList.remove("open"); btn.focus();
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  wrap.addEventListener("keydown", e => {
    if (e.key === "Escape" && wrap.classList.contains("open")) { e.stopPropagation(); wrap.classList.remove("open"); btn.focus(); }
    if (["ArrowDown", "ArrowUp"].includes(e.key)) {
      e.preventDefault(); const opts = [...menu.querySelectorAll(".dd-opt")], i = opts.indexOf(document.activeElement);
      if (!wrap.classList.contains("open")) { wrap.classList.add("open"); (opts[sel.selectedIndex] || opts[0])?.focus(); return; }
      opts[Math.max(0, Math.min(opts.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))]?.focus();
    }
  });
}
function makeDatePicker(inp) {
  inp.dataset.dd = "1";
  const wrap = document.createElement("div"); wrap.className = "dd date" + (inp.classList.contains("top-date") ? " top-date" : "") + (inp.classList.contains("date-pill") ? " date-pill" : "");
  const btn = document.createElement("button"); btn.type = "button"; btn.className = "dd-btn";
  const menu = document.createElement("div"); menu.className = "dd-menu cal-pop";
  let view = (inp.value || TODAY).slice(0, 7);
  const paintBtn = () => { btn.innerHTML = `<span class="dd-val">${inp.value ? niceDate(inp.value) : "Select date"}</span>${calIcon}`; };
  const paintCal = () => {
    const [y, m] = view.split("-").map(Number), first = new Date(y, m - 1, 1), days = new Date(y, m, 0).getDate();
    const minYear = inp.min ? Number(inp.min.slice(0, 4)) : 1900;
    const maxYear = inp.max ? Number(inp.max.slice(0, 4)) : new Date().getFullYear() + 10;
    const years = Array.from({ length: Math.max(1, maxYear - minYear + 1) }, (_, i) => minYear + i);
    let cells = "<span></span>".repeat(first.getDay());
    for (let d = 1; d <= days; d++) {
      const ds = `${view}-${String(d).padStart(2, "0")}`, off = (inp.min && ds < inp.min) || (inp.max && ds > inp.max);
      cells += `<button type="button" class="cal-d ${ds === TODAY ? "today" : ""}" data-d="${ds}" aria-pressed="${ds === inp.value}" ${off ? "disabled" : ""}>${d}</button>`;
    }
    menu.innerHTML = `<div class="cal-head"><select data-cal="month" aria-label="Month">${Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}" ${i + 1 === m ? "selected" : ""}>${new Date(2000, i, 1).toLocaleDateString("en-IN", { month: "long" })}</option>`).join("")}</select><select data-cal="year" aria-label="Year">${years.map(n => `<option value="${n}" ${n === y ? "selected" : ""}>${n}</option>`).join("")}</select></div>
      <div class="cal-grid">${["S", "M", "T", "W", "T", "F", "S"].map(x => `<i>${x}</i>`).join("")}${cells}</div>`;
  };
  paintBtn(); paintCal();
  inp.parentNode.insertBefore(wrap, inp); wrap.append(btn, menu, inp); inp.classList.add("dd-native"); inp.tabIndex = -1;
  btn.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); closeMenus(wrap); view = (inp.value || TODAY).slice(0, 7); paintCal(); wrap.classList.toggle("open"); });
  menu.addEventListener("click", e => {
    e.preventDefault(); e.stopPropagation();
    const nav = e.target.closest(".cal-nav");
    if (nav) { const [y, m] = view.split("-").map(Number); view = iso(new Date(y, m - 1 + Number(nav.dataset.m), 1)).slice(0, 7); paintCal(); return; }
    const d = e.target.closest(".cal-d"); if (!d || d.disabled) return;
    inp.value = d.dataset.d; paintBtn(); wrap.classList.remove("open");
    inp.dispatchEvent(new Event("change", { bubbles: true }));
  });
  menu.addEventListener("change", e => {
    const part = e.target.dataset.cal; if (!part) return;
    const [y, m] = view.split("-").map(Number);
    view = `${part === "year" ? e.target.value : y}-${String(part === "month" ? e.target.value : m).padStart(2, "0")}`;
    paintCal();
  });
  wrap.addEventListener("keydown", e => { if (e.key === "Escape" && wrap.classList.contains("open")) { e.stopPropagation(); wrap.classList.remove("open"); } });
}
function makeTimePicker(inp) {
  inp.dataset.dd = "1";
  const sel = document.createElement("select");
  const times = []; for (let m = 0; m < 24 * 60; m += 15) times.push(`${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`);
  if (inp.value && !times.includes(inp.value)) times.push(inp.value), times.sort();
  sel.innerHTML = times.map(t => `<option value="${t}" ${t === inp.value ? "selected" : ""}>${t}</option>`).join("");
  inp.type = "hidden"; inp.after(sel);
  sel.addEventListener("change", () => { inp.value = sel.value; inp.dispatchEvent(new Event("change", { bubbles: true })); });
  makeDropdown(sel);
}
document.addEventListener("click", e => { if (!e.target.closest(".dd")) closeMenus(); }, true);
let enhanceQueued = false;
new MutationObserver(() => { if (enhanceQueued) return; enhanceQueued = true; requestAnimationFrame(() => { enhanceQueued = false; enhance(document.body); }); })
  .observe(document.body, { childList: true, subtree: true });

boot();

// Number boxes: the browser's arrows are hidden; two slim chevrons (up, down) sit at the right edge instead.
function makeStepper(inp) {
  inp.dataset.step = "1"; inp.inputMode = "numeric";
  const box = document.createElement("span"); box.className = "stepper";
  const chev = d => `<svg viewBox="0 0 12 8" width="10" height="7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
  box.innerHTML = `<button type="button" tabindex="-1" aria-label="More">${chev("M2 6l4-4 4 4")}</button><button type="button" tabindex="-1" aria-label="Less">${chev("M2 2l4 4 4-4")}</button>`;
  const [more, less] = box.children;
  const bump = up => {
    if (inp.disabled || inp.readOnly) return;
    if (inp.value === "") inp.value = inp.min || 0; else up ? inp.stepUp() : inp.stepDown();
    inp.dispatchEvent(new Event("input", { bubbles: true })); inp.dispatchEvent(new Event("change", { bubbles: true }));
  };
  less.addEventListener("click", e => { e.preventDefault(); bump(false); });
  more.addEventListener("click", e => { e.preventDefault(); bump(true); });
  inp.after(box); inp.closest(".field")?.classList.add("has-stepper");
}
