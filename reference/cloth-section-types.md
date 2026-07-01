# Reference — MotionCloth section types

Complete `SectionTypeID → class` map for GRB's MotionCloth format, transcribed directly from `MotionSectionFactory.ReadSection` in ATK v1.3.1 (decompiled). Each section in a `MotionBody` starts with `uint16 TypeID`, `uint16 0xECD7 (60631)`, `int32 SizeIncludingHeader`. See [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md) for the format.

> IDs are decimal as they appear in the source. Sections not listed fall through to `UnknownSection` (preserved verbatim by ATK). "sized by" means the section's length is computed from an earlier counter section rather than self-describing.

## Body (rigid) sections

| ID | Class | Notes |
| ---: | --- | --- |
| 513 | `NamedObjectName` | object name |
| 3073 | `BodyType` | |
| 3074 | `BodyIndexInIsland` | |
| 3076 | `BodyUserData` | |
| 3077 | `BodyBroadPhase` | |
| 3078 | `BodyData` | |
| 3080 | `BodyColor` | |
| 3083 | `BodyTransform` | position/orientation |
| 3085 | `BodyIndexInIslandExtra` | |

## Cloth core

| ID | Class | Notes |
| ---: | --- | --- |
| 4353 | `ClothType` | |
| 4354 | `ClothUserData` | holds `UserVerticesCount` (sizes several buffers) |
| 4356 | `ClothDefinition` | **feature flags** (UseWind, UseTearing, UseClustering, …) |
| 4357 | `ClothProperties` | **simulation tunables** (Gravity, Damping, Friction, …) |

## Constraints & solver

| ID | Class | Notes |
| ---: | --- | --- |
| 4359 | `ClothPropertiesConstraintsEnable` | |
| 4360 | `ClothPropertiesConstraintsStiffness` | |
| 4361 | `ClothEngineLoopStepCount` | sizes 4362 |
| 4362 | `ClothEngineLoop` | sized by 4361 (`StepCount`) |
| 4363 | `ClothVerticesCurrentPosition` | `Vector4[]`, sized by `ClothUserData.UserVerticesCount` (rounded up to 16) |
| 4364 | `ClothConstraintsSizes` | 6 sizes; sizes 4365 |
| 4365 | `ClothConstraints` | `IntVector4[]`, sized by 4364 + 4381 |
| 4366 | `ClothConstraintsSIMDF8` | |
| 4378 | `ClothPropertiesConstraintsCorrectionFactors` | |
| 4381 | `ClothStretchingConstraintsCount` | sizes 4365 / 4394 |
| 4394 | `ClothStretchingConstraints` | `short[]`, sized by 4381 |
| 4415 | `ClothConstraintsScaleFactor` | |

## Mesh / geometry

| ID | Class | Notes |
| ---: | --- | --- |
| 4369 | `ClothMeshConstraintsOptimizedCount` | |
| 4370 | `ClothMeshIndexBufferSize` | sizes 4371 |
| 4371 | `ClothMeshIndexBuffer` | `Triangle[]`, sized by 4370 |
| 4373 | `ClothAABox` | bounding box |
| 4382 | `ClothMeshAABBTree` | sized by `ClothUserData` or `ClothMeshIndexBufferSize` depending on 4384/4385 |
| 4384 | `ClothMeshHasVertexAABBTree` | flag controlling 4382 |
| 4385 | `ClothMeshHasTriangleAABBTree` | flag controlling 4382 |
| 4387 | `ClothMeshConstraintsSizes` | sizes 4388 |
| 4388 | `ClothMeshConstraints` | `MeshConstraint[]`, sized by 4387 |

## Properties (tunable sub-sections)

| ID | Class | Notes |
| ---: | --- | --- |
| 4395 | `ClothPropertiesMeshMappings` | binds cloth to garment mesh (key for attachment) |
| 4396 | `ClothPropertiesLod` | LOD config |
| 4397 | `ClothPropertiesWind` | wind response |
| 4398 | `ClothPropertiesGravity` | `Vector3` gravity (default 0,0,−10) |
| 4399 | `ClothPropertiesAzimuthAnimation` | |
| 4400 | `ClothPropertiesInclinationAnimation` | |
| 4401 | `ClothPropertiesRadiusAnimation` | |

