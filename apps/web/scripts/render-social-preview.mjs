import { readFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const pack = JSON.parse(await readFile(resolve(root, "data/demo/memory/pack.json"), "utf8"));
const keys = ["nmda_signaling", "hippocampal_ltp", "memory_persistence"];
const names = keys.map((key) => pack.entities.find((entity) => entity.key === key).name);
const escape = (value) =>
  value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 640 } });
  await page.goto(process.env.CAUSALBIO_SCREENSHOT_URL ?? "http://127.0.0.1:3000");
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((labels) => {
    document.body.innerHTML = `<main class="preview">
      <p class="identity">c·b <span>Computational biology · Scientific computing</span></p>
      <h1>CausalBio Lab</h1>
      <p class="subtitle">Biological questions. Inspectable evidence.</p>
      <section class="figure" aria-label="Selected memory mechanism">
        <div class="nodes"><p>${labels[0]}</p><span aria-hidden="true">→</span><p>${labels[1]}</p><span class="indirect" aria-hidden="true">⇢</span><p>${labels[2]}</p></div>
        <p class="caption">Selected curated pathway · animal evidence; indirect for general human retention</p>
      </section>
      <p class="closing">Follow the sources. Compare mechanisms. Keep uncertainty visible.</p>
    </main>`;
    const style = document.createElement("style");
    style.textContent = `body{background:#f6f4ef;color:#20201d}.preview{padding:46px 64px;height:640px;min-height:0}.identity{display:flex;align-items:center;gap:26px;font-size:32px;font-family:var(--font-editorial),Georgia,serif}.identity span{font-family:var(--font-interface),sans-serif;font-size:18px;color:#68665f}.preview h1{font-size:82px;line-height:1.1;margin-top:22px;letter-spacing:-.025em}.subtitle{font-size:28px;margin-top:8px}.figure{border-top:1px solid #d8d4cb;border-bottom:1px solid #d8d4cb;padding:30px 0 22px;margin-top:36px}.nodes{display:grid;grid-template-columns:1fr 56px 1fr 56px 1fr;align-items:center;gap:18px}.nodes p{font-size:24px;line-height:1.3;max-width:290px}.nodes span{font-size:32px;color:#24483c;text-align:center}.nodes .indirect{color:#68665f}.caption{font-size:16px;color:#68665f;margin-top:23px}.closing{font-size:20px;margin-top:27px;color:#24483c}`;
    document.head.append(style);
  }, names.map(escape));
  await page.evaluate(() => document.fonts.ready);
  await mkdir(resolve(root, "docs/assets"), { recursive: true });
  await page.screenshot({ path: resolve(root, "docs/assets/social-preview.png") });
  console.log("Rendered 1280×640 social preview from actual curated entity labels.");
} finally {
  await browser.close();
}
