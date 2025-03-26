/// <reference types="vite/client" />

declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';

interface ImportMetaEnv {
  readonly VITE_WS_URL: string;
  readonly DEV: boolean;
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  // Remove all test-related functions
}

declare module "*.png" {
  const content: string;
  export default content;
}

declare module "*.jpg" {
  const content: string;
  export default content;
}

declare module "*.jpeg" {
  const content: string;
  export default content;
}

declare module "*.gif" {
  const content: string;
  export default content;
} 