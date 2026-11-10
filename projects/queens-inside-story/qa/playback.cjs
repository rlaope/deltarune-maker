const { join, resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function check(browser, file) {
  const page = await browser.newPage({ viewport: { width: 800, height: 800 } });
  const samples = [];
  const target = Number(process.env.QA_PLAY_THROUGH) || null;
  await page.goto(pathToFileURL(join(__dirname, 'player.html')).href);
  const start = Number(process.env.QA_PLAY_START) || 0;
  await page.evaluate(async ({ url, start }) => {
    const player = document.querySelector('video');
    player.muted = true;
    player.volume = 0;
    player.src = url;
    await player.play();
    if (start) player.currentTime = start;
  }, { url: pathToFileURL(resolve(file)).href, start });
  for (const second of [.2, 3.5, 8.4, 12.7, 15.4, 16.3, 18.9, 22.8, 28.9, 31.5, 32.4, 33, 37.7, 42.3, 46.9, 51.6, 53.9, 56, 59.4]) {
    if (second <= start) continue;
    if (target && second > target) break;
    const valid = await page.evaluate(time => time < document.querySelector('video').duration, second);
    if (!valid) break;
    await page.waitForFunction(time => document.querySelector('video').currentTime >= time, second, { timeout: 35000 });
    samples.push(await page.evaluate(() => document.querySelector('video').currentTime));
    if (process.env.QA_CAPTURE_PREFIX) {
      await page.screenshot({ path: `${process.env.QA_CAPTURE_PREFIX}-${second}.png` });
    }
  }
  await page.waitForFunction(time => {
    const video = document.querySelector('video');
    return video.ended || (time !== null && video.currentTime >= time);
  }, target, { timeout: 35000 });
  const outcome = await page.evaluate(() => {
    const v = document.querySelector('video');
    v.pause();
    const quality = v.getVideoPlaybackQuality();
    return { duration: v.duration, currentTime: v.currentTime, ended: v.ended, muted: v.muted,
             volume: v.volume, width: v.videoWidth, height: v.videoHeight,
             decoded: quality.totalVideoFrames, dropped: quality.droppedVideoFrames };
  });
  await page.close();
  if (!outcome.muted || outcome.volume !== 0 || outcome.decoded === 0 || (!target && !outcome.ended)) {
    throw new Error(`Playback incomplete: ${JSON.stringify(outcome)}`);
  }
  return { file, samples, ...outcome };
}

(async () => {
  if (!process.argv[2]) throw new Error('Provide at least one video path');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM,
                                          args: ['--mute-audio', '--allow-file-access-from-files'] });
  try {
    console.log(JSON.stringify(await Promise.all(process.argv.slice(2).map(file => check(browser, file))), null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
