const translations = {
  en: {
    skip: "Skip to content",
    navWhy: "Why",
    navDesktop: "Desktop",
    navWorkflow: "Workflow",
    navInstall: "Install",
    navDocs: "Docs",
    heroEyebrow: "CLI-first control for AI development workspaces",
    heroCopy:
      "Commit the shape of your workspace. Reopen the same tmux sessions, agent panes, commands, editors, remote targets, diagnostics, desktop shell, and browser controls without rebuilding the room by hand.",
    heroPrimary: "Install from GitHub",
    heroSecondary: "View source",
    tickerTmux: "tmux sessions",
    tickerDirect: "direct commands",
    tickerSsh: "SSH panes",
    tickerDesktop: "desktop shell",
    tickerWeb: "Web UI",
    whyKicker: "The local control problem",
    whyTitle: "Your project is no longer one terminal.",
    whyBody1:
      "Modern AI development means agents, shells, dev servers, editor windows, desktop controls, long-lived sessions, and remote boxes all orbiting the same repo. CC Branch gives that orbit a file format and a runtime.",
    whyBody2:
      "The committed config describes what should exist. The local state remembers what is already running. The CLI, Web UI, and desktop shell make the workspace inspectable instead of mysterious.",
    feature1Title: "Config that survives the week",
    feature1Body:
      "Put tabs, panes, agents, commands, directories, environment variables, and openers in `.cc-branch/config.yaml`.",
    feature2Title: "Sessions that come back",
    feature2Body:
      "Start, attach, stop, restart, inspect, prune, and render resume commands for long-running agent sessions.",
    feature3Title: "Desktop without setup drama",
    feature3Body:
      "The desktop shell bundles the backend sidecar, manages the local server, and keeps project control visible outside the terminal.",
    feature4Title: "Doctor before drama",
    feature4Body:
      "Check tmux, paths, commands, agent references, state drift, and low-risk fixes before a broken workspace wastes the morning.",
    desktopKicker: "Desktop shell",
    desktopTitle: "A local control room, not another cloud dashboard.",
    desktopBody:
      "CC Branch Desktop wraps the Web UI in a native shell and runs the backend sidecar locally. It is built for people who want visual project control without giving up terminal-first workflows.",
    desktopPoint1: "Bundled backend sidecar",
    desktopPoint2: "Project switcher and diagnostics",
    desktopPoint3: "Local-only workspace data",
    workflowKicker: "Workspace anatomy",
    workflowTitle: "One config. Multiple execution surfaces.",
    workflowBody:
      "Use tmux when you want durable background sessions. Use direct mode when the right answer is simply opening a local app or running a normal command. Add SSH when a pane belongs on a server.",
    installKicker: "Install today",
    installTitle: "Use the GitHub source package while registries are being prepared.",
    installBody:
      "PyPI, npm, Homebrew, and signed desktop releases are wired in the repo, but public registry publishing is intentionally gated. The source install works now and builds the bundled Web UI.",
    installNote1: "Requires Python 3.10+",
    installNote2: "Node/npm builds the Web UI from source",
    installNote3: "tmux is needed only for tmux-backed tabs",
    installNote4: "Desktop installers are prepared through GitHub Releases",
    docsKicker: "Read next",
    docsTitle: "Everything important is plain files.",
    docStartLabel: "Start",
    docStart: "Getting Started",
    docMapLabel: "Map",
    docMap: "Feature Reference",
    docUseLabel: "Use",
    docUse: "User Guide",
    docShipLabel: "Ship",
    docShip: "Publishing Runbook",
    footer: "MIT licensed. Built for local-first agent workspaces.",
    copy: "Copy",
    copied: "Copied",
    select: "Select",
  },
  zh: {
    skip: "跳到正文",
    navWhy: "为什么",
    navDesktop: "桌面端",
    navWorkflow: "工作流",
    navInstall: "安装",
    navDocs: "文档",
    heroEyebrow: "面向 AI 开发工作空间的 CLI-first 控制层",
    heroCopy:
      "把工作空间的形状提交到配置里。tmux 会话、Agent 窗格、命令、编辑器、远程目标、诊断、桌面端和浏览器控制，都可以稳定恢复，不用每次手动重搭现场。",
    heroPrimary: "从 GitHub 安装",
    heroSecondary: "查看源码",
    tickerTmux: "tmux 会话",
    tickerDirect: "直接命令",
    tickerSsh: "SSH 窗格",
    tickerDesktop: "桌面端",
    tickerWeb: "Web UI",
    whyKicker: "本地控制问题",
    whyTitle: "你的项目已经不再只是一个终端。",
    whyBody1:
      "现代 AI 开发里，Agent、shell、开发服务、编辑器窗口、桌面控制、长期会话和远程机器都围绕同一个仓库运行。CC Branch 给这套现场一个文件格式和运行时。",
    whyBody2:
      "提交的配置描述应该存在什么，本地状态记录已经在运行什么。CLI、Web UI 和桌面端让工作空间可检查、可恢复，而不是一团黑箱。",
    feature1Title: "能陪项目跑一整周的配置",
    feature1Body:
      "把 tabs、panes、agents、commands、目录、环境变量和打开方式写进 `.cc-branch/config.yaml`。",
    feature2Title: "能接回来的会话",
    feature2Body:
      "长期 Agent 会话可以 start、attach、stop、restart、inspect、prune，也可以生成恢复命令。",
    feature3Title: "桌面端，不增加配置负担",
    feature3Body:
      "桌面 shell 内置后端 sidecar，管理本地服务，把项目控制留在终端之外也看得见。",
    feature4Title: "先 doctor，再救火",
    feature4Body:
      "在工作空间浪费你一早上之前，先检查 tmux、路径、命令、Agent 引用、状态漂移和低风险修复。",
    desktopKicker: "桌面端",
    desktopTitle: "这是本地控制室，不是又一个云端 dashboard。",
    desktopBody:
      "CC Branch Desktop 把 Web UI 包进原生桌面壳，并在本地运行后端 sidecar。它适合想要可视化项目控制、但仍坚持终端优先工作流的人。",
    desktopPoint1: "内置后端 sidecar",
    desktopPoint2: "项目切换与诊断",
    desktopPoint3: "工作空间数据保留在本地",
    workflowKicker: "工作空间结构",
    workflowTitle: "一份配置，多种运行表面。",
    workflowBody:
      "需要持久后台会话时用 tmux。只是打开本地应用或运行普通命令时用 direct mode。某个窗格该跑在服务器上时，再加 SSH。",
    installKicker: "现在可用",
    installTitle: "注册表发布准备好之前，先使用 GitHub 源码包。",
    installBody:
      "PyPI、npm、Homebrew 和签名桌面安装包的发布链路已经在仓库里，但公开注册表发布仍受控。源码安装现在可用，并会构建内置 Web UI。",
    installNote1: "需要 Python 3.10+",
    installNote2: "从源码构建 Web UI 需要 Node/npm",
    installNote3: "只有 tmux 布局需要 tmux",
    installNote4: "桌面安装包通过 GitHub Releases 准备",
    docsKicker: "继续阅读",
    docsTitle: "重要的东西都是普通文件。",
    docStartLabel: "开始",
    docStart: "入门指南",
    docMapLabel: "地图",
    docMap: "功能参考",
    docUseLabel: "使用",
    docUse: "用户指南",
    docShipLabel: "发布",
    docShip: "发布手册",
    footer: "MIT 许可。为本地优先的 Agent 工作空间而建。",
    copy: "复制",
    copied: "已复制",
    select: "选中",
  },
};

