// Quran Page Viewer - Application Logic

(function () {
  "use strict";

  const TOTAL_PAGES = 604;

  // Surah names (Arabic)
  const SURAH_NAMES = [
    "", "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف",
    "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر",
    "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون",
    "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان",
    "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر",
    "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد",
    "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن",
    "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون",
    "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح",
    "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات",
    "عبس", "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى",
    "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين",
    "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر",
    "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد",
    "الإخلاص", "الفلق", "الناس"
  ];

  // State
  let allVerses = null;
  let pageIndex = {};   // page -> [verses]
  let currentPage = 1;
  let loadedFonts = new Set();
  let compareActive = false;

  // DOM refs
  const pageLines = document.getElementById("page-lines");
  const pageList = document.getElementById("page-list");
  const pageSearch = document.getElementById("page-search");
  const headerSurah = document.getElementById("header-surah");
  const headerPage = document.getElementById("header-page");
  const headerJuz = document.getElementById("header-juz");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const btnCompare = document.getElementById("btn-compare");
  const btnToggleText = document.getElementById("btn-toggle-text");
  const comparePane = document.getElementById("compare-pane");
  const compareIframe = document.getElementById("compare-iframe");
  const tooltip = document.getElementById("tooltip");
  const resizeHandle = document.getElementById("compare-resize-handle");

  // ── Data Loading ──

  async function loadData() {
    pageLines.classList.add("loading");
    pageLines.textContent = "جاري تحميل البيانات...";
    try {
      const resp = await fetch("data/quran.json");
      if (!resp.ok) throw new Error("Failed to load quran.json");
      allVerses = await resp.json();
      buildPageIndex();
      init();
    } catch (e) {
      pageLines.textContent = "خطأ في تحميل البيانات. تأكد من تشغيل scraper.py أولاً.";
      console.error(e);
    }
  }

  function buildPageIndex() {
    pageIndex = {};
    for (const verse of allVerses) {
      const p = verse.page;
      if (!pageIndex[p]) pageIndex[p] = [];
      pageIndex[p].push(verse);
    }
  }

  // ── Font Loading ──

  function loadFont(page) {
    if (loadedFonts.has(page)) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const familyName = `QCF2-p${page}`;
      const font = new FontFace(familyName, `url(fonts/p${page}.ttf)`);
      font.load().then((loaded) => {
        document.fonts.add(loaded);
        loadedFonts.add(page);
        resolve();
      }).catch(reject);
    });
  }

  // ── Sidebar ──

  function buildSidebar() {
    const fragment = document.createDocumentFragment();
    for (let p = 1; p <= TOTAL_PAGES; p++) {
      const div = document.createElement("div");
      div.className = "page-item";
      div.dataset.page = p;

      const numSpan = document.createElement("span");
      numSpan.className = "page-num";
      numSpan.textContent = p;

      const surahSpan = document.createElement("span");
      surahSpan.className = "page-surah";
      const verses = pageIndex[p];
      surahSpan.textContent = verses ? SURAH_NAMES[verses[0].surah] || "" : "";

      div.appendChild(numSpan);
      div.appendChild(surahSpan);

      div.addEventListener("click", () => navigateTo(p));
      fragment.appendChild(div);
    }
    pageList.appendChild(fragment);
  }

  function updateSidebarActive() {
    const prev = pageList.querySelector(".page-item.active");
    if (prev) prev.classList.remove("active");
    const item = pageList.querySelector(`.page-item[data-page="${currentPage}"]`);
    if (item) {
      item.classList.add("active");
      item.scrollIntoView({ block: "nearest" });
    }
  }

  // Sidebar search / filter
  pageSearch.addEventListener("input", () => {
    const val = pageSearch.value.trim();
    const items = pageList.querySelectorAll(".page-item");
    if (!val) {
      items.forEach((el) => (el.style.display = ""));
      return;
    }
    items.forEach((el) => {
      const p = el.dataset.page;
      el.style.display = p.includes(val) ? "" : "none";
    });
  });

  pageSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = parseInt(pageSearch.value.trim(), 10);
      if (val >= 1 && val <= TOTAL_PAGES) {
        navigateTo(val);
        pageSearch.value = "";
        pageSearch.dispatchEvent(new Event("input"));
      }
    }
  });

  // ── Page Rendering ──

  async function renderPage(page) {
    const verses = pageIndex[page];
    if (!verses || verses.length === 0) {
      pageLines.classList.remove("loading");
      pageLines.textContent = "لا توجد بيانات لهذه الصفحة";
      return;
    }

    pageLines.classList.add("loading");
    pageLines.textContent = "جاري التحميل...";

    // Load the page font
    try {
      await loadFont(page);
    } catch (e) {
      console.warn("Font load failed for page", page, e);
    }

    const familyName = `QCF2-p${page}`;
    const flow = document.createElement("div");
    flow.className = "quran-flow";

    let lastSurah = null;
    for (const verse of verses) {
      // Surah header when surah changes
      if (verse.surah !== lastSurah) {
        if (lastSurah !== null || verse.verse_num === 1) {
          const header = document.createElement("div");
          header.className = "surah-header";
          header.textContent = "سورة " + (SURAH_NAMES[verse.surah] || "");
          flow.appendChild(header);
        }
        lastSurah = verse.surah;
      }

      const glyphs = (verse.text_glyphs || "").split("\t");
      const words = (verse.text || "").split("\t");

      for (let i = 0; i < glyphs.length; i++) {
        const span = document.createElement("span");
        span.className = "quran-word";
        const isEnd = i >= words.length;
        const uthmani = isEnd ? "" : (words[i] || "");
        if (isEnd) span.classList.add("end-marker");

        if (!isEnd) {
          const label = document.createElement("small");
          label.className = "word-text";
          label.textContent = uthmani;
          span.appendChild(label);
        }
        const glyph = document.createElement("span");
        glyph.className = "word-glyph";
        glyph.textContent = glyphs[i];
        glyph.style.fontFamily = `"${familyName}"`;
        span.appendChild(glyph);

        span.dataset.verseKey = `${verse.surah}:${verse.verse_num}`;
        span.dataset.surah = SURAH_NAMES[verse.surah] || "";
        span.dataset.uthmani = uthmani;
        span.dataset.position = i + 1;
        span.addEventListener("mouseenter", showTooltip);
        span.addEventListener("mouseleave", hideTooltip);
        flow.appendChild(span);
      }
    }

    pageLines.classList.remove("loading");
    pageLines.innerHTML = "";
    pageLines.appendChild(flow);
  }

  function toArabicNum(n) {
    const arabic = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];
    return String(n).replace(/\d/g, (d) => arabic[d]);
  }

  // ── Header ──

  function updateHeader(page) {
    headerPage.textContent = `صفحة ${page}`;
    const verses = pageIndex[page];
    if (!verses || verses.length === 0) {
      headerSurah.textContent = "";
      headerJuz.textContent = "";
      return;
    }
    const first = verses[0];
    headerSurah.textContent = SURAH_NAMES[first.surah] || "";
    headerJuz.textContent = `الجزء ${first.juz}`;
  }

  // ── Navigation ──

  function navigateTo(page) {
    if (page < 1 || page > TOTAL_PAGES) return;
    currentPage = page;
    window.location.hash = `page=${page}`;
    updateHeader(page);
    updateSidebarActive();
    renderPage(page);

    if (compareActive) {
      compareIframe.src = `https://quran.com/page/${page}`;
    }
  }

  function getPageFromHash() {
    const match = window.location.hash.match(/page=(\d+)/);
    if (match) {
      const p = parseInt(match[1], 10);
      if (p >= 1 && p <= TOTAL_PAGES) return p;
    }
    return 1;
  }

  btnPrev.addEventListener("click", () => navigateTo(currentPage - 1));
  btnNext.addEventListener("click", () => navigateTo(currentPage + 1));

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === "ArrowRight") {
      navigateTo(currentPage - 1);
    } else if (e.key === "ArrowLeft") {
      navigateTo(currentPage + 1);
    }
  });

  window.addEventListener("hashchange", () => {
    const page = getPageFromHash();
    if (page !== currentPage) navigateTo(page);
  });

  // ── Tooltip ──

  function showTooltip(e) {
    const el = e.target;
    const uthmani = el.dataset.uthmani;
    const verseKey = el.dataset.verseKey;
    const surah = el.dataset.surah;
    const position = el.dataset.position;

    if (!uthmani) return;

    tooltip.textContent = "";
    const arabicDiv = document.createElement("div");
    arabicDiv.className = "tooltip-arabic";
    arabicDiv.textContent = uthmani;
    tooltip.appendChild(arabicDiv);
    const infoDiv = document.createElement("div");
    infoDiv.className = "tooltip-info";
    infoDiv.textContent = `${surah} ${verseKey} \u2022 كلمة ${position}`;
    tooltip.appendChild(infoDiv);
    tooltip.classList.remove("hidden");

    const rect = el.getBoundingClientRect();
    let top = rect.top - tooltip.offsetHeight - 8;
    let left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2;

    if (top < 0) top = rect.bottom + 8;
    if (left < 4) left = 4;
    if (left + tooltip.offsetWidth > window.innerWidth - 4) {
      left = window.innerWidth - tooltip.offsetWidth - 4;
    }

    tooltip.style.top = top + "px";
    tooltip.style.left = left + "px";
  }

  function hideTooltip() {
    tooltip.classList.add("hidden");
  }

  // ── Text-above-glyph toggle ──

  btnToggleText.addEventListener("click", () => {
    const on = pageLines.classList.toggle("show-text");
    btnToggleText.classList.toggle("active", on);
    btnToggleText.textContent = on ? "إخفاء النص" : "إظهار النص";
  });

  // ── Compare Tool ──

  btnCompare.addEventListener("click", () => {
    compareActive = !compareActive;
    btnCompare.classList.toggle("active", compareActive);
    comparePane.classList.toggle("hidden", !compareActive);

    if (compareActive) {
      compareIframe.src = `https://quran.com/page/${currentPage}`;
    } else {
      compareIframe.src = "";
    }
  });

  let isResizing = false;

  resizeHandle.addEventListener("mousedown", (e) => {
    isResizing = true;
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!isResizing) return;
    const contentArea = document.getElementById("content-area");
    const rect = contentArea.getBoundingClientRect();
    const newWidth = rect.right - e.clientX;
    comparePane.style.width = Math.max(200, Math.min(rect.width - 300, newWidth)) + "px";
  });

  document.addEventListener("mouseup", () => {
    isResizing = false;
  });

  // ── Init ──

  function init() {
    buildSidebar();
    const startPage = getPageFromHash();
    navigateTo(startPage);
  }

  loadData();
})();
