import { spawn } from "node:child_process";

const child = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--strictPort"], {
  stdio: "inherit",
  windowsHide: true,
  env: {
    ...process.env,
    VITE_DISABLE_WATCH: "1"
  }
});

function stopChild() {
  if (child.exitCode !== null || child.pid === undefined) return;
  child.kill();
}

process.on("SIGINT", () => {
  stopChild();
});

process.on("SIGTERM", () => {
  stopChild();
});

child.on("exit", (code) => {
  process.exit(typeof code === "number" ? code : 1);
});
