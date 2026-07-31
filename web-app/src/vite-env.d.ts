/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_START_MOCK?: string;
  readonly VITE_PROXY_TARGET?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
