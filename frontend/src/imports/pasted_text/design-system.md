# 🎨 1. DESIGN PHILOSOPHY (VERY IMPORTANT)

PrepPanda should feel:

> 🧠 Calm + Focused + Intelligent + Non-distracting
> 

### ❌ Avoid:

- Bright flashy colors
- Overloaded UI
- Too many buttons

### ✅ Aim:

- “Studying in a peaceful library”
- AI is assistant, not distraction

---

# 🌗 2. COLOR SYSTEM (LIGHT + DARK MODE)

---

## 🌙 DARK MODE (PRIMARY EXPERIENCE)

> Default mode = dark (students study at night)
> 

### 🎯 Base Colors

| Token | Color | Usage |
| --- | --- | --- |
| `--bg-primary` | #0D1117 | Main background |
| `--bg-secondary` | #111827 | Cards / panels |
| `--bg-tertiary` | #1F2937 | Hover / inputs |
| `--border` | #1F2937 | Subtle borders |

---

### ✨ Accent System (Eye Soothing Neon)

| Token | Color | Usage |
| --- | --- | --- |
| `--accent-primary` | #3B82F6 | Primary CTA |
| `--accent-secondary` | #22D3EE | AI highlight |
| `--accent-success` | #22C55E | Correct answers |
| `--accent-warning` | #F59E0B | Medium priority |
| `--accent-danger` | #EF4444 | Wrong answers |

---

### 🧾 Text Colors

| Token | Color |
| --- | --- |
| `--text-primary` | #E5E7EB |
| `--text-secondary` | #9CA3AF |
| `--text-muted` | #6B7280 |

---

### 🌈 Special AI Glow

```
linear-gradient(90deg, #3B82F6, #22D3EE)
```

Used for:

- Generate button
- AI thinking indicator

---

## ☀️ LIGHT MODE (Day Studying)

---

### 🎯 Base Colors

| Token | Color |
| --- | --- |
| `--bg-primary` | #F8FAFC |
| `--bg-secondary` | #FFFFFF |
| `--bg-tertiary` | #F1F5F9 |
| `--border` | #E2E8F0 |

---

### ✨ Accent System

| Token | Color |
| --- | --- |
| `--accent-primary` | #2563EB |
| `--accent-secondary` | #06B6D4 |

---

### 🧾 Text

| Token | Color |
| --- | --- |
| `--text-primary` | #0F172A |
| `--text-secondary` | #475569 |
| `--text-muted` | #94A3B8 |

---

# 🧩 3. LAYOUT SYSTEM (PIXEL PERFECT)

---

## 🧱 Desktop Grid

```
Sidebar: 260px
Workspace: auto
Right Panel: 320px
Max width: 1440–1600px
```

---

## 📏 Spacing System (IMPORTANT)

| Token | Value |
| --- | --- |
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| xxl | 48px |

👉 Maintain **consistent spacing → clean UI feel**

---

# 🔲 4. COMPONENT DESIGN SYSTEM

---

## 🧾 Card Component

```
background: var(--bg-secondary)
border: 1px solid var(--border)
border-radius: 14px
padding: 16px–20px
```

Hover:

```
border-color: var(--accent-primary)
```

---

## 🔘 Button System

### Primary Button

```
background: linear-gradient(90deg, #3B82F6, #22D3EE)
color: white
border-radius: 999px
height: 44px
padding: 0 20px
```

---

### Secondary Button

```
background: var(--bg-tertiary)
border: 1px solid var(--border)
```

---

### Ghost Button

```
background: transparent
hover: var(--bg-tertiary)
```

---

## 🧠 Input Field

```
background: var(--bg-tertiary)
border: 1px solid var(--border)
border-radius: 12px
padding: 14px
```

Focus:

```
border: 1px solid #3B82F6
box-shadow: 0 0 0 2px rgba(59,130,246,0.2)
```

---

# 🧠 5. AI EXPERIENCE DESIGN (CORE MAGIC)

---

## ✨ AI Response Structure

Instead of plain text → structured blocks:

```
📌 Concept
📊 Example
🧠 Explanation
📈 PYQ Insight
📝 Practice
```

---

## 💬 Chat UI Behavior

- Smooth fade-in messages
- Typing indicator:
    - “PrepPanda is thinking…”

---

## ⚡ Smart Actions (Hover on Text)

When user selects text:

```
Explain | Summarize | Quiz | Mindmap
```

---

