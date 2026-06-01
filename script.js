const translations = {
  en: {
    pageTitle: "CC Branch - Restore multi-agent CLI environments",
    description:
      "CC Branch restores your multi-agent CLI environment: Agent CLIs, terminal tasks, editors, and SSH machines.",
    ogDescription:
      "Restore Agent CLIs, terminal tasks, editors, and SSH machines from CLI, Web UI, or Desktop.",
    skip: "Skip to content",
    navValues: "Value",
    navWorkflow: "Workflow",
    navFeatures: "Features",
    navInstall: "Download",
    navCta: "Get started",
    heroEyebrow: "Multi-agent CLI workspace",
    heroTitle: "Restore your multi-agent CLI environment.",
    heroLede:
      "Bring back your Agent CLIs, terminal tasks, editors, and SSH machines as one project workspace.",
    heroPrimary: "Download desktop app",
    heroSecondary: "CLI install",
    heroRelease: "Desktop installers live on GitHub Releases",
    heroReleaseCta: "Open release",
    commandPrompt: "Restore workspace",
    orbitMeta: "5 panes · Codex · Claude · localhost:3000",
    labMeta: "remote repo · tmux · gpu-dev",
    desktopMeta: "desktop app · doctor clean",
    current: "current",
    copy: "Copy",
    copied: "Copied",
    stripCli: "Multi-agent CLI",
    stripSsh: "SSH projects",
    stripResume: "Session resume",
    stripPreview: "Plan before run",
    stripDesktop: "Web + Desktop",
    problemKicker: "User value",
    problemTitle: "Stop rebuilding the same agent environment.",
    value1Tag: "Restore",
    value2Tag: "Agents",
    value3Tag: "Remote",
    problem1Title: "Come back to the same setup",
    problem1Body:
      "No more reopening agents, terminals, editors, and SSH links by hand. Restore the project environment together.",
    problem2Title: "Keep Agent CLIs organized",
    problem2Body:
      "Codex, Claude Code, Gemini CLI, Cursor CLI, Kimi, and custom agents stay in one project workspace.",
    problem3Title: "Use local and SSH as one environment",
    problem3Body:
      "Local folders, SSH projects, GPU boxes, test machines, and tmux sessions can belong to the same workflow.",
    workflowKicker: "Work scenario",
    workflowTitle: "From project to workbench, one line.",
    workflowBody:
      "Choose a project; CC Branch brings back its local folder, SSH machines, Agent CLIs, terminal commands, editor, and sessions together.",
    workflowSource: "Project recipe",
    flowSelectTitle: "Choose the project",
    flowSelectBody:
      "Pick a saved workspace from the desktop app or CLI. It can point to a local folder, an SSH directory, or both.",
    flowSelectOut: "Project context is in one place",
    flowPlanTitle: "See what will open",
    flowPlanBody:
      "Before launching, check the agents, commands, editor, tmux panes, and remote machines that belong to this workspace.",
    flowPlanOut: "No blind startup",
    flowStartTitle: "Restore the workbench",
    flowStartBody:
      "Start the workspace once: Agent CLIs resume, local services run, editors open, and SSH/tmux sessions attach.",
    flowStartOut: "Ready to work, not ready to set up",
    flowReturnTitle: "Come back later",
    flowReturnBody:
      "When you return, reattach to existing sessions and fix missing tools, bad paths, or failed SSH links from the same entry point.",
    flowReturnOut: "The environment keeps continuity",
    featuresKicker: "Features",
    featuresTitle: "Everything an agent workspace needs to reopen cleanly.",
    featuresBody:
      "CC Branch is built around the things developers actually reopen every day: agent CLIs, terminals, editors, openers, local folders, and SSH machines.",
    featureAgentsLabel: "Multi-agent",
    featureAgentsTitle: "Run many Agent CLIs in one project",
    featureAgentsBody:
      "Codex, Claude Code, Gemini CLI, Cursor CLI, Kimi, custom commands, and reusable resume labels can live together.",
    featureTerminalLabel: "Terminals and openers",
    featureTerminalTitle: "Restore terminals, panes, and tools",
    featureTerminalBody:
      "Use tmux for long-running panes, direct commands for local tools, and openers for Cursor, VS Code, Warp, terminal, Web UI, or Desktop.",
    featureRemoteLabel: "Local and remote",
    featureRemoteTitle: "Treat local and SSH machines as one workspace",
    featureRemoteBody:
      "A workspace can include a local repo, remote project directory, GPU box, remote tmux session, and local editor without splitting the workflow.",
    installKicker: "Download",
    installTitle: "Install the desktop app or copy the pip command.",
    installBody:
      "Download the native desktop app from GitHub Releases, or install the CLI/backend and browser Web UI directly from PyPI.",
    downloadDesktopLabel: "Desktop app",
    downloadDesktopTitle: "Latest GitHub Release",
    downloadDesktopBody:
      "Get the newest desktop installer and release notes from the official release page.",
    downloadDesktopCta: "Download latest release",
    downloadCliLabel: "CLI install",
    installNote1: "Python 3.11+ recommended",
    installNote2: "tmux only required for tmux-backed tabs",
    installNote3: "SSH targets use your existing SSH config",
    docStartLabel: "Start",
    docStart: "Getting Started",
    docFeatureLabel: "Map",
    docFeature: "Feature Reference",
    docGuideLabel: "Use",
    docGuide: "User Guide",
    footer: "MIT licensed. Built for multi-agent CLI workspaces.",
  },
  zh: {
    pageTitle: "CC Branch - 恢复多 Agent CLI 工作环境",
    description:
      "CC Branch 一键恢复多 Agent CLI 工作环境：Agent、终端任务、编辑器和 SSH 机器。",
    ogDescription:
      "从 CLI、Web UI 或桌面端恢复 Agent CLI、终端任务、编辑器和 SSH 机器。",
    skip: "跳到正文",
    navValues: "价值",
    navWorkflow: "工作流",
    navFeatures: "功能",
    navInstall: "下载",
    navCta: "开始使用",
    heroEyebrow: "多 Agent CLI 工作空间",
    heroTitle: "一键恢复多 Agent CLI 工作环境。",
    heroLede:
      "把 Agent CLI、终端任务、编辑器和 SSH 机器作为一个项目工作空间一起恢复。",
    heroPrimary: "下载桌面端",
    heroSecondary: "CLI 安装",
    heroRelease: "桌面端安装包在 GitHub Releases",
    heroReleaseCta: "打开最新版本",
    commandPrompt: "恢复工作空间",
    orbitMeta: "5 个窗格 · Codex · Claude · localhost:3000",
    labMeta: "远程仓库 · tmux · gpu-dev",
    desktopMeta: "桌面端 · doctor 正常",
    current: "当前",
    copy: "复制",
    copied: "已复制",
    stripCli: "多 Agent CLI",
    stripSsh: "SSH 项目",
    stripResume: "会话恢复",
    stripPreview: "启动前预览",
    stripDesktop: "Web + 桌面端",
    problemKicker: "用户价值",
    problemTitle: "不用再反复重搭同一套 Agent 环境。",
    value1Tag: "恢复",
    value2Tag: "Agent",
    value3Tag: "远程",
    problem1Title: "回到项目就是同一套环境",
    problem1Body:
      "不用手动重新打开 Agent、终端、编辑器和 SSH 连接。项目环境可以一起恢复。",
    problem2Title: "管住多个 Agent CLI",
    problem2Body:
      "Codex、Claude Code、Gemini CLI、Cursor CLI、Kimi 和自定义 Agent 都放进同一个项目工作空间。",
    problem3Title: "把本机和 SSH 当成一个环境",
    problem3Body:
      "本机目录、SSH 项目、GPU 机器、测试机和 tmux 会话可以进入同一套工作流。",
    workflowKicker: "使用场景",
    workflowTitle: "从项目到工作台，一条线走完。",
    workflowBody:
      "选择一个项目，CC Branch 会把本机目录、SSH 机器、Agent CLI、终端命令、编辑器和已有会话一起带回来。",
    workflowSource: "项目配方",
    flowSelectTitle: "选择项目",
    flowSelectBody:
      "从桌面端或 CLI 选择一个保存好的工作空间。它可以指向本机目录、SSH 目录，或者两者同时存在。",
    flowSelectOut: "项目上下文集中在一处",
    flowPlanTitle: "先看会打开什么",
    flowPlanBody:
      "启动前看清这个工作空间会用到哪些 Agent、命令、编辑器、tmux 窗格和远程机器。",
    flowPlanOut: "不是盲目启动",
    flowStartTitle: "恢复工作台",
    flowStartBody:
      "启动一次即可：Agent CLI 接回会话，本地服务跑起来，编辑器打开，SSH/tmux 会话自动连接。",
    flowStartOut: "进入工作，而不是重新搭环境",
    flowReturnTitle: "下次回来继续",
    flowReturnBody:
      "重新进入时接回已有会话，并在同一个入口发现缺工具、路径错误或 SSH 连接失败。",
    flowReturnOut: "工作环境保持连续",
    featuresKicker: "功能",
    featuresTitle: "Agent 工作空间需要的能力，都围绕恢复体验设计。",
    featuresBody:
      "CC Branch 聚焦开发者每天反复打开的东西：Agent CLI、终端、编辑器、打开方式、本机目录和 SSH 机器。",
    featureAgentsLabel: "多 Agent",
    featureAgentsTitle: "一个项目里管理多个 Agent CLI",
    featureAgentsBody:
      "Codex、Claude Code、Gemini CLI、Cursor CLI、Kimi、自定义命令和可复用 resume 标签可以放在一起。",
    featureTerminalLabel: "终端和打开方式",
    featureTerminalTitle: "恢复终端、窗格和工具",
    featureTerminalBody:
      "长期运行的窗格用 tmux，本地工具用 direct commands，编辑器和工具通过 openers 打开，比如 Cursor、VS Code、Warp、terminal、Web UI 或 Desktop。",
    featureRemoteLabel: "本机和远程",
    featureRemoteTitle: "把本机和 SSH 机器当成一个工作空间",
    featureRemoteBody:
      "一个 workspace 可以同时包含本机仓库、远程项目目录、GPU 机器、远程 tmux 会话和本机编辑器，不用拆成几套流程。",
    installKicker: "下载",
    installTitle: "下载桌面端，或复制 pip 安装命令。",
    installBody:
      "从 GitHub Releases 下载原生桌面端；如果更习惯终端，也可以直接从 PyPI 安装 CLI/backend 和浏览器 Web UI。",
    downloadDesktopLabel: "桌面端",
    downloadDesktopTitle: "最新 GitHub Release",
    downloadDesktopBody:
      "在官方 Release 页面获取最新桌面端安装包和版本说明。",
    downloadDesktopCta: "下载最新版本",
    downloadCliLabel: "CLI 安装",
    installNote1: "推荐 Python 3.11+",
    installNote2: "只有 tmux 布局需要 tmux",
    installNote3: "SSH 目标使用你现有的 SSH 配置",
    docStartLabel: "开始",
    docStart: "快速开始",
    docFeatureLabel: "地图",
    docFeature: "功能参考",
    docGuideLabel: "使用",
    docGuide: "用户指南",
    footer: "MIT 协议。为多 Agent CLI 工作空间而构建。",
  },
};

