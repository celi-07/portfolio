# Jason Luman portfolio

A static portfolio with product case studies, career and education timelines, and an original Blender cat that can fetch a project for visitors. The site is served from `dist/` and needs no build or package installation.

## Run locally

Open a terminal in the repository root, the folder containing this README and `dist/`. With Node.js installed, run

```text
npx --yes serve dist --listen 8000
```

Open [http://localhost:8000](http://localhost:8000). The portfolio uses HTML, CSS, JavaScript, JSON, and a 3D model. The command starts a local static file server. It requires Node.js and downloads the `serve` package on first use. Stop the server with Ctrl+C.

If port 8000 is already in use, stop the existing server or choose another port, for example `npx --yes serve dist --listen 8080`, and open http://localhost:8080. Always start the command from the same checkout that contains the JSON you are editing.

## Edit content

Edit `dist/portfolio.json` and refresh the browser. The file contains these top-level fields.

- `profile` holds the name, introduction, page metadata, contact links, and the CV link shown in the header and hero.
- `sections` holds the lists in display order. The current section IDs are `work`, `career`, `education`, `credentials`, `leadership`, and `skills`. The `kind` controls the layout. Keep each item's `id` unique across the site and stable so existing detail links continue to work. For example, Finance Studio opens at `/#/item/finance-studio` and the Junior Software Engineer role opens at `/#/item/junior-software-engineer`.
- `guide` holds the cat model and poster paths and the labels for the project-fetch controls.
- `ui` holds navigation, contact, and detail-view labels.

To add a role, copy the example below into the `items` array of the `career` section. Replace the example text and keep the roles ordered from most to least recent. Product case studies live in `work`. A product item can also have an `image` with `src`, `alt`, and an optional `caption`.

```json
{
  "id": "example-role",
  "title": "Software Engineer",
  "subtitle": "Example team",
  "period": "Jan 2027 – Present",
  "summary": "I build and maintain a mobile app.",
  "stack": ["React Native"],
  "blocks": [
    {
      "heading": "Mobile development",
      "paragraphs": ["I built the app's account settings screen."]
    }
  ],
  "links": [
    { "label": "Project website", "url": "https://example.com/" }
  ]
}
```

Within a detail block, use `paragraphs` for prose and `bullets` for a list. The `stack`, `blocks`, `links`, and `image` fields can be omitted. Asset paths in the JSON are relative to `dist/`, so `./assets/work/finance-studio-demo.webp` points to `dist/assets/work/finance-studio-demo.webp`. To update the CV, replace `dist/assets/Jason-Luman-CV.pdf` or change `profile.cv.url` to the new path.

Save the file, then refresh the local page. Check that you are editing `dist/portfolio.json` in the same checkout from which the server was started. Open http://localhost:8000/portfolio.json to inspect the data the server is providing. If it differs from your edits, an older server or another checkout may be serving that port.

To validate the JSON, run `node -e "JSON.parse(require('fs').readFileSync('dist/portfolio.json', 'utf8')); console.log('Valid JSON')"`. Refresh the local site and open the edited item to confirm the summary, detail, and links. Deploy the updated `dist/` directory to publish the changes.

## Edit the design and cat

- Adjust typography, colors, and layout in `dist/styles.css`. Page rendering and detail navigation live in `dist/app.js`.
- Edit the original model in `art/collectible-cat.blend`. Export a Y-up GLB to `dist/assets/cat.glb` and update `dist/assets/cat.png` with the matching transparent poster. The `Fetch` clip starts and ends seated. Its `FetchRoot` node lets the camera follow the cat, and the node's `fetchHandoffSeconds` custom property times the project card update. Keep `HeadPivot` free for pointer tracking while the cat is seated. The guide behavior lives in `dist/cat.js`. Use the `guide` fields in `dist/portfolio.json` if the asset filenames change.
- Bundled fonts and their licenses are in `dist/assets/fonts/`. Three.js and its license are in `dist/assets/vendor/`.

Interaction references include [model-viewer’s annotations examples](https://modelviewer.dev/examples/annotations/) and [Bruno Simon’s portfolio](https://bruno-simon.com/).
