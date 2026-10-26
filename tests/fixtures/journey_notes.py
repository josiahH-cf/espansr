"""Synthetic local journey target with an intentional gap, never product code.

Requirement: print unread note titles in input order without changing input.
The current candidate mistakenly includes read notes, so :user-journey should
document that gap and author a filtering spec, not silently implement it.
"""

import json
import sys


def titles(notes):
    return [note["title"] for note in notes]


if __name__ == "__main__":
    print(json.dumps(titles(json.loads(sys.argv[1]))))
