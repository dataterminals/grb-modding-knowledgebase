# Reference — Resource types

Typed resources are what live inside `.data` containers (see [`docs/03-data-and-resources.md`](../docs/03-data-and-resources.md)). This is a catalog of the types relevant to GRB, what each is, and how ATK lets you work with it. Compiled from ATK's `README.txt` changelog (which enumerates GRB support explicitly) plus direct observation.

> "GRB-supported" below means ATK's changelog specifically lists GRB/Breakpoint support, or it was observed in GRB data. Anvil shares types across games, so some types exist in GRB data even where ATK's GRB editor support is partial.

## Geometry & rigging

| Type | Description | ATK workflow | GRB |
| --- | --- | --- | --- |
| **Mesh** | 3D geometry; primitives, vertex buffers (pos/normal/tangent/binormal/UVx5/color/weights), index buffer, material refs. | Mesh Viewer; export/import **glTF/GLB** | ✅ all GRB vertex formats |
| **Skeleton** | Bone hierarchy + bind transforms for skinned meshes. | Mesh Viewer; GLB / XML / BuildTable export | ✅ |
| **Cloth** (MotionCloth / `ClothPackage`) | Physics cloth simulation data (capes, coats, straps). **Format reverse-engineered** — see [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) and [`cloth-section-types.md`](cloth-section-types.md). | Mesh Viewer load; GLB export; **XML** (tune gravity/stiffness/wind) | ✅ |
| **SoftBody** / **MotionSoftBody** | Soft-body physics deformables; `SoftBody` carries `ClothGenerationSettings` (generate cloth from a mesh). | Mesh Viewer load; GLB export; BuildTable gen | ✅ |
| **FacialSolverData** | Facial-animation solver data. | supported (1.3.0) | ✅ |
| **HairMesh** | Hair geometry (preview re-added in 1.3.1). | Mesh Viewer preview | ✅ |

## Textures & materials

| Type | Description | ATK workflow | GRB |
| --- | --- | --- | --- |
| **TextureMap** | One texture image + mip chain. | Texture Viewer; DDS/PNG/TGA/JPG export & replace | ✅ |
| **TextureSet** | Named slot bundle (DiffuseMap, NormalMap, …) → TextureMaps. | XML export/import (names on all slots) | ✅ |
| **Material** | Shader params + texture/TextureSet references. | XML export/import | ✅ |
| **MaterialTemplate** | Reusable material definition. | hashes resolved | ✅ (hashes added) |

## Definitions / data-driven assembly

| Type | Description | ATK workflow | GRB |
| --- | --- | --- | --- |
| **BuildTable** | Node graph assembling an entity/item from parts, meshes, materials, properties — references other resources by ID. | XML export/import; generate from Mesh Viewer | ✅ |
| **EntityBuilder** | Entity assembly definition. | XML export/import | ✅ |
| **EntityGroupBuilder** | Group of entities. | XML export/import | ✅ (Anvil-wide) |
| **LODSelector** | Chooses LOD by distance/criteria. | (resolved/handled) | ✅ (Anvil-wide) |

## Localization & UI

| Type | Description | ATK workflow | GRB |
| --- | --- | --- | --- |
| **LocalizationPackage** | Text/strings table. | XML export/import | ✅ (added 1.2.2) |
| UI assets (`UI_…`) | Inventory icons / maps, etc. | as TextureMaps | ✅ (observed) |

## Container / streaming sidecars

| Type | Description | Notes |
| --- | --- | --- |
| **GlobalMetaFile** | Forge-wide metadata. | Written as `.MetaFile` (older ATK used `.data` — rename required). |
| **PrefetchingFileInfos** | Streaming/prefetch hints. | Written as `.PrefetchInfo`. GRB support added 1.2.9. Large ones can cause in-game errors if mishandled. |
| **Dependency** | Inter-resource dependency info. | `.dependency`; auto-deleted for games that don't need it; in ATK's ignored-extensions. |

## Audio (peripheral to cosmetic modding)

The install has a `sounddata\` directory and `.tbf`/sound blobs; ATK's GRB audio editing is not a focus of the changelog. Treat audio modding as **not yet characterized** here — see open questions in [`meta/research-log.md`](../meta/research-log.md).

## How to tell what a `.data` contains

1. Unpack the `.data` in ATK — the inner files carry **type-specific extensions** (`.BuildTable`, `.Mesh`, etc.) or resolve to a known type.
2. The **resolved name** hints at the type (`…DiffuseMap…` → TextureMap; `…_LOD0` → Mesh; `Head_…` BuildTable in a `_Template` → BuildTable).
3. When in doubt, the **hash/ID** plus ATK's recognition is authoritative.
