const translations = {
  en: {
    pageTitle: "CC Branch - Restore multi-agent CLI environments",
    description:
      "CC Branch restores your multi-agent CLI environment: Agent CLIs, terminal tasks, editors, and SSH machines.",
    ogDescription:
      "Restore Agent CLIs, terminal tasks, editors, and SSH machines from CLI, Web UI, or Desktop.",
    skip: "Skip to content",
    navValues: "Value",
    navRemote: "Remote",
    navDesktop: "Desktop",
    navInstall: "Install",
    navCta: "Get started",
    heroEyebrow: "Multi-agent CLI workspace",
    heroTitle: "Restore your multi-agent CLI environment.",
    heroLede:
      "Bring back your Agent CLIs, terminal tasks, editors, and SSH machines as one project workspace.",
    heroPrimary: "Install CC Branch",
    heroSecondary: "See the value",
    commandPrompt: "Restore workspace",
    orbitMeta: "5 panes · Codex · Claude · localhost:3000",
    labMeta: "remote repo · tmux · gpu-dev",
    desktopMeta: "web ui · sidecar · doctor clean",
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
    workflowKicker: "Daily flow",
    workflowTitle: "Start, resume, connect, inspect.",
    workflowBody:
      "Use the CLI, Web UI, or Desktop to restore the environment, attach to existing sessions, open tools, and check what is broken.",
    flowDefine: "Save the agents, commands, tools, folders, and SSH targets a project needs.",
    flowPreview: "See which agents, commands, tools, and machines will be used before launch.",
    flowRestore: "Bring back the project environment with cc-branch start.",
    flowInspect: "Catch missing Agent CLIs, bad paths, failed SSH links, and stale state.",
    remoteKicker: "Remote workspaces",
    remoteTitle: "Local project. Remote machine. Same workspace.",
    remoteBody:
      "Add projects and panes that live on SSH hosts, then launch them beside local agents and servers. The directory can be local or remote; the workspace still opens as one unit.",
    desktopProjects: "Projects",
    desktopReady: "Workspace ready",
    desktopKicker: "Desktop shell",
    desktopTitle: "A quiet desktop shell for local work.",
    desktopBody:
      "The desktop app wraps the Web UI with a local sidecar, so switching projects, checking status, and restoring sessions feels like a native utility.",
    installKicker: "Install",
    installTitle: "Start from the terminal.",
    installBody:
      "Install from source while public registries and signed desktop releases are finalized.",
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
    navRemote: "远程",
    navDesktop: "桌面端",
    navInstall: "安装",
    navCta: "开始使用",
    heroEyebrow: "多 Agent CLI 工作空间",
    heroTitle: "一键恢复多 Agent CLI 工作环境。",
    heroLede:
      "把 Agent CLI、终端任务、编辑器和 SSH 机器作为一个项目工作空间一起恢复。",
    heroPrimary: "安装 CC Branch",
    heroSecondary: "查看价值",
    commandPrompt: "恢复工作空间",
    orbitMeta: "5 个窗格 · Codex · Claude · localhost:3000",
    labMeta: "远程仓库 · tmux · gpu-dev",
    desktopMeta: "Web UI · sidecar · doctor 正常",
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
    workflowKicker: "日常流程",
    workflowTitle: "启动、恢复、连接、检查。",
    workflowBody:
      "从 CLI、Web UI 或桌面端恢复环境、接回会话、打开工具，并检查哪里出了问题。",
    flowDefine: "保存项目需要的 Agent、命令、工具、目录和 SSH 目标。",
    flowPreview: "启动前先看清会用到哪些 Agent、命令、工具和机器。",
    flowRestore: "用 cc-branch start 恢复项目工作环境。",
    flowInspect: "发现缺失 Agent CLI、错误路径、SSH 连接失败和旧状态问题。",
    remoteKicker: "远程工作空间",
    remoteTitle: "本地项目。远程机器。同一个工作空间。",
    remoteBody:
      "添加位于 SSH 主机上的项目和窗格，然后和本地 Agent、服务一起启动。目录可以在本机，也可以在远程；工作空间仍然作为一个整体打开。",
    desktopProjects: "项目",
    desktopReady: "工作空间就绪",
    desktopKicker: "桌面端",
    desktopTitle: "一个安静的本地桌面壳。",
    desktopBody:
      "桌面端把 Web UI 和本地 sidecar 包在一起，让项目切换、状态检查和会话恢复更像一个原生效率工具。",
    installKicker: "安装",
    installTitle: "从终端开始。",
    installBody:
      "公开注册表和签名桌面安装包最终确定前，可以先从源码安装。",
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

  document.querySelectorAll("[data-copy-label]").forEach((button) => {
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
    const label = button.dataset.copyLabel || translations[activeLanguage].copy;
    try {
      await navigator.clipboard.writeText(button.dataset.copy || "");
      button.textContent = translations[activeLanguage].copied;
      window.setTimeout(() => {
        button.textContent = label;
      }, 1400);
    } catch {
      button.textContent = label;
    }
  });
});

translate(activeLanguage);
