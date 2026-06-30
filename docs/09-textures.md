# 09 — Textures (TextureMap, DDS, mips, gamma)

Textures are the most commonly modded GRB asset (retextures, camos, face/skin edits). This doc covers the texture resource model and the practical rules for replacing one.

## The resource types

| Type | What it is |
| --- | --- |
| **TextureMap** | A single texture image (diffuse, normal, roughness, etc.) with its mip chain. The thing you open in ATK's Texture Viewer. |
| **TextureSet** | A named bundle that maps **slots** (DiffuseMap, NormalMap, …) to TextureMaps for a material. ATK "added names to all TextureMap slots." |
| **Material** | Shader parameters + references to a TextureSet / TextureMaps. |

A material points at a TextureSet; the TextureSet's slots point at TextureMaps; each TextureMap carries the actual pixels and mips. To change how a surface looks, you usually replace the **TextureMap(s)** a material already references (a "retexture"), which is why texture-only mods often touch just the resources forge.

## DDS is the working format

ATK exports/imports TextureMaps as **DDS, PNG, TGA, or JPG**, and **recommends DDS** for replacement because it carries the parameters the engine cares about:

- **Pixel format** (the compression/encoding of the texture data — see below).
- **Mip chain** (precomputed downscales).
- **Gamma / color-space** information.
- **Cube map** faces (ATK supports cube-map DDS import/export).

PNG/JPG/TGA are fine for quick edits, but they discard pixel-format and gamma intent, leaving ATK to infer them. DDS keeps you in control.

## Pixel formats

GRB uses the standard DirectX block-compressed (BCn) family plus uncompressed formats. ATK "added support for all the DDS PixelFormats the game uses" and, as of 1.3.0, **removed its custom DDS code in favor of DirectXTex** (so its DDS handling is now industry-standard via `DirectXTexNet`).

Practical guidance:
- **Diffuse/albedo** → typically a BC-compressed sRGB format.
- **Normal maps** → typically BC5 (two-channel) or similar, **linear** (not sRGB) — getting gamma/color-space right matters here.
- ATK's default import quality is `Best Quality` (`DefaultTexturePixelFormat`), and it can be set to specific formats. There was a fix for "incorrect pixel format assignment when using DTX5 quality setting," so be deliberate about the format rather than trusting a quality preset blindly.

> **Match the original.** The safest replacement keeps the **same pixel format, dimensions, and gamma** as the texture you're replacing. Export the original first, read its format, and author your replacement to match.

## Mips

- `Mip0` is full resolution; each subsequent mip halves the dimensions. The game streams/selects mips by distance and settings.
- TextureMaps may store mips as **separate entries** (`…_Mip0`, `…_Mip1`) alongside a base entry, or as a chain inside one DDS. ATK `GenerateMipsWhenImporting` defaults `True`, so importing a single full-res image will build the chain for you.
- Skipping mips (importing only Mip0) can cause shimmering/aliasing at distance and larger memory use — let ATK generate the full chain unless you have a reason not to.

## Gamma / color space

ATK added **Gamma Settings** to the Texture Viewer (1.3.0): gamma auto-updates on import and textures export with the correct gamma. This solved a class of "texture looks too dark/washed out" bugs. The rule of thumb:
- **Color/albedo** textures are **sRGB** (gamma-encoded).
- **Data** textures (normal, roughness, metalness, masks) are **linear**.
- If a replacement looks wrong tonally in-game, gamma/color-space mismatch is a prime suspect.

## Swizzling (console only — usually irrelevant on PC)

"Swizzling" reorders texture bytes for console GPU memory layouts. ATK ships `DDSUnswizzle` and an `UnswizzleTextures` option (default **`False`**, with a per-game override). For **PC GRB this is off** — PC textures are not swizzled. You only care about this if working with console data.

## Replacing a texture — the short version

1. In ATK, navigate to the TextureMap, **export the original as DDS** (so you have a reference and a backup).
2. Note its **pixel format, dimensions, gamma/color-space, mip count**.
3. Author your replacement in an image editor / Blender bake to **match** those properties.
4. Open the TextureMap in the **Texture Viewer** → **Replace** (or drag-drop the new file onto the entry). Confirm format/gamma in the import dialog; let it generate mips.
5. Repack the resources forge and test at multiple distances.

## Things that commonly go wrong

- **Wrong color space** → too dark/bright. Fix gamma/sRGB-vs-linear.
- **Wrong pixel format for normals** → blocky or inverted-looking normals.
- **Dimension change** that breaks the mip assumptions or memory budget → glitches or crashes; match original dimensions unless you know the asset tolerates change.
- **Only replacing Mip0** and leaving stale lower mips → wrong texture appears at distance.
