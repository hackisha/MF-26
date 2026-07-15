import { spawn } from "node:child_process";

const electronBin = process.platform === "win32" ? "node_modules\\.bin\\electron.cmd" : "node_modules/.bin/electron";
const child = spawn(electronBin, ["."], {
  stdio: "inherit",
  windowsHide: false,
  env: {
    ...process.env,
    VITE_DEV_SERVER_URL: "http://127.0.0.1:5173"
  }
});

child.on("exit", (code) => {
  process.exit(typeof code === "number" ? code : 1);
});