## Presets & colliders

| ID | Class | Notes |
| ---: | --- | --- |
| 4433 | `ClothPresets` | |
| 4434 | `ClothPresetsCount` | |
| 4435 | `ClothPresetDefinition` | |
| 4436 | `ClothPresetBufferSize` | |
| 4443 | `ClothPresetDefinitionPerVertexData` | |
| 4444 | `ClothPresetPerVertexDataSize` | |
| 4465 | `ClothRegisteredCollidersCount` | |

## Per-vertex data

| ID | Class | Notes |
| ---: | --- | --- |
| 4529 | `ClothPerVertexDataDefinition` | |
| 4530 | `ClothPerVertexDataCounters` | sizes 4531 / 4532 |
| 4531 | `ClothPerVertexDataBuffer` | `byte[]`, sized by 4530 (`PerVertexDataBufferSize × 16`) |
| 4532 | `ClothPerVertexDataSIMDF8` | sized by 4530 (`PerVertexDataSIMDSize`) |

## Additional render vertices — the render↔sim binding

The render (visual) mesh = the sim vertices (driven directly) **+ `A` "additional" vertices**, each pinned onto a sim **triangle** by barycentric coords. Stored as a CSR layout indexed **per sim triangle** (`N` = triangle count), not per additional vertex. Verified on Walker LOD0 (170 sim verts, 288 tris, `A`=62, `M`=64).

| ID | Class | Notes |
| ---: | --- | --- |
| 4561 | `ClothAdditionalVerticesCounters` | `{int32 AdditionalVerticesBufferSize N, int32 AdditionalVerticesSIMDSize M}`; `N` = sim triangle count, `M` = `A` padded to ×8; sizes 4562/4563/4565 |
| 4562 | `ClothAdditionalVerticesTriangleVerticesCount` | `byte[N]`, **per sim triangle**: # additional verts on it (`sum = A`) |
| 4563 | `ClothAdditionalVerticesTriangleFirstVertexIndex` | `ushort[N]`, **per sim triangle**: first additional-vertex index (CSR offset into the `A`-list); `4563[last]+4562[last]=A` |
| 4564 | `ClothAdditionalVerticesBarycentricCoordinatesParameters` | `SIMDF8` = `{Scale, Offset, Magic}` dequant params for 4565 (`Magic ≈ Scale·255`) |
| 4565 | `ClothAdditionalVerticesBarycentricCoordinatesData` | `ushort[M]`, one per additional vert (tail padded `0xFFFF`); decode = split into hi/lo bytes, `coord = byte·Scale + Offset` → the two smaller barycentric weights, third = `1−u−v` |

> **Render↔sim binding (barycentric scheme):** present only in some cloths (e.g. `TP_WalkerCoat_Cloth`); many GRB cloths omit 4561–4565 and the render mesh *is* the sim mesh (direct). Triangle `t`'s 3 sim verts are `ClothMeshIndexBuffer(4371)[3t..3t+2]`. Recomputing these for a new render mesh is the render↔sim remap — see [`docs/11-cloth-and-physics.md`](../docs/11-cloth-and-physics.md).

## Editor metadata (authoring)

| ID | Class | Notes |
| ---: | --- | --- |
| 4657 | `ClothEditorData` | |
| 4658 | `ClothEditorDataClothID` | the cloth's editor ID (attachment) |
| 4659 | `ClothEditorDataVisibility` | |
| 4661 | `ClothEditorDataCollisionEnabledColliders` | |
| 4662 | `ClothEditorDataPresetsNames` | named presets |

## Strips untwisting

| ID | Class | Notes |
| ---: | --- | --- |
| 4833 | `ClothStripsUntwistingIndicesCount` | sizes 4834 |
| 4834 | `ClothStripsUntwistingIndices` | `ushort[]`, sized by 4833 |
