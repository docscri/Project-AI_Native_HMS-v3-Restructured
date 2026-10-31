/* Documents open inside the app: PDFs drawn page by page with PDF.js (bundled in /static/vendor/pdfjs, works on
   phones too), photos as images, text as text. Download keeps the original file. */
let pdfLib;
function loadPdfJs() {
  if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
  return pdfLib || (pdfLib = new Promise((ok, fail) => {
    const s = document.createElement("script");
    s.src = "/static/vendor/pdfjs/pdf.min.js";
    s.onload = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.js"; ok(window.pdfjsLib); };
    s.onerror = () => { pdfLib = null; fail(new Error("PDF reader didn't load")); };
    document.head.appendChild(s);
  }));
}
const fileNameOf = res => {
  const h = res.headers.get("content-disposition") || "", star = h.match(/filename\*=UTF-8''([^;]+)/i), plain = h.match(/filename="([^"]+)"/i);
  return star ? decodeURIComponent(star[1]) : plain ? plain[1] : "document";
};
async function openDocViewer(id) {
  M = { kind: "doc", id };
  modal(`<div class="dv"><div class="dv-top"><b class="dv-name">Opening…</b></div><div class="dv-body"><div class="dv-wait">Loading the document…</div></div></div>`, true);
  const res = await fetch(`/api/documents/${id}/file`, { headers: { Authorization: "Bearer " + S.token } });
  if (!res.ok) { closeModal(); return toast(res.status === 404 ? "The file isn't there any more." : "Couldn't open the document.", true); }
  const blob = await res.blob(), name = fileNameOf(res), type = blob.type || "", url = URL.createObjectURL(blob);
  if (M?.kind !== "doc" || M.id !== id) return URL.revokeObjectURL(url);   // closed while loading
  M.url = url;
  modal(`<div class="dv"><div class="dv-top"><b class="dv-name" title="${esc(name)}">${esc(name)}</b><span class="dv-pages" id="dv-pages"></span>
      <a class="btn small" href="${url}" download="${esc(name)}">Download</a></div>
    <div class="dv-body" id="dv-body"><div class="dv-wait">Loading the document…</div></div></div>`, true);
  const body = $("#dv-body");
  if (type.startsWith("image/")) body.innerHTML = `<img class="dv-img" src="${url}" alt="${esc(name)}">`;
  else if (type.startsWith("text/")) body.innerHTML = `<pre class="dv-text">${esc(await blob.text())}</pre>`;
  else if (type === "application/pdf") {
    try {
      const lib = await loadPdfJs(), pdf = await lib.getDocument({ data: await blob.arrayBuffer() }).promise;
      if (M?.url !== url) return;
      body.innerHTML = ""; $("#dv-pages").textContent = `${pdf.numPages} page${pdf.numPages > 1 ? "s" : ""}`;
      const width = body.clientWidth - 2, ratio = Math.min(window.devicePixelRatio || 1, 2);
      for (let n = 1; n <= pdf.numPages; n++) {
        if (M?.url !== url) return;   // stop drawing once closed
        const page = await pdf.getPage(n), base = page.getViewport({ scale: 1 }), vp = page.getViewport({ scale: width / base.width * ratio });
        const c = document.createElement("canvas"); c.className = "dv-page"; c.width = vp.width; c.height = vp.height; c.style.width = width + "px";
        body.appendChild(c); await page.render({ canvasContext: c.getContext("2d"), viewport: vp }).promise;
      }
    } catch { body.innerHTML = `<iframe class="dv-frame" src="${url}" title="${esc(name)}"></iframe>`; }   // the browser's own reader, still in the app
  } else body.innerHTML = `<div class="dv-wait">This file type can't be shown here. Use Download to open it.</div>`;
}
