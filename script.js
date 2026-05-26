const translations = {
  en: {
    pageTitle: "CC Branch - Multi-agent workspace control",
    description:
      "CC Branch turns a project workspace into committed config, reusable tmux sessions, desktop control, local Web UI diagnostics, and AI agent launch plans.",
    ogDescription:
      "A CLI-first workspace orchestrator with Web UI and desktop shell for developers running multiple AI agents, terminals, editors, and project commands.",
    skip: "Skip to content",
    navWhy: "Why",
    navDesktop: "Desktop",
    navWorkflow: "Workflow",
    navInstall: "Install",
    navDocs: "Docs",
    heroEyebrow: "CLI-first control for AI development workspaces",
    heroCopy:
      "Keep tabs, panes, agents, local apps, and remote work in one config. Reopen the same layout without rebuilding it by hand.",
    heroPrimary: "Install from GitHub",
    heroSecondary: "View source",
    heroPanelLabel: "workspace orbit",
    heroPanelState: "local-first",
    heroSummaryTabs: "Tabs",
    heroSummarySurfaces: "Surfaces",
    heroSummaryState: "State",
    heroSummaryLocal: "local",
    heroPoint1: "CLI, Web UI, and desktop app share one workspace model",
    heroPoint2: "Chinese and English content switch from the top bar",
    heroPoint3: "Light and dark themes stay in sync with the page",
    capability1Kicker: "Source install",
    capability1Title: "Build from the repo today.",
    capability1Body:
      "The Python package bundles the Web UI, so one install covers the CLI and the browser view.",
    capability2Kicker: "Desktop app",
    capability2Title: "Use the native shell when you want it.",
    capability2Body:
      "Desktop wraps the same workspace model without turning the project into a cloud dashboard.",
    capability3Kicker: "Language switch",
    capability3Title: "Chinese and English stay aligned.",
    capability3Body:
      "The page title, descriptions, buttons, and visible content all change with the selected language.",
    capability4Kicker: "Theme switch",
    capability4Title: "Light and dark mode use the same layout.",
    capability4Body:
      "The palette updates without changing the structure, so the page stays readable in both modes.",
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
    pageTitle: "CC Branch - 多代理工作空间控制",
    description:
      "CC Branch 把项目工作空间变成可提交的配置、可复用的 tmux 会话、桌面端控制、本地 Web UI 诊断和 AI Agent 启动方案。",
    ogDescription:
      "一个 CLI-first 的工作空间编排器，带 Web UI 和桌面壳，适合同时运行多个 AI Agent、终端、编辑器和项目命令。",
    skip: "跳到正文",
    navWhy: "为什么",
    navDesktop: "桌面端",
    navWorkflow: "工作流",
    navInstall: "安装",
    navDocs: "文档",
    heroEyebrow: "面向 AI 开发工作空间的 CLI-first 控制层",
    heroCopy:
      "把 tabs、panes、Agent、本地应用和远程工作放进同一份配置。下次打开时恢复同一套布局，不用手动重搭现场。",
    heroPrimary: "从 GitHub 安装",
    heroSecondary: "查看源码",
    heroPanelLabel: "工作空间 orbit",
    heroPanelState: "本地优先",
    heroSummaryTabs: "标签页",
    heroSummarySurfaces: "表面",
    heroSummaryState: "状态",
    heroSummaryLocal: "本地",
    heroPoint1: "CLI、Web UI 和桌面端共用同一套工作空间模型",
    heroPoint2: "中英文内容可从顶部直接切换",
    heroPoint3: "亮暗色模式和页面结构保持一致",
    capability1Kicker: "源码安装",
    capability1Title: "今天就能从仓库构建。",
    capability1Body:
      "Python 包会内置 Web UI，一次安装同时覆盖 CLI 和浏览器界面。",
    capability2Kicker: "桌面端",
    capability2Title: "需要原生壳时再用它。",
    capability2Body:
      "桌面端共享同一套工作空间模型，但不会把项目变成云端 dashboard。",
    capability3Kicker: "语言切换",
    capability3Title: "中英文始终保持一致。",
    capability3Body:
      "页面标题、描述、按钮和可见内容都会随着语言同步切换。",
    capability4Kicker: "主题切换",
    capability4Title: "亮色和暗色共用同一版布局。",
    capability4Body:
      "配色会变化，但结构不变，所以两种模式都保持可读。",
    whyKicker: "本地控制问题",
    whyTitle: "你的项目已经不再只是一个终端。",
    whyBody1:
      "现代 AI 工作会在终端、编辑器、浏览器和桌面应用之间移动。CC Branch 把这些表面收进一份文件和一个运行时。",
    whyBody2:
      "提交的配置描述应该存在什么，本地状态记录已经运行什么，界面负责把结果展示出来，而不是藏起来。",
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
      "CC Branch Desktop 把 Web UI 包进原生桌面壳，并在本地运行后端 sidecar。它适合想要可视化控制室、但不想把工作空间搬进云产品的人。",
    desktopPoint1: "内置后端 sidecar",
    desktopPoint2: "项目切换与诊断",
    desktopPoint3: "工作空间数据保留在本地",
    workflowKicker: "工作空间结构",
    workflowTitle: "一份配置，多种运行表面。",
    workflowBody:
      "长期会话用 tmux，本地应用用 direct mode，需要跑在远程机器上的窗格再加 SSH。",
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
