import { spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";
import { setTimeout as delay } from "node:timers/promises";

const host = "127.0.0.1";
const configuredPort = process.env.PLAYWRIGHT_PORT;
const port = configuredPort && /^\d+$/.test(configuredPort) ? configuredPort : "5173";
const baseUrl = `http://${host}:${port}`;

function spawnCommand(command, args, options = {}) {
  return spawn(command, args, {
    stdio: "inherit",
    windowsHide: true,
    ...options
  });
}

async function assertPortAvailable() {
  await new Promise((resolve, reject) => {
    const probe = createServer();

    probe.once("error", () => {
      reject(new Error(`Port ${port} is already in use. Stop the existing server or set PLAYWRIGHT_PORT.`));
    });

    probe.once("listening", () => {
      probe.close(resolve);
    });

    probe.listen(Number(port), host);
  });
}

async function waitForServer(child) {
  const deadline = Date.now() + 30_000;

  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Vite dev server exited early with code ${child.exitCode}.`);
    }

    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // Server is still starting.
    }

    await delay(250);
  }

  throw new Error(`Timed out waiting for ${baseUrl}.`);
}

async function stopProcessTree(child) {
  if (child.exitCode !== null || child.pid === undefined) return;

  if (globalThis.process.platform === "win32") {
    const killer = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true
    });
    await once(killer, "exit").catch(() => undefined);
    await Promise.race([once(child, "exit"), delay(1_500)]).catch(() => undefined);
    return;
  }

  child.kill("SIGTERM");
  await Promise.race([once(child, "exit"), delay(1_500)]).catch(() => undefined);
  if (child.exitCode === null) child.kill("SIGKILL");
}

let exitCode = 1;
let vite;

try {
  await assertPortAvailable();

  vite = spawnCommand(process.execPath, [
    "node_modules/vite/bin/vite.js",
    "--host",
    host,
    "--port",
    port,
    "--strictPort",
    "--clearScreen",
    "false"
  ], {
    env: {
      ...process.env,
      VITE_DISABLE_WATCH: "1"
    }
  });

  await waitForServer(vite);

  const playwright = spawnCommand(process.execPath, ["node_modules/@playwright/test/cli.js", "test", ...process.argv.slice(2)], {
    env: {
      ...process.env,
      PLAYWRIGHT_SKIP_WEB_SERVER: "1"
    }
  });

  const [code] = await once(playwright, "exit");
  exitCode = typeof code === "number" ? code : 1;
} finally {
  if (vite) await stopProcessTree(vite);
}

process.exit(exitCode);
