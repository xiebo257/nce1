/* Shared behavior for the static lesson pages. No network requests or dependencies. */
(() => {
  "use strict";
  const form = document.querySelector("#lesson-form");
  if (!form) return;
  const answers = [...form.querySelectorAll("[data-answer]")];
  const editable = answers.filter(
    (field) => !field.hasAttribute("data-example"),
  );
  const submit = document.querySelector("#submit-answers");
  const status = document.querySelector("#copy-status");
  const dialog = document.querySelector("#copy-dialog");
  const reportField = document.querySelector("#copy-report");
  let statusTimeout;

  function updateProgress() {
    const completed = editable.filter((field) => field.value.trim()).length;
    document.querySelector("#answered-count").textContent = completed;
    document.querySelector("#question-count").textContent = editable.length;
    const progress = document.querySelector("#answer-progress");
    progress.max = editable.length;
    progress.value = completed;
  }

  function buildReport() {
    const count = editable.filter((field) => field.value.trim()).length;
    const lines = [
      `New Concept English · Book 1 · Lesson ${document.body.dataset.lesson}`,
      document.querySelector("h1").textContent.trim(),
      `Completed: ${count}/${editable.length} questions (worked examples excluded)`,
      "Your answers and answer key / 我的答案与参考答案",
      "",
    ];
    let group = "";
    for (const field of answers) {
      if (field.dataset.group !== group) {
        group = field.dataset.group;
        lines.push(`=== ${group} ===`, "");
      }
      const example = field.hasAttribute("data-example");
      lines.push(
        `${field.dataset.number}. ${field.dataset.prompt}${example ? " [Worked example / 示例]" : ""}`,
        `${example ? "Example" : "Your answer"}: ${field.value.trim() || "[Not answered / 未作答]"}`,
        `Key: ${field.dataset.key}`,
        "",
      );
    }
    lines.push("Sources:");
    for (const link of document.querySelectorAll(".source-links a")) {
      lines.push(`${link.textContent.trim()}: ${link.getAttribute("href")}`);
    }
    if (form.dataset.answerNote) lines.push("", form.dataset.answerNote);
    return lines.join("\n");
  }

  function notify(message) {
    clearTimeout(statusTimeout);
    status.textContent = message;
    status.hidden = false;
    statusTimeout = setTimeout(() => {
      status.hidden = true;
    }, 5000);
  }

  function legacyCopy(text) {
    const previousFocus = document.activeElement;
    const buffer = document.createElement("textarea");
    buffer.value = text;
    buffer.readOnly = true;
    buffer.setAttribute("aria-label", "Answer report for copying");
    Object.assign(buffer.style, {
      position: "fixed",
      left: "-9999px",
      top: "0",
    });
    document.body.append(buffer);
    buffer.select();
    buffer.setSelectionRange(0, buffer.value.length);
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      /* Manual copy is available below. */
    }
    buffer.remove();
    previousFocus?.focus({ preventScroll: true });
    return copied;
  }

  async function copyReport(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        /* File URLs and browser permissions can require a fallback. */
      }
    }
    return legacyCopy(text);
  }

  form.addEventListener("input", updateProgress);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    submit.disabled = true;
    submit.setAttribute("aria-busy", "true");
    const report = buildReport();
    try {
      if (await copyReport(report)) {
        notify("Copied all answers + key. 全部答案和参考答案已复制。");
      } else {
        reportField.value = report;
        dialog.showModal();
        reportField.focus();
        reportField.select();
      }
    } finally {
      submit.disabled = false;
      submit.removeAttribute("aria-busy");
    }
  });
  document.querySelector("#select-report").addEventListener("click", () => {
    reportField.focus();
    reportField.select();
    reportField.setSelectionRange(0, reportField.value.length);
  });
  document
    .querySelector("#close-dialog")
    .addEventListener("click", () => dialog.close());

  const menu = document.querySelector("#section-menu");
  const compact = window.matchMedia("(max-width: 960px)");
  function adaptMenu() {
    menu.open = !compact.matches;
  }
  adaptMenu();
  compact.addEventListener("change", adaptMenu);
  const navLinks = [...menu.querySelectorAll("nav a")];
  const sections = navLinks.map((link) =>
    document.querySelector(link.getAttribute("href")),
  );
  let scheduled = false;
  function updateNavigation() {
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= window.innerHeight * 0.32)
        current = section;
    }
    for (const link of navLinks) {
      if (link.getAttribute("href") === `#${current.id}`)
        link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
    scheduled = false;
  }
  window.addEventListener(
    "scroll",
    () => {
      if (!scheduled) {
        scheduled = true;
        requestAnimationFrame(updateNavigation);
      }
    },
    { passive: true },
  );
  menu.querySelectorAll("a").forEach((link) =>
    link.addEventListener("click", () => {
      if (compact.matches) menu.open = false;
    }),
  );
  updateProgress();
  updateNavigation();
})();
