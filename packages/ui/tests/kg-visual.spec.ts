import { expect, test } from "@playwright/test";
import { PNG } from "pngjs";

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "mobile", width: 390, height: 844 }
];

function canvasStats(buffer: Buffer) {
  const image = PNG.sync.read(buffer);
  const colors = new Set<string>();
  let coloredPixels = 0;

  for (let y = 0; y < image.height; y += 8) {
    for (let x = 0; x < image.width; x += 8) {
      const index = (image.width * y + x) << 2;
      const r = image.data[index] ?? 0;
      const g = image.data[index + 1] ?? 0;
      const b = image.data[index + 2] ?? 0;
      const a = image.data[index + 3] ?? 0;
      colors.add(`${r},${g},${b},${a}`);
      if (a > 0 && (Math.abs(r - g) > 8 || Math.abs(g - b) > 8 || r + g + b > 90)) {
        coloredPixels += 1;
      }
    }
  }

  return { coloredPixels, uniqueColors: colors.size };
}

for (const viewport of viewports) {
  test(`KG explorer renders a nonblank interactive 3D canvas on ${viewport.name}`, async ({
    page
  }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto("/kg");
    await expect(page.getByRole("combobox").nth(1)).toBeVisible();
    await page.getByRole("combobox").nth(1).selectOption("2");
    await expect(page.locator("canvas").first()).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(3_000);

    const canvas = page.locator("canvas").first();
    const before = await canvas.boundingBox();
    expect(before?.width).toBeGreaterThan(300);
    expect(before?.height).toBeGreaterThan(300);

    await page.mouse.move((before?.x ?? 0) + 120, (before?.y ?? 0) + 120);
    await page.mouse.wheel(0, -300);
    await page.waitForTimeout(600);

    const screenshot = await canvas.screenshot();
    await testInfo.attach(`kg-${viewport.name}.png`, {
      body: screenshot,
      contentType: "image/png"
    });

    const stats = canvasStats(screenshot);
    expect(stats.uniqueColors).toBeGreaterThan(8);
    expect(stats.coloredPixels).toBeGreaterThan(20);
  });
}
