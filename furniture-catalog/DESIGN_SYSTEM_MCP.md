# MCP Apps Design System

Based on Figma analysis of nodes `67:2867` (App Interface), `24:1672` (Components), and `81:720` (Inline Cards).

## Core References

### Layout
The interface features a split-pane layout typical of modern chat applications:

1.  **Sidebar**: Navigation rail (`Sidebar` component) with core actions.
2.  **Main Area**:
    *   **Chat Titlebar**: Header for the conversation context.
    *   **Chat Area**: Contains the conversation thread (`User message`, `Claude response`).
    *   **App Container**: Dedicated area for rendering MCP-driven applications/artifacts.
    *   **Chat Input**: Fixed bottom area (`Chat input`).

### Component Library

#### Icons & Navigation
Defined in the design system with specific semantic IDs:

*   **Chat Add** (`24:535`, `365:4353`): New conversation.
*   **Chats** (`24:537`, `370:4818`): List of conversations.
*   **Projects** (`24:706`, `370:4820`): Organization folders.
*   **Artifacts** (`24:1244`, `370:4808`): Generated content library.
*   **Code** (`24:554`): Code snippets/execution.

#### Actions
*   **ThumbsUp** (`24:1586`) / **ThumbsDown** (`24:1600`): Feedback mechanism.
*   **Copy** (`24:1614`): Clipboard action.
*   **ArrowClockwise** (`291:2361`): Retry/Refresh.
*   **X** (`24:837`): Close/Dismiss modal.
*   **Dots Horizontal** (`24:607`): Overflow menu.

#### Input
*   **Add** (`24:461`): Attach/Create.
*   **ArrowUp** (`24:1505`): Send message.
*   **Caret Down Small** (`24:523`): Dropdown triggers.
*   **Arrow Right** (`24:2481`): Navigation/Next (used in cards).

### App Cards (Inline Apps)
The design system defines specific card layouts for application artifacts displayed within the chat stream.

#### 1. Loading State (`85:4557`)
*   Simple placeholder indicating active processing.
*   Likely uses same container dimensions as active apps.

#### 2. List Views (`85:4573`)
Standard layout for displaying collections of items (e.g., tasks, files).
*   **Structure**: Vertical list of items.
*   **Item layout**: Icon/Avatar + Title + Meta/Status.

#### 3. Meeting / Agenda Card (`291:12869`)
Specialized card for meeting details.
*   **Header**:
    *   **Date**: Label "Date" (Width 72px, Text/500 `#73726c`) + Value (Text/300 `#3d3d3a`). 
    *   **Time**: Label "Time" + Value.
    *   **Attendees**: List of avatars (24x24px circles).
*   **Content Sections**:
    *   **Discussion Points**: Bulleted list.
    *   **Action Items**: Checkbox list (`Checkbox` component + Text).
*   **Typography**:
    *   Labels: 14px, Color `Text/500` (#73726c).
    *   Values: 14px, Color `Text/300` (#3d3d3a).
    *   Values: 14px, Color `Text/300` (#3d3d3a).
    *   Font Family: `Anthropic Sans Text`.

#### 4. Product Card
Card used for displaying catalog items (e.g., bricks) in a carousel or grid.
*   **Dimensions**: Width 280px, Aspect Ratio 4/3.
*   **Radius**: 16px (`Radius/2XL`) for image container.
*   **Content**:
    *   **Image**: Cover fit `aspect-[4/3]`, background `Tertiary` (#f0eee6) or `secondary/50`.
    *   **Title**: 15px Bold, Color `Text/Primary` (#141413).
    *   **Texture/Subtitle**: 13px, Color `Text/400` (#565552).
    *   **Meta Row**: 12px Medium, Color `Text/Muted` (#73726c). Displays Brand, Separator, Article.
*   **Interaction**: Hover scale effect on image (scale-105).


### Asset Handling
*   Images and SVGs are served from a local asset server (e.g., `http://localhost:3845/assets/...`).
*   Implemented as constant references in code for consistency.

## Visual Style

### Typography & Fonts
*   **Font Family**: "Anthropic Sans Text", "Anthropic Sans Variable" (fallback to sans-serif).
*   **Body Text**: Size 16px (`Size/Text/md`), Line Height ~22.4px (`Line height/Text/md`), Weight 400.
*   **Small Text**: Size 14px (`Size/Text/sm`), Line Height ~19.6px (`Line height/Heading/sm`).

### Color Palette (Variables)

#### Text
*   **Primary**: `#141413` (`Text/Primary`, `Text/100`) - Main content.
*   **Secondary**: `#3d3d3a` (`Text/Secondary`, `Text/300`) - Supporting text.
*   **Texture/Label**: `#565552` (`Text/400`) - Specific for texture labels.
*   **Muted**: `#73726c` (`Text/500`, `Muted Text (500)`) - Meta info.
*   **Ghost**: `#73726c80` (`Text/Ghost`) - Placeholders/disabled state.

#### Backgrounds
*   **Primary**: `#ffffff` (`Background/Primary`, `bg-000`, `Grayscale/Gray 000 (White)`).
*   **Secondary/surface**: `#faf9f5` (`BG/100`) - Likely sidebar or panel bg.
*   **Tertiary**: `#f0eee6` (`BG/300`) - Hover states or inputs.
*   **Dark**: `#242424` (`BG/200`) - Inverted elements.

#### Accents
*   **Main**: `#c6613f` (`Accent/Main/000`).
*   **Clay**: `#d97757` (`Accent/Clay`).
*   **Heather**: `#cbcadb` (`Secondary/Anthropic/Heather`).
*   **Fig**: `#c46686` (`Secondary/Anthropic/Fig`).

#### Borders
*   **Primary**: `#1f1e1d66` (`Border/Primary`).
*   **Secondary**: `#1f1e1d4d` (`Border/Secondary`, `Border/200`).
*   **Subtle**: `#1f1e1d26` (`Border/300`).

### Metrics & Effects

#### Radius
*   **MD**: 8px (`Radius/MD`).
*   **LG**: 10px (`Radius/LG`).
*   **XL**: 12px (`Radius/XL`).
*   **2XL**: 16px (`Border radius/2xl`).

#### Shadows (Effects)
*   **Low**: `0px 1px 2px rgba(0, 0, 0, 0.05)` (Offset 0,1; Radius 2).

## Implementation Data
(Raw asset references and CSS variables)

```css
:root {
  /* Colors */
  --text-primary: #141413;
  --text-secondary: #3d3d3a;
  --text-muted: #73726c;
  --bg-primary: #ffffff;
  --bg-secondary: #faf9f5;
  --accent-main: #c6613f;
  
  /* Fonts */
  --font-sans: "Anthropic Sans Text", sans-serif;
  
  /* Spacing/Radius */
  --radius-md: 8px;
  --radius-xl: 12px;
}
```

```javascript
/* Icons */
const ICON_UNION = "http://localhost:3845/assets/32a1cb6380576179566f610f34b79b556436e05f.svg";
const ICON_GENERIC = "http://localhost:3845/assets/2d560c39dcd88d477eeed6b7759806c63e3858c4.svg";
```
