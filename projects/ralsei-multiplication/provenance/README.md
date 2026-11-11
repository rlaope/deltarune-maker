# Original asset source metadata

These JSON inventories record DELTARUNE asset names, pinned source URLs/revisions, content hashes, dimensions and relevant extraction provenance. Rights remain with Toby Fox and the DELTARUNE contributors. Third-party mirrors are source references, not evidence of redistribution permission.

Runtime filesystem paths, font glyph tables and asset payloads are omitted. Native sprites, portraits, font atlases, music, sounds, room images, MP4 files and compiled game bundles remain outside this public repository. Metadata alone cannot run the film. Supply the separately prepared private runtime asset tree described in the [project README](../README.md).

`source-hashes.json` describes the studio-authored production Python files, not original game assets. The training dummy used in space is the original `spr_dummynpc`; its movement and the procedural black hole are authored staging. Asset acquisition does not establish permission to redistribute the originals.

Audio follows the production precedence `native` → `extras` → `voices-v3`. Overridden legacy audio entries and the obsolete Tenna fallback note are omitted from this public inventory; v3 uses the native writer samples recorded in `voices-v3.json`.
