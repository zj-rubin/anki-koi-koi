"""
vocab_bridge.py — vocab challenges with session-based card tracking.
"""

import random
import re
from typing import Optional

from anki.collection import Collection

QUESTION_PREFERRED = [
    'hanzi','chinese','japanese','kanji','tibetan','arabic','korean',
    'russian','german','french','spanish','italian','portuguese','dutch',
    'hebrew','turkish','hindi','thai','vietnamese','latin','greek',
    'word','term','front','target','vocab','vocabulary','expression',
    'phrase','character','kana','foreign','question',
]
ANSWER_PREFERRED = [
    'definition','meaning','translation','english','back','answer',
    'gloss','explanation','notes','note','description','native',
    'deutsch','français','español','italiano','português','usage','sense',
]


def _strip_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[sound:[^\]]+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _is_usable(text):
    if not text:
        return False
    if re.match(r'^\d+$', text):
        return False
    return True


class VocabSession:
    """
    Tracks card exposure within one game session.

    Key design:
    - `pending`: card currently being shown (not yet answered)
    - `seen`: cards answered correctly at least once this session
    - `wrong_queue`: cards answered wrong — come back sooner
    - `last_id`: last card shown — never shown twice in a row

    Pick priority:
      1. Due + unseen + not last
      2. Any unseen + not last
      3. Wrong queue + not last
      4. Full reset (cycle complete)
    """
    def __init__(self, all_ids, due_ids, card_to_note=None):
        self.all_ids = list(all_ids)
        self.due_ids = due_ids
        self.seen = set()
        self.wrong_queue = []
        self.pending = None
        self.last_id = None
        self.focus = 1       # 0=New, 1=Balanced, 2=Review
        self.pool_size = 20  # max unseen cards active at once
        # Maps card_id → note_id so we can mark all sibling cards seen together
        self.card_to_note = card_to_note or {}
        # Build reverse map: note_id → [card_ids]
        note_to_cards = {}  # dict[int,list[int]]
        for cid, nid in self.card_to_note.items():
            note_to_cards.setdefault(nid, []).append(cid)
        self.note_to_cards = note_to_cards
        random.shuffle(self.all_ids)

    def pick(self):
        """Return next card ID respecting pool_size, focus and priority."""
        def exclude(lst):
            return [c for c in lst if c != self.last_id]

        def choose(pool):
            chosen = random.choice(pool)
            self.pending = chosen
            self.last_id = chosen
            return chosen

        # Active pool: only the first pool_size unseen cards are in play
        all_unseen = [c for c in self.all_ids if c not in self.seen]
        unseen = all_unseen[:self.pool_size]  # windowed
        seen_list = [c for c in self.all_ids if c in self.seen]

        # focus=0 (New): prioritise unseen heavily, only use review if no new cards
        # focus=1 (Balanced): due unseen > any unseen > wrong queue
        # focus=2 (Review): prioritise seen/wrong cards, only use new if nothing else

        if self.focus == 0:
            # New focus: unseen due > any unseen > wrong queue > reset
            pool = exclude([c for c in unseen if c in self.due_ids])
            if pool: return choose(pool)
            pool = exclude(unseen)
            if pool: return choose(pool)
            pool = exclude(self.wrong_queue)
            if pool: return choose(pool)

        elif self.focus == 1:
            # Balanced: unseen due > any unseen > wrong queue
            pool = exclude([c for c in unseen if c in self.due_ids])
            if pool: return choose(pool)
            pool = exclude(unseen)
            if pool: return choose(pool)
            pool = exclude(self.wrong_queue)
            if pool: return choose(pool)

        else:  # focus == 2 (Review)
            # Review focus: wrong queue > seen due > any seen > unseen due > any unseen
            pool = exclude(self.wrong_queue)
            if pool: return choose(pool)
            pool = exclude([c for c in seen_list if c in self.due_ids])
            if pool: return choose(pool)
            pool = exclude(seen_list)
            if pool: return choose(pool)
            pool = exclude([c for c in unseen if c in self.due_ids])
            if pool: return choose(pool)
            pool = exclude(unseen)
            if pool: return choose(pool)

        # Active window exhausted — check if there are more unseen cards globally
        global_unseen = [c for c in self.all_ids if c not in self.seen]
        if global_unseen:
            # Advance window: next batch of unseen cards
            print("[Hanafuda] Pool window exhausted, advancing to next %d cards" % self.pool_size)
            unseen = global_unseen[:self.pool_size]
            pool = exclude(unseen) or unseen
            return choose(pool) if pool else None
        # Full deck seen — reset everything and start over
        print("[Hanafuda] Full deck seen (%d cards). Restarting." % len(self.all_ids))
        self.seen = set()
        self.wrong_queue = []
        random.shuffle(self.all_ids)
        pool = exclude(self.all_ids) or self.all_ids
        return choose(pool) if pool else None

    def record_correct(self, card_id):
        # Mark this card and all sibling cards (same note) as seen
        note_id = self.card_to_note.get(card_id)
        siblings = self.note_to_cards.get(note_id, [card_id]) if note_id else [card_id]
        for cid in siblings:
            self.seen.add(cid)
            if cid in self.wrong_queue:
                self.wrong_queue.remove(cid)
        self.pending = None

    def record_wrong(self, card_id):
        if card_id not in self.wrong_queue:
            self.wrong_queue.append(card_id)
        # Don't mark siblings wrong — only this specific card
        self.pending = None

    @property
    def stats(self):
        return (f"seen {len(self.seen)}/{len(self.all_ids)}, "
                f"wrong queue: {len(self.wrong_queue)}, "
                f"last: {self.last_id}")


