#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

async function run() {
  const { chromium } = require("playwright");
  const grafanaUrl = process.env.GRAFANA_URL || "http://127.0.0.1:3000";
  const dashboardUrl = `${grafanaUrl.replace(/\/$/, "")}/d/cloudwalk-monitoring-test`;
  const outputDir = process.env.PLAYWRIGHT_OUTPUT_DIR || "logs/playwright";
  const screenshotPath = path.join(outputDir, "grafana-dashboard-playwright-check.png");
  const requiredTitles = [
    "What Needs Attention Right Now",
    "Why Each Metric Is Ranked This Way",
    "What Could Get Worse In The Forecast Window",
    "Evidence Behind The Current Recommendation",
    "What This Top Issue Means For The Business",
    "Formal Alerts That Have Already Fired",
    "How Risk Rates Are Moving Over Time",
    "How Much Traffic These Rates Represent",
    "How To Read This Dashboard On First Login",
  ];

  fs.mkdirSync(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });

  try {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(5000);
    await page.evaluate(async () => {
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const seen = new Set();
      const scrollables = Array.from(document.querySelectorAll("*")).filter((el) => {
        const style = window.getComputedStyle(el);
        const overflowY = style.overflowY || style.overflow;
        if (overflowY === "visible") {
          return false;
        }
        return el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 100;
      });
      for (const el of scrollables) {
        const key = `${el.tagName}:${el.className}`;
        if (seen.has(key)) {
          continue;
        }
        seen.add(key);
        const step = Math.max(200, Math.floor(el.clientHeight * 0.8));
        for (let y = 0; y <= el.scrollHeight; y += step) {
          el.scrollTop = y;
          await sleep(150);
        }
        el.scrollTop = 0;
      }
      await sleep(400);
    });
    const bodyText = (await page.textContent("body")) || "";

    const missing = requiredTitles.filter((title) => !bodyText.includes(title));
    await page.screenshot({ path: screenshotPath, fullPage: true });

    if (missing.length > 0) {
      throw new Error(`Dashboard missing expected panel titles: ${missing.join(", ")}`);
    }

    console.log(`[check] Playwright dashboard validation passed: ${screenshotPath}`);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(`[check] Playwright dashboard validation failed: ${error.message}`);
  process.exit(1);
});
