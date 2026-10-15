export default async function run(page, ui) {
  await ui.click('@e2');
  await page.waitForTimeout(500);
  const scrollY = await page.evaluate(() => window.scrollY);
  return { scrollY };
}