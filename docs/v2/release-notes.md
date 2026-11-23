# PokerMind 2.0.0 — readable poker, authoritative results

PokerMind 2.0 makes the local four-seat Hold'em game easier to follow and control while preserving its trained AI and scientific evidence.

## Playing experience

- **Normal, Schnell and Sofort:** Normal highlights each bot for 1.25 seconds before its real decision, then holds the action for 1.75 seconds. Actual browser measurements were 3.03–3.05 seconds per bot action. Fast shortens the pauses; instant adds no deliberate waits.
- **Sequential real actions:** dealing, board cards, decisions and payouts advance through versioned server operations. The current player and actual action remain readable.
- **Stable controls:** persistent buttons, amount input, slider and presets stay disabled during foreign turns. Animation updates do not rebuild inputs or reset a draft.
- **Hands at each seat:** actual PokerKit descriptions appear beside the relevant player after settlement. Learning mode may reveal additional cards only after full payout; realistic mode retains normal concealment.
- **Central winner display:** a four-second Normal celebration followed by persistent results until the user starts the next hand. Actual gross receipts and net changes remain separate, with every split/side-pot recipient and an explicit fold-win reason.
- Responsive local visuals, optional synthesized sound, keyboard controls and reduced-motion support.

## Verification and frozen science

The suite has **114 tests: 94 Python + 20 JavaScript**. Local and independently extracted-package verification includes dependency and artifact checks, saved-model inference and real browser play. Existing evidence covers four viewports and true 200% Chrome zoom; rare split/side-pot and elimination states use labeled PokerKit fixtures. The PR and merged-main CI runs are linked in the attached verification manifest.

The original rules, Teacher, Random Forest, datasets/splits and evaluation results are preserved. The model still uses **54 allowed features and 200 trees**, trained on the frozen **20,024-decision** corpus. **78.70%** measures Teacher imitation, not hand-winning probability. The **176-session / 12,601-hand** evaluation is unchanged. This is not a claim of optimal poker.

## Install

Download `PokerMind-v2.0.0-cleaned.zip` and its `.sha256`, verify the checksum, extract, then follow the README. Python 3.11 and the pinned `requirements.txt` are required; no frontend build is needed. The cleaned ZIP contains the saved model, data, evaluation evidence, tests and documentation. No virtual environments, credentials or private study notes are included.

## Boundaries and previous release

Small windows may require vertical scrolling. Smartphones were emulated rather than physically tested. The application supports one local in-memory table and one server process; a server restart loses the game. The model does not learn during play. The project license remains an owner decision; this release invents no license.

**v1.0.0 remains available with its existing tag and assets unchanged.** Historical reports retain their original dates and measurements. See the README, `docs/v2/release.md`, and the attached verification manifest for reproducible commands and exact release provenance.
