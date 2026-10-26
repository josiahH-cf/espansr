## BASIS

Target: the synthetic local notes CLI in `tests/fixtures/journey_notes.py`.
Its stated requirement is to print unread note titles in input order without
changing the input. The current candidate includes read notes. This example
shows the final output after that requirement is implemented.

SYNTHETIC input:

```json
[{"title": "Moon", "read": false}, {"title": "Sea", "read": true}, {"title": "Forest", "read": false}]
```

Assume valid records with a title and boolean read flag, as supplied here.
No account, persistent store or external service is involved.

## FINAL-STATE SAMPLE

PROJECTED completed CLI output:

```json
["Moon", "Forest"]
```

The person receives the two unread titles in input order. The original three
records remain unchanged. A list containing only read notes produces `[]`.

## REQUIREMENT TRACE

| Requirement | Projected result |
| --- | --- |
| Print unread titles | Moon and Forest appear; Sea is excluded. |
| Retain input order | Moon precedes Forest. |
| Preserve input | No record or read flag is written or modified. |

## LIMITS

The projected filter has not been implemented or executed by this sample.
The current fixture's observed output is `["Moon", "Sea", "Forest"]`; the
regression test executes that CLI separately. The final-state sample is an
illustrative model-authored projection, not proof of implementation, installation
or human acceptance. Invalid-record behavior is outside this fixture's stated
requirement. No runtime data, network calls or shared services are involved.
