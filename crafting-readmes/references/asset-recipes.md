# Asset recipes

Read this in step 5 before building any image.

## Tools

Check each with `<tool> --version`. Install the missing ones with `brew install librsvg imagemagick ffmpeg` (macOS) or the distro package.

- `rsvg-convert`: SVG to PNG.
- `magick`: crop, round corners, resize.
- `ffmpeg`: frames to GIF.
- Optional: `gifsicle`, `pngquant`, `uv` (runs fonttools without installing it).

## Banner SVG

- Size: `viewBox="0 0 1280 420"`.
- Animate with CSS `@keyframes` or SMIL inside the SVG. GitHub plays both in `<img>`.
- GitHub loads no web fonts and no external files for an SVG in `<img>`. Convert headline text to paths:
  - Get an OFL font (Google Fonts) as a static TTF. For a variable font, run `fontTools.varLib.instancer` to fix the weight.
  - Shape the text with `uharfbuzz`, read the outlines with `fontTools.pens.svgPathPen.SVGPathPen`, write each glyph as a `<path>`.
  - Run it with `uv run --with fonttools --with uharfbuzz python script.py`.
- Draw the banner's own background. It must read on light and dark GitHub themes.
- Render it once with `rsvg-convert -w 1280 banner.svg -o /tmp/check.png` and look at the PNG.

## Screenshots

- Use real screenshots when the project has a UI that builds and runs without side effects.
- macOS window capture: `screencapture -x -o -l<window-id> out.png`. It needs Screen Recording permission. Find the window id with a CGWindowList query.
- Round the corners and add a soft shadow with `magick`.
- Compress with `pngquant --quality 70-90 --ext .png --force out.png` when installed.
- No runnable UI: draw an illustration in SVG that uses the real labels and layout from the source. Show only behavior the facts list backs.

## Demo GIF

1. Write a script that emits one SVG scene per frame: 20 fps, 6 to 10 s, loop.
2. Render the frames: `rsvg-convert -w 960 frame_000.svg -o frame_000.png` for each.
3. Join them:

```bash
ffmpeg -framerate 20 -i frame_%03d.png \
  -vf "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  -loop 0 demo.gif
```

4. Make frame 0 a full composition. Previews and the first paint show frame 0.
5. Keep the file under 3 MB. Over it: lower fps, width or colors, then `gifsicle -O3 --lossy=80 -o demo.gif demo.gif` when installed.
6. Look at 3 frames: first, middle, last. Zoom into text with `magick frame.png -crop 400x200+X+Y -scale 300% zoom.png`.

## Sketches for the concept board

- Size: `viewBox="0 0 1600 900"`.
- Show: palette background, tagline in the heading font, a slot for the hero art, three feature cards.
- Embed a real screenshot as `<image href="data:image/png;base64,...">` when step 1 captured one. Else draw a labeled placeholder rect.
- Export a PNG for any editor, GIMP included: `rsvg-convert -w 1600 sketch-a.svg -o sketch-a.png`. Open it with `open -a GIMP sketch-a.png` when GIMP is installed.
- Batch edits without a window: `/Applications/GIMP.app/Contents/MacOS/gimp-console -i -d --quit --batch-interpreter=plug-in-script-fu-eval -b '<script-fu>'`. The binary is not on `PATH` (Homebrew links only `gimp`). Without `--quit` it never exits. GIMP 3 Script-Fu: run `gimp-console --help` for the batch flags.
