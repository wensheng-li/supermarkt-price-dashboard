/**
 * Runs the Python scraper as a child process, passing the product query as an argument.
 */
import { execFile } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Path to the Python scraper from the backend directory
const SCRAPER_PATH = path.resolve(
  __dirname,
  "../../../scraper/scraper_runner.py",
);
const PYTHON_BIN = path.resolve(
  __dirname,
  "../../../scraper/.venv/bin/python3",
);

export function runScraper(productQuery) {
  return new Promise((resolve, reject) => {
    console.log(`[scraper] Triggering scrape for: "${productQuery}"`);

    execFile(
      PYTHON_BIN,
      [SCRAPER_PATH, productQuery],
      {
        timeout: 60000, // 60 second max — OFF API can be slow
        cwd: path.resolve(__dirname, "../../../scraper"),
      },
      (error, stdout, stderr) => {
        if (error) {
          console.error(`[scraper] Error: ${error.message}`);
          console.error(`[scraper] stderr: ${stderr}`);
          return reject(error);
        }
        console.log(`[scraper] Done:\n${stdout}`);
        resolve(stdout);
      },
    );
  });
}
