# Art Bible: [Game Title]

## Document Status
- **Version**: 1.0
- **Last Updated**: [Date]
- **Owned By**: art-director
- **Status**: [Draft / Under Review / Approved]

## Visual Identity Summary
[2-3 sentences describing the overall visual identity]

## Reference Board
[List reference games, films, art, and what specific visual quality each represents]

| Reference | Medium | What We're Taking |
| --------- | ------ | ----------------- |
| [Name] | [Game/Film/Art] | [Specific quality] |

## Color Palette

### Primary Palette
| Name | Hex | Usage |
| ---- | --- | ----- |
| [Color Name] | #XXXXXX | [Where and when to use] |

### Emotional Color Mapping
| Game State | Dominant Colors | Mood |
| ---------- | --------------- | ---- |
| Exploration | [Colors] | [Feeling] |
| Combat | [Colors] | [Feeling] |
| Safe zones | [Colors] | [Feeling] |
| Danger | [Colors] | [Feeling] |

## Art Style

### Rendering Style
[Realistic / Stylized / Hand-painted / Cel-shaded / Low-poly / etc.]

### Proportions
[Character proportions, environment scale, UI scale relationships]

### Level of Detail
[How detailed are characters, environments, UI elements?]

### Visual Hierarchy
[How do we guide the player's eye? What's always most prominent?]

## Character Art Standards
[Silhouette requirements, color coding, animation style, proportions]

## Environment Art Standards
[Modular props, environment kits, lighting setups, scale reference]

## UI Art Standards
[Button styles, typography, icon style, menu layout principles, HUD density]

## VFX Standards
[Particle style, screen effects, impact feedback, color coding]

## Asset Production Standards

### Naming Convention
`[category]_[name]_[variant]_[size].[ext]`

### Texture Standards
| Category | Max Resolution | Format | Color Space |
| -------- | -------------- | ------ | ----------- |
| Characters | [Size] | [Format] | [Space] |
| Environments | [Size] | [Format] | [Space] |
| UI | [Size] | [Format] | [Space] |
| VFX | [Size] | [Format] | [Space] |

### Animation Standards
[Frame rates, blend times, animation graph structure]

### 3D Pipeline Standards

#### Mesh Format
[glTF/GLB / FBX / both — which format for which use case]

#### Polycount Tiers
| Category | LOD0 | LOD1 | LOD2 |
|----------|------|------|------|
| Characters | [N tris] | [N tris] | [N tris] |
| Environment Props | [N tris] | [N tris] | [N tris] |
| Background | [N tris] | [N tris] | [N tris] |

#### Texture Map Standards
| Map Type | Resolution | Format | Color Space |
|----------|-----------|--------|-------------|
| Albedo | [Size] | [Format] | sRGB |
| Normal | [Size] | [Format] | Linear |
| Roughness | [Size] | [Format] | Linear |
| Metallic | [Size] | [Format] | Linear |
| AO | [Size] | [Format] | Linear |

#### Rigging Standards
[Skeleton type, bone count limits, naming convention for bones]

#### LOD Strategy
[Number of levels, reduction ratio, distance thresholds]

## Accessibility
- Colorblind-safe UI elements required
- Minimum text size: [X]px at 1080p
- High contrast mode specifications
- Icon + color (never color alone) for game state
