# Hexagram State Mapping / 卦象狀態映射

This document defines a safe public mapping from six-line hexagram representation to engineering state codes.

| Yao Line | Engineering Field | Description |
|---|---|---|
| Line 1 | source_class | source device or origin class |
| Line 2 | route_class | destination or service class |
| Line 3 | payload_class | data/event category |
| Line 4 | intent_class | behavior/risk category |
| Line 5 | authority_class | role and permission class |
| Line 6 | ttl_integrity | lifecycle and integrity class |

## Operators

| I-Ching Term | Engineering Operator |
|---|---|
| 錯卦 | bitwise complement |
| 綜卦 | bit order reverse |
| 變爻 | bit flip state transition |
| 本卦 | initial state |
| 之卦 | resulting state |