# 📚 6. PDF + AI SPLIT UX (CRITICAL)

---

## Layout

```
| PDF | AI |
| 60% | 40% |
```

---

## PDF Interactions

- Highlight → auto-save
- Right click → “Ask AI”
- Bookmark → quick revisit

---

## AI Sync Behavior

When user scrolls PDF:

👉 AI context auto-updates

---

# 🧠 7. MINDMAP UX DETAILS

---

### Node States

| State | Style |
| --- | --- |
| Default | subtle border |
| Active | glowing border |
| Weak topic | red tint |
| Strong topic | green tint |

---

### Interaction

- Click → expand
- Double click → focus mode
- Drag → reposition

---

# 📝 8. QUIZ UX (HIGH ENGAGEMENT)

---

## Question Card

```
background: var(--bg-secondary)
padding: 20px
radius: 14px
```

---

## Options

Hover:

```
background: var(--bg-tertiary)
```

Selected:

```
border: #3B82F6
```

Correct:

```
background: rgba(34,197,94,0.1)
```

Wrong:

```
background: rgba(239,68,68,0.1)
```

---

# 📊 9. ANALYTICS UX (INSIGHT DRIVEN)

---

## Charts Style

- Soft gradients
- No harsh lines
- Rounded bars

---

## Heatmap

- Green → strong
- Yellow → medium
- Red → weak

---

## Insight Cards

```
"You forget formulas after 3 days"
"Revise Organic Chemistry"
```

---

# ⚡ 10. MICRO INTERACTIONS (PREMIUM FEEL)

---

## 🎯 Timing

| Action | Duration |
| --- | --- |
| Hover | 120ms |
| Click | 90ms |
| Page load | 150ms |

---

## ✨ Effects

- Button press → slight scale (0.97)
- Card hover → lift (shadow)
- AI response → fade + slide

---

# 📱 11. MOBILE UX (IMPORTANT)

---

## Bottom Nav

```
Home | Study | Quiz | AI | Profile
```

---

## Behavior

- AI input always sticky bottom
- Swipe between tabs

---

# 🧠 12. UX PRINCIPLES (MOST IMPORTANT PART)

---

## 1. Reduce Cognitive Load

- Show only what’s needed

---

## 2. Context is Everything

- AI must always know:
    - Class
    - Subject
    - Chapter

---

## 3. One-Click Learning

- No friction between:
    - Reading → Asking → Practicing

---

## 4. Feedback Loop

```
Study → Quiz → Analyze → Improve
```

---

# 🔥 FINAL DESIGN FEEL

PrepPanda should feel like:

> 📘 “A calm digital study desk powered by AI”
> 

# 🧩 PREPPANDA — PIXEL PERFECT FIGMA SCREENS

---

# 🖥️ 1. MAIN FRAME SETUP

### 🎯 Desktop Frame

```
Frame: Desktop
Width: 1440px
Height: 1024px
Layout: Grid (12 columns)

Margin: 80px
Gutter: 24px
```

---

# 📌 2. GLOBAL LAYOUT (MASTER COMPONENT)

```
| Sidebar | Workspace | Right Panel |
| 260px   | 1fr       | 320px       |
```

---

# 🧱 3. SIDEBAR (LEFT)

### Frame

```
Width: 260px
Fill: #0D1117
Padding: 16px
Auto Layout: Vertical
Gap: 12px
```

---

### 🟢 Logo Section

```
Height: 48px
Items: Logo + PrepPanda text

Text:
Font: Inter
Weight: 600
Size: 16px
Color: #E5E7EB
```

---

### 🔍 Search Bar

```
Height: 40px
Radius: 10px
Fill: #111827
Border: #1F2937
Padding: 12px
```

---

### 📚 Nav Items (Component)

```
Height: 44px
Radius: 10px
Padding: 12px
Gap: 10px
```

### Default

```
Text: #9CA3AF
```

### Hover

```
Fill: #1F2937
```

### Active

```
Fill: #111827
Left Border: 3px solid #3B82F6
Text: #E5E7EB
```

---

# 🧠 4. WORKSPACE (CENTER)

### Frame

```
Padding: 32px
Auto Layout: Vertical
Gap: 24px
Fill: #0D1117
```

---

## 🧾 A. CONTEXT HEADER

```
Height: 64px
Radius: 14px
Fill: #111827
Border: #1F2937
Padding: 16px
```

### Content

```
Title: PrepPanda AI
Font: 16px semibold

Subtitle:
"Class 10 • Science • Chemical Reactions"
Font: 13px
Color: #9CA3AF
```

