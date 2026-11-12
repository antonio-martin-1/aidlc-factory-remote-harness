# Typography Tokens

Allowed font sizes, weights, and line heights.

## Font sizes

| Token | Pixels | Used for |
|-------|--------|----------|
| `font-size.caption` | 12 | Captions, metadata, timestamps |
| `font-size.body` | 14 | Body text, paragraphs, labels |
| `font-size.body-large` | 16 | Lead text, large inputs |
| `font-size.h4` | 20 | Section headings, card titles |
| `font-size.h3` | 24 | Page section headings |
| `font-size.h2` | 32 | Page titles |
| `font-size.h1` | 40 | Hero titles |

## Font weights

| Token | Value | Used for |
|-------|-------|----------|
| `font-weight.regular` | 400 | Body text, labels |
| `font-weight.medium` | 500 | Input text, button labels |
| `font-weight.semibold` | 600 | Section headings, strong emphasis |
| `font-weight.bold` | 700 | Page titles, display text |

## Line heights

| Token | Ratio | Used for |
|-------|-------|----------|
| `line-height.tight` | 1.2 | Headings |
| `line-height.normal` | 1.5 | Body text |
| `line-height.relaxed` | 1.75 | Long-form reading |

## Snap rules

| If font-size is | Snap to |
|-----------------|---------|
| 11-13 | 12 (caption) |
| 13-15 | 14 (body) |
| 15-18 | 16 (body-large) |
| 19-22 | 20 (h4) |
| 23-28 | 24 (h3) |
| 29-36 | 32 (h2) |
| 37+ | 40 (h1) |
