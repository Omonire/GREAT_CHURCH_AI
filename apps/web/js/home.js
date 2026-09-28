/* Great Church AI — home page: today's passage + share/copy. */

(() => {
  "use strict";

  const { $, api, el, copyText, toast, describeError, icons } = window.GCA;

  const target = $("[data-votd]");
  if (!target) return;

  const render = (data) => {
    target.textContent = "";

    target.append(
      el("p", { class: "hero__verse", text: `“${data.text}”` }),
      el("p", { class: "hero__ref", text: data.reference })
    );

    // Keep the reference in the DOM so the copy button has something to read.
    target.dataset.text = `${data.text} — ${data.reference} (${data.translation_short})`;
  };

  const fail = (error) => {
    target.textContent = "";
    target.append(
      el("p", {
        class: "small muted",
        text: "Today's passage could not be loaded. The Bible reader still works without a connection.",
      })
    );
    const note = $("[data-votd-note]");
    if (note) note.textContent = describeError(error);
  };

  api
    .verseOfTheDay()
    .then(render)
    .catch(fail);

  const copyBtn = $("[data-copy-target='votd']");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const text = target.dataset.text;
      if (!text) {
        toast("There is nothing to copy yet.");
        return;
      }
      const ok = await copyText(text);
      if (ok) {
        copyBtn.innerHTML = `${icons.check(15)}<span>Copied</span>`;
        copyBtn.classList.add("is-done");
        setTimeout(() => {
          copyBtn.innerHTML = `${icons.copy(15)}<span>Copy</span>`;
          copyBtn.classList.remove("is-done");
        }, 1800);
      } else {
        toast("Your browser blocked copying. Select the text and copy it manually.");
      }
    });
  }
})();
