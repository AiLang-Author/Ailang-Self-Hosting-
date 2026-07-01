# Chapter 30: A Text Editor — Surfaces and Input

**What you'll learn:** How to handle raw keyboard input in a terminal. How to manage an in-memory text buffer. The difference between the logical document and the visible viewport. Basic cursor movement, scrolling, and editing.

---

## From Calculator to Editor

The calculator project was mostly about *parsing and evaluation* — turning text into structure and then computing with it.

A text editor is a different kind of project. It is about:

- Managing a dynamic, two-dimensional piece of data (lines of text)
- Handling input from a human in real time
- Presenting a *view* of that data on a limited screen
- Keeping the view and the data in sync as the user edits

It is one of the best projects for learning about state, invariants, and the gap between "what the program knows" and "what the user sees."

---

## Raw Terminal Input

Most programs that read from the terminal use "cooked" mode: the operating system buffers a line, handles backspace, and only delivers the line to the program when the user presses Enter.

For a real text editor, you need **raw mode**.

In raw mode:
- Every keypress is delivered to the program immediately.
- You see the actual bytes the keyboard sent (including arrow keys, which usually send escape sequences like `ESC [ A` for up arrow).
- You are responsible for echoing characters, handling backspace, etc.

Switching to raw mode is done with system calls (`tcgetattr` / `tcsetattr` on Unix-like systems, or equivalent on other platforms). The editor must remember the original terminal settings and restore them when it exits — otherwise the user's shell is left in a broken state.

---

## The Text Buffer

The core data structure is the document itself: a sequence of lines.

A simple representation is an array (or dynamic array / linked list) of strings, where each string is one line.

Basic operations the editor must support:
- Insert a character at the current cursor position
- Delete the character before or after the cursor
- Split a line when the user presses Enter
- Join two lines when the user presses Backspace at the beginning of a line
- Move the cursor up, down, left, right (with sensible edge behavior)

All of these operations must maintain the fundamental invariant: "the in-memory representation exactly matches what the user believes they have typed."

---

## The Viewport Problem

The screen is much smaller than most documents.

The editor must maintain a **viewport** — a window into the larger document:

- Which line is at the top of the screen?
- Which column is at the left edge?
- How do we scroll smoothly when the cursor moves?

This is a classic "model vs. view" problem. The full document is the model. The visible portion on screen is the view. The editor must keep them consistent as the user moves and edits.

Scrolling logic is surprisingly subtle once you want it to feel natural (especially when the user is moving the cursor quickly or when lines have very different lengths).

---

## Cursor Movement and State

The cursor position must be tracked in both:
- Logical coordinates (which line, which column within that line)
- Screen coordinates (row and column on the terminal)

These are not always the same, because of:
- Tab characters
- Multi-byte characters (especially with Unicode)
- Lines that are longer than the screen width (wrapping or horizontal scrolling)

Maintaining the mapping between logical and screen positions, while handling all the edge cases, is excellent practice for thinking precisely about state.

---

## Why This Project Is Valuable

A text editor forces the student to confront several deep ideas simultaneously:

- State that must remain consistent across multiple representations (document, cursor, viewport, screen)
- Event-driven input (the program spends most of its time waiting for the next key)
- The gap between the abstract document and its concrete presentation
- Error handling when the user does something unexpected
- Performance (a naive implementation can become sluggish on large files or fast typing)

It is also deeply satisfying: at the end of the project the student has a program they can actually use to edit its own source code.

---

## Possible Extensions

Once a basic editor works, natural extensions include:

- Search and replace
- Multiple buffers / tabs
- Syntax highlighting (which requires a simple lexer for the language being edited)
- Mouse support
- Configuration file
- Undo / redo (which forces a much more sophisticated model of the document state)

Each of these extensions teaches new lessons while building on the foundation already laid.

---

## Hardware / Systems Connection

The editor is one of the best places to see the full stack in action:

- Keyboard hardware → kernel input layer → terminal emulator → raw bytes delivered to the program via `read` system calls.
- The program's output goes through `write` calls, is interpreted by the terminal (ANSI escape codes for cursor movement, colors, etc.), and eventually becomes photons on the screen.
- All the memory management, data structures, and control flow the student has been learning are now in service of a program that feels "instant" to a human user.

This is systems programming made tangible.

---

## Key Concepts

- Raw vs. cooked terminal modes
- The document as a sequence of lines
- Viewport vs. full document
- Maintaining consistent state between model and view
- Event-driven programming in a terminal environment

---

*Next: We build something even more ambitious — a simple database that stores records in a file and supports both sequential scan and indexed lookup.*