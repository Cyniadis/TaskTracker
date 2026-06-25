# TaskTracker Web UI

A static browser interface for TaskTracker that can be hosted on GitHub Pages.

## What this adds

- `index.html` — a two-tab dashboard for today's list and the general task list.
- `styles.css` — styling for the web interface.
- `app.js` — task parsing, daily selection, editing, and CSV export.

## How to use

1. Open `index.html` through a static host or GitHub Pages.
2. The app loads `tasklist.csv` automatically.
3. Edit tasks in the **General Tasks** tab.
4. In the **Today** tab, edit or move the tasks selected for today.
5. Click **Download CSV** to export the updated `tasklist.csv` file.

## GitHub Pages setup

1. Commit the new files to your repository.
2. In GitHub, open repository settings and enable GitHub Pages.
3. Select the `main` branch and the root folder as the publishing source.
4. Save, then visit the generated GitHub Pages URL.

## Notes

- Because GitHub Pages is static, edits are saved locally in your browser's `localStorage`.
- Use **Reload CSV** to reset the interface from the repository file.
- To persist changes in the repo, download the updated CSV and replace `tasklist.csv` in the repository.
