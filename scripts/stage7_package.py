"""Build the Stage 7 deliverable with the existing byte-verifying archive utility."""
from stage6_package import build
from stage7_integrity import verify

if __name__ == '__main__':
    verify()
    build()
