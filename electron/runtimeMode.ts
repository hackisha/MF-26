export type RuntimeModeInput = {
  appIsPackaged: boolean;
  packagedRendererExists: boolean;
  viteDevServerUrl: string | undefined;
};

export function isDevRuntime({ appIsPackaged, packagedRendererExists, viteDevServerUrl }: RuntimeModeInput): boolean {
  return viteDevServerUrl !== undefined || (!appIsPackaged && !packagedRendererExists);
}

export function rendererUrlForRoute({
  devOrigin,
  isDev,
  rendererEntryUrl,
  route = "/"
}: {
  devOrigin: string;
  isDev: boolean;
  rendererEntryUrl: string;
  route?: string;
}): string {
  if (isDev) return `${devOrigin}${route}`;
  return `${rendererEntryUrl}${route === "/" ? "" : `#${route}`}`;
}

export function isAllowedNavigationUrl({
  devOrigin,
  isDev,
  rendererEntryUrl,
  url
}: {
  devOrigin: string;
  isDev: boolean;
  rendererEntryUrl: string;
  url: string;
}): boolean {
  if (isDev) return url.startsWith(`${devOrigin}/`) || url === devOrigin;
  return url === rendererEntryUrl || url.startsWith(`${rendererEntryUrl}#`);
}
