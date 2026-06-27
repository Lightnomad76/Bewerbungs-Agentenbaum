/* =========================================================================
   Bewerbungs-Agentenbaum — Job-Treffer UI (vanilla, file://-tauglich)
   Liest window.TREFFER (von der JS-Bridge gesetzt). Kein fetch, kein Server.
   Alle Job-Daten sind potenziell gescrapt -> ausschliesslich textContent /
   createElement, NIE innerHTML mit Rohdaten (XSS-Schutz).
   ========================================================================= */
(function () {
  "use strict";

  // -------------------------------------------------- Daten laden / Guard
  var DATA = (typeof window !== "undefined" && window.TREFFER) ? window.TREFFER : null;

  var resultsEl = document.getElementById("results");
  var headEl    = document.getElementById("appHead");
  var countEl   = document.getElementById("resultCount");

  if (!DATA || !Array.isArray(DATA.treffer)) {
    showError(
      "Keine Treffer-Daten gefunden. Pruefe die Daten-Bridge in index.html " +
      "(Default: ../treffer_v2.example.js). Erwartet wird window.TREFFER = {meta, treffer[]}."
    );
    return;
  }

  var META    = DATA.meta || {};
  var TREFFER = DATA.treffer;

  // -------------------------------------------------------------- Helpers
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  // null/leer -> "k.A." (nie "null"/"NaN" anzeigen)
  function ka(v) {
    if (v == null || v === "" || (typeof v === "number" && !isFinite(v))) return "k.A.";
    return v;
  }

  function fmtSalary(min, max) {
    var hasMin = isNum(min), hasMax = isNum(max);
    if (!hasMin && !hasMax) return "k.A.";
    var f = function (n) { return n.toLocaleString("de-DE"); };
    if (hasMin && hasMax) return f(min) + "–" + f(max) + " €";
    if (hasMin) return "ab " + f(min) + " €";
    return "bis " + f(max) + " €";
  }

  // date_posted kann null sein -> nach hinten sortieren
  function dateKey(t) {
    var d = t && t.date_posted;
    if (!d) return null;
    var ms = Date.parse(d);
    return isFinite(ms) ? ms : null;
  }

  function safeHref(url) {
    if (typeof url !== "string") return null;
    // nur http/https zulassen (kein javascript:, data: etc.)
    return /^https?:\/\//i.test(url.trim()) ? url.trim() : null;
  }

  function scoreClass(score) {
    if (!isNum(score)) return { card: "is-low", pill: "s-low" };
    if (score >= 20) return { card: "is-strong", pill: "s-strong" };
    if (score >= 8)  return { card: "is-mid",    pill: "s-mid" };
    if (score > 0)   return { card: "is-low",    pill: "s-low" };
    return { card: "is-neg", pill: "s-neg" };
  }

  function match(t) { return (t && t.match) || {}; }
  function arr(v) { return Array.isArray(v) ? v : []; }

  // ------------------------------------------------------------ State
  var state = {
    sort: "score_desc",
    minScore: null,   // wird auf Daten-Minimum gesetzt
    titel: "__all__",
    search: "",
    hideAusschluss: false
  };

  // Score-Spanne aus Daten ableiten (negativ moeglich)
  var scores = TREFFER.map(function (t) { return match(t).score; }).filter(isNum);
  var SCORE_MIN = scores.length ? Math.min.apply(null, scores) : 0;
  var SCORE_MAX = scores.length ? Math.max.apply(null, scores) : 0;
  if (SCORE_MIN === SCORE_MAX) { SCORE_MIN -= 1; } // Slider braucht Spanne
  state.minScore = SCORE_MIN;

  // ------------------------------------------------------------ Kopf rendern
  function renderHead() {
    headEl.textContent = "";
    headEl.appendChild(el("h1", null, "Job-Treffer"));

    var grid = el("div", "meta-grid");

    function item(key, valNode) {
      var wrap = el("div", "meta-item");
      wrap.appendChild(el("span", "meta-key", key));
      if (typeof valNode === "string") wrap.appendChild(el("span", "meta-val", valNode));
      else wrap.appendChild(valNode);
      grid.appendChild(wrap);
    }

    item("Profil", String(ka(META.profil)));
    item("Standort", String(ka(META.standort)));

    // Quellen generisch (nicht hardcoden)
    var quellen = arr(META.quellen);
    if (quellen.length) {
      var qval = el("span", "meta-val");
      quellen.forEach(function (q) { qval.appendChild(el("span", "source-tag", String(q))); });
      item("Quellen", qval);
    } else {
      item("Quellen", "k.A.");
    }

    var anzahl = isNum(META.anzahl) ? META.anzahl : TREFFER.length;
    item("Treffer gesamt", String(anzahl));

    var erzeugt = formatErzeugt(META.erzeugt);
    item("Erzeugt", erzeugt);

    if (META.version) item("Version", String(META.version));

    headEl.appendChild(grid);
  }

  function formatErzeugt(iso) {
    if (!iso) return "k.A.";
    var ms = Date.parse(iso);
    if (!isFinite(ms)) return String(iso);
    try {
      return new Date(ms).toLocaleString("de-DE", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit"
      }) + " Uhr";
    } catch (e) { return String(iso); }
  }

  // ------------------------------------------------------------ Such-Titel-Filter befuellen
  function populateTitelFilter() {
    var sel = document.getElementById("titelSel");
    var seen = {};
    var titles = [];
    TREFFER.forEach(function (t) {
      arr(t.such_titel).forEach(function (s) {
        var key = String(s);
        if (!seen[key]) { seen[key] = true; titles.push(key); }
      });
    });
    titles.sort(function (a, b) { return a.localeCompare(b, "de"); });
    titles.forEach(function (titel) {
      var o = document.createElement("option");
      o.value = titel;
      o.textContent = titel;
      sel.appendChild(o);
    });
  }

  // ------------------------------------------------------------ Filter + Sort
  function applyFilters() {
    var q = state.search.trim().toLowerCase();

    var list = TREFFER.filter(function (t) {
      var m = match(t);

      // Min-Score (nicht-numerische Scores nie wegfiltern)
      if (isNum(m.score) && m.score < state.minScore) return false;

      // Such-Titel
      if (state.titel !== "__all__") {
        if (arr(t.such_titel).indexOf(state.titel) === -1) return false;
      }

      // Ausschluss ausblenden
      if (state.hideAusschluss && arr(m.ausschluss_treffer).length > 0) return false;

      // Freitext
      if (q) {
        var hay = [
          t.title, t.company, t.location, t.description
        ].concat(arr(m.kann_treffer)).concat(arr(t.such_titel))
         .filter(function (x) { return typeof x === "string"; })
         .join("  ").toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });

    list.sort(getSorter());
    return list;
  }

  function getSorter() {
    switch (state.sort) {
      case "score_asc":
        return function (a, b) { return num(match(a).score) - num(match(b).score); };
      case "date_desc":
        return byDate(-1);
      case "date_asc":
        return byDate(1);
      case "score_desc":
      default:
        return function (a, b) { return num(match(b).score) - num(match(a).score); };
    }
    function num(s) { return isNum(s) ? s : -Infinity; }
  }

  // Datum-Sortierung: nulls IMMER ans Ende, egal welche Richtung
  function byDate(dir) {
    return function (a, b) {
      var ka = dateKey(a), kb = dateKey(b);
      if (ka == null && kb == null) return 0;
      if (ka == null) return 1;
      if (kb == null) return -1;
      return dir * (ka - kb);
    };
  }

  // ------------------------------------------------------------ Karte bauen
  function buildCard(t) {
    var m = match(t);
    var sc = scoreClass(m.score);

    var card = el("article", "card " + (m.ko ? "is-ko" : sc.card));

    // --- Top: Titel + Score
    var top = el("div", "card-top");

    var h = el("h2", "card-title");
    var href = safeHref(t.job_url);
    var titleText = String(ka(t.title));
    if (href) {
      var a = el("a", null, titleText);
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      h.appendChild(a);
    } else {
      h.appendChild(document.createTextNode(titleText));
    }
    top.appendChild(h);

    var score = el("div", "score " + sc.pill);
    score.appendChild(el("span", "score-num", isNum(m.score) ? String(m.score) : "?"));
    score.appendChild(el("span", "score-lbl", "Score"));
    top.appendChild(score);
    card.appendChild(top);

    // --- Sub: Firma · Ort · Datum · Gehalt
    var sub = el("div", "card-sub");
    sub.appendChild(el("span", "sub-strong", String(ka(t.company))));
    sub.appendChild(el("span", null, "· " + String(ka(t.location))));
    sub.appendChild(el("span", null, "· " + String(ka(t.date_posted))));
    sub.appendChild(el("span", null, "· " + fmtSalary(t.min_amount, t.max_amount)));
    card.appendChild(sub);

    // --- via Such-Titel
    var st = arr(t.such_titel);
    if (st.length) {
      var via = el("div", "via-line");
      via.appendChild(document.createTextNode("via: "));
      via.appendChild(el("span", "via-titel", st.join(", ")));
      card.appendChild(via);
    }

    // --- Warn-/Info-Badges
    var badges = el("div", "badges");
    if (m.ko === true) {
      badges.appendChild(el("span", "badge badge--ko", "K.-o.-Kriterium"));
    }
    var aus = arr(m.ausschluss_treffer);
    if (aus.length) {
      badges.appendChild(el("span", "badge badge--ausschluss", "Ausschluss: " + aus.join(", ")));
    }
    if (m.gehalt_unter_min === true) {
      badges.appendChild(el("span", "badge badge--gehalt", "Gehalt unter Minimum"));
    }
    var fehlt = arr(m.muss_fehlt);
    if (fehlt.length) {
      badges.appendChild(el("span", "badge badge--info", "Fehlt: " + fehlt.join(", ")));
    }
    if (badges.childNodes.length) card.appendChild(badges);

    // --- kann_treffer-Chips (Hauptsignal)
    var kann = arr(m.kann_treffer);
    if (kann.length) {
      var chipWrap = el("div");
      chipWrap.appendChild(el("div", "chips-label", "Passende Skills"));
      var chips = el("div", "chips");
      kann.forEach(function (k) { chips.appendChild(el("span", "chip", String(k))); });
      chipWrap.appendChild(chips);
      card.appendChild(chipWrap);
    }

    // --- Beschreibung ein-/ausklappbar
    if (typeof t.description === "string" && t.description.trim() !== "") {
      var det = el("details", "desc");
      det.appendChild(el("summary", null, "Beschreibung"));
      det.appendChild(el("p", null, t.description));
      card.appendChild(det);
    } else {
      var noDesc = el("p", "desc muted", "Beschreibung: k.A.");
      card.appendChild(noDesc);
    }

    return card;
  }

  // ------------------------------------------------------------ Render-Liste
  function render() {
    var list = applyFilters();
    resultsEl.textContent = "";

    if (!list.length) {
      var empty = el("div", "empty-state",
        "Keine Treffer fuer die aktuellen Filter. " +
        "Min-Score senken oder Filter zuruecksetzen.");
      resultsEl.appendChild(empty);
    } else {
      var frag = document.createDocumentFragment();
      list.forEach(function (t) { frag.appendChild(buildCard(t)); });
      resultsEl.appendChild(frag);
    }

    countEl.textContent =
      list.length + " von " + TREFFER.length + " Treffer angezeigt" +
      (state.minScore > SCORE_MIN ? "  ·  Min-Score ≥ " + state.minScore : "");
  }

  // ------------------------------------------------------------ Controls verdrahten
  function wireControls() {
    var sortSel = document.getElementById("sortSel");
    var range   = document.getElementById("scoreRange");
    var scoreVal= document.getElementById("scoreVal");
    var titelSel= document.getElementById("titelSel");
    var search  = document.getElementById("searchInp");
    var hideChk = document.getElementById("hideAusschluss");
    var resetBtn= document.getElementById("resetBtn");

    range.min = String(SCORE_MIN);
    range.max = String(SCORE_MAX);
    range.value = String(state.minScore);
    scoreVal.textContent = String(state.minScore);

    sortSel.value = state.sort;

    sortSel.addEventListener("change", function () { state.sort = sortSel.value; render(); });
    range.addEventListener("input", function () {
      state.minScore = parseInt(range.value, 10);
      scoreVal.textContent = String(state.minScore);
      render();
    });
    titelSel.addEventListener("change", function () { state.titel = titelSel.value; render(); });
    search.addEventListener("input", function () { state.search = search.value; render(); });
    hideChk.addEventListener("change", function () { state.hideAusschluss = hideChk.checked; render(); });

    resetBtn.addEventListener("click", function () {
      state.sort = "score_desc";
      state.minScore = SCORE_MIN;
      state.titel = "__all__";
      state.search = "";
      state.hideAusschluss = false;
      sortSel.value = state.sort;
      range.value = String(SCORE_MIN);
      scoreVal.textContent = String(SCORE_MIN);
      titelSel.value = "__all__";
      search.value = "";
      hideChk.checked = false;
      render();
    });
  }

  // ------------------------------------------------------------ Fehleranzeige
  function showError(msg) {
    if (headEl) headEl.textContent = "";
    if (countEl) countEl.textContent = "";
    if (resultsEl) {
      resultsEl.textContent = "";
      resultsEl.appendChild(el("div", "error-box", msg));
    }
  }

  // ------------------------------------------------------------ Init
  renderHead();
  populateTitelFilter();
  wireControls();
  render();
})();
