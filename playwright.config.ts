import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'tests',
  timeout: 120_000,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:4173', ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
  webServer: { command: 'npm run preview', url: 'http://localhost:4173', reuseExistingServer: true, timeout: 60_000 },
})
