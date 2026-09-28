/* ==========================================================================
   Great Church AI — Bible reader and search
   ========================================================================== */

(() => {
  "use strict";

  const {
    $, $$, el, api, toast, copyText, describeError, icons, setNotice, renderRich,
  } = window.GCA;

  const bookSelect = $("[data-book]");
  const chapterSelect = $("[data-chapter]");
  const testamentSelect = $("[data-testament]");
  const referenceInput = $("[data-reference]");
  const goBtn = $("[data-go]");
  const passageEl = $("[data-passage]");
  const titleEl = $("[data-passage-title]");
  const metaEl = $("[data-meta]");
  const errorBox = $("[data-error]");
  const chaptersEl = $("[data-chapters]");
  const refEl = $("[data-ref]");
  const translationEl = $("[data-translation]");
  const countEl = $("[data-count]");
  const studyLink = $("[data-study-link]");
  const prayerLink = $("[data-prayer-link]");

  if (!bookSelect) return;

  /** All 66 books with their chapter counts. */
  let books = [];
  let currentReference = "";

  /* --- Book / chapter pickers -------------------------------------------- */
  const fillBooks = (testament) => {
    const list = testament
      ? books.filter((b) => b.testament === testament)
      : books;

    bookSelect.textContent = "";
    list.forEach((book) => {
      bookSelect.append(el("option", { value: book.name }, book.name));
    });
    bookSelect.disabled = false;
    return list;
  };

  const fillChapters = (bookName) => {
    const book = books.find((b) => b.name === bookName);
    chapterSelect.textContent = "";
    if (!book) {
      chapterSelect.disabled = true;
      return 0;
    }
    for (let n = 1; n <= book.chapters; n += 1) {
      chapterSelect.append(el("option", { value: String(n) }, String(n)));
    }
    chapterSelect.disabled = false;
    return book.chapters;
  };

  /* --- Rendering a passage ----------------------------------------------- */
  const showPlaceholder = (text) => {
    passageEl.textContent = "";
    metaEl.hidden = true;
    chaptersEl.textContent = "";
    passageEl.append(el("p", { class: "muted" }, text));
  };

  const renderPassage = (data) => {
    currentReference = data.reference;

    titleEl.textContent = data.reference;
    refEl.textContent = data.reference;
    translationEl.textContent = data.translation;
    countEl.textContent = `${data.verses.length} verse${data.verses.length === 1 ? "" : "s"}`;
    metaEl.hidden = false;
    passageEl.textContent = "";

    data.verses.forEach((verse) => {
      passageEl.append(
        el("p", { class: "scripture__verse", "data-verse": verse.verse }, [
          el("span", { class: "scripture__num", "aria-hidden": "true" }, String(verse.verse)),
          el("span", {}, [el("span", { class: "sr-only" }, `Verse ${verse.verse}: `), verse.text]),
        ])
      );
    });

    if (data.warning) {
      passageEl.append(
        el("div", { class: "notice notice--info", style: "margin-top:20px" }, [
          icons.info(18),
          el("span", { text: data.warning }),
        ])
      );
    }

    studyLink.href = `/study.html?reference=${encodeURIComponent(data.reference)}`;
    prayerLink.href = `/prayer.html?reference=${encodeURIComponent(data.reference)}`;

    renderChapterJump(data.book, data.chapter);
  };

  const renderChapterJump = (bookName, activeChapter) => {
    const book = books.find((b) => b.name === bookName);
    chaptersEl.textContent = "";
    if (!book || book.chapters < 2) return;

    for (let n = 1; n <= book.chapters; n += 1) {
      chaptersEl.append(
        el("button", {
          class: "chapter-jump__btn",
          type: "button",
          "aria-current": String(n === activeChapter),
          "aria-label": `Go to ${bookName} chapter ${n}`,
          onClick: () => loadBookChapter(bookName, n),
        }, String(n))
      );
    }
  };

  const loadPassage = async (book, chapter) => {
    setNotice(errorBox, "");
    showPlaceholder("Loading…");
    try {
      const data = await api.book(book, chapter);
      renderPassage(data);
      bookSelect.value = data.book;
      fillChapters(data.book);
      chapterSelect.value = String(data.chapter);
    } catch (error) {
      showPlaceholder("");
      metaEl.hidden = true;
      chaptersEl.textContent = "";
      setNotice(errorBox, describeError(error), "error");
    }
  };

  const loadReference = async (reference) => {
    setNotice(errorBox, "");
    showPlaceholder("Loading…");
    try {
      const data = await api.passage(reference);
      renderPassage(data);
      if (books.some((b) => b.name === data.book)) {
        bookSelect.value = data.book;
        fillChapters(data.book);
        if (data.chapter) chapterSelect.value = String(data.chapter);
      }
    } catch (error) {
      showPlaceholder("");
      metaEl.hidden = true;
      chaptersEl.textContent = "";
      setNotice(errorBox, describeError(error), "error");
    }
  };

  const loadBookChapter = (book, chapter) => loadPassage(book, Number(chapter));

  /* --- Events ------------------------------------------------------------ */
  testamentSelect?.addEventListener("change", () => {
    const list = fillBooks(testamentSelect.value);
    if (list.length) {
      fillChapters(list[0].name);
      loadPassage(list[0].name, 1);
    }
  });

  bookSelect.addEventListener("change", () => {
    fillChapters(bookSelect.value);
    loadPassage(bookSelect.value, 1);
  });

  chapterSelect.addEventListener("change", () => {
    loadBookChapter(bookSelect.value, chapterSelect.value);
  });

  const go = () => {
    const value = referenceInput.value.trim();
    if (!value) {
      setNotice(errorBox, "Type a reference such as John 3:16.", "error");
      referenceInput.focus();
      return;
    }
    loadReference(value);
  };

  goBtn?.addEventListener("click", go);
  referenceInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      go();
    }
  });

  $("[data-copy-passage]")?.addEventListener("click", async () => {
    if (!currentReference) {
      toast("Open a passage first.");
      return;
    }
    const text = `${currentReference}\n\n${passageEl.textContent.trim()}`;
    if (await copyText(text)) {
      toast(`${currentReference} copied.`);
    } else {
      toast("Your browser blocked copying. Select the text and copy it manually.");
    }
  });

  /* --- View switch -------------------------------------------------------- */
  const panes = {
    read: $('[data-pane="read"]'),
    search: $('[data-pane="search"]'),
  };

  const setView = (view) => {
    $$("[data-view]").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.view === view));
    });
    Object.entries(panes).forEach(([name, pane]) => {
      if (pane) pane.hidden = name !== view;
    });
  };

  $$("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  /* --- Search ------------------------------------------------------------- */
  const resultsWrap = $("[data-search-results]");
  const searchTitle = $("[data-search-title]");
  const searchCount = $("[data-search-count]");

  const highlight = (text, query) => {
    const fragment = document.createDocumentFragment();
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) {
      fragment.append(document.createTextNode(text));
      return fragment;
    }

    const pattern = new RegExp(
      `(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
      "gi"
    );

    let last = 0;
    text.split(pattern).forEach((part, index) => {
      if (index % 2 === 1) {
        fragment.append(el("mark", { text: part }));
      } else if (part) {
        fragment.append(document.createTextNode(part));
        last += part.length;
      }
    });
    return fragment;
  };

  const renderResults = (data) => {
    resultsWrap.textContent = "";
    searchTitle.textContent = data.query ? `Results for “${data.query}”` : "Search results";

    if (!data.results.length) {
      resultsWrap.append(
        el("div", { class: "panel__body" }, [
          el("p", { class: "muted" },
            "No verses match that. Try a shorter or more common word — the search " +
            "looks for every word you type."),
        ])
      );
      searchCount.hidden = true;
      return;
    }

    searchCount.hidden = false;
    searchCount.textContent = `${data.count} match${data.count === 1 ? "" : "es"}`;

    const list = el("div");
    data.results.forEach((item) => {
      const reference = item.verse
        ? `${item.book} ${item.chapter}:${item.verse}`
        : item.reference;

      list.append(
        el("a", { class: "result", href: `#${encodeURIComponent(reference)}` }, [
          el("p", { class: "result__ref" }, reference),
          el("p", { class: "result__text" }, [highlight(item.text, data.query)]),
        ])
      );
    });

    // Clicking a result should open that passage in the reader.
    $$(".result", list).forEach((node) => {
      node.addEventListener("click", (event) => {
        event.preventDefault();
        const label = node.querySelector(".result__ref").textContent;
        referenceInput.value = label;
        setView("read");
        loadReference(label);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });

    resultsWrap.append(list);
  };

  const runSearch = async (query) => {
    const term = query.trim();
    if (term.length < 2) {
      setView("read");
      setNotice(errorBox, "Enter at least two characters to search.", "error");
      return;
    }

    setView("search");
    resultsWrap.textContent = "";
    resultsWrap.append(
      el("div", { class: "panel__body" }, [
        el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Searching…"]),
      ])
    );

    try {
      const data = await api.searchBible(term, 40);
      renderResults(data);
    } catch (error) {
      resultsWrap.textContent = "";
      resultsWrap.append(
        el("div", { class: "panel__body" }, [
          el("div", { class: "notice notice--error" }, [
            icons.alert(18),
            el("span", { text: describeError(error) }),
          ]),
        ])
      );
    }
  };

  $("[data-search-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch($("[data-search]").value);
  });

  /* --- Daily verse -------------------------------------------------------- */
  const dailyWrap = $("[data-daily]");
  if (dailyWrap) {
    api
      .verseOfTheDay()
      .then((data) => {
        dailyWrap.textContent = "";
        dailyWrap.append(
          el("span", { class: "badge badge--gold" }, data.theme),
          el("p", { class: "hero__verse", style: "margin-top:18px" }, `“${data.text}”`),
          el("p", { class: "hero__ref" }, data.reference),
          el("div", { class: "row", style: "justify-content:center;margin-top:24px" }, [
            el("a", {
              class: "btn btn--ghost btn--sm",
              href: `#${encodeURIComponent(data.reference)}`,
              onClick: (event) => {
                event.preventDefault();
                referenceInput.value = data.reference;
                setView("read");
                loadReference(data.reference);
                window.scrollTo({ top: 0, behavior: "smooth" });
              },
            }, "Read the passage"),
            el("a", {
              class: "btn btn--gold btn--sm",
              href: `/prayer.html?reference=${encodeURIComponent(data.reference)}`,
            }, "Pray about it"),
          ])
        );
      })
      .catch((error) => {
        dailyWrap.textContent = "";
        dailyWrap.append(
          el("p", { class: "small muted" }, describeError(error))
        );
      });
  }

  /* --- Boot --------------------------------------------------------------- */
  api
    .books()
    .then((data) => {
      books = [];
      data.testaments.old.forEach((book) =>
        books.push({ ...book, testament: "Old Testament" })
      );
      data.testaments.new.forEach((book) =>
        books.push({ ...book, testament: "New Testament" })
      );

      const list = fillBooks("");
      if (list.length) {
        fillChapters("John");
        bookSelect.value = "John";
        chapterSelect.value = "3";
        loadPassage("John", 3);
      }
    })
    .catch((error) => {
      bookSelect.textContent = "";
      bookSelect.append(el("option", {}, "Could not load books"));
      setNotice(errorBox, describeError(error), "error");
    });
})();
