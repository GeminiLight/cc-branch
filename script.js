const translations = {
  en: {
    pageTitle: "CC Branch - Restore agent workspaces",
    description:
      "CC Branch restores every agent, terminal, dev server, editor, and SSH workspace from one local project config.",
    ogDescription:
      "A local control plane for agentic CLI work. Define the workspace once, then reopen it from CLI, Web, or Desktop.",
    skip: "Skip to content",
    navWorkflow: "Workflow",
    navRemote: "Remote",
    navDesktop: "Desktop",
    navInstall: "Install",
    navCta: "Get started",
    heroEyebrow: "Local workspace control for agentic CLI work",
    heroTitle: "Reopen every agent workspace.",
    heroLede:
      "Define the workspace once. CC Branch brings back the agents, terminals, dev servers, editors, and SSH machines behind a project.",
    heroPrimary: "Install CC Branch",
    heroSecondary: "See the workflow",
    commandPrompt: "Restore workspace",
    orbitMeta: "5 panes · Codex · Claude · localhost:3000",
    labMeta: "remote repo · tmux · gpu-dev",
    desktopMeta: "web ui · sidecar · doctor clean",
    current: "current",
    copy: "Copy",
    copied: "Copied",
    stripCli: "CLI-first",
    stripLocal: "Local state",
    stripTmux: "Tmux sessions",
    stripSsh: "SSH workspaces",
    stripDesktop: "Desktop shell",
    problemKicker: "Why it exists",
    problemTitle: "A project is no longer one terminal.",
    problem1Title: "Agent sessions scatter",
    problem1Body:
      "Codex, Claude, Gemini, review panes, and long-running terminals all need a stable place to return to.",
    problem2Title: "Context lives in terminals",
    problem2Body:
      "Dev servers, logs, shell state, and editor launch commands are part of the workspace, not afterthoughts.",
    problem3Title: "Remote machines matter",
    problem3Body:
      "Some panes belong on SSH hosts. CC Branch treats them as first-class workspace targets.",
    workflowKicker: "The model",
    workflowTitle: "One local contract for the whole workspace.",
    workflowBody:
      "Keep the workspace contract in .cc-branch/config.yaml. Runtime state stays local, so teams can share the shape without sharing machine-specific sessions.",
    flowDefine: "Describe tabs, panes, agents, commands, openers, and SSH targets.",
    flowPreview: "Run cc-branch plan to see what will start, attach, or open.",
    flowRestore: "Bring the whole workspace back with cc-branch start.",
    flowInspect: "Use doctor checks to catch missing tools, bad paths, and state drift.",
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
    footer: "MIT licensed. Built for local-first agent workspaces.",
  },
  zh: {
    pageTitle: "CC Branch - 恢复 Agent 工作空间",
    description:
      "CC Branch 从一份本地项目配置恢复 Agent、终端、开发服务、编辑器和 SSH 工作空间。",
    ogDescription:
      "面向 agentic CLI 工作流的本地控制层。定义一次工作空间，然后从 CLI、Web 或桌面端重新打开。",
    skip: "跳到正文",
    navWorkflow: "工作流",
    navRemote: "远程",
    navDesktop: "桌面端",
    navInstall: "安装",
    navCta: "开始使用",
    heroEyebrow: "面向 Agent CLI 工作流的本地工作空间控制",
    heroTitle: "重新打开完整的 Agent 工作空间。",
    heroLede:
      "先定义一次工作空间。CC Branch 会把项目背后的 Agent、终端、开发服务、编辑器和 SSH 机器恢复回来。",
    heroPrimary: "安装 CC Branch",
    heroSecondary: "查看工作流",
    commandPrompt: "恢复工作空间",
    orbitMeta: "5 个窗格 · Codex · Claude · localhost:3000",
    labMeta: "远程仓库 · tmux · gpu-dev",
    desktopMeta: "Web UI · sidecar · doctor 正常",
    current: "当前",
    copy: "复制",
    copied: "已复制",
    stripCli: "CLI 优先",
    stripLocal: "本地状态",
    stripTmux: "tmux 会话",
    stripSsh: "SSH 工作空间",
    stripDesktop: "桌面端壳",
    problemKicker: "为什么需要它",
    problemTitle: "一个项目已经不再只是一个终端。",
    problem1Title: "Agent 会话分散",
    problem1Body:
      "Codex、Claude、Gemini、评审窗格和长期运行的终端，都需要一个稳定的返回位置。",
    problem2Title: "上下文就在终端里",
    problem2Body:
      "开发服务、日志、shell 状态和编辑器启动命令，都是工作空间的一部分，不是附属物。",
    problem3Title: "远程机器也在现场里",
    problem3Body:
      "有些窗格应该跑在 SSH 主机上。CC Branch 把它们当作一等工作空间目标。",
    workflowKicker: "模型",
    workflowTitle: "用一份本地契约定义整个工作空间。",
    workflowBody:
      "把工作空间契约放在 .cc-branch/config.yaml。运行状态保留在本地，所以团队能共享结构，不会共享机器私有会话。",
    flowDefine: "描述 tabs、panes、Agent、命令、打开方式和 SSH 目标。",
    flowPreview: "运行 cc-branch plan，先看会启动、接回或打开什么。",
    flowRestore: "用 cc-branch start 把整个工作空间恢复回来。",
    flowInspect: "用 doctor 检查缺失工具、错误路径和状态漂移。",
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
    footer: "MIT 协议。为 local-first Agent 工作空间而构建。",
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
