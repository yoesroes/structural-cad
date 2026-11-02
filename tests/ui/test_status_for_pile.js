"use strict";
const fs = require("fs");
const appPath = process.argv[2] || "src/scad_ui/static/app.js";
const src = fs.readFileSync(appPath, "utf8");

function extractFn(name) {
  const re = new RegExp("function " + name + "\\s*\\([^)]*\\)\\s*\\{");
  const start = src.search(re);
  if (start < 0) throw new Error("fungsi tidak ditemukan: " + name);
  let i = src.indexOf("{", start);
  let depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error("kurung tidak seimbang: " + name);
}

// Strict mode: deklarasi function di eval tidak mengikat ke scope luar.
// Bungkus jadi expression lalu assign.
const statusForPile = new Function(
  "return (" + extractFn("statusForPile") + ");"
)();

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    process.exit(1);
  }
}

{
  const st = statusForPile("P1-1", { issues: [] });
  assert(st.text === "Sesuai" && st.cls === "status-ok", "empty issues");
}

{
  const st = statusForPile("P1-1", {
    issues: [
      { level: "error", code: "SCHEMA", path: "/project", message: "skema rusak" },
    ],
  });
  assert(st.text !== "Sesuai", "global error must not be Sesuai: " + st.text);
  assert(
    st.text.includes("Error proyek") || st.text.includes("SCHEMA"),
    "global error visible: " + st.text
  );
  assert(
    st.cls === "status-err" || st.cls === "status-warn",
    "error class: " + st.cls
  );
}

{
  const st = statusForPile("P1-1", {
    issues: [
      {
        level: "error",
        code: "ZONE_DEPTH_SHORT",
        pile: "P1-10",
        path: "/groups/0/instances/9",
      },
    ],
  });
  assert(st.text === "Sesuai", "other pile must not affect P1-1");
}

{
  const st = statusForPile("P1-2", {
    issues: [
      { level: "error", code: "SCHEMA", path: "/" },
      {
        level: "error",
        code: "ZONE_DEPTH_SHORT",
        pile: "P1-2",
        path: "/groups/0/instances/1",
      },
    ],
  });
  assert(
    String(st.text).includes("ZONE_DEPTH_SHORT"),
    "pile error preferred: " + st.text
  );
}

{
  const st = statusForPile("P1-3", {
    issues: [{ level: "warning", code: "ZONE_GAP", pile: "P1-3" }],
  });
  assert(String(st.text).includes("ZONE_GAP"), "warning text");
  assert(st.cls === "status-warn", "warning class");
}

console.log("ok statusForPile aktual");
