# API9: preserve current images and cache exact observation history

Live API8 completed 7/8 levels in 248 actions but stopped at $51.284389 in token
charges. Its 1,256-check independent saved-evidence audit passed for the incomplete
attempt. A bounded compaction request succeeded with reported usage.

Controlled synthetic API comparisons found that repeated inline image inputs failed
to reuse the prefix despite unchanged earlier request items. Text-only controls hit
the cache. Merely switching image detail or using a single moving explicit boundary
did not resolve reuse. Keeping only the current screenshot on the wire and retaining
the latest four text boundaries yielded five consecutive cache hits, including after
older cache markers were removed. All probes and unsuccessful variants are preserved.

API9 supplies the current original-detail screenshot on every decision. Earlier
screenshots are not replayed: their exact hexadecimal grids, dimensions, colors and
component observations remain in the text history, with all tool results and opaque
reasoning. The runner already supplies every pixel in each decision context. The
provider now rejects an image without a complete exact grid before any paid request.
This is a disclosed multimodal history representation change; raw-100 performance
must be established by a fresh full API run. No image is uploaded to a new endpoint.

At most four recent text blocks receive explicit cache markers in a wire copy. Stored
text, tool and opaque items are unchanged. Only the current screenshot follows that
cacheable prefix. Compaction receives the text/opaque history; the latest exact
observation is restored explicitly before the next image-backed decision. Published
input/output reservation bounds remain unchanged. API context events record hashes
of retained items and wire input, image count, and cache-boundary count.

The solver instructions, tools, perception, memory, action dispatcher and raw-100
acceptance remain unchanged. API9 live score and full runtime/submission requirements
are NOT SATISFIED until supported by their own evidence.
