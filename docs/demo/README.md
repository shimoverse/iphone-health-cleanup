# Phone cleanup illustrated walkthrough

[Play the GIF](phone-cleanup-demo.gif) · [Download the MP4](phone-cleanup-demo.mp4) · [View the poster](phone-cleanup-demo-poster.png)

This 32-second storyboard uses fictional apps and AI-assisted illustrations. It is not a screen recording, a working phone controller, a measured cleanup duration or evidence of recovered storage. It connects to no device. No personal phone screenshots, inventories or account information are included.

## What it shows

1. Ask a local assistant: “My phone is slow. Check its health and help me make some space.”
2. Choose iPhone Mirroring for supported screen steps or trusted USB for the included scripts. Mirroring needs a nearby locked iPhone; USB read-only checks generally allow phone use. Actual changes need an idle window.
3. Inspect storage, battery and the slow task before changes. State whether the inventory is complete.
4. Show the proposed app decisions and saved-data consequences.
5. Override a recommendation: keep Example Travel.
6. Approve only Example Game and Example Trial, including their local data.
7. Check the sample removals and retained apps. Real storage and performance measurements are separate.

The illustration uses the iPhone journey. Android has a separate connection and safety model, explained in the main README.

## Reuse

Use the MP4 for social video, the GIF for README/blog embeds and the poster for an email thumbnail. Keep the illustration label and fictional-data caption visible. The project is GPL-3.0-or-later; see the repository license.

The optional renderer is [tools/render_demo.py](../../tools/render_demo.py). It needs Python, Pillow, FFmpeg and the macOS Arial/Georgia fonts. It does not access a phone or network. Run it with `--out` pointing to a temporary output folder outside this checkout. The publication check allows only the exact reviewed asset hashes; regeneration requires visual/privacy review before updating those hashes.
