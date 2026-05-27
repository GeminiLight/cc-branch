const translations = {
  en: {
    pageTitle: "CC Branch - Restore CLI workbenches",
    description:
      "CC Branch restores a CLI workbench in one command: agents, tmux sessions, dev servers, editors, SSH panes, Web UI, and desktop control.",
    ogDescription:
      "A CLI-first workspace orchestrator for restoring the full CLI workbench whenever you return to a repo.",
    skip: "Skip to content",
    navWhy: "Why",
    navDesktop: "Desktop",
    navWorkflow: "Workflow",
    navInstall: "Install",
    navDocs: "Docs",
    heroEyebrow: "Multi-agent CLI workbench",
    heroTitle: "Restore the whole workbench.",
    heroCopy:
      "Agents, tmux panes, dev servers, editors, and SSH targets come back from one project config.",
    heroPrimary: "Install",
    heroSecondary: "View workflow",
    heroPanelLabel: "restore preview",
    heroPanelState: "ready in 1 command",
    restoreStep1: "Committed config",
    restoreStep2: "Run once",
    restoreStep3: "Workspace restored",
    restoreStep3Value: "4 panes attached",
    panePlanner: "planner",
    paneServer: "server",
    paneReview: "review",
    paneRemote: "remote qa",
    paneAttached: "attached",
    paneRunning: "running",
    paneReady: "ready",
    heroSummaryTabs: "Reusable tabs",
    heroSummarySurfaces: "Launch surfaces",
    heroSummaryState: "State file",
    heroSummaryLocal: "local only",
    heroPoint1: "Config in repo",
    heroPoint2: "Sessions resume",
    heroPoint3: "CLI · Web · Desktop",
    capability1Kicker: "Define",
    capability1Title: "One YAML file.",
    capability1Body:
      "Tabs, panes, agents, commands, env, openers, and SSH targets.",
    capability2Kicker: "Preview",
    capability2Title: "Plan before launch.",
    capability2Body:
      "See tmux sessions, commands, remotes, and resume actions first.",
    capability3Kicker: "Restore",
    capability3Title: "Resume the room.",
    capability3Body:
      "Start missing sessions or attach to running ones.",
    capability4Kicker: "Inspect",
    capability4Title: "Fix drift early.",
    capability4Body:
      "Doctor checks tools, paths, agents, state, and safe fixes.",
    whyKicker: "The local control problem",
    whyTitle: "Your project is no longer one terminal.",
    whyBody1:
      "Modern AI work spreads across agent CLIs, dev servers, editors, terminals, browser diagnostics, desktop controls, and remote machines.",
    whyBody2:
      "CC Branch gives that workspace a contract: committed config defines what should exist; local state remembers what is already running.",
    feature1Title: "Config becomes the source of truth",
    feature1Body:
      "Commit the workspace structure so teammates and future you know what should open.",
    feature2Title: "Sessions resume instead of restarting blind",
    feature2Body:
      "Agent panes keep IDs and labels, so attach and resume commands stay predictable.",
    feature3Title: "Open the same workspace from multiple surfaces",
    feature3Body:
      "Use the CLI, Web UI, or desktop shell without changing the underlying model.",
    feature4Title: "Doctor catches broken workspaces early",
    feature4Body:
      "Check tmux, paths, commands, agent references, and state drift before launch.",
    desktopKicker: "Desktop shell",
    desktopTitle: "A local control room, not another cloud dashboard.",
    desktopBody:
      "CC Branch Desktop wraps the Web UI in a native shell and runs the backend sidecar locally. It is for people who want a visual control room without moving their workspace into a cloud product.",
    desktopPoint1: "Bundled backend sidecar",
    desktopPoint2: "Project switcher and diagnostics",
    desktopPoint3: "Local-only workspace data",
    workflowKicker: "Workspace anatomy",
    workflowTitle: "One config. Multiple execution surfaces.",
    workflowBody:
      "Use tmux for long-lived sessions, direct mode for local apps, and SSH when a pane belongs on a remote machine.",
    stepsKicker: "How it works",
    stepsTitle: "From empty terminal to restored workspace.",
    stepInit: "Create the project config and local state files.",
    stepPlan: "Preview tabs, panes, agents, commands, and remote targets before launch.",
    stepStart: "Start missing sessions or attach to the ones already running.",
    stepDoctor: "Catch missing tools, broken paths, and state drift early.",
    installKicker: "Install today",
    installTitle: "Install from source while registries are prepared.",
    installBody:
      "PyPI, npm, Homebrew, and signed desktop releases are wired in the repo, but public registry publishing is intentionally gated. The source install works now and builds the bundled Web UI.",
    installNote1: "Requires Python 3.10+",
    installNote2: "Node/npm builds the Web UI from source",
    installNote3: "tmux is needed only for tmux-backed tabs",
    installNote4: "Desktop installers are prepared through GitHub Releases",
    docsKicker: "Read next",
    docsTitle: "Start with the files you will actually use.",
    deviceProjects: "Projects",
    deviceReady: "Workspace ready",
    boardProject: "project: orbit",
    boardLayout: "layoutBackend: tmux",
    boardPlanner: "planner",
    boardServer: "server",
    boardReview: "review",
    boardRemote: "remote qa",
    boardEditor: "editor",
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
    pageTitle: "CC Branch - 一键恢复 CLI 工作台",
    description:
      "CC Branch 一键恢复 CLI 工作台：Agent、tmux 会话、开发服务、编辑器、SSH 窗格、Web UI 和桌面端控制。",
    ogDescription:
      "一个 CLI-first 工作空间编排器，让开发者每次回到项目都能恢复整套 CLI 工作台。",
    skip: "跳到正文",
    navWhy: "为什么",
    navDesktop: "桌面端",
    navWorkflow: "工作流",
    navInstall: "安装",
    navDocs: "文档",
    heroEyebrow: "多 Agent CLI 工作台",
    heroTitle: "一键恢复整个工作台。",
    heroCopy:
      "Agent、tmux 窗格、开发服务、编辑器和 SSH 目标，都从一份项目配置恢复。",
    heroPrimary: "安装",
    heroSecondary: "看工作流",
    heroPanelLabel: "恢复预览",
    heroPanelState: "一条命令就绪",
    restoreStep1: "提交的配置",
    restoreStep2: "运行一次",
    restoreStep3: "工作空间已恢复",
    restoreStep3Value: "4 个窗格已接回",
    panePlanner: "规划",
    paneServer: "服务",
    paneReview: "评审",
    paneRemote: "远程 QA",
    paneAttached: "已接回",
    paneRunning: "运行中",
    paneReady: "就绪",
    heroSummaryTabs: "可复用标签页",
    heroSummarySurfaces: "启动入口",
    heroSummaryState: "状态文件",
    heroSummaryLocal: "仅本地",
    heroPoint1: "配置随项目提交",
    heroPoint2: "会话可恢复",
    heroPoint3: "CLI · Web · 桌面端",
    capability1Kicker: "定义",
    capability1Title: "一份 YAML。",
    capability1Body:
      "tabs、panes、Agent、命令、环境、打开方式和 SSH 目标。",
    capability2Kicker: "预览",
    capability2Title: "先 plan，再启动。",
    capability2Body:
      "先看 tmux 会话、命令、远程目标和恢复动作。",
    capability3Kicker: "恢复",
    capability3Title: "接回现场。",
    capability3Body:
      "启动缺失会话，或接回正在运行的会话。",
    capability4Kicker: "检查",
    capability4Title: "提前修漂移。",
    capability4Body:
      "Doctor 检查工具、路径、Agent、状态和安全修复。",
    whyKicker: "本地控制问题",
    whyTitle: "你的项目已经不再只是一个终端。",
    whyBody1:
      "现代 AI 工作会分散在 Agent CLI、开发服务、编辑器、终端、浏览器诊断、桌面控制和远程机器里。",
    whyBody2:
      "CC Branch 给这套现场一个契约：提交的配置定义应该存在什么，本地状态记住已经运行什么。",
    feature1Title: "配置成为事实来源",
    feature1Body:
      "把工作空间结构提交进项目，让团队和未来的你知道应该打开什么。",
    feature2Title: "会话可恢复，不是盲目重启",
    feature2Body:
      "Agent 窗格保留 ID 和标签，attach 与 resume 命令保持可预测。",
    feature3Title: "多个入口打开同一个工作空间",
    feature3Body:
      "CLI、Web UI 和桌面壳都使用同一套底层工作空间模型。",
    feature4Title: "Doctor 提前发现坏掉的工作空间",
    feature4Body:
      "启动前检查 tmux、路径、命令、Agent 引用和状态漂移。",
    desktopKicker: "桌面端",
    desktopTitle: "这是本地控制室，不是又一个云端 dashboard。",
    desktopBody:
      "CC Branch Desktop 把 Web UI 包进原生桌面壳，并在本地运行后端 sidecar。它适合想要可视化控制室、但不想把工作空间搬进云产品的人。",
    desktopPoint1: "内置后端 sidecar",
    desktopPoint2: "项目切换与诊断",
    desktopPoint3: "工作空间数据保留在本地",
    workflowKicker: "工作空间结构",
    workflowTitle: "一份配置，多种运行表面。",
    workflowBody:
      "长期会话用 tmux，本地应用用 direct mode，需要跑在远程机器上的窗格再加 SSH。",
    stepsKicker: "工作方式",
    stepsTitle: "从空终端到恢复完整工作空间。",
    stepInit: "创建项目配置和本地状态文件。",
    stepPlan: "启动前预览 tabs、panes、Agent、命令和远程目标。",
    stepStart: "启动缺失会话，或接回已经运行的会话。",
    stepDoctor: "提前发现缺失工具、坏路径和状态漂移。",
    installKicker: "现在可用",
    installTitle: "注册表准备好之前，先从源码安装。",
    installBody:
      "PyPI、npm、Homebrew 和签名桌面安装包的发布链路已经在仓库里，但公开注册表发布仍受控。源码安装现在可用，并会构建内置 Web UI。",
    installNote1: "需要 Python 3.10+",
    installNote2: "从源码构建 Web UI 需要 Node/npm",
    installNote3: "只有 tmux 布局需要 tmux",
    installNote4: "桌面安装包通过 GitHub Releases 准备",
    docsKicker: "继续阅读",
    docsTitle: "从真正会用到的文件开始。",
    deviceProjects: "项目",
    deviceReady: "工作空间已就绪",
    boardProject: "项目：orbit",
    boardLayout: "layoutBackend：tmux",
    boardPlanner: "规划",
    boardServer: "服务",
    boardReview: "评审",
    boardRemote: "远程 QA",
    boardEditor: "编辑器",
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
  document.title = dictionary.pageTitle;
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
  document.querySelectorAll("[data-i18n-meta]").forEach((node) => {
    const key = node.getAttribute("data-i18n-meta");
    if (key && dictionary[key]) {
      node.setAttribute("content", dictionary[key]);
    }
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
