/* ==========================================================================
   Great Church AI — prayer
   Left:  fixed templates, always available, no AI needed.
   Right: AI-written, only offered when an engine actually answers.
   ========================================================================== */

(() => {
  "use strict";

  const {
    $, $$, el, api, ai, toast, copyText, describeError, icons, setNotice,
  } = window.GCA;

  const topicSelect = $("[data-topic]");
  const detailInput = $("[data-detail]");
  const referenceInput = $("[data-reference]");
  const generateBtn = $("[data-generate]");
  const outputEl = $("[data-output]");
  const errorBox = $("[data-error]");
  const copyBtn = $("[data-copy]");
  const saveBtn = $("[data-save]");

  const aiPrompt = $("[data-ai-prompt]");
  const aiGenerate = $("[data-ai-generate]");
  const aiOutput = $("[data-ai-output]");
  const aiError = $("[data-ai-error]");
  const aiCopy = $("[data-ai-copy]");
  const aiSave = $("[data-ai-save]");
  const aiStatus = $("[data-ai-status]");
  const engineEl = $("[data-engine]");

  if (!topicSelect) return;

  let busy = false;
  let savedTitle = "Prayer";

  /* --- Saving (this device only) ------------------------------------------ */
  const save = (text) => {
    const stored = JSON.parse(localStorage.getItem("gca:prayers") || "[]");
    stored.unshift({
      title: savedTitle,
      text,
      saved: new Date().toISOString(),
    });
    localStorage.setItem("gca:prayers", JSON.stringify(stored.slice(0, 50)));
    toast("Saved on this device only.");
  };

  const wireActions = (text, copyButton, saveButton) => {
    copyButton.hidden = false;
    saveButton.hidden = false;

    copyButton.onclick = async () => {
      if (await copyText(text)) {
        copyButton.innerHTML = `${icons.check(14)}<span>Copied</span>`;
        copyButton.classList.add("is-done");
        setTimeout(() => {
          copyButton.innerHTML = `${icons.copy(14)}<span>Copy</span>`;
          copyButton.classList.remove("is-done");
        }, 1800);
      } else {
        toast("Your browser blocked copying. Select the text and copy it manually.");
      }
    };

    saveButton.onclick = () => save(text);
  };

  /* --- Offline prayer ----------------------------------------------------- */
  const buildOffline = async () => {
    if (busy) return;
    busy = true;
    generateBtn.disabled = true;
    setNotice(errorBox, "");
    outputEl.textContent = "";
    outputEl.append(
      el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Assembling…"])
    );

    try {
      const data = await api.generatePrayer({
        topic: topicSelect.value,
        detail: detailInput.value.trim() || null,
        reference: referenceInput.value.trim() || null,
      });

      // The server either generated it, or it sent the assembled fallback.
      const text = data.text || data.fallback?.text;
      if (!text) throw new Error("No prayer text came back.");

      savedTitle = data.fallback?.anchor_scripture
        ? `Prayer · ${data.fallback.anchor_scripture.reference}`
        : `Prayer · ${data.topic}`;

      outputEl.textContent = "";
      outputEl.append(
        el("p", { class: "eyebrow" }, data.topic)
      );

      if (data.source === "ai") {
        outputEl.append(
          el("div", { class: "notice notice--quiet", style: "margin-bottom:20px" }, [
            icons.alert(17),
            el("span", { text: "AI-written. Make it yours before you pray it." }),
          ])
        );
      } else {
        outputEl.append(
          el("div", { class: "notice notice--info", style: "margin-bottom:20px" }, [
            icons.info(17),
            el("span", {
              text:
                "Assembled on the server from fixed text and a real KJV verse. " +
                "It is not AI-written. For a prayer written to your situation, use " +
                "the panel on the right.",
            }),
          ])
        );
      }

      outputEl.append(el("div", { class: "prayer-text" }, text));

      const anchor = data.anchor_scripture || data.fallback?.anchor_scripture;
      if (anchor) {
        outputEl.append(
          el("p", { class: "prayer-ref" }, [
            el("a", {
              href: `/bible.html#${encodeURIComponent(anchor.reference)}`,
            }, anchor.reference),
          ]),
          el("blockquote", { class: "scripture-quote" }, anchor.text)
        );
      }

      if (data.warning || data.fallback?.warning) {
        outputEl.append(
          el("p", { class: "small muted", style: "margin-top:16px" },
            data.warning || data.fallback.warning)
        );
      }

      wireActions(text, copyBtn, saveBtn);
    } catch (error) {
      setNotice(errorBox, describeError(error), "error");
    } finally {
      busy = false;
      generateBtn.disabled = false;
    }
  };

  generateBtn?.addEventListener("click", buildOffline);

  /* --- AI prayer ---------------------------------------------------------- */
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

  const buildAi = async () => {
    if (busy) return;

    const situation = aiPrompt.value.trim();
    if (!situation) {
      setNotice(aiError, "Tell it what you want to pray about first.", "error");
      aiPrompt.focus();
      return;
    }

    busy = true;
    aiGenerate.disabled = true;
    setNotice(aiError, "");
    if (aiStatus) aiStatus.textContent = "Writing…";
    aiOutput.textContent = "";
    aiOutput.append(
      el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Writing your prayer…"])
    );

    try {
      const prepared = await api.prayerDraft(
        situation,
        referenceInput.value.trim() || null
      );

      let reply = prepared.reply;

      if (!reply) {
        const ready = await waitForPuter();
        if (!ready) {
          setNotice(
            aiError,
            "The AI engine did not load, so nothing was written. The template prayer " +
            "on the left works without it.",
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
              : "The model did not return a prayer. Please try again.",
            "error"
          );
          return;
        }
        reply = result.text;
      }

      savedTitle = `Prayer · ${new Date().toLocaleDateString()}`;

      aiOutput.textContent = "";
      aiOutput.append(
        el("div", { class: "notice notice--quiet", style: "margin-bottom:20px" }, [
          icons.alert(17),
          el("span", { text: "AI-written. Make it yours before you pray it." }),
        ]),
        el("div", { class: "prayer-text" }, reply)
      );

      if (prepared.scripture) {
        aiOutput.append(
          el("p", { class: "prayer-ref" }, [
            el("a", {
              href: `/bible.html#${encodeURIComponent(prepared.scripture.reference)}`,
            }, prepared.scripture.reference),
          ]),
          el("blockquote", { class: "scripture-quote" }, prepared.scripture.text)
        );
      }

      wireActions(reply, aiCopy, aiSave);
    } catch (error) {
      setNotice(aiError, describeError(error), "error");
    } finally {
      busy = false;
      aiGenerate.disabled = false;
      if (aiStatus) aiStatus.textContent = "Nothing is sent anywhere until you press this.";
    }
  };

  aiGenerate?.addEventListener("click", buildAi);
  aiPrompt?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      buildAi();
    }
  });

  /* --- Engine badge -------------------------------------------------------- */
  const reportEngine = () => {
    if (!engineEl) return;
    if (ai.isReady()) {
      engineEl.textContent = "AI in your browser via Puter";
      engineEl.style.color = "var(--success)";
    } else {
      engineEl.textContent = "AI unavailable — template prayer still works";
      engineEl.style.color = "var(--ink-muted)";
    }
  };
  reportEngine();
  setTimeout(reportEngine, 1200);
  setTimeout(reportEngine, 3000);

  /* --- Boot ---------------------------------------------------------------- */
  api
    .prayerTopics()
    .then((data) => {
      const topics = data.topics || [];
      topicSelect.textContent = "";
      topics.forEach((topic) => {
        const label = topic.scripture
          ? `${topic.label} · ${topic.scripture}`
          : topic.label;
        topicSelect.append(el("option", { value: topic.id }, label));
      });
      if (topics.some((t) => t.id === "peace")) topicSelect.value = "peace";
    })
    .catch((error) => {
      topicSelect.textContent = "";
      topicSelect.append(el("option", {}, "Could not load topics"));
      setNotice(errorBox, describeError(error), "error");
    });

  // Arriving from a passage link, e.g. prayer.html?reference=Psalm 34:18
  const requested = new URLSearchParams(location.search).get("reference");
  if (requested && referenceInput) {
    referenceInput.value = requested;
    detailInput.placeholder = `What is happening with ${requested}?`;
  }
})();