const storage = {
  get(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Ignore storage failures in locked-down browsers.
    }
  },
};

const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
let currentLang = storage.get("cc-branch-lang", navigator.language?.startsWith("zh") ? "zh" : "en");
let currentTheme = storage.get("cc-branch-theme", prefersDark ? "dark" : "light");

const langButton = document.querySelector("[data-lang-toggle]");
const themeButton = document.querySelector("[data-theme-toggle]");

function applyLanguage(lang) {
  currentLang = translations[lang] ? lang : "en";
  const dictionary = translations[currentLang];
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.getAttribute("data-i18n");
    if (key && dictionary[key]) {
      node.textContent = dictionary[key];
    }
  });
  document.querySelectorAll("[data-copy-label]").forEach((button) => {
    button.textContent = dictionary.copy;
    button.setAttribute("data-copy-label", dictionary.copy);
  });
  if (langButton) {
    langButton.textContent = currentLang === "zh" ? "EN" : "中文";
    langButton.setAttribute("aria-label", currentLang === "zh" ? "Switch to English" : "切换到中文");
  }
  storage.set("cc-branch-lang", currentLang);
}

function applyTheme(theme) {
  currentTheme = theme === "dark" ? "dark" : "light";
  document.body.dataset.theme = currentTheme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    "content",
    currentTheme === "dark" ? "#071415" : "#10292b",
  );
  if (themeButton) {
    themeButton.setAttribute(
      "aria-label",
      currentTheme === "dark" ? "Switch to light mode" : "Switch to dark mode",
    );
  }
  storage.set("cc-branch-theme", currentTheme);
}

langButton?.addEventListener("click", () => {
  applyLanguage(currentLang === "zh" ? "en" : "zh");
});

themeButton?.addEventListener("click", () => {
  applyTheme(currentTheme === "dark" ? "light" : "dark");
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const value = button.getAttribute("data-copy") || "";
    const dictionary = translations[currentLang] || translations.en;
    try {
      await navigator.clipboard.writeText(value);
      button.textContent = dictionary.copied;
      window.setTimeout(() => {
        button.textContent = dictionary.copy;
      }, 1400);
    } catch {
      button.textContent = dictionary.select;
    }
  });
});

const revealTargets = document.querySelectorAll(
  ".feature-card, .desktop-device, .workspace-board, .doc-grid a",
);

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18 },
  );

  revealTargets.forEach((target) => observer.observe(target));
} else {
  revealTargets.forEach((target) => target.classList.add("is-visible"));
}

applyTheme(currentTheme);
applyLanguage(currentLang);
