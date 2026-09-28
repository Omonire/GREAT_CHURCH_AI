/* ==========================================================================
   Great Church AI — Bible study
   Step 1: choose passage  Step 2: read  Step 3: work through it
   ========================================================================== */

(() => {
  "use strict";

  const {
    $, $$, el, api, ai, toast, copyText, describeError, icons, setNotice, renderRich,
  } = window.GCA;

  const testamentSelect = $("[data-testament]");
  const bookSelect = $("[data-book]");
  const chapterSelect = $("[data-chapter]");
  const versesInput = $("[data-verses]");
  const referenceInput = $("[data-reference]");
  const goBtn = $("[data-go]");
  const errorBox = $("[data-error]");
  const metaEl = $("[data-meta]");
  const refEl = $("[data-ref]");
  const countEl = $("[data-count]");
  const translationEl = $("[data-translation]");
  const passageEl = $("[data-passage]");
  const copyBtn = $("[data-copy]");
  const outputEl = $("[data-output]");
  const aiError = $("[data-ai-error]");
  const engineEl = $("[data-engine]");

  if (!bookSelect) return;

  let books = [];
  let current = null;
  let busy = false;

  /* --- Pickers ----------------------------------------------------------- */
  const fillBooks = (testament) => {
    const list = testament
      ? books.filter((b) => b.testament === testament)
      : books;

    bookSelect.textContent = "";
    list.forEach((book) => bookSelect.append(el("option", { value: book.name }, book.name)));
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

  /* --- Reading ----------------------------------------------------------- */
  const showPlaceholder = (text) => {
    passageEl.textContent = "";
    metaEl.hidden = true;
    passageEl.append(el("p", { class: "muted" }, text));
  };

  const paintPassage = (data) => {
    current = data;

    refEl.textContent = data.reference;
    countEl.textContent = `${data.verses.length} verse${data.verses.length === 1 ? "" : "s"}`;
    translationEl.textContent = data.translation;
    translationEl.hidden = false;
    copyBtn.hidden = false;
    metaEl.hidden = false;

    passageEl.textContent = "";
    data.verses.forEach((verse) => {
      passageEl.append(
        el("p", { class: "scripture__verse" }, [
          el("span", { class: "scripture__num", "aria-hidden": "true" }, String(verse.verse)),
          el("span", {}, [el("span", { class: "sr-only" }, `Verse ${verse.verse}: `), verse.text]),
        ])
      );
    });

    // The passage loaded, so the study actions are now meaningful.
    outputEl.textContent = "";
    outputEl.append(
      el("p", { class: "muted small" },
        `${data.reference} is loaded. Choose an action above to work through it.`)
    );

    // Keep the "next step" links pointed at this passage.
    const encoded = encodeURIComponent(data.reference);
    const prayerLink = $("[data-next='prayer']");
    const chatLink = $("[data-next='chat']");
    if (prayerLink) prayerLink.href = `/prayer.html?reference=${encoded}`;
    if (chatLink) chatLink.href = `/chat.html?reference=${encoded}`;

    referenceInput.value = data.reference;
  };

  const loadByReference = async (reference) => {
    setNotice(errorBox, "");
    showPlaceholder("Loading…");
    try {
      paintPassage(await api.passage(reference));
    } catch (error) {
      showPlaceholder("");
      metaEl.hidden = true;
      copyBtn.hidden = true;
      setNotice(errorBox, describeError(error), "error");
    }
  };

  const loadFromPickers = () => {
    const book = bookSelect.value;
    const chapter = chapterSelect.value;
    if (!book || !chapter) {
      setNotice(errorBox, "Choose a book and a chapter first.", "error");
      return;
    }
    const verses = versesInput.value.trim();
    const reference = verses
      ? `${book} ${chapter}:${verses.replace(/\s+/g, "")}`
      : `${book} ${chapter}`;
    loadByReference(reference);
  };

  /* --- Events ------------------------------------------------------------ */
  testamentSelect?.addEventListener("change", () => {
    const list = fillBooks(testamentSelect.value);
    if (list.length) {
      fillChapters(list[0].name);
      chapterSelect.value = "1";
    }
  });

  bookSelect.addEventListener("change", () => fillChapters(bookSelect.value));
  chapterSelect.addEventListener("change", () => versesInput.focus());
  goBtn?.addEventListener("click", loadFromPickers);
  versesInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadFromPickers();
    }
  });
  referenceInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      referenceInput.value.trim() && loadByReference(referenceInput.value.trim());
    }
  });

  copyBtn?.addEventListener("click", async () => {
    if (!current) return;
    const text = `${current.reference}\n\n${passageEl.textContent.trim()}`;
    if (await copyText(text)) toast(`${current.reference} copied.`);
    else toast("Your browser blocked copying. Select the text and copy it manually.");
  });

  /* --- Study actions ----------------------------------------------------- */
  const ACTIONS = {
    explain: "Explain this passage clearly and faithfully.",
    summarize: "Summarise the main point of this passage in a few sentences.",
    themes: "What are the key themes in this passage?",
    reflect: "Give me reflection questions to work through this passage myself.",
    related: "Which other Scripture passages relate to this one, and why?",
  };

  const waitForPuter = (timeout = 6000) =>
    new Promise((resolve) => {
      if (ai.isReady()) return resolve(true);
      const started = Date.now();
      const tick = setInterval(() => {
        if (ai.isReady()) {
          clearInterval(tick);
          resolve(true);
        } else if (Date.now() - started > timeout) {
          clearInterval(tick);
          resolve(false);
        }
      }, 180);
    });

  const runAction = async (action) => {
    if (busy) return;

    if (!current) {
      setNotice(aiError, "Load a passage first, then choose an action.", "error");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    busy = true;
    $$("[data-action]").forEach((b) => (b.disabled = true));
    setNotice(aiError, "");
    outputEl.textContent = "";
    outputEl.append(
      el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Thinking…"])
    );

    try {
      const prepared = await api.prepareStudy(current.reference, ACTIONS[action]);

      let reply = prepared.reply;
      if (!reply) {
        const ready = await waitForPuter();
        if (!ready) {
          setNotice(
            aiError,
            "The AI engine did not load, so no answer was produced. The passage above is " +
            "still readable, and the Bible reader works without AI.",
            "error"
          );
          return;
        }
        const result = await ai.run({
          system: prepared.prompt.system,
          messages: prepared.prompt.messages,
        });
        if (!result.ok) {
          setNotice(
            aiError,
            result.reason === "unavailable"
              ? "No AI engine is available in this browser right now."
              : "The model did not return an answer. Please try that action again.",
            "error"
          );
          return;
        }
        reply = result.text;
      }

      renderRich(outputEl, reply);
      outputEl.append(
        el("div", { class: "row", style: "margin-top:24px;padding-top:20px;border-top:1px solid var(--line)" }, [
          el("button", {
            class: "icon-btn",
            type: "button",
            onClick: async (event) => {
              if (await copyText(reply)) {
                const b = event.currentTarget;
                b.innerHTML = `${icons.check(14)}<span>Copied</span>`;
                b.classList.add("is-done");
                setTimeout(() => {
                  b.innerHTML = `${icons.copy(14)}<span>Copy</span>`;
                  b.classList.remove("is-done");
                }, 1800);
              } else {
                toast("Your browser blocked copying. Select the text and copy it manually.");
              }
            },
          }, [`${icons.copy(14)}<span>Copy</span>`]),
          el("a", {
            class: "icon-btn",
            href: `/prayer.html?reference=${encodeURIComponent(current.reference)}`,
          }, [`${icons.spark(14)}<span>Pray about this</span>`])
        ])
      );
    } catch (error) {
      setNotice(aiError, describeError(error), "error");
    } finally {
      busy = false;
      $$("[data-action]").forEach((b) => (b.disabled = false));
    }
  };

  $$("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });

  /* --- Engine badge ------------------------------------------------------ */
  const reportEngine = () => {
    if (!engineEl) return;
    if (ai.isReady()) {
      engineEl.textContent = "AI in your browser via Puter";
      engineEl.style.color = "var(--success)";
    } else {
      engineEl.textContent = "AI unavailable — reading still works";
      engineEl.style.color = "var(--ink-muted)";
    }
  };
  reportEngine();
  setTimeout(reportEngine, 1200);
  setTimeout(reportEngine, 3000);

  /* --- Boot -------------------------------------------------------------- */
  api
    .books()
    .then((data) => {
      books = [];
      data.testaments.old.forEach((b) => books.push({ ...b, testament: "Old Testament" }));
      data.testaments.new.forEach((b) => books.push({ ...b, testament: "New Testament" }));

      const list = fillBooks("");
      if (list.length) {
        bookSelect.value = "John";
        fillChapters("John");
        chapterSelect.value = "3";
      }

      // Support arriving from a link such as study.html?reference=Romans 8:28
      const requested = new URLSearchParams(location.search).get("reference");
      if (requested) {
        loadByReference(requested);
      } else {
        showPlaceholder("Choose a book and chapter above, then press Load passage.");
      }
    })
    .catch((error) => {
      bookSelect.textContent = "";
      bookSelect.append(el("option", {}, "Could not load books"));
      setNotice(errorBox, describeError(error), "error");
    });
})();
