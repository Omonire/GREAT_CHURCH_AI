/* ==========================================================================
   Great Church AI — chat
   Server prepares the prompt; Puter.js runs it in the browser.
   Every failure path ends in an honest message, never a fake answer.
   ========================================================================== */

(() => {
  "use strict";

  const {
    $, el, api, ai, toast, copyText, describeError, icons, renderRich, setNotice,
  } = window.GCA;

  const form = $("[data-form]");
  const input = $("[data-input]");
  const sendBtn = $("[data-send]");
  const thread = $("[data-thread]");
  const log = $("[data-log]");
  const welcome = $("[data-welcome]");
  const startersWrap = $("[data-starters]");
  const statusEl = $("[data-status]");
  const engineEl = $("[data-engine]");
  const errorBox = $("[data-ai-error]");

  if (!form) return;

  /** @type {{role:string, content:string}[]} */
  const history = [];
  const MAX_HISTORY = 12;
  let busy = false;
  let controller = null;

  /* --- Engine status ---------------------------------------------------- */
  const reportEngine = () => {
    if (!engineEl) return;
    if (ai.isReady()) {
      engineEl.textContent = "AI running in your browser via Puter";
      engineEl.style.color = "var(--success)";
    } else {
      engineEl.textContent = "AI unavailable — read, search, and study still work";
      engineEl.style.color = "var(--ink-muted)";
    }
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

  /* --- Message rendering ------------------------------------------------ */
  const scrollToEnd = () => {
    requestAnimationFrame(() => {
      log.scrollTop = log.scrollHeight;
    });
  };

  const hideWelcome = () => {
    if (welcome && welcome.parentNode) welcome.remove();
  };

  const addUserMessage = (text) => {
    hideWelcome();
    const bubble = el("div", { class: "msg__bubble" }, [el("p", { text })]);
    thread.append(
      el("div", { class: "msg msg--user" }, [
        el("div", { class: "msg__avatar" }, [iconNode(icons.chat(17))]),
        bubble,
      ])
    );
    scrollToEnd();
  };

  const iconNode = (markup) => {
    const span = document.createElement("span");
    span.innerHTML = markup;
    return span.firstElementChild;
  };

  /** Adds an assistant message and returns its body node for streaming text. */
  const addAiMessage = () => {
    hideWelcome();

    const body = el("div", { class: "msg__bubble" });
    const typing = el("span", { class: "typing" }, [
      el("span"), el("span"), el("span"),
    ]);
    body.append(typing);

    const foot = el("div", { class: "msg__foot" });
    const wrapper = el("div", { class: "msg msg--ai" }, [
      el("div", { class: "msg__avatar" }, [iconNode(icons.spark(17))]),
      el("div", { style: "min-width:0" }, [body, foot]),
    ]);

    thread.append(wrapper);
    scrollToEnd();

    return { body, foot, typing };
  };

  const showTyping = (message, label = "Great Church AI is thinking") => {
    message.typing.setAttribute("role", "status");
    message.typing.setAttribute("aria-label", label);
  };

  const renderAnswer = (message, text) => {
    message.typing.remove();
    renderRich(message.body, text);
    message.foot.append(
      el("button", {
        class: "icon-btn",
        type: "button",
        onClick: async (event) => {
          const button = event.currentTarget;
          if (await copyText(text)) {
            button.innerHTML = `${icons.check(14)}<span>Copied</span>`;
            button.classList.add("is-done");
            setTimeout(() => {
              button.innerHTML = `${icons.copy(14)}<span>Copy</span>`;
              button.classList.remove("is-done");
            }, 1800);
          } else {
            toast("Your browser blocked copying. Select the text and copy it manually.");
          }
        },
      }, [`${icons.copy(14)}<span>Copy</span>`]),

      el("button", {
        class: "icon-btn",
        type: "button",
        onClick: () => retryLast(text),
      }, [`${icons.retry(14)}<span>Ask again</span>`])
    );
    scrollToEnd();
  };

  const renderFailure = (message, { title, body, offerRetry = true }) => {
    message.typing.remove();
    message.body.textContent = "";
    message.body.append(
      el("div", { class: "notice notice--error" }, [
        icons.alert(18),
        el("div", {}, [
          el("strong", { text: title }),
          el("p", { text: body, style: "margin-top:6px" }),
        ]),
      ])
    );

    if (offerRetry) {
      message.foot.append(
        el("button", {
          class: "icon-btn",
          type: "button",
          onClick: () => retryLast(title),
        }, [`${icons.retry(14)}<span>Try again</span>`])
      );
    }
    scrollToEnd();
  };

  /* --- Conversation ----------------------------------------------------- */
  let lastQuestion = "";

  /* A passage pinned by ?reference=… keeps the whole conversation anchored to
     the same text, which is what someone arriving from a study link wants. */
  const anchorReference =
    new URLSearchParams(location.search).get("reference") || null;

  if (anchorReference && thread) {
    thread.prepend(
      el("div", { class: "shell shell--narrow", style: "margin-bottom:6px" }, [
        el("div", { class: "notice notice--info" }, [
          icons.book(18),
          el("span", { text: `Answering in the context of ${anchorReference}.` }),
        ]),
      ])
    );
  }

  const pushHistory = (role, content) => {
    history.push({ role, content });
    if (history.length > MAX_HISTORY) {
      history.splice(0, history.length - MAX_HISTORY);
    }
  };

  const ask = async (question) => {
    if (busy || !question.trim()) return;

    lastQuestion = question.trim();
    busy = true;
    sendBtn.disabled = true;
    setNotice(errorBox, "");
    if (statusEl) statusEl.textContent = "Preparing your question…";

    addUserMessage(lastQuestion);

    const message = addAiMessage();
    controller = new AbortController();

    try {
      // 1. The server works out what you are asking and frames it properly.
      const prepared = await api.prepareChat(
        lastQuestion,
        history.slice(0, -1),
        anchorReference
      );

      if (prepared.scripture?.text) {
        message.body.insertBefore(
          el("div", {
            class: "notice notice--info",
            style: "margin-bottom:14px",
          }, [
            icons.book(18),
            el("span", {
              text: `Anchored to ${prepared.scripture.reference} (${prepared.scripture.translation_short}).`,
            }),
          ]),
          message.typing
        );
      }

      // 2. The browser runs the model. No key, nothing stored server-side.
      if (statusEl) statusEl.textContent = "Thinking…";
      showTyping(message);

      if (prepared.reply) {
        // A server-side provider is configured, so use its answer.
        renderAnswer(message, prepared.reply);
        pushHistory("assistant", prepared.reply);
      } else {
        const ready = await waitForPuter();
        if (!ready) {
          renderFailure(message, {
            title: "The AI engine did not load.",
            body:
              "Puter.js could not be reached, so no model answered. This usually means a " +
              "content blocker, an offline connection, or a network that blocks the script. " +
              "The Bible reader, search, and study pages work without it.",
            offerRetry: false,
          });
          return;
        }

        const result = await ai.run({
          system: prepared.prompt.system,
          messages: prepared.prompt.messages,
        });

        if (!result.ok) {
          if (result.reason === "aborted") {
            message.typing.remove();
            message.body.textContent = "";
            message.body.append(
              el("p", { class: "muted small", text: "Cancelled." })
            );
            return;
          }
          renderFailure(message, {
            title: "The AI could not answer just now.",
            body:
              result.reason === "unavailable"
                ? "No AI engine is available in this browser right now."
                : "The model did not return an answer. You can try again, or open the passage in the Bible reader.",
          });
          return;
        }

        renderAnswer(message, result.text);
        pushHistory("assistant", result.text);
      }

      if (statusEl) statusEl.textContent = "Press Enter to send · Shift + Enter for a new line";
    } catch (error) {
      if (error?.name === "AbortError") return;
      renderFailure(message, {
        title: "Something went wrong while preparing your response.",
        body: describeError(error),
      });
      if (statusEl) statusEl.textContent = "Press Enter to send · Shift + Enter for a new line";
    } finally {
      busy = false;
      sendBtn.disabled = false;
      input.focus();
    }
  };

  const retryLast = (question) => {
    const text = typeof question === "string" && question.length < 200 ? question : lastQuestion;
    if (!text) return;
    // Drop the failed turn so the retry is not sent twice.
    const index = history.findIndex((item) => item.content === lastQuestion);
    if (index >= 0) history.splice(index, 1);
    ask(text);
  };

  /* --- Submit ---------------------------------------------------------- */
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    input.value = "";
    input.style.height = "auto";
    pushHistory("user", value);
    ask(value);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  /* --- Clear ------------------------------------------------------------ */
  const clearBtn = $("[data-clear]");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (controller) controller.abort();
      history.length = 0;
      lastQuestion = "";
      thread.textContent = "";
      window.location.reload();
    });
  }

  /* --- Starter prompts -------------------------------------------------- */
  const paintStarters = (starters) => {
    if (!startersWrap) return;
    startersWrap.textContent = "";
    starters.slice(0, 6).forEach((item) => {
      startersWrap.append(
        el("button", {
          class: "starter",
          type: "button",
          onClick: () => {
            input.value = item.prompt;
            pushHistory("user", item.prompt);
            ask(item.prompt);
          },
        }, item.label)
      );
    });
  };

  api
    .starterPrompts()
    .then((data) => paintStarters(data.starters || []))
    .catch(() => {
      if (startersWrap) {
        startersWrap.append(
          el("p", {
            class: "small muted",
            text: "Suggested questions could not be loaded. Type your own below.",
          })
        );
      }
    });

  reportEngine();
  // Puter loads with `defer`, so poll briefly until it is usable.
  setTimeout(reportEngine, 1200);
  setTimeout(reportEngine, 3000);
})();