const prefersChinese = navigator.language.toLowerCase().startsWith("zh");
const storedLanguage = localStorage.getItem("cc-branch-lang");
let activeLanguage = storedLanguage || (prefersChinese ? "zh" : "en");

function translate(language) {
  const dictionary = translations[language] || translations.en;
  document.documentElement.lang = language;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (dictionary[key]) {
      element.textContent = dictionary[key];
    }
  });

  document.querySelectorAll("[data-i18n-meta]").forEach((element) => {
    const key = element.dataset.i18nMeta;
    if (dictionary[key]) {
      element.setAttribute("content", dictionary[key]);
    }
  });

  document.querySelectorAll("[data-copy-label][data-i18n='copy']").forEach((button) => {
    button.dataset.copyLabel = dictionary.copy;
    button.textContent = dictionary.copy;
  });

  const toggle = document.querySelector("[data-lang-toggle]");
  if (toggle) {
    toggle.textContent = language === "en" ? "中文" : "EN";
  }

  localStorage.setItem("cc-branch-lang", language);
}

document.querySelector("[data-lang-toggle]")?.addEventListener("click", () => {
  activeLanguage = activeLanguage === "en" ? "zh" : "en";
  translate(activeLanguage);
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const originalHtml = button.innerHTML;
    try {
      await navigator.clipboard.writeText(button.dataset.copy || "");
      button.textContent = translations[activeLanguage].copied;
      window.setTimeout(() => {
        button.innerHTML = originalHtml;
      }, 1400);
    } catch {
      button.innerHTML = originalHtml;
    }
  });
});

translate(activeLanguage);
