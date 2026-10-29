# Radix Colors

The Ocean, Forest, Violet, and Slate presets use selected values from
Radix Colors 3.0.0, under the MIT license in `LICENSE`.
Terracotta is DoukiMD's original palette.

Source: https://github.com/radix-ui/colors

Pinned distribution: https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/index.mjs

Distribution SHA-256: `35560544c86ca2c2fa79e5fdfba40d18312e11e21fd81d52af524b94c117294d`

| Preset | Accent scale | Neutral scale |
| --- | --- | --- |
| Ocean | Blue | Slate |
| Forest | Green | Sage |
| Violet | Violet | Mauve |
| Slate | Slate | Gray |

Both light and dark values are stored in `default/palettes.json`.
Neutral steps 1/2/3/7/11/12 supply backgrounds, surfaces, code, borders,
muted text, and body text. Accent steps 3/11/12 supply highlights, links,
and stronger active-navigation text.
Forest's light-mode links also use step 12 to meet 4.5:1 contrast on surfaces.
The rendered combinations are checked for WCAG text contrast.
No npm package, remote styles, or Radix UI components are required.