---

## 💬 B. CHAT AREA

### Container

```
Auto Layout: Vertical
Gap: 16px
```

---

### 👤 User Message

```
Max Width: 520px
Padding: 12px 16px
Radius: 12px
Fill: #1F2937
Text: #E5E7EB
Align: Right
```

---

### 🤖 AI Message

```
Max Width: 640px
Padding: 16px
Radius: 14px
Fill: #111827
Border: #1F2937
```

---

### 📦 AI Card Inside Message

```
Padding: 16px
Gap: 10px
Radius: 12px
Fill: #0D1117
Border: #1F2937
```

---

## ✍️ C. INPUT BAR

```
Height: 72px
Radius: 16px
Fill: #111827
Border: #1F2937
Padding: 16px
```

---

### Input Text

```
Font: 14px
Color: #E5E7EB
Placeholder: #6B7280
```

---

### 🚀 Generate Button

```
Height: 40px
Padding: 0 18px
Radius: 999px

Fill:
linear-gradient(90deg, #3B82F6, #22D3EE)

Text: White
Weight: 500
```

---

# 🧠 5. MODE SELECTOR (ABOVE INPUT)

```
Auto Layout: Horizontal
Gap: 10px
```

### Button

```
Height: 32px
Padding: 0 14px
Radius: 999px
Fill: #111827
Border: #1F2937
```

---

### Active

```
Fill: #3B82F6
Text: white
```

---

# 📊 6. RIGHT PANEL

### Frame

```
Width: 320px
Padding: 16px
Gap: 16px
Fill: #0D1117
Border-left: #1F2937
```

---

## 🔹 Tool Card

```
Padding: 16px
Radius: 14px
Fill: #111827
Border: #1F2937
```

---

### Button Inside

```
Height: 40px
Radius: 10px
Fill: #1F2937
Hover: #374151
```

---

# 📚 7. LIBRARY SCREEN

---

## Grid Layout

```
Columns: 3
Gap: 24px
```

---

## 📦 Card

```
Height: 160px
Radius: 16px
Padding: 20px
Fill: #111827
Border: #1F2937
```

---

### Hover

```
Border: #3B82F6
Scale: 1.02
```

---

### Content

```
Title: 16px semibold
Subtitle: 13px muted
```

---

# 📝 8. QUIZ SCREEN

---

## Question Card

```
Padding: 20px
Radius: 16px
Fill: #111827
Border: #1F2937
```

---

## Options

```
Height: 52px
Padding: 16px
Radius: 12px
Border: #1F2937
```

---

### States

| State | Style |
| --- | --- |
| Hover | #1F2937 |
| Selected | border: #3B82F6 |
| Correct | bg: rgba(34,197,94,0.1) |
| Wrong | bg: rgba(239,68,68,0.1) |

---

# 🧠 9. MINDMAP SCREEN

---

## Canvas

```
Fill: #0D1117
Grid: Dot pattern (opacity 0.1)
```

---

## Node

```
Padding: 12px
Radius: 10px
Fill: #111827
Border: #1F2937
```

---

### Active Node

```
Border: #22D3EE
Glow: subtle
```

---

# 📊 10. DASHBOARD SCREEN

---

## Card Grid

```
Columns: 2
Gap: 20px
```

---

## Stats Card

```
Height: 120px
Radius: 16px
Padding: 20px
Fill: #111827
```

---

### Example Content

```
72% Accuracy
Weak Topic: Thermodynamics
```

---

# 🎯 11. TYPOGRAPHY SYSTEM

---

## Font: Inter

| Type | Size | Weight |
| --- | --- | --- |
| H1 | 24px | 600 |
| H2 | 20px | 600 |
| Body | 14px | 400 |
| Small | 12px | 400 |

---

# ✨ 12. MICRO INTERACTIONS (FIGMA PROTOTYPE)

---

### Button Click

```
Scale: 0.97
Duration: 90ms
```

---

### Card Hover

```
Shadow: 0 4px 20px rgba(0,0,0,0.3)
```

---

### AI Response

```
Opacity: 0 → 1
Y: 10px → 0
Duration: 150ms
```

---

# 🧩 13. FIGMA COMPONENT STRUCTURE

Create these as components:

```
Button (Primary, Secondary, Ghost)
Card
Input Field
Nav Item
Chat Bubble
AI Card
Quiz Option
Mindmap Node
```