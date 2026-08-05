# Chapter 31: A Simple Database — Files and Indexing

**What you'll learn:** How to treat a file as structured storage. Fixed-length records. Sequential scan vs. indexed lookup. The basic ideas behind real database systems, implemented with nothing more than files, arrays, and the memory primitives we already understand.

---

## From Editor to Database

The text editor project was about managing an in-memory document and presenting a view of it.

A database is about **persistent structured data** — records that live on disk, survive program restarts, and can be queried efficiently.

At its core, a database is just:
- A file (or set of files) containing records
- Code that knows how to find and manipulate those records according to some rules

Everything else (query languages, transactions, replication, etc.) is built on top of this foundation.

---

## Fixed-Length Records

The simplest persistent database uses **fixed-length records**.

Each record is exactly N bytes. If you know the record size, then:
- Record number K starts at byte offset `K * N` in the file.
- You can jump directly to any record without scanning.

This is the database equivalent of array indexing.

A record might contain:
- An integer ID
- A fixed-length name or key (padded with zeros or spaces)
- Some numeric fields
- Whatever else fits in the remaining space

Because everything is fixed size, the math is trivial and the code is easy to reason about.

---

## Sequential Scan

The most basic query is "read every record and check if it matches."

```ailang
offset = 0
WhileLoop LessThan(offset, file_size) {
    record = ReadFixedRecordAt(file, offset)
    IfCondition MatchesQuery(record) ThenBlock: {
        Process(record)
    }
    offset = Add(offset, RECORD_SIZE)
}
```

This is O(N) in the number of records. For small databases it is perfectly fine. For large ones it becomes painfully slow.

Sequential scan is the database equivalent of a linear search through an array.

---

## Indexing

To make lookups fast, we need an **index** — a separate data structure that lets us find records without scanning the whole file.

The classic simple index is a sorted array of (key, file_offset) pairs.

To look up a key:
1. Do a binary search on the index array (very fast).
2. When you find the matching entry, you now know the exact byte offset in the data file.
3. Jump directly to that offset and read the record.

Building the index:
- On startup (or when the database is opened), read the entire data file once and build the sorted index in memory.
- Or, maintain the index on disk as a separate file and keep it consistent with the data file.

This is the basic idea behind almost every indexing scheme:
- You pay some cost to build or maintain the index.
- You get much faster lookups in return.

---

## Trade-offs Made Visible

Implementing even this simple database makes several deep trade-offs concrete:

- **Space vs. time**: The index takes extra space (on disk or in memory) but buys speed.
- **Update cost**: When you insert, delete, or modify a record, you may need to update the index. Keeping them consistent is the hard part.
- **Durability**: If the program crashes while writing, the data file and index can become inconsistent. Real databases spend enormous effort on write-ahead logging, fsync, checksums, etc.
- **Query power**: With only a sorted index on one field, you can do efficient equality and range queries on that field. Anything else requires a full scan (or additional indexes).

Students who build this see directly why real database systems are so large and complex — not because the ideas are exotic, but because getting all the edge cases, performance, and durability right is extremely difficult.

---

## Hardware / OS Connection

Everything ultimately comes down to:
- `open`, `read`, `write`, `lseek` (or their AILang equivalents) system calls.
- The filesystem's block cache (which is why sequential scans can be surprisingly fast even on spinning disks).
- The cost of random I/O vs. sequential I/O (still one of the largest performance gaps in computing).
- Durability guarantees (when does `write` actually make it to stable storage?).

A student who has built even a toy database has a visceral understanding of why database people care so much about fsync, write barriers, and storage hardware characteristics.

---

## Possible Extensions

A minimal but very educational database project can grow in many directions:

- Multiple indexes (on different fields)
- Variable-length records (with an offset + length in the index)
- A simple query language (even just "field = value")
- Deletion (with tombstones or compaction)
- A write-ahead log for durability
- A B-tree index instead of a sorted array (much more realistic for large data)

Each extension forces the student to confront new design problems while staying grounded in the explicit model of files and memory they already understand.

---

## Why This Project Matters

By the time a student builds this, they have seen:

- How the hardware actually works (from the primer)
- How to manage memory explicitly
- How to build data structures from pointers and arrays
- How to talk to the operating system through files
- How to think about performance and trade-offs

A simple database is one of the best capstone projects for an explicit, ground-up computer science education because it ties almost everything together in a single, tangible artifact.

---

## Key Concepts

- Fixed-length records enable direct addressing by record number.
- Sequential scan is simple but O(N).
- An index (sorted array of key + offset) turns lookup into O(log N) plus one random I/O.
- Keeping data and indexes consistent under updates and crashes is the real engineering challenge.
- The performance characteristics of databases are direct consequences of the underlying storage hardware and operating system.

---

*Next: We close the main content with a look at how to participate in the broader AILang ecosystem and contribute to real systems built in the language.*