def get_field_names(col, deck_id=None):
    try:
        if deck_id is not None:
            deck = col.decks.get(deck_id)
            if not deck:
                return []
            card_ids = list(col.find_cards(f'"deck:{deck["name"]}"'))
        else:
            card_ids = list(col.find_cards(''))
        if not card_ids:
            return []
        mid_counts = {}
        for cid in card_ids[:200]:
            try:
                mid = col.get_card(cid).note().mid
                mid_counts[mid] = mid_counts.get(mid, 0) + 1
            except Exception:
                continue
        if not mid_counts:
            return []
        model = col.models.get(max(mid_counts, key=mid_counts.get))
        return [f['name'] for f in model['flds']] if model else []
    except Exception as e:
        print(f"[Hanafuda] get_field_names error: {e}")
        return []


def auto_detect_fields(field_names):
    if len(field_names) < 2:
        return 0, 1
    lower = [f.lower() for f in field_names]
    q_idx = next(
        (i for pref in QUESTION_PREFERRED
         for i, f in enumerate(lower) if pref in f), 0)
    a_idx = next(
        (i for pref in ANSWER_PREFERRED
         for i, f in enumerate(lower) if pref in f and i != q_idx),
        next((i for i in range(len(field_names)) if i != q_idx), 1))
    return q_idx, a_idx


def _get_fields_from_note(note, q_idx, a_idx):
    fields = note.fields
    if q_idx < 0 or q_idx >= len(fields) or a_idx < 0 or a_idx >= len(fields):
        return '', ''
    return _strip_html(fields[q_idx]), _strip_html(fields[a_idx])


def get_decks(col):
    decks = []
    for deck in col.decks.all_names_and_ids():
        decks.append({'id': deck.id, 'name': deck.name})
    return sorted(decks, key=lambda d: d['name'])


def build_session(col, deck_id=None):
    try:
        if deck_id is not None:
            deck = col.decks.get(deck_id)
            if not deck:
                return None
            all_ids = list(col.find_cards(f'"deck:{deck["name"]}"'))
            due_ids = set(col.find_cards(f'"deck:{deck["name"]}" is:due'))
        else:
            all_ids = list(col.find_cards(''))
            due_ids = set(col.find_cards('is:due'))
        if not all_ids:
            return None
        # Build card→note map to group sibling cards
        card_to_note = {}
        for cid in all_ids:
            try:
                card_to_note[cid] = col.get_card(cid).nid
            except Exception:
                pass
        # Deduplicate: keep only one card per note in the pool
        seen_notes = set()
        deduped_ids = []
        for cid in all_ids:
            nid = card_to_note.get(cid)
            if nid is None or nid not in seen_notes:
                deduped_ids.append(cid)
                if nid: seen_notes.add(nid)
        print(f"[Hanafuda] New session: {len(deduped_ids)} unique notes "
              f"({len(all_ids)} cards total), {len(due_ids)} due")
        return VocabSession(deduped_ids, due_ids, card_to_note)
    except Exception as e:
        print(f"[Hanafuda] build_session error: {e}")
        return None


