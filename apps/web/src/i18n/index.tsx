/**
 * Lightweight i18n system.
 *
 * No external dependencies — just a typed dictionary + React context.
 * Desktop (Tauri) can extend this with OS locale detection.
 */

import { createContext, useContext, useState, useCallback, useEffect } from "react";

export type Lang = "en" | "zh";

const STORAGE_KEY = "cc-branch-lang";

function interpolate(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`));
}

const dict: Record<Lang, Record<string, string>> = {
  en: {
    appTitle: "CC Branch",
    workspaceControl: "Workspace control",
    dashboard: "Dashboard",
    config: "Config",
    doctor: "Doctor",
    project: "Project",
    status: "Status",
    configPath: "Config",
    running: "running",
    stopped: "stopped",
    stop: "Stop",
    open: "Open",
    launch: "Launch",
    openTerminal: "Open terminal",
    openWith: "Open with {app}",
    openProjectIn: "Open project in {app}",
    startOnly: "Start in background",
    restart: "Restart",
    launchWorkspace: "Open workspace in terminal",
    openWorkspace: "Open workspace in terminal",
    stopWorkspace: "Stop workspace",
    cancel: "Cancel",
    copy: "Copy",
    copied: "Copied!",
    refresh: "Refresh",
    connected: "Connected",
    disconnected: "Disconnected",
    refreshing: "Refreshing",
    lastUpdated: "Last updated",
    noSlots: "No slots configured",
    loading: "Loading...",
    errorLoading: "Error loading workspace",
    healthCheck: "Health Check",
    configuration: "Configuration",
    webUiFooter: "cc-branch Web UI",
    noConfigTitle: "No workspace config found",
    noConfigDesc: "Create one from a starter profile or open the YAML editor.",
    step1Title: "Create From Profile",
    step1Desc: "Choose a starter profile. We'll detect available agents and generate the config from the browser.",
    step1Code: "Web UI → Create from a starter profile",
    step1Tip: "Creates .cc-branch.yaml, .cc-branch.state.toml, and .gitignore entries",
    step2Title: "Customize Config",
    step2Desc: "Edit .cc-branch.yaml to adjust slots, agents, and windows.",
    step2Slots: "Top-level workspace containers",
    step2Agents: "Reusable AI tool definitions",
    step2Windows: "Execution units within slots",
    step3Title: "Launch Workspace",
    step3Desc: "Run cc-branch start to create tmux sessions and enter the workspace.",
    step3Tip: "Run cc-branch doctor first to validate your setup",
    langSwitch: "Language",
    themeSwitch: "Theme",
    light: "Light",
    dark: "Dark",
    agent: "Agent",
    id: "ID",
    slots: "slots",
    selectProject: "Select a project from the sidebar",
    openSidebar: "Open sidebar",
    edit: "Edit",
    save: "Save",
    configSaved: "Config saved",
    checksPassed: "All checks passed",
    checksWarnings: "Warnings found",
    checksIssues: "Issues found",
    addProject: "Add Project",
    scan: "Scan",
    createConfig: "Create Config",
    review: "Review",
    done: "Done",
    chooseTemplate: "Choose a template. We'll detect available agents and generate a config.",
    projectDirectory: "Project Directory",
    noConfigFound: "No config found — initialize after adding",
    step: "Step",
    createConfigInteractively: "Create from a starter profile",
    confirm: "Confirm",
    preview: "Preview",
    projectAdded: "Project added",
    remove: "Remove",
    offline: "You are offline",
    unknownError: "An unexpected error occurred",
    confirmStop: "Stop \"{name}\"?",
    confirmAction: "{action} \"{name}\"?",
    dismissNotification: "Dismiss notification",
    skipToContent: "Skip to main content",
    noProjects: "No projects yet",
    addProjectHint: "Click + below to add one",
    current: "current",
    pathNotFound: "Path does not exist",
    canInitializeAfterAdd: "No config yet — add it, then initialize from Overview",
    backendUnreachable: "Backend unreachable — check if cc-branch server is running",
    manualClose: "Close",
    pathExample: "~/projects/my-project",
    useCurrentDir: "Use current directory",
    fromRecent: "From recent",
    formMode: "Form",
    yamlMode: "YAML",
    generatedYaml: "Generated YAML",
    unsaved: "unsaved",
    add: "Add",
    moveUp: "Move up",
    moveDown: "Move down",
    advanced: "Advanced",
    name: "Name",
    backend: "Backend",
    workingDirectory: "Working directory",
    environmentVariables: "Environment variables",
    noSlotsYet: "No slots yet",
    addSlotHint: "Add a slot to define workspace containers",
    noAgentsYet: "No agents yet",
    addAgentHint: "Add an agent to bind to windows",
    duplicateName: "Duplicate name",
    required: "Required",
    commentsWillBeLost: "Switching to Form mode rewrites YAML and removes comments. Continue?",
  },
  zh: {
    appTitle: "CC Branch",
    workspaceControl: "工作空间控制台",
    dashboard: "仪表板",
    config: "配置",
    doctor: "诊断",
    project: "项目",
    status: "状态",
    configPath: "配置路径",
    running: "运行中",
    stopped: "已停止",
    stop: "停止",
    open: "打开",
    launch: "启动",
    openTerminal: "打开终端",
    openWith: "使用 {app} 打开",
    openProjectIn: "在 {app} 打开项目",
    startOnly: "后台启动",
    restart: "重启",
    launchWorkspace: "在终端打开工作空间",
    openWorkspace: "在终端打开工作空间",
    stopWorkspace: "停止工作空间",
    cancel: "取消",
    copy: "复制",
    copied: "已复制!",
    refresh: "刷新",
    connected: "已连接",
    disconnected: "已断开",
    refreshing: "刷新中",
    lastUpdated: "最后更新",
    noSlots: "未配置任何 slot",
    loading: "加载中...",
    errorLoading: "加载工作空间失败",
    healthCheck: "健康检查",
    configuration: "配置",
    webUiFooter: "cc-branch Web UI",
    noConfigTitle: "未找到工作空间配置",
    noConfigDesc: "可以从 starter profile 创建，也可以打开 YAML 编辑器手动配置。",
    step1Title: "从 Profile 创建",
    step1Desc: "选择一个 starter profile。我们会在浏览器里检测可用 agent 并生成配置。",
    step1Code: "Web UI → 从 starter profile 创建",
    step1Tip: "会创建 .cc-branch.yaml、.cc-branch.state.toml 和 .gitignore",
    step2Title: "自定义配置",
    step2Desc: "编辑 .cc-branch.yaml，调整 slots、agents 和 windows。",
    step2Slots: "顶层工作空间容器",
    step2Agents: "可复用的 AI 工具定义",
    step2Windows: "Slot 内的执行单元",
    step3Title: "启动工作空间",
    step3Desc: "运行 cc-branch start 创建 tmux 会话并进入工作空间。",
    step3Tip: "先用 cc-branch doctor 检查配置是否正确",
    langSwitch: "语言",
    themeSwitch: "主题",
    light: "亮色",
    dark: "暗色",
    agent: "Agent",
    id: "ID",
    slots: "个 slot",
    selectProject: "从侧边栏选择一个项目",
    openSidebar: "打开侧边栏",
    edit: "编辑",
    save: "保存",
    configSaved: "配置已保存",
    checksPassed: "全部通过",
    checksWarnings: "发现警告",
    checksIssues: "发现问题",
    addProject: "添加项目",
    scan: "扫描",
    createConfig: "创建配置",
    review: "预览",
    done: "完成",
    chooseTemplate: "选择一个模板。我们将检测可用的 agent 并生成配置。",
    projectDirectory: "项目目录",
    noConfigFound: "未找到配置 — 添加后初始化",
    step: "步骤",
    createConfigInteractively: "从 starter profile 创建",
    confirm: "确认",
    preview: "预览",
    projectAdded: "项目已添加",
    remove: "移除",
    offline: "当前处于离线状态",
    unknownError: "发生未知错误",
    confirmStop: "停止 \"{name}\"？",
    confirmAction: "{action} \"{name}\"？",
    dismissNotification: "关闭通知",
    skipToContent: "跳转到主内容",
    noProjects: "暂无项目",
    addProjectHint: "点击下方 + 添加项目",
    current: "当前",
    pathNotFound: "路径不存在",
    canInitializeAfterAdd: "暂无配置 — 添加后可在概览中初始化",
    backendUnreachable: "后端连接失败 — 请检查 cc-branch server 是否运行",
    manualClose: "关闭",
    pathExample: "~/projects/my-project",
    useCurrentDir: "使用当前目录",
    fromRecent: "最近使用",
    formMode: "表单",
    yamlMode: "YAML",
    generatedYaml: "生成的 YAML",
    unsaved: "未保存",
    add: "添加",
    moveUp: "上移",
    moveDown: "下移",
    advanced: "高级",
    name: "名称",
    backend: "后端",
    workingDirectory: "工作目录",
    environmentVariables: "环境变量",
    noSlotsYet: "暂无 slots",
    addSlotHint: "添加 slot 以定义工作空间容器",
    noAgentsYet: "暂无 agents",
    addAgentHint: "添加 agent 以绑定到窗口",
    duplicateName: "重复的名称",
    required: "必填",
    commentsWillBeLost: "切换到表单模式会重写 YAML 并移除注释。是否继续？",
  },
};

export function t(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  const template = dict[lang][key] || key;
  return vars ? interpolate(template, vars) : template;
}

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nCtx>({
  lang: "en",
  setLang: () => {},
  t: (k) => k,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, _setLang] = useState<Lang>(
    () => (localStorage.getItem(STORAGE_KEY) as Lang) || "en"
  );

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(STORAGE_KEY, l);
    _setLang(l);
  }, []);

  const translate = useCallback(
    (key: string, vars?: Record<string, string | number>) => t(lang, key, vars),
    [lang]
  );

  // Sync html lang attribute
  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  return (
    <I18nContext.Provider value={{ lang, setLang, t: translate }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
