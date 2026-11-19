# gudilko.com

Personal website of Alex Gudilko. A static one-page site: `index.html` plus images in `assets/`.

## Forbes articles

`.github/workflows/forbes.yml` runs every Monday. It reads the Forbes Technology Council author page, updates `data/forbes.json`, and rewrites the "Most read on Forbes" and "Latest" lists in `index.html`. To change how a title is shown, edit `display_title` in `data/forbes.json`. To run it by hand: Actions, "Update Forbes articles", "Run workflow".
