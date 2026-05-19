# Hanafuda Koi-Koi — Anki Add-on

Play Koi-Koi Hanafuda inside Anki, with vocab challenges drawn from your own decks.

---

## Installation

1. Locate your Anki add-ons folder:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`

2. Copy the `hanafuda_game/` folder into `addons21/`

3. Restart Anki

4. Go to **Tools → 🌸 Hanafuda Koi-Koi**

---

## Adding Card Images

The game works without images (falls back to emoji + color), but looks much
better with real Hanafuda card art.

**Naming convention** — place PNG files in `hanafuda_game/web/cards/`:

```
cards/{month}_{position}.png
```

- `month` is 0–11 (January = 0, December = 11)
- `position` is 0–3 (the 4 cards within each month)

Example filenames:
```
0_0.png   ← January Crane (bright)
0_1.png   ← January Pine ribbon
0_2.png   ← January Pine junk
0_3.png   ← January Pine junk
1_0.png   ← February Bush Warbler (bright)
...
11_3.png  ← December Rain Junk
```

Cards are 54×80px in the UI; any aspect ratio image will be scaled to fit.

### Month reference
| Index | Month    | Theme          |
|-------|----------|----------------|
| 0     | January  | Pine / Crane   |
| 1     | February | Plum / Warbler |
| 2     | March    | Cherry Blossom |
| 3     | April    | Wisteria       |
| 4     | May      | Iris           |
| 5     | June     | Peony          |
| 6     | July     | Bush Clover    |
| 7     | August   | Susuki / Moon  |
| 8     | September| Chrysanthemum  |
| 9     | October  | Maple          |
| 10    | November | Willow / Rain  |
| 11    | December | Paulownia      |

---

## How to Play

1. Select a deck for vocab challenges in the dropdown at the top
2. Click a card from your hand to select it
3. If it matches a field card (same month), click the glowing field card
4. A **vocab challenge** appears — answer correctly to capture both cards
5. Wrong answer → your card goes to the field instead
6. Drawn deck cards capture automatically (no challenge for deck draws)
7. When you form a **yaku** (combo), choose **Koi-Koi** to push for more points
   or **Stop** to collect your points safely

---

## Yaku (Scoring Combos)

| Name       | Description          | Points |
|------------|----------------------|--------|
| Goko       | All 5 brights        | 15     |
| Shiko      | 4 brights (no rain)  | 8      |
| Ame-Shiko  | 4 brights + rain     | 7      |
| Sankou     | 3 brights (no rain)  | 5      |
| Aka-Tan    | 3 poetry ribbons     | 5      |
| Ao-Tan     | 3 blue ribbons       | 5      |
| Tan-Zaku   | 5+ ribbons           | 1+     |
| Kasu       | 10+ junk cards       | 1+     |

---

## Vocab Challenge Format

The add-on reads field 0 (front) as the question and field 1 (back) as the
correct answer. Wrong choices are pulled from other random cards in the same
deck. Works best with simple word ↔ meaning note types.
