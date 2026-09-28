/* ==========================================================================
   Great Church AI — sermon notes
   The passage text is fetched from the API and sent with the outline prompt,
   so the model works from the actual KJV words rather than from memory.
   ========================================================================== */

(() => {
  "use strict";

  const {
    $, $$, el, api, ai, toast, copyText, describeError, icons, setNotice, renderRich,
  } = window.GCA;

  const referenceInput = $("[data-reference]");
  const titleInput = $("[data-title]");
  const bodyInput = $("[data-body]");
  const buildBtn = $("[data-outline]");
  const outputEl = $("[data-output]");
  const errorBox = $("[data-error]");
  const aiError = $("[data-ai-error]");
  const copyBtn = $("[data-copy]");
  const downloadBtn = $("[data-download]");
  const sourceEl = $("[data-source]");
  const translationEl = $("[data-translation]");

  if (!buildBtn) return;

  let currentText = "";
  let busy = false;

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

  const download = (text, reference) => {
    const header = [
      "SERMON NOTES — DRAFT SCAFFOLD",
      `Passage: ${reference}`,
      `Prepared: ${new Date().toLocaleString()}`,
      "",
      "This is a drafting outline produced by Great Church AI. It is not a sermon,",
      "and it is not the Word of God. Check every point against the text and",
      "preach it in your own voice.",
      "",
      "=".repeat(60),
      "",
    ].join("\n");

    const blob = new Blob([`${header}${text}\n`], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = el("a", {
      href: url,
      download: `sermon-${reference.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.txt`,
    });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast("Outline saved to your downloads.");
  };

  const build = async () => {
    if (busy) return;

    const reference = referenceInput.value.trim();
    if (!reference) {
      setNotice(errorBox, "Enter a passage, for example Psalm 23 or Mark 4:35-41.", "error");
      referenceInput.focus();
      return;
    }

    busy = true;
    buildBtn.disabled = true;
    setNotice(errorBox, "");
    setNotice(aiError, "");
    outputEl.textContent = "";
    outputEl.append(
      el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Reading the text…"])
    );
    sourceEl.hidden = true;
    copyBtn.hidden = true;
    downloadBtn.hidden = true;
    translationEl.hidden = true;

    try {
      const data = await api.outlineSermon({
        reference,
        title: titleInput.value.trim() || null,
        body: bodyInput.value.trim() || null,
      });

      translationEl.textContent = data.translation || "KJV";
      translationEl.hidden = false;

      let reply = data.reply;

      if (!reply) {
        const ready = await waitForPuter();
        if (!ready) {
          outputEl.textContent = "";
          setNotice(
            aiError,
            "The AI engine did not load, so no outline was written. The passage is " +
            "still readable in the Bible reader, and you can keep drafting here.",
            "error"
          );
          return;
        }

        outputEl.textContent = "";
        outputEl.append(
          el("p", { class: "muted row" }, [el("span", { class: "spinner" }), " Building the outline…"])
        );

        const result = await ai.run({
          system: data.prompt.system,
          messages: data.prompt.messages,
        });

        if (!result.ok) {
          outputEl.textContent = "";
          setNotice(
            aiError,
            result.reason === "unavailable"
              ? "No AI engine is available in this browser right now."
              : "The model did not return an outline. Please try again.",
            "error"
          );
          return;
        }
        reply = result.text;
      }

      currentText = reply;

      outputEl.textContent = "";
      outputEl.append(
        el("div", { class: "notice notice--quiet", style: "margin-bottom:22px" }, [
          icons.alert(17),
          el("span", {
            text:
              "A drafting scaffold from a machine, not from your church. Every point " +
              "below should be checked against the text before you preach it.",
          }),
        ])
      );
      renderRich(outputEl, reply);

      sourceEl.hidden = false;
      sourceEl.textContent = data.mode === "server" ? "Server model" : "Your browser";
      copyBtn.hidden = false;
      downloadBtn.hidden = false;

      copyBtn.onclick = async () => {
        if (await copyText(currentText)) {
          copyBtn.innerHTML = `${icons.check(14)}<span>Copied</span>`;
          copyBtn.classList.add("is-done");
          setTimeout(() => {
            copyBtn.innerHTML = `${icons.copy(14)}<span>Copy</span>`;
            copyBtn.classList.remove("is-done");
          }, 1800);
        } else {
          toast("Your browser blocked copying. Select the text and copy it manually.");
        }
      };

      downloadBtn.onclick = () => download(currentText, data.reference);
    } catch (error) {
      outputEl.textContent = "";
      outputEl.append(
        el("p", { class: "muted" }, "No outline was produced.")
      );
      setNotice(errorBox, describeError(error), "error");
    } finally {
      busy = false;
      buildBtn.disabled = false;
    }
  };

  buildBtn.addEventListener("click", build);

  referenceInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      build();
    }
  });

  // Arriving from a passage link, e.g. sermons.html?reference=Romans 8:28
  const requested = new URLSearchParams(location.search).get("reference");
  if (requested) referenceInput.value = requested;
})();