def get_challenge(col, session, n_choices=4, q_field=-1, a_field=-1, deck_id=None):

    # Resolve field indices — use stored values, only auto-detect if truly unset
    if q_field < 0 or a_field < 0:
        field_names = get_field_names(col, deck_id)
        if not field_names:
            print("[Hanafuda] No field names found")
            return None
        auto_q, auto_a = auto_detect_fields(field_names)
        if q_field < 0:
            q_field = auto_q
        if a_field < 0:
            a_field = auto_a
        print(f"[Hanafuda] Using fields Q=[{q_field}] A=[{a_field}]")

    # Get FULL card pool for wrong-answer choices (not deduplicated session pool)
    if deck_id is not None:
        deck = col.decks.get(deck_id)
        all_ids = list(col.find_cards(f'"deck:{deck["name"]}"')) if deck else []
    else:
        all_ids = list(col.find_cards(''))
    # Session pool for picking the target card
    session_pool = session.all_ids if (session and session.all_ids) else all_ids

    if len(all_ids) < n_choices:
        print(f"[Hanafuda] Not enough cards: {len(all_ids)}")
        return None

    # Pick target card
    target_id = None
    question = ''
    correct = ''

    if session:
        tried = set()
        for attempt in range(min(20, len(session_pool))):
            cid = session.pick()
            if cid is None:
                break
            if cid in tried:
                # Picked same card again — mark seen to advance pool
                session.seen.add(cid)
                continue
            tried.add(cid)
            try:
                note = col.get_card(cid).note()
                q, a = _get_fields_from_note(note, q_field, a_field)
                if _is_usable(q) and _is_usable(a):
                    target_id = cid
                    question = q
                    correct = a
                    break
                else:
                    # Unusable card — mark seen so we skip it next time
                    print(f"[Hanafuda] Card {cid} unusable with q={q_field} a={a_field}: q='{q}' a='{a}'")
                    session.seen.add(cid)
            except Exception as e:
                print(f"[Hanafuda] Card {cid} error: {e}")
                session.seen.add(cid)

    # Fallback: random from full pool
    if target_id is None:
        print("[Hanafuda] Falling back to random pick")
        for cid in random.sample(all_ids, min(50, len(all_ids))):
            try:
                note = col.get_card(cid).note()
                q, a = _get_fields_from_note(note, q_field, a_field)
                if _is_usable(q) and _is_usable(a):
                    target_id = cid
                    question = q
                    correct = a
                    break
            except Exception:
                continue

    if target_id is None:
        print(f"[Hanafuda] No usable card found (q={q_field}, a={a_field})")
        return None

    # Build wrong choices
    other_ids = [c for c in all_ids if c != target_id]
    random.shuffle(other_ids)
    wrong_choices = []
    for cid in other_ids:
        if len(wrong_choices) >= n_choices - 1:
            break
        try:
            note = col.get_card(cid).note()
            _, ans = _get_fields_from_note(note, q_field, a_field)
            if _is_usable(ans) and ans != correct and ans not in wrong_choices:
                wrong_choices.append(ans)
        except Exception:
            continue

    if len(wrong_choices) < n_choices - 1:
        print(f"[Hanafuda] Not enough distinct answers: {len(wrong_choices)}")
        return None

    choices = wrong_choices[:n_choices - 1] + [correct]
    random.shuffle(choices)

    if session:
        print(f"[Hanafuda] Challenge ({session.stats}): "
              f"Q='{question[:30]}' A='{correct[:30]}'")

    # Get note_id from the card we already loaded (avoid second DB fetch)
    try:
        note_id = col.get_card(target_id).nid
    except Exception:
        note_id = 0
    return {
        'question': question,
        'answer': correct,
        'choices': choices,
        'card_id': target_id,
        'note_id': note_id,
        'is_due': bool(session and target_id in session.due_ids),
    }


def record_answer(col, card_id, ease):
    try:
        card = col.get_card(card_id)
        col.sched.reset_card(card)
        col.sched.answer_card(card, ease)
        print(f"[Hanafuda] Recorded: card={card_id} ease={ease}")
        return True
    except Exception as e:
        print(f"[Hanafuda] record_answer failed: {e}")
        return False
